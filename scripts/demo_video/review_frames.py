"""Extract frames from the final MP4 and tile them for visual review: review_frames.py <t1,t2,...> <out.png> [video]"""
import subprocess, sys, tempfile
from pathlib import Path
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FF = 'ffmpeg'
times = [float(x) for x in sys.argv[1].split(',')]
out = sys.argv[2]
video = sys.argv[3] if len(sys.argv) > 3 else str(Path(__file__).resolve().parents[2] / 'artifacts' / 'demo' / 'pulse-xi-final-demo.mp4')
tmp = Path(tempfile.mkdtemp())
for i, t in enumerate(times):
    subprocess.run([FF, '-v', 'error', '-y', '-ss', str(t), '-i', video, '-frames:v', '1', '-vf', 'scale=800:-1', str(tmp / f'{i:02d}.png')], check=True)
cols = 2
inputs = []
for i in range(len(times)):
    inputs += ['-i', str(tmp / f'{i:02d}.png')]
layout = '|'.join(f"{(i % cols) * 800}_{(i // cols) * 450}" for i in range(len(times)))
subprocess.run([FF, '-v', 'error', '-y', *inputs, '-filter_complex', f'xstack=inputs={len(times)}:layout={layout}', out], check=True)
print(out)
