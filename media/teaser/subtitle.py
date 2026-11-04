#!/usr/bin/env python3
"""Burn the voice-over captions into the teaser, in the app's typeface.

This ffmpeg has no libass, so each line of dist/teaser/travaux_teaser.srt is rendered by Playwright as a transparent
1920x1080 PNG (a dark box at the bottom, Source Serif 4) and overlaid for its time span, with a short fade.

  python3 media/teaser/subtitle.py      # -> dist/teaser/travaux_teaser_16x9_subtitled.mp4
"""
from __future__ import annotations

import html
import re
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "dist" / "teaser"
FONTS = (ROOT / "site" / "assets" / "fonts.css").as_uri()
PAGE = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{fonts}">
<style>html,body{{margin:0;width:1920px;height:1080px;background:transparent}}
.box{{position:absolute;left:50%;bottom:64px;transform:translateX(-50%);max-width:1480px;padding:14px 30px 16px;
 background:rgba(24,26,32,.80);border-radius:6px;color:#fff;font-family:'Source Serif 4',serif;font-size:42px;line-height:1.3;
 text-align:center;box-shadow:0 2px 14px rgba(0,0,0,.25)}}</style></head>
<body><div class="box">{text}</div></body></html>"""


def secs(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def main() -> int:
    blocks = [b for b in (T / "travaux_teaser.srt").read_text(encoding="utf-8").split("\n\n") if b.strip()]
    cues = []
    for b in blocks:
        lines = b.strip().splitlines()
        a, z = [secs(x.strip()) for x in lines[1].split("-->")]
        cues.append((a, z, " ".join(lines[2:])))
    sdir = T / "subs"
    sdir.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for i, (_, _, text) in enumerate(cues):
            (sdir / f"c{i}.html").write_text(PAGE.format(fonts=FONTS, text=html.escape(text)), encoding="utf-8")
            pg.goto((sdir / f"c{i}.html").as_uri())
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(sdir / f"c{i}.png"), omit_background=True)
        b.close()
    inputs = ["-i", str(T / "travaux_teaser_16x9.mp4")]
    chain, cur = [], "[0:v]"
    for i, (a, z, _) in enumerate(cues):
        z = z + 0.35  # let a caption stay a moment after the voice
        inputs += ["-framerate", "30", "-loop", "1", "-t", f"{z + 1:.2f}", "-i", str(sdir / f"c{i}.png")]
        chain.append(f"[{i + 1}:v]format=rgba,fade=t=in:st={a:.2f}:d=0.2:alpha=1,fade=t=out:st={z - 0.2:.2f}:d=0.2:alpha=1[s{i}]")
        nxt = f"[o{i}]"
        chain.append(f"{cur}[s{i}]overlay=0:0:enable='between(t,{a:.2f},{z:.2f})':eof_action=pass{nxt}")
        cur = nxt
    out = T / "travaux_teaser_16x9_subtitled.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(chain), "-map", cur, "-map", "0:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "copy", "-movflags", "+faststart", "-t", "30", str(out)], check=True)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
