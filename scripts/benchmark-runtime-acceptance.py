"""Bounded local checkpoint/ForkCast measurements using disposable SQLite only."""
import argparse
import json
import os
import platform
import secrets
import sys
import tempfile
import tracemalloc
from pathlib import Path
from statistics import median
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.sandbox import storage, control
from app.sandbox.engine import build_scenario, canonical
from app.sandbox.models import Command, ScenarioConfig
from app.sandbox.experiments import bundle, verify_bundle

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--iterations', type=int, default=3)
args = parser.parse_args()
if not 1 <= args.iterations <= 5:
    parser.error('iterations must be between 1 and 5 to stay within runtime quotas')

def timed(operation):
    start = perf_counter()
    value = operation()
    return value, (perf_counter()-start)*1000

def summary(values):
    return {'median_ms': round(median(values),3), 'maximum_ms':round(max(values),3), 'samples':len(values)}

owner = 'acceptance-benchmark'
with tempfile.TemporaryDirectory(prefix='pulse-runtime-benchmark-') as directory:
    os.environ['PULSE_RUNTIME_DB_PATH'] = str(Path(directory)/'runtime.sqlite')
    os.environ['PULSE_RUNTIME_DRIVER'] = '0'
    scenario = storage.save_scenario(owner, build_scenario(ScenarioConfig(seed=7)))
    receipt = storage.create_session(owner,'checkpoint-benchmark',scenario.scenario_id)
    view = storage.get_runtime(owner,receipt.session_id)
    checkpoints = []
    for tick in (0,2700,5400):
        while view.tick < tick:
            receipt = storage.mutate(owner,view.session_id,Command(operation_id=f'step-{view.revision}',expected_revision=view.revision,kind='step',ticks=min(300,tick-view.tick)))
            view = storage.get_runtime(owner,receipt.session_id)
        save,restore,sizes = [],[],[]
        for index in range(args.iterations):
            receipt,elapsed = timed(lambda: storage.mutate(owner,view.session_id,Command(operation_id=f'save-{tick}-{index}',expected_revision=view.revision,kind='checkpoint')))
            save.append(elapsed)
            checkpoint = storage.get_checkpoint(owner,receipt.checkpoint_id)
            sizes.append(len(canonical(checkpoint.snapshot).encode('utf8')))
            branch,elapsed = timed(lambda: storage.create_session(owner,f'restore-{tick}-{index}',checkpoint_id=checkpoint.checkpoint_id,expected_revision=checkpoint.revision))
            restore.append(elapsed)
            assert storage.get_runtime(owner,branch.session_id).state_hash == checkpoint.snapshot.state_hash
            view = storage.get_runtime(owner,view.session_id)
        checkpoints.append({'tick':tick,'events':view.event_cursor,'snapshot_bytes':max(sizes),'save':summary(save),'restore':summary(restore)})
    before = view.state_hash
    history = []
    for _ in range(args.iterations):
        result,elapsed = timed(lambda: storage.history_at(owner,view.session_id,5399))
        assert result['snapshot'].state.tick == 5399
        history.append(elapsed)
    assert storage.get_runtime(owner,view.session_id).state_hash == before
    root = storage.create_session(owner,'trial-benchmark',scenario.scenario_id)
    root = storage.mutate(owner,root.session_id,Command(operation_id='trial-checkpoint',expected_revision=root.revision,kind='checkpoint'))
    experiments = []
    for trials in (1,3):
        samples,peaks = [],[]
        for index in range(args.iterations):
            tracemalloc.start()
            start = perf_counter()
            experiment = control.create_experiment(owner,control.ExperimentRequest(operation_id=f'trial-{trials}-{index}',checkpoint_id=root.checkpoint_id,expected_revision=root.revision,trials=trials,horizon=120,variation=[control.Change(team_id='home',field='pressing',value=90)]))
            for _ in range(150):
                control.tick_experiment(owner,experiment.experiment_id)
                experiment = control.read('experiments',owner,experiment.experiment_id)[1]
                if experiment.status not in ('queued','running'):
                    break
            samples.append((perf_counter()-start)*1000)
            peaks.append(tracemalloc.get_traced_memory()[1]); tracemalloc.stop()
            assert experiment.status == 'completed'
            assert verify_bundle(bundle(owner,experiment.experiment_id)).verified
            assert storage.get_runtime(owner,root.session_id).state_hash == root.state_hash
        experiments.append({'trials':trials,'horizon':120,'execution_with_tracemalloc':summary(samples),'maximum_traced_python_bytes':max(peaks)})
    # Exercise real HTTP validation/auth/serialization in-process, without a port.
    from fastapi.testclient import TestClient
    from app.main import app
    token = secrets.token_urlsafe(32)
    os.environ['PULSE_RUNTIME_TOKENS'] = json.dumps({owner: token})
    headers = {'Authorization': 'Bearer ' + token}
    current = storage.create_session(owner, 'control-benchmark', scenario.scenario_id)
    for index in range(9):
        current = storage.mutate(owner, current.session_id, Command(operation_id=f'control-advance-{index}',
            expected_revision=current.revision, kind='step', ticks=300))
    route = f'/api/sandbox/sessions/{current.session_id}'
    acknowledgments, applications, verifications = [], [], []
    with TestClient(app) as client:
        for index in range(20):
            response, elapsed = timed(lambda: client.post(route+'/commands', headers=headers, json={
                'operation_id': f'press-{index}', 'expected_revision': current.revision, 'kind': 'intervene',
                'requested_tick': current.tick, 'team_id': 'home', 'field': 'pressing', 'value': 100 if index % 2 == 0 else 0}))
            assert response.status_code == 200, response.text
            acknowledgments.append(elapsed)
            revision = response.json()['revision']
            response, elapsed = timed(lambda: client.post(route+'/commands', headers=headers, json={
                'operation_id': f'control-tick-{index}', 'expected_revision': revision, 'kind': 'step', 'ticks': 1}))
            assert response.status_code == 200, response.text
            applications.append(elapsed)
            current = storage.get_runtime(owner, current.session_id)
            assert current.state.interventions[-1].result == 'applied'
            assert current.state.interventions[-1].effective_tick == current.tick
        manifest = client.get(route+'/manifest', headers=headers).json()
        for _ in range(5):
            response, elapsed = timed(lambda: client.post('/api/sandbox/verify', headers=headers, json=manifest))
            assert response.status_code == 200 and response.json()['verified'], response.text
            verifications.append(elapsed)
    controls = {'method': 'warm TestClient HTTP including auth/validation/serialization; seed7; ticks2700-2720; no network latency guarantee',
                'intervention_ack': summary(acknowledgments), 'next_tick_request': summary(applications),
                'manifest_verify': summary(verifications), 'manifest_bytes': len(canonical(manifest).encode('ascii'))}
    print(json.dumps({'python':platform.python_version(),'os':platform.platform(),'processor':platform.processor(),
        'method':'isolated temporary SQLite; in-process storage calls; warm process; not HTTP or deployment latency. Experiment timings include tracemalloc instrumentation; traced allocations are not process RSS.',
        'controls':controls,'checkpoints':checkpoints,'read_only_history_5399':summary(history),'experiments':experiments},indent=2))
