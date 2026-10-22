"""Offline inventory, not a legal approval or comprehensive secret scanner.

Run with the requirements environment after npm ci:
  python scripts/release-inventory.py > inventory.json
No database is opened and no configured credential values are read.
"""
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.main import app
from app.sandbox.api import router


def main():
    routes = {(r.path, method.lower()): r for r in [*app.routes, *router.routes]
              if hasattr(r, 'dependant') for method in getattr(r, 'methods', ())}
    protected = {'ingest_match': 'shared import bearer', 'preview_package': 'shared import bearer',
        'import_package': 'shared import bearer',
        'agent_traces': 'X-Admin-Token; configured capability',
        'agent_run': 'X-Admin-Token + explicitly enabled Foundry; paid path not exercised'}
    endpoints = []
    schema = app.openapi()
    for path, operations in sorted(schema['paths'].items()):
        for method, operation in sorted(operations.items()):
            route = routes.get((path, method))
            if route is None:
                raise RuntimeError(f'Unmapped OpenAPI operation: {method} {path}')
            dependencies = sorted({getattr(d.call, '__name__', str(d.call))
                                   for d in route.dependant.dependencies})
            name = route.endpoint.__name__
            access = 'owner-scoped operator bearer' if 'require_operator' in dependencies else protected.get(name)
            # Dependencies remain primary evidence if a function is renamed.
            if access is None:
                access = ('import bearer + opt-in direct loopback' if 'require_local_admin' in dependencies
                          else 'shared import bearer' if 'require_import_token' in dependencies
                          else 'public; inspect operation semantics')
            endpoints.append({'method': method.upper(), 'path': path, 'function': name,
                'dependencies': dependencies, 'access': access,
                'openapi_responses': sorted(operation.get('responses', {})),
                'response_schemas': {code: response.get('content', {}).get('application/json', {}).get('schema')
                    for code, response in operation.get('responses', {}).items()}})
    python = []
    for distribution in importlib.metadata.distributions():
        metadata = distribution.metadata
        license_text = metadata.get('License-Expression') or metadata.get('License') or ''
        classifiers = [c for c in metadata.get_all('Classifier', []) if c.startswith('License ::')]
        python.append({'name': metadata['Name'], 'version': distribution.version,
            'license_declaration': license_text.splitlines()[0][:160] if license_text else None,
            'license_classifiers': classifiers,
            'license_files': [str(f) for f in distribution.files or []
                if any(word in str(f).lower() for word in ('license', 'copying', 'notice'))
                and '.dist-info/' in str(f)]})
    lock = json.loads((ROOT / 'frontend/package-lock.json').read_text(encoding='utf-8'))
    node = [{'package_path': path, 'version': item.get('version'), 'license': item.get('license'),
             'development': bool(item.get('dev')), 'optional': bool(item.get('optional'))}
            for path, item in sorted(lock['packages'].items()) if path]
    patterns = [re.compile(r'AKIA[0-9A-Z]{16}'), re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
                re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')]
    files = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True, capture_output=True).stdout
    paths = [ROOT / p.decode('utf-8') for p in files.split(b'\0') if p]
    paths += list((ROOT / 'frontend/dist').rglob('*.js'))
    hits = []
    scanned = 0
    for path in paths:
        raw = path.read_bytes()
        if b'\0' in raw:
            continue  # Binary assets require separate provenance checks.
        scanned += 1
        for number, line in enumerate(raw.decode('utf-8', errors='replace').splitlines(), 1):
            if any(pattern.search(line) for pattern in patterns):
                hits.append({'file': path.relative_to(ROOT).as_posix(), 'line': number})
    print(json.dumps({'inventory_version': 'release-inventory/1', 'http_endpoints': endpoints,
        'websockets': [{'path': '/api/sandbox/sessions/{session_id}/observe',
            'access': 'origin check + first-frame operator token; rechecked during observation; 1008 on rejection'},
            {'path': '/ws/matches/{match_id}', 'access': 'public synthetic recorded-event replay'}],
        'python_distributions': sorted(python, key=lambda d: d['name'].lower()),
        'node_lockfile_packages': node,
        'limited_secret_scan': {'text_files_and_built_js': scanned, 'findings': hits,
            'scope': 'AWS access-key IDs, GitHub token patterns and private-key headers only; no entropy/history scan'},
        'limitations': 'Declarations are not rights clearance. Missing licenses require review; root application license unresolved. '
            'OpenAPI responses are declared responses, not exhaustive middleware/auth failure codes. '
            'Installed optional SDKs outside this environment are not inventoried.'}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
