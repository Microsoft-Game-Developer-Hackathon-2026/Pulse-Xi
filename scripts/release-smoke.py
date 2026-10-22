"""Real loopback HTTP acceptance journey with disposable databases and no inference.

Build frontend first, then: python scripts/release-smoke.py
No existing database, credentials or server is used. No artifacts contain tokens.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not (ROOT / 'frontend/dist/index.html').is_file():
        raise SystemExit('Build frontend first: npm run build (from frontend)')
    with tempfile.TemporaryDirectory(prefix='pulse-release-smoke-') as folder:
        directory = Path(folder)
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('PULSE_', 'FOUNDRY_')):
                del env[key]
        token = secrets.token_urlsafe(40)
        env.update(PULSE_ENABLE_FOUNDRY='false', PULSE_RUNTIME_TOKEN=token,
                   PULSE_DB_PATH=str(directory / 'library.sqlite'),
                   PULSE_RUNTIME_DB_PATH=str(directory / 'runtime.sqlite'))
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        started = time.perf_counter()
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
            '--loop', 'app.local_event_loop:create_loop', '--app-dir', str(ROOT / 'backend'),
            '--host', '127.0.0.1', '--port', str(port)], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=20) as client:
                health_deadline = time.monotonic() + 15
                while time.monotonic() < health_deadline:
                    if server.poll() is not None:
                        raise RuntimeError('Temporary server exited before health check')
                    try:
                        if client.get('/health', timeout=1).status_code == 200:
                            break
                    except httpx.RequestError:
                        pass
                    time.sleep(.1)
                else:
                    raise RuntimeError('Temporary server did not become healthy in 15 seconds')
                startup_ms = (time.perf_counter() - started) * 1000
                assert client.get('/health').json()['narrative_provider'] == 'not_configured'
                page = client.get('/')
                assert page.status_code == 200 and '<html' in page.text.lower()
                assert client.get('/api/sandbox/scenarios').status_code == 403
                headers = {'Authorization': 'Bearer ' + token}

                def request(method, path, payload=None):
                    response = client.request(method, '/api/sandbox' + path,
                                              headers=headers, json=payload)
                    response.raise_for_status()
                    return response.json()

                presets = request('GET', '/presets')
                config = presets['balanced']
                config.update(seed=7, duration_seconds=120)
                cold_creation = time.perf_counter()
                scenario = request('POST', '/scenarios', config)
                cold_creation_ms = (time.perf_counter() - cold_creation) * 1000
                assert any(s['scenario_id'] == scenario['scenario_id']
                           for s in request('GET', '/scenarios'))
                archive = request('GET', f"/scenarios/{scenario['scenario_id']}/archive")
                assert request('POST', '/scenarios/import', archive) == archive
                state = request('POST', '/sessions', {'operation_id': 'release-create',
                    'scenario_id': scenario['scenario_id']})
                sid = state['session_id']

                def command(kind, **values):
                    nonlocal state
                    state = request('POST', f'/sessions/{sid}/commands', {
                        'operation_id': f'release-{kind}-{state["revision"]}',
                        'expected_revision': state['revision'], 'kind': kind, **values})
                    return state

                command('step', ticks=30)
                saved = command('checkpoint')
                cid = saved['checkpoint_id']
                checkpoint = request('GET', f'/checkpoints/{cid}')
                assert checkpoint['created_at_utc'].endswith('Z')
                child = request('POST', f'/checkpoints/{cid}/restore', {
                    'operation_id': 'release-restore', 'expected_revision': saved['revision']})
                assert child['session_id'] != sid
                assert child['state_hash'] == saved['state_hash']
                command('intervene', team_id='home', field='pressing', value=90, requested_tick=30)
                command('step', ticks=1)
                audit = request('GET', f'/sessions/{sid}/audit')
                assert audit
                job = request('POST', '/experiments', {'operation_id': 'release-experiment',
                    'checkpoint_id': cid, 'expected_revision': saved['revision'],
                    'trials': 1, 'horizon': 30,
                    'variation': [{'team_id': 'home', 'field': 'tempo', 'value': 90}]})
                eid = job['experiment_id']
                deadline = time.monotonic() + 60
                while job['status'] not in ('completed', 'failed', 'cancelled'):
                    if time.monotonic() > deadline:
                        raise RuntimeError('Bounded experiment exceeded local smoke deadline')
                    time.sleep(.1)
                    job = request('GET', f'/experiments/{eid}')
                assert job['status'] == 'completed', job['status']
                comparison = request('GET', f'/experiments/{eid}/comparison')
                for route, module in [(f'/sessions/{sid}/reproduction', 'verify_manifest'),
                                      (f'/experiments/{eid}/reproduction', 'verify_experiment')]:
                    artifact = directory / f'{module}.json'
                    artifact.write_text(json.dumps(request('GET', route)), encoding='utf-8')
                    result = subprocess.run([sys.executable, '-m', 'app.sandbox.' + module, str(artifact)],
                        cwd=ROOT / 'backend', env=env, capture_output=True, text=True, timeout=30)
                    assert result.returncode == 0, result.stdout
                    assert json.loads(result.stdout)['verified'] is True
                print(json.dumps({'status': 'passed', 'transport': 'real loopback HTTP + independent CLI',
                    'startup_health_ms': round(startup_ms, 2), 'config_hash': scenario['config_hash'],
                    'cold_scenario_create_ms': round(cold_creation_ms, 2),
                    'checkpoint_utc_recorded': True, 'audit_records': len(audit),
                    'comparison_available': bool(comparison), 'verifiers': 2,
                    'foundry': 'disabled; no inference', 'database': 'disposable isolated files',
                    'elapsed_seconds': round(time.perf_counter() - started, 2)}, sort_keys=True))
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)


if __name__ == '__main__':
    main()
