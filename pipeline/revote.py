#!/usr/bin/env python3
"""Re-run the word-level vote (and the correction step) for documents already OCR'd.

The engines' page texts and the page selection are kept; only the vote is redone, with the
current weights (ocr_select.DEFAULT_WEIGHTS) and word frequencies (spellfix). Use it after
changing either, or for documents OCR'd by a process started before the change.

Usage: python3 pipeline/revote.py data/manifest/harvest_udhr.json [...] [--workers 4]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402
from ocr_select import CANDIDATES, DEFAULT_WEIGHTS, OCR, vote  # noqa: E402


def one(sym: str) -> int:
    if not (OCR / safe_name(sym) / "selection.json").exists():
        return 0
    return vote(sym, CANDIDATES, DEFAULT_WEIGHTS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+", type=Path)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    syms = sorted({s for log in args.logs for s, e in json.loads(log.read_text()).items() if e.get("status") == "ok"})
    t = time.time()
    with Pool(args.workers) as pool:
        changed = sum(pool.imap_unordered(one, syms, chunksize=8))
    print(f"re-voted {len(syms)} documents, {changed} tokens changed, {time.time() - t:.0f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
