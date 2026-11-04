#!/usr/bin/env python3
"""Segment every OCR'd document, resolve speakers and authors, and rebuild the database.

For each harvested document whose voted OCR text is complete: meeting records are split
into speeches and resolved session by session; other documents are split into paragraphs
with their submitting state. Then api/build_db.py rebuilds data/travaux.sqlite3.

Usage: python3 pipeline/build_all.py data/manifest/harvest_udhr.json data/manifest/harvest_udhr_supplement.json ... [--no-db]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entities  # noqa: E402
from common import safe_name  # noqa: E402
from ocr import OCR  # noqa: E402
from segment import segment  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEG = ROOT / "data" / "segments"
ENGINE = "vote"


def irrelevant() -> set[str]:
    """Records of the Covenants' meeting series judged not to be about them (pipeline/ocr_all.py; changed by hand
    where the full text or the agenda showed otherwise): their OCR, if it exists, stays out of the database."""
    out: set[str] = set()
    for path in (ROOT / "data" / "manifest").glob("relevance_*.json"):
        out |= {sym for sym, v in json.loads(path.read_text()).items() if v.get("relevant") is False}
    return out


def ready(symbol: str, pages: int) -> bool:
    d = OCR / safe_name(symbol) / ENGINE
    return d.exists() and len(list(d.glob("page-*.txt"))) >= pages


def main() -> int:
    no_db = "--no-db" in sys.argv  # segment and resolve only (pipeline/resegment.py builds the database itself)
    logs = [Path(a) for a in sys.argv[1:] if a != "--no-db"]
    todo = {}
    skip = irrelevant()
    for log in logs:
        if log.exists():
            for sym, e in json.loads(log.read_text()).items():
                if e.get("status") == "ok" and e.get("pages") and sym not in skip and ready(sym, e["pages"]):
                    todo[sym] = e
    SEG.mkdir(parents=True, exist_ok=True)
    for sym in skip:  # a segmentation left by an earlier run must not reach the database
        for stale in SEG.glob(f"{safe_name(sym)}.{ENGINE}.json"):
            stale.unlink()
    records, documents, failed = [], [], []
    for sym in sorted(todo):
        try:
            segs = segment(sym, ENGINE)
        except Exception as exc:  # noqa: BLE001  one bad document must not stop the build
            failed.append((sym, str(exc)[:120]))
            continue
        (SEG / f"{safe_name(sym)}.{ENGINE}.json").write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
        (records if re.search(r"/(?:SR|PV)\.\d", sym) else documents).append(sym)
    print(f"segmented {len(records)} meeting records, {len(documents)} documents; failed {len(failed)}", file=sys.stderr)
    for f in failed[:10]:
        print("  !!", f, file=sys.stderr)
    totals = entities.run(records, ENGINE, quiet=True)
    print(f"speakers: {totals}", file=sys.stderr)
    gaz = entities.load_gazetteer()
    authored = sum(entities.resolve_authors(sym, ENGINE, gaz) for sym in documents)
    print(f"document paragraphs with an author: {authored}", file=sys.stderr)
    if not no_db:
        subprocess.run([sys.executable, str(ROOT / "api" / "build_db.py"), "--engine", ENGINE], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
