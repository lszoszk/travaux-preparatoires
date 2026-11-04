#!/usr/bin/env python3
"""OCR every harvested document of a corpus, following a running harvest.

Loops over the harvest logs: each document with a PDF and no complete OCR is OCR'd on
all pages with FULL_RUN_ENGINES (layer, tess6, tess3, vision), then its best engine is
chosen and the words voted (pipeline/ocr_select.py). When nothing is pending it waits,
and it exits once the harvest log says the harvest finished (a "HARVEST EXIT" line).

Usage: python3 pipeline/ocr_all.py data/manifest/harvest_udhr.json data/manifest/harvest_udhr_supplement.json \
         --harvest-log data/logs/harvest_udhr.log [--shard 0/3]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import zlib
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402
from ocr import OCR, ocr_document  # noqa: E402
from ocr_select import DEFAULT_WEIGHTS, FULL_RUN_ENGINES, load_words, select, vote  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# "Covenant" as the text layer of a 1949-66 scan may spell it ("oovenant", "Oovenants", "COVENANT")
COVENANT_RE = re.compile(r"[cCoO0][oO0][vV][eEc][nN][aA@][nN][tT1]")


def relevant(pdf: Path) -> tuple[bool, str]:
    """Does the record's agenda (text layer of its first two pages) mention the Covenants?
    A record with no usable text layer counts as relevant: only OCR can tell."""
    try:
        with fitz.open(pdf) as doc:
            text = " ".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
    except Exception as exc:  # noqa: BLE001
        return True, f"unreadable: {exc}"
    if len(text.strip()) < 200:
        return True, "no text layer"
    m = COVENANT_RE.search(text)
    if m:
        return True, text[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")
    compact = re.sub(r"\s+", "", text)  # letter-spaced OCR: "c o v e n a n t"
    m = COVENANT_RE.search(compact)
    return (True, compact[max(0, m.start() - 40): m.end() + 40]) if m else (False, "no mention on pp. 1-2")


def complete(symbol: str, n_pages: int) -> bool:
    d = OCR / safe_name(symbol)
    return all(len(list((d / e).glob("page-*.txt"))) >= n_pages for e in FULL_RUN_ENGINES) and (d / "vote").exists() \
        and len(list((d / "vote").glob("page-*.txt"))) >= n_pages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+", type=Path)
    ap.add_argument("--harvest-log", type=Path, help="stop once it contains 'HARVEST EXIT'")
    ap.add_argument("--shard", default="0/1", help="i/k: take only documents whose symbol hashes to i mod k, "
                    "so k processes can share the work (small documents leave one process's threads idle)")
    ap.add_argument("--manifest", type=Path, help="with relevance_check flags: skip records not about the Covenants")
    args = ap.parse_args()
    shard, shards = (int(x) for x in args.shard.split("/"))
    check = set()
    if args.manifest:
        check = {d["symbol"] for d in json.loads(args.manifest.read_text())["documents"] if d.get("relevance_check")}
    rel_path = ROOT / "data" / "manifest" / f"relevance_{args.manifest.stem}_{shard}.json" if args.manifest else None
    rel = json.loads(rel_path.read_text()) if rel_path and rel_path.exists() else {}
    words = load_words()
    done_pages = 0
    t0 = time.time()
    while True:
        pending = []
        for log_path in args.logs:
            if log_path.exists():
                for sym, e in json.loads(log_path.read_text()).items():
                    if zlib.crc32(sym.encode()) % shards != shard:
                        continue
                    if e.get("status") != "ok" or not e.get("pages") or complete(sym, e["pages"]):
                        continue
                    if sym in check:
                        if sym not in rel:
                            ok, why = relevant(ROOT / e["file"])
                            rel[sym] = {"relevant": ok, "evidence": why}
                            rel_path.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
                        if not rel[sym]["relevant"]:
                            continue
                    pending.append((sym, ROOT / e["file"], e["pages"]))
        if not pending:
            finished = not args.harvest_log or "HARVEST EXIT" in args.harvest_log.read_text()
            if finished:
                print(f"OCR ALL DONE: {done_pages} pages in {(time.time() - t0) / 60:.0f} min", flush=True)
                return 0
            time.sleep(60)
            continue
        for sym, pdf, n in pending:
            try:
                ocr_document(sym, pdf, 0, FULL_RUN_ENGINES)
                select(sym, FULL_RUN_ENGINES, words)
                vote(sym, FULL_RUN_ENGINES, DEFAULT_WEIGHTS)
                done_pages += n
                print(f"  {sym}: {n}pp  (total {done_pages}pp, {(time.time() - t0) / 60:.0f} min)", flush=True)
            except Exception as exc:  # noqa: BLE001  one bad PDF must not stop the night
                print(f"  !! {sym}: {exc}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
