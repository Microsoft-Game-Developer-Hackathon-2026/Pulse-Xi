"""Tile frames from a recorded scene clip for visual review: contact_sheet.py <scene> <t1,t2,...> <out.png>"""
import json, subprocess, sys, pathlib, tempfile
scene, times, out = sys.argv[1], [float(x) for x in sys.argv[2].split(',')], sys.argv[3]
import shutil
try:
    import imageio_ffmpeg; ff = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    ff = shutil.which('ffmpeg') or 'ffmpeg'
report = json.load(open(f'artifacts/demo/work/clips/{scene}.json'))
tmp = pathlib.Path(tempfile.mkdtemp())
for i, t in enumerate(times):
    subprocess.run([ff, '-v', 'error', '-y', '-ss', str(report['trimStartSeconds'] + t), '-i', report['video'], '-frames:v', '1', '-vf', 'scale=800:-1', str(tmp / f'{i:02d}.png')], check=True)
cols = 2
inputs = []; [inputs.extend(['-i', str(tmp / f'{i:02d}.png')]) for i in range(len(times))]
layout = '|'.join(f"{(i % cols) * 800}_{(i // cols) * 450}" for i in range(len(times)))
subprocess.run([ff, '-v', 'error', '-y', *inputs, '-filter_complex', f"xstack=inputs={len(times)}:layout={layout}", out], check=True)
print(out)
