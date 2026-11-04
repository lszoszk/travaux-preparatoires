#!/usr/bin/env python3
"""The preregistered text analysis of the vision-reader pilot (docs/preregistration_vlm_pilot.md, 4.2-4.3) on block B: the
character error rate of each reading against the retyped reference, per page and pooled by characters, for typewritten
summary records, typewritten documents and printed pages; the difference between a reading and the OCR vote with a 95%
interval by bootstrap over pages (10,000 resamples, fixed seed). The method of eval/ocr_bench.py, page by page: the
reference cut into segments of at least 40 characters, each located in the page's reading; a segment counts only if some
reading matches it with a score of at least 88.

  python3 eval/vlm_pilot_cer.py --engines vote chandra [--block B] [--json eval/vlm_pilot/cer_blockB.json]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402
from ocr_bench import MIN_FOUND, OCR, REF, engine_text, locate, ref_segments  # noqa: E402

KIND = {"record": "typewritten records", "document": "typewritten documents", "printed": "printed pages"}


def kind_of(item: dict) -> str:
    sym = item["symbol"]
    return "printed" if sym.startswith("A/C.3/SR.") else "record" if "/SR." in sym else "document"


def pooled(rows: list[dict], engine: str) -> float:
    chars = sum(r["chars"] for r in rows)
    return sum(r["errors"][engine] for r in rows) / chars if chars else float("nan")


def interval(rows: list[dict], a: str, b: str, n: int = 10_000, seed: int = 2026) -> tuple[float, float]:
    """95% bootstrap interval over pages of the pooled CER difference b - a."""
    rnd = random.Random(seed)
    diffs = []
    for _ in range(n):
        s = [rnd.choice(rows) for _ in rows]
        diffs.append(pooled(s, b) - pooled(s, a))
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n) - 1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=["vote", "chandra"])
    ap.add_argument("--block", default="B")
    ap.add_argument("--sample", type=Path, default=ROOT / "eval" / "vlm_pilot" / "sample.json")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    items = [x for x in json.loads(args.sample.read_text())["pages"] if x["block"] == args.block]
    refs: dict[str, list[str]] = {}
    rows, missing = [], []
    for x in items:
        safe = safe_name(x["symbol"])
        name = f"page-{x['page']:03d}.txt"
        if not all((OCR / safe / e / name).exists() for e in args.engines):
            missing.append(x["id"])
            continue
        if safe not in refs:
            refs[safe] = ref_segments(json.loads((REF / f"{safe}.json").read_text())["pages"])
        hyps = {e: engine_text(OCR / safe, e, [name]) for e in args.engines}
        errors, chars, n = defaultdict(int), 0, 0
        for seg in refs[safe]:
            res = {e: locate(seg, h) for e, h in hyps.items()}
            if max(score for score, _ in res.values()) < MIN_FOUND:
                continue
            n += 1
            chars += len(seg)
            for e, (_, d) in res.items():
                errors[e] += d
        rows.append({"id": x["id"], "kind": kind_of(x), "cell": x["cell"], "segments": n, "chars": chars,
                     "errors": dict(errors), "cer": {e: (errors[e] / chars if chars else None) for e in args.engines}})
    rows = [r for r in rows if r["chars"]]
    out = {"block": args.block, "engines": args.engines, "pages_scored": len(rows), "missing": missing, "groups": {}}
    groups = {**{KIND[k]: [r for r in rows if r["kind"] == k] for k in KIND},
              "typewritten (records and documents)": [r for r in rows if r["kind"] != "printed"], "all": rows}
    print(f"block {args.block}: {len(rows)} pages scored, {len(missing)} not read by every engine", file=sys.stderr)
    for g, rs in groups.items():
        if not rs:
            continue
        res = {"pages": len(rs), "chars": sum(r["chars"] for r in rs), "cer": {e: pooled(rs, e) for e in args.engines}}
        for e in args.engines[1:]:
            lo, hi = interval(rs, args.engines[0], e)
            res[f"diff_{e}_minus_{args.engines[0]}"] = {"point": res["cer"][e] - res["cer"][args.engines[0]], "ci95": [lo, hi]}
        out["groups"][g] = res
        print(f"  {g:38} {res['pages']:3} pp {res['chars']:7} chars  "
              + "  ".join(f"{e} {res['cer'][e]:.4f}" for e in args.engines)
              + "".join(f"  | {k[5:]} {v['point']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]"
                        for k, v in res.items() if k.startswith("diff_")), file=sys.stderr)
    out["pages"] = rows
    if args.json:
        args.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
