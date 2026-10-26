"""Assemble the final demo video from recorded scene clips, TTS narration and original overlays.

  python scripts/demo_video/assemble.py     # builds artifacts/demo/pulse-xi-final-demo.mp4 and .srt
Requires imageio-ffmpeg (a bundled ffmpeg with libx264, aac and libass), recorded clips and synthesized audio.
"""
import json
import re
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'scripts' / 'demo_video'
OUT = ROOT / 'artifacts' / 'demo'
WORK = OUT / 'work'
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FF = 'ffmpeg'

timeline = json.loads((HERE / 'timeline.json').read_text(encoding='utf-8'))
narration = json.loads((HERE / 'narration.json').read_text(encoding='utf-8'))
segments = {s['id']: s for s in narration['segments']}
fps, W, H, fade = timeline['fps'], timeline['width'], timeline['height'], timeline['fade']

# ---- scene placement
starts, cursor_time = {}, 0.0
for scene in timeline['scenes']:
    starts[scene['id']] = cursor_time
    cursor_time += scene['duration']
TOTAL = round(cursor_time, 3)

# ---- narration placement from the real audio durations
placed = []
for item in timeline['narration']:
    wav = WORK / 'audio' / f"{item['id']}.wav"
    with wave.open(str(wav)) as handle:
        duration = handle.getnframes() / handle.getframerate()
    start = starts[item['scene']] + item['offset']
    placed.append({**item, 'wav': wav, 'start': start, 'duration': duration, 'end': start + duration})
placed.sort(key=lambda p: p['start'])
for a, b in zip(placed, placed[1:]):
    assert a['end'] <= b['start'] + 0.01, f"narration overlap {a['id']} -> {b['id']}"
assert placed[-1]['end'] <= TOTAL - 0.5, 'narration must end before the video does'


def clock(seconds, separator=','):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d}{separator}{ms:03d}'


# ---- captions: sentence cues timed proportionally to each segment's real audio
cues = []
for p in placed:
    text = segments[p['id']]['caption']
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    weights = [len(s) for s in sentences]
    total_weight = sum(weights)
    cursor = p['start']
    for sentence, weight in zip(sentences, weights):
        span = p['duration'] * weight / total_weight
        cues.append((cursor, min(cursor + span - 0.04, p['end']), sentence, segments[p['id']].get('style', {})))
        cursor += span
srt = '\n'.join(f"{i}\n{clock(a)} --> {clock(b)}\n{text}\n" for i, (a, b, text, _style) in enumerate(cues, 1))
(OUT / 'pulse-xi-final-demo.srt').write_text(srt, encoding='utf-8')


def override(style):
    # ASS override tags use a literal backslash; build it explicitly so no string escape can swallow it.
    return '{' + chr(92) + 'fs%d}' % style['fontsize'] if 'fontsize' in style else ''


def ass_time(seconds):
    return clock(seconds, '.')[:-1]


ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Segoe UI Semibold,44,&H00FFFFFF,&H000000FF,&HC0101010,&HC0101010,0,0,0,0,100,100,0,0,3,12,0,2,230,230,54,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
ass_lines = [f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,{st.get('marginV', 0)},,{override(st)}{text}" for a, b, text, st in cues]
(WORK / 'captions.ass').write_text(ass_header + '\n'.join(ass_lines) + '\n', encoding='utf-8')

# ---- ffmpeg filter graph
inputs, graph = [], []
for scene in timeline['scenes']:
    info = json.loads((WORK / 'clips' / f"{scene['clip']}.json").read_text(encoding='utf-8'))
    ss = info['trimStartSeconds'] + scene['from']
    inputs += ['-ss', f'{ss:.3f}', '-t', f"{scene['duration'] + 1.0:.3f}", '-i', info['video']]
n = len(timeline['scenes'])
for i, scene in enumerate(timeline['scenes']):
    d = scene['duration']
    graph.append(
        f"[{i}:v]fps={fps},scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=2,"
        f"trim=duration={d},setpts=PTS-STARTPTS,fade=t=in:st=0:d={fade},fade=t=out:st={d - fade}:d={fade}[v{i}]")
graph.append(''.join(f'[v{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0[base]')

names = ('title', 'endcard', 'chip-live', 'chip-local', 'chip-reel')
for name in names:
    inputs += ['-loop', '1', '-framerate', str(fps), '-t', str(TOTAL), '-i', str(WORK / 'overlays' / f'{name}.png')]
idx = {name: n + k for k, name in enumerate(names)}
title = timeline['titleCard']
end_start = starts['close'] + timeline['endCard']['sceneOffset']
last = 'base'
chip_floor = title['end'] if timeline.get('hideChipDuringTitle') else 0
for scene in timeline['scenes']:
    if not scene.get('chip'):
        continue   # e.g. the reel page draws its own header; a chip would cover its score
    a = max(starts[scene['id']], chip_floor)
    b = starts[scene['id']] + scene['duration']
    if scene['id'] == 'close':
        b = end_start
    graph.append(f"[{last}][{idx[scene['chip']]}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[c_{scene['id']}]")
    last = f"c_{scene['id']}"
graph.append(f"[{idx['title']}:v]format=rgba,fade=t=out:st={title['end'] - title['fadeOut']}:d={title['fadeOut']}:alpha=1[ttl]")
graph.append(f"[{last}][ttl]overlay=0:0:enable='between(t,{title['start']},{title['end']})'[withtitle]")
graph.append(f"[{idx['endcard']}:v]format=rgba,fade=t=in:st=0:d={timeline['endCard']['fadeIn']}:alpha=1,setpts=PTS+{end_start}/TB[endc]")
graph.append(f"[withtitle][endc]overlay=0:0:enable='between(t,{end_start:.3f},{TOTAL})'[withend]")
graph.append("[withend]ass=captions.ass:fontsdir=C\\\\:/Windows/Fonts,fade=t=out:st=%s:d=0.6[vout]" % (TOTAL - 0.6))

audio_first = n + len(names)
for p in placed:
    inputs += ['-i', str(p['wav'])]
for k, p in enumerate(placed):
    ms = int(round(p['start'] * 1000))
    graph.append(f"[{audio_first + k}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={ms}|{ms}[a{k}]")
graph.append(''.join(f'[a{k}]' for k in range(len(placed))) +
             f"amix=inputs={len(placed)}:normalize=0:duration=longest,apad,atrim=0:{TOTAL},loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,atrim=0:{TOTAL}[aout]")

out = OUT / 'pulse-xi-final-demo.mp4'
cmd = [FF, '-y', '-hide_banner', '-loglevel', 'error', '-stats', *inputs, '-filter_complex', ';'.join(graph),
       '-map', '[vout]', '-map', '[aout]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
       '-r', str(fps), '-profile:v', 'high', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
       '-t', str(TOTAL), str(out)]
(WORK / 'ffmpeg-command.txt').write_text(' '.join(f'"{c}"' if ' ' in c else c for c in cmd), encoding='utf-8')
print(json.dumps({'total_seconds': TOTAL, 'scene_starts': starts,
                  'narration': [(p['id'], round(p['start'], 2), round(p['end'], 2)) for p in placed], 'cues': len(cues)}))
subprocess.run(cmd, cwd=WORK, check=True)
print('wrote', out)
