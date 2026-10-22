"""Bounded offline measurements; prints evidence without rewriting golden fixtures.

python scripts/sandbox-benchmark.py --samples 5
Requires backend/requirements.txt. No databases, credentials or providers used.
"""
import argparse
import cProfile
import json
import platform
import pstats
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from app.sandbox.engine import apply_command, build_scenario, digest, initial_state, presets
from app.sandbox.models import Command, ENGINE_VERSION, SCHEMA_VERSION, RNG_ALGORITHM, ScenarioConfig


def finish(config):
    state = initial_state(build_scenario(config))
    while state.tick < config.duration_seconds:
        state = apply_command(state, Command(operation_id=f'benchmark-{state.revision}',
            expected_revision=state.revision, kind='step', ticks=min(300, config.duration_seconds - state.tick)))
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=5, choices=range(1, 21))
    args = parser.parse_args()
    maximal = ScenarioConfig(preset='custom', seed=2147483647)
    for team in (maximal.home, maximal.away):
        team.name = 'F' * 80
        for player in team.players:
            player.name = 'F' * 80
            player.passing = player.finishing = player.defending = 100
    construction = {}
    for name, config in [('default', ScenarioConfig()), ('maximal_names_attributes', maximal)]:
        build_scenario(config)  # warm validation/model construction outside measured samples
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            build_scenario(config)
            times.append((time.perf_counter() - start) * 1000)
        construction[name] = {'samples': len(times), 'median_ms': statistics.median(times),
                              'p95_ms': sorted(times)[949]}
    rows = []
    for name, template in presets().items():
        finish(template.model_copy(update={'seed': 2_147_483_647}, deep=True))  # warm this preset; discard output
        for seed in range(args.samples):
            config = template.model_copy(update={'seed': seed}, deep=True)
            start = time.perf_counter()
            state = finish(config)
            elapsed = time.perf_counter() - start
            rows.append({'preset': name, 'seed': seed, 'tick': state.tick, 'events': len(state.events),
                         'seconds': elapsed, 'events_per_second': len(state.events) / elapsed,
                         'event_hash': digest(state.events)})
    profile = cProfile.Profile()
    profile.runcall(finish, ScenarioConfig())
    decision = next(entry for key, entry in pstats.Stats(profile).stats.items()
                    if key[2] == 'decision' and key[0].endswith('engine.py'))
    print(json.dumps({'python': platform.python_version(), 'platform': platform.system(),
        'engine_version': ENGINE_VERSION, 'schema_version': SCHEMA_VERSION, 'rng_algorithm': RNG_ALGORITHM,
        'construction': construction, 'fulltime_runs': rows,
        'warmup_runs_per_preset': 1,
        'warmup_runs_per_construction_case': 1,
        'profiled_decisions': {'calls': decision[1], 'cumulative_seconds': decision[3],
                              'mean_microseconds': decision[3] / decision[1] * 1_000_000},
        'limitations': 'Local wall times include validation/copying; profiler adds overhead. No deployment SLA or real-football accuracy claim.'}, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
