#!/usr/bin/env python3
"""Build the Phase 1 pilot manifest: UDHR Articles 18-19.

Inputs:
- data/manifest/udhr.json (the UN Library guide manifest; every pilot symbol must be in it,
  except user seeds from the Covenant period)
- data/private/schabas_art18_19_findingaid.json (optional, private): symbols whose pages
  Schabas's table of provisions lists for arts 18-19. Only the symbols are used; the
  article tags themselves are later derived from the UN text.
- SEEDS: records already verified by hand in the book wiki.
- CONTROLS: extra records chosen to cover each scan type in the OCR benchmark.

Output: data/manifest/pilot_udhr_18_19.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UDHR = ROOT / "data" / "manifest" / "udhr.json"
FINDING_AID = ROOT / "data" / "private" / "schabas_art18_19_findingaid.json"
OUT = ROOT / "data" / "manifest" / "pilot_udhr_18_19.json"

# Hand-verified pinpoints (The Book/00_PROJECT/wiki/entities/article-18-udhr-iccpr-travaux.md).
# These double as the end-to-end retrieval checks.
SEEDS = {
    "E/CN.4/AC.1/SR.31": "p 6: first paragraph divided to separate inner belief from practice",
    "E/CN.4/SR.60": "p 10: Cassin distinguishes thought from expression; pp 12-13",
    "E/CN.4/SR.164": "p 4: expression as continuation of freedom of thought (1950, Covenant)",
}

# One record per scan type, so the OCR benchmark sees each layout at least once.
CONTROLS = {
    "E/CN.4/SR.1": "1947 mimeographed summary record, noisy existing OCR",
    "E/CN.4/AC.1/SR.1": "1947 Drafting Committee record, two-column attendance list",
    "A/C.3/SR.89": "1948 printed GAOR volume, English/French parallel columns, meeting overlap",
    "E/800": "1948 CHR report with the draft Declaration",
    "E/CN.4/21": "1947 Drafting Committee report",
}


def main() -> int:
    guide = {d["symbol"]: d for d in json.loads(UDHR.read_text())["documents"]}
    picked: dict[str, dict] = {}

    if FINDING_AID.exists():
        aid = json.loads(FINDING_AID.read_text())
        for art, info in aid.items():
            for symbol, pages in info["symbols"]:
                if symbol is None:
                    continue
                if symbol not in guide:
                    print(f"  not in guide, skipped: {symbol} (art {art}, {pages}pp)", file=sys.stderr)
                    continue
                entry = picked.setdefault(symbol, {"symbol": symbol, "basis": [], "articles_hint": []})
                if "finding_aid" not in entry["basis"]:
                    entry["basis"].append("finding_aid")
                entry["articles_hint"].append(int(art))
    else:
        print("no private finding aid; pilot = seeds + controls only", file=sys.stderr)

    for symbol, note in SEEDS.items():
        entry = picked.setdefault(symbol, {"symbol": symbol, "basis": [], "articles_hint": []})
        entry["basis"].append("verified_seed")
        entry["seed_note"] = note
    for symbol, note in CONTROLS.items():
        entry = picked.setdefault(symbol, {"symbol": symbol, "basis": [], "articles_hint": []})
        entry["basis"].append("ocr_control")
        entry["control_note"] = note

    for entry in picked.values():
        g = guide.get(entry["symbol"])
        entry["articles_hint"] = sorted(set(entry["articles_hint"]))
        entry["in_guide"] = g is not None
        entry["doc_type"] = g["doc_type"] if g else None
        entry["meeting_date"] = g["meeting_date"] if g else None
        entry["body"] = g["mentions"][0]["body"] if g else None

    docs = sorted(picked.values(), key=lambda e: (e["meeting_date"] or "9999", e["symbol"]))
    OUT.write_text(json.dumps({
        "pilot": "UDHR articles 18-19",
        "count": len(docs),
        "documents": docs,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(docs)} pilot documents -> {OUT.relative_to(ROOT)}", file=sys.stderr)
    for d in docs:
        print(f"  {d['meeting_date'] or '          '}  {d['symbol']:24} {','.join(d['basis']):28} {d['articles_hint']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
