"""Loopback HTTP benchmark. Disposable stores, no provider calls or private data."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=20)
    args = parser.parse_args()
    if not 5 <= args.samples <= 100:
        parser.error('samples must be between 5 and 100')
    with tempfile.TemporaryDirectory(prefix='pulse-api-benchmark-') as folder:
        env = {k: v for k, v in os.environ.items() if not k.startswith(('PULSE_', 'FOUNDRY_'))}
        env.update(PULSE_ENABLE_FOUNDRY='false', PULSE_DB_PATH=str(Path(folder) / 'events.sqlite'),
                   PULSE_RUNTIME_DB_PATH=str(Path(folder) / 'runtime.sqlite'))
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        with open(Path(folder) / 'server.log', 'w') as log:
            process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
                '--app-dir', str(ROOT / 'backend'), '--host', '127.0.0.1', '--port', str(port)],
                cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=30) as client:
                    for _ in range(150):
                        try:
                            if client.get('/health').status_code == 200:
                                break
                        except httpx.RequestError:
                            pass
                        time.sleep(.1)
                    else:
                        raise RuntimeError('Server startup failed')
                    match = client.get('/api/matches').json()[0]['match_id']
                    base = f'/api/matches/{match}'
                    endpoints = [('health', '/health'), ('matches', '/api/matches'),
                        ('match', base), ('events', base + '/events'),
                        ('state', base + '/state?at_second=3500'),
                        ('metrics', base + '/metrics?at_second=3500'),
                        ('tactics', base + '/tactics?at_second=3500'),
                        ('insights', base + '/insights'), ('overlays', base + '/overlays'),
                        ('control-chaos', base + '/control-chaos?at_second=3500&window_seconds=300'),
                        ('recap', base + '/recap?at_second=3500&persona=analyst&locale=en'),
                        ('data-hub', '/api/data-hub'),
                        ('export', base + '/analysis-export?at_second=3500')]
                    rows = []
                    for name, path in endpoints:
                        values = []
                        size = 0
                        for _ in range(args.samples + 1):
                            start = time.perf_counter()
                            response = client.request('POST' if name == 'recap' else 'GET', path)
                            elapsed = (time.perf_counter() - start) * 1000
                            response.raise_for_status()
                            values.append(elapsed)
                            size = len(response.content)
                        warm = sorted(values[1:])
                        rows.append(dict(endpoint=name, path=path, first_request_ms=values[0],
                            warm_p50_ms=statistics.median(warm), warm_p95_ms=warm[math.ceil(.95 * len(warm))-1],
                            min_ms=min(warm), max_ms=max(warm), bytes=size, warm_samples=args.samples,
                            raw_ms=values))
                    result = dict(source_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                        platform=platform.platform(), cpu=platform.processor(), python=platform.python_version(),
                        concurrency=1, stores='empty temporary SQLite; built-in fixture',
                        methodology='First request is NOT a process-cold estimate; shared caches may already be warm. Warm requests sequential; no P99 claim.',
                        results=rows)
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
                    print(json.dumps([{k: row[k] for k in ('endpoint', 'warm_p50_ms', 'warm_p95_ms')} for row in rows], indent=2))
            finally:
                process.terminate()
                process.wait(timeout=15)


if __name__ == '__main__':
    main()
