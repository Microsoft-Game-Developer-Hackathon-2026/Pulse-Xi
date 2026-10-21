"""Rebuild both original asset kits twice in temporary storage, never in-place."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
blender = os.getenv('PULSE_BLENDER_PATH') or shutil.which('blender')
if not blender:
    paths = sorted(Path(os.getenv('ProgramFiles', 'C:/Program Files')).glob('Blender Foundation/Blender */blender.exe'))
    blender = str(paths[-1]) if paths else None
if not blender:
    raise SystemExit('Blender required; set PULSE_BLENDER_PATH')
expected = {a['name']: a['output_sha256'] for a in json.loads((ROOT / 'assets/manifest.json').read_text())['assets']}
records = []
with tempfile.TemporaryDirectory(prefix='pulse-release-rebuild-') as folder:
    target = Path(folder)
    for path in ['scripts', 'assets', 'frontend/src/features/observer/assets']:
        shutil.copytree(ROOT / path, target / path)
    for trial in range(2):
        for script in ['build-blender-assets.py', 'build-professional-assets.py']:
            start = time.perf_counter()
            result = subprocess.run([blender, '--background', '--factory-startup', '--disable-autoexec',
                '--python-exit-code', '1', '--python', str(target / 'scripts' / script)], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout[-4000:] + result.stderr[-4000:])
            hashes = {a['name']: a['output_sha256'] for a in json.loads((target / 'assets/manifest.json').read_text())['assets']}
            record = {'trial': trial + 1, 'generator': script, 'seconds': time.perf_counter() - start,
                      'hashes': hashes, 'matches_committed': hashes == expected}
            records.append(record)
            print(json.dumps(record), flush=True)
            assert hashes == expected, 'Rebuilt GLB mismatch; do not update hashes without diagnosis'
output = ROOT / 'test-results/asset-review/rebuilds-fixed.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(records, indent=2) + '\n')
