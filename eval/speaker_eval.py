#!/usr/bin/env python3
"""Speaker attribution: freeze a reference set, then score later runs against it.

  --freeze   write data/gold/speakers_<name>.jsonl from the current segments, applying
             the hand corrections in CORRECTIONS. The result is a SILVER set: reviewed
             against the OCR text, not yet against the page images.
  (default)  score the current segments against that file: precision (resolved and
             right), recall (right out of all speeches) and the wrong attributions.

Reference speeches carry their page and opening words. A run is scored by matching each
reference speech to the run's speech on the same page with the most similar opening
(so a run that splits the record differently, e.g. from another OCR engine, is still
scored fairly). Unmatched reference speeches count as missed; run speeches matched to
nothing are reported as extra (often real speeches the reference run missed).

Usage: python3 eval/speaker_eval.py chr3 E/CN.4/SR.60 ... [--freeze] [--engine layer]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402

SEG = ROOT / "data" / "segments"
GOLD = ROOT / "data" / "gold"

# Hand corrections, read off the OCR text (speaker_raw and country_raw as printed).
# key: (symbol, page, n-th speech on the page, from 0) -> (speaker, delegation)
CORRECTIONS = {
    ("E/CN.4/SR.63", 5, 0): ("CHANG", "China"),  # "Mr. CEAUG- (Chim)"
    ("E/CN.4/SR.63", 7, 2): ("KLEKOVKIN", "Ukrainian Soviet Socialist Republic"),  # "XLËXDVKIH"
}
# One delegate, spelled differently in the attendance lists: the reference spelling.
CANONICAL = {"KLEKOVKEN": "KLEKOVKIN"}


def keyed_speeches(symbol: str, engine: str) -> dict[tuple, dict]:
    """The speeches of a record, keyed by (symbol, page, order on the page). Speaker and delegation
    are taken from the database where it has them: it holds the final spelling (names unified
    across sessions, organisations normalised), which is what users see."""
    segs = json.loads((SEG / f"{safe_name(symbol)}.{engine}.json").read_text())
    db = ROOT / "data" / "travaux.sqlite3"
    if db.exists():
        import sqlite3
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        final = {r[0]: (r[1], r[2]) for r in con.execute("SELECT id, speaker, delegation FROM segments WHERE symbol = ?", (symbol,))}
        con.close()
        for s in segs:
            if s.get("id") in final and final[s["id"]][0]:
                s["speaker"], s["delegation"] = final[s["id"]]
    out, per_page = {}, Counter()
    for s in segs:
        if s["kind"] == "speech":
            per_page[s["page_start"]] += 1
            out[(symbol, s["page_start"], per_page[s["page_start"]] - 1)] = s
    return out


def fold(name: str) -> str:
    """Names compared without case or accents: CAÑAS is CANAS (the OCR drops the tilde)."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", name.upper()) if not unicodedata.combining(c))


def opening_match(text: str, opening: str) -> float:
    """How well a speech's first 100 characters match the reference opening. A speech now shorter
    than the opening (a vote that followed it is split off) is compared on its own length."""
    a, b = text[:100].lower(), opening.lower()
    return fuzz.ratio(a, b[:len(a)]) if len(a) < len(b) else fuzz.ratio(a, b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--engine", default="layer")
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    path = GOLD / f"speakers_{args.name}.jsonl"

    speeches = {}
    for sym in args.symbols:
        speeches.update(keyed_speeches(sym, args.engine))

    if args.freeze:
        GOLD.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            for key, s in speeches.items():
                spk, dele = CORRECTIONS.get(key, (s.get("speaker"), s.get("delegation")))
                spk = CANONICAL.get(spk, spk)
                f.write(json.dumps({"symbol": key[0], "page": key[1], "n": key[2],
                                    "opening": s["text"][:100],
                                    "speaker_raw": s.get("speaker_raw"), "country_raw": s.get("country_raw"),
                                    "speaker": spk, "delegation": dele,
                                    "status": "silver: checked against OCR text, not page images"},
                                   ensure_ascii=False) + "\n")
        print(f"froze {len(speeches)} speeches -> {path.relative_to(ROOT)}", file=sys.stderr)
        return 0

    gold = [json.loads(line) for line in path.read_text().splitlines()]
    by_page: dict[tuple, list[dict]] = {}
    for (sym, page, _), s in speeches.items():
        by_page.setdefault((sym, page), []).append(s)
    used: set[int] = set()
    right = wrong = unresolved = missed = 0
    errors = []
    for g in gold:
        cands = [s for s in by_page.get((g["symbol"], g["page"]), []) if id(s) not in used]
        best = max(cands, key=lambda s: opening_match(s["text"], g["opening"]), default=None)
        if best is None or opening_match(best["text"], g["opening"]) < 60:
            missed += 1
            print(f"  missed: {g['symbol']} p. {g['page']} {g['speaker']} | {g['opening'][:70]!r}", file=sys.stderr)
            continue
        used.add(id(best))
        spk = CANONICAL.get(best.get("speaker"), best.get("speaker"))
        if not spk:
            unresolved += 1
        elif fold(spk) == fold(g["speaker"]) and best.get("delegation") == g["delegation"]:
            right += 1
        else:
            wrong += 1
            errors.append((g["symbol"], g["page"], best.get("speaker_raw"), spk, best.get("delegation"),
                           g["speaker"], g["delegation"]))
    extra = sum(1 for s in speeches.values() if id(s) not in used)
    n = len(gold)
    print(f"{args.name} [{args.engine}]: {n} reference speeches | right {right} | wrong {wrong} | "
          f"unresolved {unresolved} | missed {missed} | extra speeches in run {extra}", file=sys.stderr)
    print(f"  precision {right / max(right + wrong, 1):.3f}   recall {right / n:.3f}", file=sys.stderr)
    for e in errors:
        print(f"  WRONG {e[0]} p{e[1]} raw={e[2]!r}: got {e[3]}/{e[4]}, expected {e[5]}/{e[6]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
