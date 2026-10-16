"""Reproducible local, in-process API benchmark; no external services."""
import argparse
import json
import platform
import sys
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi.testclient import TestClient
from app.main import app

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--iterations", type=int, default=30)
args = parser.parse_args()
if not 5 <= args.iterations <= 1000:
    parser.error("iterations must be between 5 and 1000")
client = TestClient(app)
url = "/api/matches/comeback-1107/pass-difficulty?at_second=5400&limit=200"
client.get(url).raise_for_status()  # warm the deterministic fixture cache
samples = []
for _ in range(args.iterations):
    start = perf_counter()
    response = client.get(url)
    response.raise_for_status()
    samples.append((perf_counter() - start) * 1000)
ordered = sorted(samples)
print(json.dumps({
    "environment": {"python": platform.python_version(), "os": platform.platform(),
                    "processor": platform.processor()},
    "method": "warm TestClient in-process GET; includes DTO construction and JSON serialization",
    "iterations": len(samples), "passes": len(response.json()["items"]),
    "response_bytes": len(response.content), "median_ms": round(median(samples), 3),
    "p95_ms": round(ordered[ceil(len(ordered) * .95) - 1], 3),
}, indent=2))
