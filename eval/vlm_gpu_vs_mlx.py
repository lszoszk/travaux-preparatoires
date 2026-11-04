#!/usr/bin/env python3
"""The two builds of the local vision reader page by page: the laptop's MLX 5-bit build (engine "chandra") and the original
Chandra OCR 2 in fp16 served by vLLM on Kaggle's T4s (engine "chandra-gpu"), on the same pages and with the same prompt. Before a
GPU reading is used in place of a laptop one, the two should read the same words; where they differ, the CER against the retyped
reference (eval/vlm_local_dev_cer.py) says which is right.

Per page: words of each reading (eval/ocr_bench.py norm), the share of words the two readings share in order (difflib), and the
differing word runs (the first few kept for reading).

  python3 eval/vlm_gpu_vs_mlx.py eval/vlm_pilot/dev_set.json [--json eval/vlm_pilot/gpu_vs_mlx_dev1.json]
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402
from ocr_bench import OCR, norm  # noqa: E402

A, B = "chandra", "chandra-gpu"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", type=Path, help="a set of pages: {documents: [{symbol, pages: [...]}, ...]}")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    rows, missing = [], []
    for d in json.loads(args.pages.read_text())["documents"]:
        for p in d["pages"]:
            name = f"page-{p:03d}.txt"
            fa, fb = (OCR / safe_name(d["symbol"]) / e / name for e in (A, B))
            if not (fa.exists() and fb.exists()):
                missing.append(f"{d['symbol']} p{p}")
                continue
            wa, wb = (norm(f.read_text(encoding="utf-8")).split() for f in (fa, fb))
            sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
            same = sum(b.size for b in sm.get_matching_blocks())
            diffs = [(" ".join(wa[i1:i2]), " ".join(wb[j1:j2])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
            rows.append({"page": f"{d['symbol']} p{p}", "words": [len(wa), len(wb)], "shared": same,
                         "agreement": same / max(len(wa), len(wb), 1), "differing_runs": len(diffs), "examples": diffs[:8]})
    words = sum(max(r["words"]) for r in rows)
    shared = sum(r["shared"] for r in rows)
    print(f"{len(rows)} pages read by both builds ({len(missing)} not): {shared} of {words} words shared in order "
          f"({shared / max(words, 1):.2%}), {sum(r['differing_runs'] for r in rows)} differing runs", file=sys.stderr)
    for r in sorted(rows, key=lambda r: r["agreement"]):
        print(f"  {r['page']:24} {r['agreement']:.3f}  {r['words'][0]:4}/{r['words'][1]:4} words  "
              + "; ".join(f"{a!r}->{b!r}" for a, b in r["examples"][:3]), file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps({"builds": [A, B], "pages": len(rows), "missing": missing, "words": words,
                                         "shared": shared, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
