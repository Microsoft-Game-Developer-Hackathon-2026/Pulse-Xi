"""Measure a real paired comparison in isolated SQLite; no HTTP or hosted AI."""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--application-root', type=Path, default=ROOT)
    args = parser.parse_args()
    application_root = args.application_root.resolve()
    if not (application_root / "backend/app/sandbox/experiments.py").is_file():
        parser.error("application-root must identify a Pulse-Xi checkout")
    sys.path.insert(0, str(application_root / "backend"))
    with tempfile.TemporaryDirectory(prefix='pulse-comparison-profile-') as folder:
        os.environ['PULSE_RUNTIME_DB_PATH'] = str(Path(folder) / 'runtime.sqlite')
        os.environ['PULSE_DB_PATH'] = str(Path(folder) / 'library.sqlite')
        os.environ['PULSE_RUNTIME_DRIVER'] = '0'
        from app.sandbox import storage, control, experiments, manifest
        from app.sandbox.engine import build_scenario, digest
        from app.sandbox.models import ScenarioConfig, Command
        from app.sandbox.control import ExperimentRequest, Change

        scenario = storage.save_scenario('benchmark', build_scenario(ScenarioConfig(seed=7, duration_seconds=1800)))
        state = storage.create_session('benchmark', 'create', scenario.scenario_id)
        for index in range(4):
            state = storage.mutate('benchmark', state.session_id, Command(operation_id=f'step-{index}',
                expected_revision=state.revision, kind='step', ticks=300))
        state = storage.mutate('benchmark', state.session_id, Command(operation_id='checkpoint',
            expected_revision=state.revision, kind='checkpoint'))
        job = control.create_experiment('benchmark', ExperimentRequest(operation_id='experiment',
            checkpoint_id=state.checkpoint_id, expected_revision=state.revision, trials=2, horizon=300,
            variation=[Change(team_id='home', field='pressing', value=100)]))
        for _ in range(150):
            control.tick_experiment('benchmark', job.experiment_id)
            job = control.read('experiments', 'benchmark', job.experiment_id)[1]
            if job.status == 'completed':
                break
        assert job.status == 'completed'
        calls = {'comparison_replay': 0, 'independent_verifier_replay': 0, 'historical_boundary_replay': 0}
        real_comparison_apply, real_manifest_apply, real_history_apply = experiments.apply_command, manifest.apply_command, storage.apply_command

        def comparison_apply(*values):
            calls['comparison_replay'] += 1
            return real_comparison_apply(*values)

        def verifier_apply(*values):
            calls['independent_verifier_replay'] += 1
            return real_manifest_apply(*values)

        def history_apply(*values):
            calls['historical_boundary_replay'] += 1
            return real_history_apply(*values)

        experiments.apply_command, manifest.apply_command, storage.apply_command = comparison_apply, verifier_apply, history_apply
        samples = []
        try:
            for _ in range(3):
                calls.update(comparison_replay=0, independent_verifier_replay=0, historical_boundary_replay=0)
                start = time.perf_counter()
                result = experiments.comparison('benchmark', job.experiment_id)
                elapsed = (time.perf_counter() - start) * 1000
                samples.append(dict(milliseconds=elapsed, replay_calls=dict(calls), comparison_hash=digest(result)))
        finally:
            experiments.apply_command, manifest.apply_command, storage.apply_command = real_comparison_apply, real_manifest_apply, real_history_apply
        assert len({row['comparison_hash'] for row in samples}) == 1
        assert storage.get_runtime('benchmark', state.session_id).state_hash == state.state_hash
        output = dict(source_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=application_root, text=True).strip(),
            experiment_implementation_hash=experiments.experiment_implementation_hash(),
            os=platform.platform(), cpu=platform.processor(), python=platform.python_version(),
            seed=7, duration=1800, checkpoint_tick=1200, horizon=300, paired_trials=2,
            concurrency=1, samples=samples, p50_ms=statistics.median(row['milliseconds'] for row in samples),
            limitations='Three sequential in-process samples; temporary stores; uncontrolled background load; not HTTP/P95/GPU/provider measurement.')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2), encoding='utf-8')
        print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
