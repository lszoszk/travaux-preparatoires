#!/usr/bin/env python3
"""Manifest for the drafting records of the two Covenants (ICCPR and ICESCR), 1949-66.

There is no UN Library guide for the Covenants, so the manifest is built from:
- series ranges: the Commission on Human Rights summary records of its 5th-10th sessions
  (E/CN.4/SR.82-479, 1949-54) and the Third Committee summary records 1950-66
  (A/C.3/SR.287-1460). Not every meeting in these ranges was about the Covenants: the
  records say so themselves (agenda item on page 1), which ocr_all.py --relevance checks
  before OCR'ing a record in full;
- known documents: the CHR session reports, the Secretary-General's annotations (A/2929),
  the Third Committee reports cited in the UN procedural history, and the adoption
  (A/PV.1495-1496, A/RES/2200(XXI)).
Amendments (E/CN.4/L..., A/C.3/L...) are added later from the references in the records.

Usage: python3 pipeline/build_covenant_manifest.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_udhr_manifest import doc_type, meeting_no, series  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "manifest" / "covenants.json"

KNOWN = {
    # CHR session reports, 5th-10th sessions
    "E/1371": "CHR 5th session report (1949)",
    "E/1681": "CHR 6th session report (1950)",
    "E/1992": "CHR 7th session report (1951)",
    "E/2256": "CHR 8th session report (1952)",
    "E/2447": "CHR 9th session report (1953)",
    "E/2573": "CHR 10th session report (1954); the draft Covenants sent to the GA",
    # ECOSOC documents cited in the UN procedural history
    "E/1618": "ECOSOC, 1950", "E/1721": "ECOSOC, 1950", "E/1732": "ECOSOC, 1950",
    # Secretary-General's article-by-article annotations
    "A/2929": "Annotations on the text of the draft International Covenants on Human Rights (1955)",
    # Third Committee reports cited in the UN procedural history
    "A/5655": "Third Committee report, 18th session (1963)",
    "A/6546": "Third Committee report, 21st session (1966)",
    "A/6564": "Third Committee report, 21st session (1966)",
    "A/5365": "Third Committee report, 17th session (1962)",
    # adoption
    "A/PV.1495": "GA plenary, 16 December 1966", "A/PV.1496": "GA plenary, 16 December 1966",
    "A/RES/2200(XXI)": "The Covenants adopted",
}
# The same reports under their Commission symbols, for those ODS lacks under the ECOSOC one
# (E/1371, E/1681, E/2256, E/2447, E/2573 returned no PDF). Harvested after the main run.
ALTERNATES = {
    "E/CN.4/350": "= E/1371, CHR 5th session report (1949): draft covenant as revised in 1949",
    "E/CN.4/507": "= E/1681, CHR 6th session report (1950): draft covenant, 1950 text",
    "E/CN.4/640": "= E/1992, CHR 7th session report (1951)",
    "E/CN.4/669": "= E/2256, CHR 8th session report (1952): the two draft covenants",
    "E/CN.4/689": "= E/2447, CHR 9th session report (1953)",
    "E/CN.4/705": "= E/2573, CHR 10th session report (1954): the drafts sent to the General Assembly",
    # retry: a UDHR record whose download failed with an error (not "unavailable")
    "E/CN.4/SR.52": "retry of a failed UDHR download (CHR 3rd session)",
}
ALT_OUT = ROOT / "data" / "manifest" / "covenants_alt.json"
RANGES = [
    ("E/CN.4/SR.", 82, 479, "Commission on Human Rights", "5th-10th sessions (1949-54)"),
    ("A/C.3/SR.", 287, 1460, "General Assembly Third Committee", "5th-21st sessions (1950-66)"),
]


def main() -> int:
    docs = []
    for sym, note in KNOWN.items():
        docs.append({"symbol": sym, "doc_type": doc_type(sym), "series": series(sym), "meeting_no": meeting_no(sym),
                     "discovery_basis": "known_document", "note": note, "body": None, "session": None,
                     "relevance_check": False})
    for prefix, lo, hi, body, sessions in RANGES:
        for n in range(lo, hi + 1):
            sym = f"{prefix}{n}"
            # the session comes from the meeting date (pipeline/sessions.py); the range is kept
            docs.append({"symbol": sym, "doc_type": "summary_record", "series": prefix, "meeting_no": n,
                         "discovery_basis": "series_range", "body": body, "session": None, "sessions": sessions,
                         "relevance_check": True})
    OUT.write_text(json.dumps({
        "description": "Drafting records of the ICCPR and ICESCR, 1949-66: known documents and series ranges "
                       "(relevance checked from each record's agenda before full OCR)",
        "count": len(docs), "documents": docs}, ensure_ascii=False, indent=1), encoding="utf-8")
    alt = [{"symbol": sym, "doc_type": doc_type(sym), "series": series(sym), "meeting_no": meeting_no(sym),
            "discovery_basis": "alternate_symbol", "note": note, "body": "Commission on Human Rights", "session": None,
            "relevance_check": False} for sym, note in ALTERNATES.items()]
    ALT_OUT.write_text(json.dumps({"description": "Covenant reports under their Commission symbols", "count": len(alt),
                                   "documents": alt}, ensure_ascii=False, indent=1), encoding="utf-8")
    by = {}
    for d in docs:
        by[d["discovery_basis"]] = by.get(d["discovery_basis"], 0) + 1
    print(f"{len(docs)} documents -> {OUT.relative_to(ROOT)} {by}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
