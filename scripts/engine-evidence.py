"""Generate integration examples and golden evidence by executing the real API/core.

Run with the backend dependencies installed: python scripts/engine-evidence.py
The temporary database is isolated; no operator credentials enter the outputs.
"""
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from fastapi.testclient import TestClient
from app.main import app
from app.sandbox.engine import apply_command, build_scenario, canonical, capture_state, digest, initial_state, restore_state
from app.sandbox.models import Command, ScenarioConfig
from app.sandbox.control import tick_experiment, read as read_job


def main():
    output = ROOT / 'docs' / 'examples' / 'sandbox'
    output.mkdir(parents=True, exist_ok=True)
    transcript = []
    previous = {key: os.environ.get(key) for key in ('PULSE_RUNTIME_TOKEN', 'PULSE_RUNTIME_TOKENS', 'PULSE_RUNTIME_DB_PATH', 'PULSE_RUNTIME_DRIVER')}
    try:
        with tempfile.TemporaryDirectory(prefix='pulse-engine-evidence-') as directory:
            os.environ['PULSE_RUNTIME_TOKEN'] = 'temporary-test-operator-token-32-characters'
            os.environ.pop('PULSE_RUNTIME_TOKENS', None)
            os.environ['PULSE_RUNTIME_DRIVER'] = '0'
            os.environ['PULSE_RUNTIME_DB_PATH'] = str(Path(directory) / 'runtime.sqlite')
            with TestClient(app) as client:
                def request(method, path, body=None):
                    response = client.request(method, path, json=body, headers={
                        'Authorization': 'Bearer temporary-test-operator-token-32-characters'})
                    if response.status_code != 200:
                        raise RuntimeError(response.text)
                    transcript.append({'method': method, 'path': path, 'request': body, 'response': response.json()})
                    return response.json()

                scenario = request('POST', '/api/sandbox/scenarios', {'seed': 7, 'duration_seconds': 120})
                root = request('POST', '/api/sandbox/sessions', {'operation_id': 'example-create', 'scenario_id': scenario['scenario_id']})
                route = '/api/sandbox/sessions/' + root['session_id']
                root = request('POST', route + '/commands', {'operation_id': 'example-step', 'expected_revision': 0, 'kind': 'step', 'ticks': 30})
                root = request('POST', route + '/commands', {'operation_id': 'example-save', 'expected_revision': 1, 'kind': 'checkpoint'})
                request('GET', '/api/sandbox/checkpoints/' + root['checkpoint_id'])
                branch = request('POST', '/api/sandbox/checkpoints/' + root['checkpoint_id'] + '/restore',
                                 {'operation_id': 'example-fork', 'expected_revision': 2})
                child_route = '/api/sandbox/sessions/' + branch['session_id']
                request('POST', child_route + '/commands', {'operation_id': 'example-press', 'expected_revision': 2,
                        'kind': 'intervene', 'team_id': 'home', 'field': 'pressing', 'value': 100, 'requested_tick': 30})
                request('POST', child_route + '/commands', {'operation_id': 'example-finish', 'expected_revision': 3, 'kind': 'step', 'ticks': 90})
                request('GET', child_route + '/events?cursor=1&limit=3')
                manifest = request('GET', child_route + '/manifest')
                assert request('POST', '/api/sandbox/verify', manifest)['verified']
                (output / 'experiment.json').write_text(canonical(manifest) + '\n', encoding='utf-8')
                # The manifest has its own file; keep the route transcript compact.
                transcript[-1]['request'] = '<contents of experiment.json>'
                transcript[-2]['response'] = '<contents of experiment.json>'
                (output / 'journey.json').write_text(json.dumps(transcript, indent=2) + '\n', encoding='utf-8')
                experiment = request('POST', '/api/sandbox/experiments', {'operation_id': 'example-experiment',
                    'checkpoint_id': root['checkpoint_id'], 'expected_revision': 2, 'trials': 2, 'horizon': 60,
                    'baseline': [], 'variation': [{'team_id': 'home', 'field': 'pressing', 'value': 100}]})
                for _ in range(100):
                    tick_experiment('operator', experiment['experiment_id'])
                    if read_job('experiments', 'operator', experiment['experiment_id'])[1].status == 'completed':
                        break
                comparison = request('GET', '/api/sandbox/experiments/' + experiment['experiment_id'] + '/comparison')
                bundle = request('GET', '/api/sandbox/experiments/' + experiment['experiment_id'] + '/manifest')
                assert request('POST', '/api/sandbox/experiments/verify', bundle)['verified']
                (output / 'forkcast.json').write_text(canonical(bundle) + '\n', encoding='utf-8')
                (output / 'comparison.json').write_text(canonical(comparison) + '\n', encoding='utf-8')
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    state = initial_state(build_scenario(ScenarioConfig(seed=7)))
    start = time.perf_counter()
    while state.tick < 5400:
        state = apply_command(state, Command(operation_id=f'op-{state.revision}', expected_revision=state.revision,
                                             kind='step', ticks=300))
    elapsed = time.perf_counter() - start
    start = time.perf_counter()
    snapshot = capture_state(state)
    capture_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    assert restore_state(snapshot) == state
    restore_ms = (time.perf_counter() - start) * 1000
    golden = {'seed': 7, 'duration_seconds': 5400, 'command_ticks': 300, 'commands': 18,
              'state_hash': digest(state), 'event_hash': digest(state.events), 'events': len(state.events), 'score': state.score}
    (output / 'golden.json').write_text(json.dumps(golden, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({**golden, 'python': platform.python_version(), 'system': platform.system(),
                      'fulltime_ms': round(elapsed * 1000, 2), 'capture_ms': round(capture_ms, 2),
                      'restore_ms': round(restore_ms, 2), 'snapshot_bytes': len(canonical(snapshot))}, indent=2))


if __name__ == '__main__':
    main()
