#!/usr/bin/env python3
"""Two readings of the same pages by the vision reader, from two environments (preregistered in docs/devlog.md, 21 Oct 2026):
the corpus's (data/ocr/<doc>/chandra/, Kaggle's T4s in fp16, or the laptop's quantized build) and Athena's (an A100 in bf16,
the results folder of pipeline/hpc/athena_chandra.sbatch).

Per page: the characters that differ (Levenshtein distance over the longer reading, both normalised as eval/ocr_bench.py
does), whether either reading ran away (a .failed marker), and the names at turn openings and in the officers' lines
(pipeline/name_guard.py cues) that differ. The rule: the corpus's readings stay if at least 45 of the 50 pages differ by
0.5% of characters or less and no name differs; otherwise the pages of that environment are read again.

  python3 eval/gpu_consistency.py --queue data/logs/chandra_queue_consistency.json --other RESULTS [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
from common import safe_name  # noqa: E402
from name_guard import cues  # noqa: E402
from ocr_bench import norm  # noqa: E402

MAX_DIFF = 0.005
MIN_PAGES = 45


def compare(a: str, b: str) -> dict:
    na, nb = norm(a), norm(b)
    diff = Levenshtein.distance(na, nb) / max(len(na), len(nb), 1)
    names_a = Counter((c["kind"], c["name"]) for c in cues(a))
    names_b = Counter((c["kind"], c["name"]) for c in cues(b))
    return {"diff": round(diff, 5), "names_only_corpus": sorted(n for _, n in (names_a - names_b)),
            "names_only_other": sorted(n for _, n in (names_b - names_a))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=Path, required=True)
    ap.add_argument("--other", type=Path, required=True, help="the other environment's results folder (<doc>/chandra/page-NNN.txt)")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    pages, missing = [], 0
    for x in json.loads(args.queue.read_text())["pages"]:
        name = f"page-{x['page']:03d}"
        mine = ROOT / "data" / "ocr" / safe_name(x["symbol"]) / "chandra"
        other = args.other / safe_name(x["symbol"]) / "chandra"
        if not (mine / f"{name}.txt").exists() or not (other / f"{name}.txt").exists():
            missing += 1
            continue
        r = {"symbol": x["symbol"], "page": x["page"],
             **compare((mine / f"{name}.txt").read_text(encoding="utf-8"), (other / f"{name}.txt").read_text(encoding="utf-8")),
             "runaway_corpus": (mine / f"{name}.failed").exists(), "runaway_other": (other / f"{name}.failed").exists()}
        pages.append(r)
    close = sum(r["diff"] <= MAX_DIFF for r in pages)
    named = [r for r in pages if r["names_only_corpus"] or r["names_only_other"]]
    keep = len(pages) >= 50 and close >= MIN_PAGES and not named
    diffs = sorted(r["diff"] for r in pages)
    print(f"{len(pages)} pages compared ({missing} missing); identical {sum(r['diff'] == 0 for r in pages)}; "
          f"within {MAX_DIFF:.1%}: {close}; median difference {diffs[len(diffs) // 2] if diffs else 0:.3%}; "
          f"pages with a name that differs: {len(named)}; runaway: {sum(r['runaway_corpus'] or r['runaway_other'] for r in pages)}",
          file=sys.stderr)
    for r in named:
        print(f"  {r['symbol']} p{r['page']}: corpus {r['names_only_corpus']} / other {r['names_only_other']}", file=sys.stderr)
    print("rule: " + ("the corpus's readings stay" if keep else "read these pages again in the new environment"
                      + ("" if len(pages) >= 50 else " (fewer than 50 pages compared: the rule cannot be applied yet)")),
          file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps({"pages": pages, "close": close, "named": len(named), "keep": keep}, ensure_ascii=False,
                                        indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
