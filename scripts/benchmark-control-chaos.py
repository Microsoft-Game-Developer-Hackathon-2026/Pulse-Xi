"""Reproducible in-process Control vs Chaos query benchmark."""
import argparse
import json
import os
import platform
import sys
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.analytics import MAX_CONTROL_CHAOS_EVENTS, control_chaos_at
from app.evidence import verify_control_turning_point
from app.models import MatchEvent
from app.simulator import generate

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--iterations", type=int, default=30)
parser.add_argument("--synthetic-events", type=int, default=10_000)
args = parser.parse_args()
if not 5 <= args.iterations <= 1000:
    parser.error("iterations must be between 5 and 1000")
if not 1 <= args.synthetic_events <= MAX_CONTROL_CHAOS_EVENTS:
    parser.error(f"synthetic-events must be between 1 and {MAX_CONTROL_CHAOS_EVENTS}")

match, fixture_events = generate("comeback")


def synthetic_events(count: int) -> list[MatchEvent]:
    values = []
    for index in range(count):
        second = min(5399, index * 5400 // count)
        template = fixture_events[index % len(fixture_events)]
        values.append(template.model_copy(update={
            "event_id": f"bench-{index + 1}",
            "sequence": index + 1,
            "match_second": second,
            "period": 1 if second <= 2700 else 2,
        }))
    return values


def benchmark(events: list[MatchEvent]) -> dict:
    def query():
        packet = control_chaos_at(match, events, 5400, 900)
        for claim in packet.interpretation.turning_points:
            if not verify_control_turning_point(claim, match, events, 5400, 900):
                raise RuntimeError(f"evidence verification failed: {claim.evidence_id}")
        return packet

    query()
    samples = []
    for _ in range(args.iterations):
        start = perf_counter()
        query()
        samples.append((perf_counter() - start) * 1000)
    ordered = sorted(samples)
    return {
        "input_events": len(events),
        "window_seconds": 900,
        "iterations": len(samples),
        "median_ms": round(median(samples), 3),
        "p95_ms": round(ordered[ceil(len(ordered) * .95) - 1], 3),
    }


large_events = synthetic_events(args.synthetic_events)
print(json.dumps({
    "environment": {
        "python": platform.python_version(),
        "os": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "logical_cpus": os.cpu_count(),
    },
    "method": "Warm in-process analytics plus turning-point verification; excludes HTTP and JSON serialization.",
    "fixture": benchmark(fixture_events),
    "bounded_synthetic": benchmark(large_events),
}, indent=2))
