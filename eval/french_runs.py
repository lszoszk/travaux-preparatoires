#!/usr/bin/env python3
"""French runs in the text that reaches the segmenter (preregistered in docs/devlog.md, 28 Oct 2026): for every document
that is not a machine translation, the lines segment.load_lines gives, each labelled by its own function words
(normalize.line_language, nothing carried over from its neighbours); a run is a stretch of French lines on one page, with
the lines without evidence between them, that begins and ends with a French line. A French column or page comes out as a
long run; a French quotation in English text as a short one.

  python3 eval/french_runs.py --out eval/french_runs_before.json
  python3 eval/french_runs.py --out eval/french_runs_after.json --before eval/french_runs_before.json   # gate, dropped runs
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import segment  # noqa: E402
from common import safe_name  # noqa: E402
from normalize import line_evidence  # noqa: E402

MIN_LINES = 3  # the gate's runs: at least three French lines


def runs_of(symbol: str) -> list[dict]:
    lines = [(p, ln, *line_evidence(ln)) for p, ln in segment.load_lines(symbol, "vote")]
    lab = [("en" if en > fr else "fr" if fr > en else None) for _, _, en, fr in lines]
    out, i = [], 0
    while i < len(lines):
        if lab[i] != "fr":
            i += 1
            continue
        j = last = i
        while j + 1 < len(lines) and lines[j + 1][0] == lines[i][0] and lab[j + 1] != "en":
            j += 1
            if lab[j] == "fr":
                last = j
        run = lines[i:last + 1]
        out.append({"symbol": symbol, "page": lines[i][0], "french_lines": sum(lab[k] == "fr" for k in range(i, last + 1)),
                    "lines": len(run), "french_words": sum(x[3] for x in run), "english_words": sum(x[2] for x in run),
                    "first": run[0][1][:100], "last": run[-1][1][:100]})
        i = last + 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--before", type=Path)
    args = ap.parse_args()
    con = sqlite3.connect(f"file:{ROOT / 'data' / 'travaux.sqlite3'}?mode=ro", uri=True)
    mt = {s for (s,) in con.execute("SELECT symbol FROM documents WHERE machine_translated = 1")}
    symbols = sorted(s for (s,) in con.execute("SELECT DISTINCT symbol FROM segments")
                     if s not in mt and (segment.OCR / safe_name(s) / "vote").exists())
    runs = [r for s in symbols for r in runs_of(s)]
    long_ = [r for r in runs if r["french_lines"] >= MIN_LINES]
    summary = {"documents": len(symbols), "runs": len(runs), "french_words_in_runs": sum(r["french_words"] for r in runs),
               f"runs_{MIN_LINES}_lines": len(long_), f"french_words_in_runs_{MIN_LINES}_lines": sum(r["french_words"] for r in long_)}
    args.out.write_text(json.dumps({"summary": summary, "runs": runs}, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summary))
    if args.before:
        old = json.loads(args.before.read_text())
        key = lambda r: (r["symbol"], r["page"], r["first"])
        now = {key(r) for r in runs}
        gone = [r for r in old["runs"] if key(r) not in now]
        f0, f1 = old["summary"][f"french_words_in_runs_{MIN_LINES}_lines"], summary[f"french_words_in_runs_{MIN_LINES}_lines"]
        print(f"French words in runs of {MIN_LINES}+ French lines {f0:,} -> {f1:,} ({(f0 - f1) / max(f0, 1):.1%} fewer; gate 90%)")
        print(f"runs gone: {len(gone)} ({sum(r['french_words'] for r in gone):,} French words, "
              f"{sum(r['english_words'] for r in gone)} English words)")
        for r in gone:
            print(f"  {r['symbol']} p.{r['page']} {r['french_lines']} lines, {r['french_words']} fr / {r['english_words']} en: {r['first'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
