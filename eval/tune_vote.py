#!/usr/bin/env python3
"""Choose the engine weights of the word-level vote on the full benchmark, with a held-out half.

The weights in pipeline/ocr_select.py (DEFAULT_WEIGHTS) were set on the 28 pilot documents.
This recomputes the vote for every benchmark document under several weight sets and measures
the character error against the private references, exactly as eval/ocr_bench.py does (same
segments: those some engine reads with a match score of at least MIN_FOUND). Documents are
split in two by symbol hash: weights are compared on one half and confirmed on the other.

Usage: python3 eval/tune_vote.py [--workers 4]
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
from normalize import strip_furniture  # noqa: E402
from ocr_bench import MIN_FOUND, OCR, REF, common_pages, engine_text, group_of, locate, norm, ref_segments  # noqa: E402
from ocr_select import COLUMN_AWARE  # noqa: E402
from vote import vote_page  # noqa: E402

ENGINES = ["layer", "tess6", "tess3", "vision"]
# (layer, tess6, tess3, vision)
WEIGHT_SETS = {
    "current 1.5/.5/.5/1": (1.5, 0.5, 0.5, 1.0),
    "equal 1/1/1/1": (1.0, 1.0, 1.0, 1.0),
    "1/.5/1/1": (1.0, 0.5, 1.0, 1.0),
    "1.5/.5/1/1": (1.5, 0.5, 1.0, 1.0),
    "1/.5/1.5/1": (1.0, 0.5, 1.5, 1.0),
    ".5/.5/1/1": (0.5, 0.5, 1.0, 1.0),
    "1.5/.5/1/.75": (1.5, 0.5, 1.0, 0.75),
    "1.2/.6/1.2/1": (1.2, 0.6, 1.2, 1.0),
}
MAX_CHARS = 80_000  # the long reports: their first segments are enough


def vote_text(doc_dir: Path, pages: list[str], weights: dict[str, float]) -> str:
    sel = json.loads((doc_dir / "selection.json").read_text())
    out = []
    for name in pages:
        c = sel.get(name)
        if not c:
            continue
        voters = [e for e in ENGINES if not c.get("two_column") or e in COLUMN_AWARE]
        texts = {e: strip_furniture((doc_dir / e / name).read_text(encoding="utf-8"), first_page=name == "page-001.txt")[0]
                 for e in voters if (doc_dir / e / name).exists()}
        if c["engine"] not in texts:
            continue
        out.append(vote_page(texts, c["engine"], weights)[0])
    return norm("\n".join(out))


def one_doc(ref_path: Path):
    ref = json.loads(ref_path.read_text())
    doc_dir = OCR / ref_path.stem
    if not (doc_dir / "selection.json").exists():
        return None
    pages = common_pages(doc_dir, ENGINES)
    hyps = {e: engine_text(doc_dir, e, pages) for e in ENGINES}
    if not all(hyps.values()):
        return None
    segs = []
    total = 0
    for seg in ref_segments(ref["pages"]):
        if max(locate(seg, h)[0] for h in hyps.values()) >= MIN_FOUND:
            segs.append(seg)
            total += len(seg)
            if total > MAX_CHARS:
                break
    if not segs:
        return None
    dist = {}
    for name, w in WEIGHT_SETS.items():
        hyp = vote_text(doc_dir, pages, dict(zip(ENGINES, w)))
        dist[name] = sum(locate(seg, hyp)[1] for seg in segs)
    return {"symbol": ref["symbol"], "group": group_of(ref["symbol"]), "chars": total, "dist": dist,
            "half": zlib.crc32(ref["symbol"].encode()) % 2}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    refs = sorted(REF.glob("*.json"))
    with Pool(args.workers) as pool:
        rows = [r for r in pool.imap_unordered(one_doc, refs, chunksize=4) if r]
    print(f"{len(rows)} documents", file=sys.stderr)
    for half in (0, 1, None):
        sel = [r for r in rows if half is None or r["half"] == half]
        by = defaultdict(lambda: defaultdict(float))
        chars = defaultdict(int)
        for r in sel:
            for g in (r["group"], "ALL"):
                chars[g] += r["chars"]
                for name, d in r["dist"].items():
                    by[g][name] += d
        label = {0: "half A (choose)", 1: "half B (confirm)", None: "all"}[half]
        print(f"\n{label}:", file=sys.stderr)
        print(f"  {'weights':22}" + "".join(f"{g[:22]:>24}" for g in sorted(chars)), file=sys.stderr)
        for name in WEIGHT_SETS:
            print(f"  {name:22}" + "".join(f"{by[g][name] / chars[g]:24.4f}" for g in sorted(chars)), file=sys.stderr)
    (ROOT / "eval" / "tune_vote.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
