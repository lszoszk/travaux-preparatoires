#!/usr/bin/env python3
"""Cut the teaser: title card, four screen scenes, end card, crossfades, the scan sliding in beside the record, the
voice-over at each scene's start, loudness to -16 LUFS; H.264/AAC, 1920x1080, 30 fps, 30 s.

  python3 media/teaser/voice.py && python3 media/teaser/record.py && python3 media/teaser/cards.py && python3 media/teaser/build.py

Writes dist/teaser/travaux_teaser_16x9.mp4, travaux_teaser.srt and poster.png.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "dist" / "teaser"
FPS, D, LEAD = 30, 0.35, 0.25          # frame rate, crossfade, silence before each line
SCENES = [("s1", 3.6), ("s2", 9.8), ("s3", 3.2), ("s4", 5.4), ("s5", 3.9), ("s6", 4.1)]   # 30.0 s


def srt_time(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def main() -> int:
    voice = json.loads((T / "voice" / "durations.json").read_text())
    offs = json.loads((T / "clips" / "offsets.json").read_text())
    starts, t = {}, 0.0
    for name, length in SCENES:
        starts[name] = t
        t += length
        assert voice["durations"][name] + LEAD < length, f"{name}: the line is longer than the scene"
    total = t
    scan = ROOT / "data" / "ocr" / offs["s3"]["symbol"].replace("/", "_") / "img" / f"page-{offs['s3']['page']:03d}.png"

    inputs, chains, last = [], [], len(SCENES) - 1
    n_in = 0  # the next input's index
    for k, (name, length) in enumerate(SCENES):
        L = length + (D if k < last else 0)
        idx = n_in
        n_in += 1
        if name in ("s1", "s6"):
            card = T / ("card_title.png" if name == "s1" else "card_end.png")
            inputs += ["-framerate", str(FPS), "-loop", "1", "-t", f"{L:.2f}", "-i", str(card)]
            zoom = "zoompan=z='min(zoom+0.0005,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30" if name == "s1" else "fps=30"
            chains.append(f"[{idx}:v]{zoom},format=yuv420p,setsar=1,trim=duration={L:.2f},setpts=PTS-STARTPTS[v{k}]")
        else:
            inputs += ["-ss", f"{offs[name]['start']:.2f}", "-t", f"{L:.2f}", "-i", str(T / "clips" / f"{name}.webm")]
            chains.append(f"[{idx}:v]fps=30,scale=1920:1080,format=yuv420p,setsar=1,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=2,"
                          f"trim=duration={L:.2f}[v{k}]")
    # the scan of the page slides in beside the record (scene s3)
    if scan.exists():
        s3 = [n for n, _ in SCENES].index("s3")
        inputs += ["-framerate", str(FPS), "-loop", "1", "-i", str(scan)]
        si = n_in
        n_in += 1
        chains.append(f"[{si}:v]scale=-2:900,pad=iw+8:ih+8:4:4:color=0x2b2e35,format=yuva420p[scan]")
        chains[s3] = chains[s3].replace(f"[v{s3}]", "[s3base]")
        chains.append(f"[s3base][scan]overlay=x=420:y='if(lt(t\\,1.3)\\,H\\,max(110\\,H-(t-1.3)*2800))':shortest=1[v{s3}]")
    # crossfades
    cur, off, label = f"[v0]", SCENES[0][1] + D, "v0"
    acc = SCENES[0][1] + D
    for k in range(1, len(SCENES)):
        offset = acc - D
        out = f"x{k}"
        chains.append(f"{cur}[v{k}]xfade=transition=fade:duration={D}:offset={offset:.3f}[{out}]")
        acc = offset + SCENES[k][1] + (D if k < last else 0)
        cur = f"[{out}]"
    chains.append(f"{cur}fade=t=out:st={total - 0.6:.2f}:d=0.6,trim=duration={total:.2f}[vout]")
    # voice
    vi0 = n_in
    amix = []
    for j, (name, _) in enumerate(SCENES):
        inputs += ["-i", str(T / "voice" / f"{name}.wav")]
        ms = int((starts[name] + LEAD) * 1000)
        chains.append(f"[{vi0 + j}:a]adelay={ms}|{ms}[a{j}]")
        amix.append(f"[a{j}]")
    chains.append(f"{''.join(amix)}amix=inputs={len(amix)}:normalize=0,apad,atrim=duration={total:.2f},loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    out = T / "travaux_teaser_16x9.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{total:.2f}", str(out)]
    subprocess.run(cmd, check=True)
    # captions
    lines = []
    for j, (name, _) in enumerate(SCENES):
        a = starts[name] + LEAD
        lines.append(f"{j + 1}\n{srt_time(a)} --> {srt_time(a + voice['durations'][name])}\n{voice['lines'][name]}\n")
    (T / "travaux_teaser.srt").write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "6.5", "-i", str(out), "-frames:v", "1", str(T / "poster.png")], check=True)
    print(out, f"{total:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
