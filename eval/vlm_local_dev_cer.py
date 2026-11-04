#!/usr/bin/env python3
"""Character error rate of the OCR engines on a set of pages, against the retyped reference (eval/ocr_bench.py's method:
the reference cut into sentence-sized segments, each located in each engine's reading, a segment counted only if some
engine finds it with a score of at least 88). Unlike ocr_bench.py, only the listed pages are read, so a few pages read by a
slow engine (the local model of the vision-reader pilot) can be compared with the OCR vote on the same pages.

  python3 eval/vlm_local_dev_cer.py eval/vlm_pilot/dev_set.json --engines vote chandra [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402
from ocr_bench import MIN_FOUND, OCR, REF, engine_text, group_of, locate, ref_segments  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", type=Path, help="a set of pages: {documents: [{symbol, pages: [...]}, ...]}")
    ap.add_argument("--engines", nargs="+", default=["vote", "chandra"])
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    rows = []
    for d in json.loads(args.pages.read_text())["documents"]:
        safe = safe_name(d["symbol"])
        ref_path = REF / f"{safe}.json"
        if not ref_path.exists():
            continue
        names = [f"page-{p:03d}.txt" for p in d["pages"]]
        names = [n for n in names if all((OCR / safe / e / n).exists() for e in args.engines)]
        if not names:
            print(f"  {d['symbol']}: not read by every engine yet", file=sys.stderr)
            continue
        hyps = {e: engine_text(OCR / safe, e, names) for e in args.engines}
        dist, chars, n = defaultdict(int), 0, 0
        for seg in ref_segments(json.loads(ref_path.read_text())["pages"]):
            res = {e: locate(seg, h) for e, h in hyps.items()}
            if max(score for score, _ in res.values()) < MIN_FOUND:
                continue
            n += 1
            chars += len(seg)
            for e, (_, dd) in res.items():
                dist[e] += dd
        if chars:
            rows.append({"symbol": d["symbol"], "group": group_of(d["symbol"]), "pages": len(names), "segments": n,
                         "chars": chars, "errors": dict(dist), "cer": {e: dist[e] / chars for e in args.engines}})
            print(f"  {d['symbol']:20} {len(names)} pp {n:4} segs  "
                  + "  ".join(f"{e} {dist[e] / chars:.4f}" for e in args.engines), file=sys.stderr)
    groups = defaultdict(list)
    for r in rows:
        groups[r["group"]].append(r)
    summary = {}
    for g, rs in sorted(groups.items()) + [("ALL", rows)]:
        tot = sum(r["chars"] for r in rs)
        if tot:
            summary[g] = {"pages": sum(r["pages"] for r in rs), "chars": tot,
                          "cer": {e: sum(r["errors"][e] for r in rs) / tot for e in args.engines}}
            print(f"{g:42} {summary[g]['pages']:3} pp {tot:7} chars  "
                  + "  ".join(f"{e} {summary[g]['cer'][e]:.4f}" for e in args.engines), file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps({"pages_file": str(args.pages), "min_found": MIN_FOUND, "summary": summary,
                                         "documents": rows}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
