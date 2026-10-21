"""Collect existing installed production-package license texts; no network calls.

Run after npm ci. The Fiber tarball omits its license; its exact-version upstream
MIT text is retained in licenses/react-three-fiber-9.4.0-MIT.txt.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
paths = subprocess.check_output(['npm.cmd' if os.name == 'nt' else 'npm', 'ls', '--omit=dev', '--all', '--parseable'],
                                cwd=ROOT / 'frontend', text=True).splitlines()[1:]
records = []
sections = ['Third-party frontend runtime notices.\nThis does not license PULSE XI application source.\n']
for raw in paths:
    path = Path(raw)
    package = json.loads((path / 'package.json').read_text(encoding='utf-8'))
    files = sorted(f for f in path.iterdir() if f.is_file() and f.name.lower().startswith(('license', 'licence', 'copying', 'notice')))
    if not files and package['name'] == '@react-three/fiber' and package['version'] == '9.4.0':
        files = [ROOT / 'licenses/react-three-fiber-9.4.0-MIT.txt']
    if not files:
        raise ValueError(f"Review required: no license text for {package['name']}")
    sections.append('\n=== ' + package['name'] + ' ' + package['version'] + ' (' + str(package.get('license')) + ') ===\n' +
                    '\n'.join(f.read_text(encoding='utf-8') for f in files))
    records.append({'name': package['name'], 'version': package['version'], 'license': package.get('license'),
                    'notice_files': [f.name for f in files]})
for relative, value in [('frontend/public/assets/THIRD_PARTY_NOTICES.txt', '\n\n'.join(sections)),
                         ('docs/asset-review-evidence/runtime-licenses.json', json.dumps(records, indent=2))]:
    path = ROOT / relative
    if args.check:
        assert path.read_text(encoding='utf-8') == value, f'Stale notices: {relative}'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8')
print(f'Runtime notice inventory: {len(records)} package instances')
