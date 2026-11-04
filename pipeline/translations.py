#!/usr/bin/env python3
"""Documents that exist only in French, machine-translated into English and flagged as such.

The Digital Library holds some corrigenda and revisions in French only. Each is translated from the
scan (data/raw/<symbol>-FR.pdf) by one model, checked against the scan by a second, and the
discrepancies settled by the first. The record of that work is data/translations/<safe symbol>.json:

  symbol, source_language, source_file, translation_model, check_model, translation_date,
  title, date, stated_original_language, pages [{page, text}], uncertain, check {verdict, issues, summary}

`python3 pipeline/translations.py` lays the translated pages out as the voted OCR text of the document
(data/ocr/<safe>/vote/page-NNN.txt) and logs the document as fetched ("via": "machine_translation") in
the harvest log that listed it, so pipeline/build_all.py segments it like any other. api/build_db.py
reads the same records and sets documents.machine_translated, translation_model, translation_check and
translation_date; the API, the MCP server and the site label every passage of such a document.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "data" / "translations"
MAN = ROOT / "data" / "manifest"
OCR = ROOT / "data" / "ocr"


def lay_out(t: dict) -> int:
    """Write the translated pages as the document's voted OCR text; returns the page count."""
    d = OCR / safe_name(t["symbol"])
    for sub in ("vote", "best"):
        (d / sub).mkdir(parents=True, exist_ok=True)
        for old in (d / sub).glob("page-*.txt"):
            old.unlink()
    selection = {}
    for page in t["pages"]:
        name = f"page-{page['page']:03d}.txt"
        for sub in ("vote", "best"):
            (d / sub / name).write_text(page["text"].strip() + "\n", encoding="utf-8")
        selection[name] = {"engine": "translation", "two_column": False, "scores": {}}
    (d / "selection.json").write_text(json.dumps(selection, indent=1), encoding="utf-8")
    return len(t["pages"])


def log_entry(t: dict, pages: int) -> str:
    """Log the document as fetched, in the harvest log that listed it (or the supplement's)."""
    source = ROOT / "data" / "raw" / t["source_file"]
    entry = {"status": "ok", "via": "machine_translation", "file": str(source.relative_to(ROOT)), "pages": pages,
             "source_language": t["source_language"], "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
             "bytes": source.stat().st_size, "translation_date": t["translation_date"]}
    target = MAN / "harvest_udhr_supplement.json"
    for path in sorted(MAN.glob("harvest_*.json")):
        if t["symbol"] in json.loads(path.read_text()):
            target = path
            break
    log = json.loads(target.read_text())
    entry["earlier_problem"] = log.get(t["symbol"], {}).get("earlier_problem") or log.get(t["symbol"], {}).get("status")
    log[t["symbol"]] = entry
    target.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    return target.name


def main() -> int:
    for path in sorted(TRANSLATIONS.glob("*.json")):
        t = json.loads(path.read_text())
        pages = lay_out(t)
        where = log_entry(t, pages)
        print(f"  {t['symbol']}: {pages}pp translated ({t['translation_model']}), logged in {where}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
