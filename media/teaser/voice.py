#!/usr/bin/env python3
"""The teaser's voice-over: one clip per scene with macOS `say`, as WAV, with its duration.

  python3 media/teaser/voice.py [--voice Daniel] [--rate 175]

Writes dist/teaser/voice/sN.wav and dist/teaser/voice/durations.json, and dist/teaser/travaux_teaser.srt (the lines, timed
to the scene starts that media/teaser/build.sh uses).
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dist" / "teaser"
SCENES = [
    ("s1", "How were the Universal Declaration and the two Covenants written?"),
    ("s2", "Search every speech in the UN drafting records, 1946 to 1966: who spoke, for which country, on which article."),
    ("s3", "Open the record, and the original scan."),
    ("s4", "Follow an article from first draft to adopted text, through every meeting and vote."),
    ("s5", "See who proposed each amendment, and how the vote went."),
    ("s6", "UN Travaux Préparatoires. Coming soon."),
]


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Daniel")
    ap.add_argument("--rate", type=int, default=182)
    args = ap.parse_args()
    vdir = OUT / "voice"
    vdir.mkdir(parents=True, exist_ok=True)
    durs = {}
    for name, text in SCENES:
        aiff = vdir / f"{name}.aiff"
        subprocess.run(["say", "-v", args.voice, "-r", str(args.rate), "-o", str(aiff), text], check=True)
        wav = vdir / f"{name}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(aiff), "-ar", "48000", "-ac", "2", str(wav)], check=True)
        aiff.unlink()
        durs[name] = round(duration(wav), 2)
    (vdir / "durations.json").write_text(json.dumps({"voice": args.voice, "rate": args.rate, "durations": durs,
                                                     "lines": dict(SCENES)}, indent=1))
    for k, v in durs.items():
        print(f"{k}: {v:.2f} s")
    print(f"total speech {sum(durs.values()):.2f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
