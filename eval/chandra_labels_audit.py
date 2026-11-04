#!/usr/bin/env python3
"""Round 116: would the vision reader's layout labels show the segmentation errors of round 109's page audit?

For each error of eval/segment_audit_round109.json, the words its description quotes ('...') are looked up in the vision
reader's blocks (data/ocr/<doc>/chandra/page-NNN.html: Text, Section-Header, Page-Header, Page-Footer, Footnote) on the page
and its neighbours, fuzzy (rapidfuzz partial_ratio >= 85). Shown, by class:
- header_or_footer_in_text: a quote inside a Page-Header or Page-Footer block;
- other (decisions, headings, footnotes inside a segment) and wrong_kind: a quote inside a Footnote or Section-Header block,
  or at the start of a block of its own (a paragraph the reader set apart);
- missed_turn: the turn's opening at the start of a block;
- text_missing: the quote present in the reading at all.
Errors without a usable quote, or on pages with no reading, are counted apart. Writes eval/round116_labels.json.
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402

BLOCK_RE = re.compile(r'<div[^>]*data-label="([^"]+)"[^>]*>(.*?)</div>', re.S)
QUOTE_RE = re.compile(r"'([^']{12,})'")
MIN = 85


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", html.unescape(s)).lower().split())


def blocks(symbol: str, page: int) -> list[tuple[str, str]]:
    out = []
    for p in (page - 1, page, page + 1):
        f = ROOT / "data" / "ocr" / safe_name(symbol) / "chandra" / f"page-{p:03d}.html"
        if f.exists():
            out += [(lab, norm(re.sub(r"<[^>]+>", " ", body))) for lab, body in BLOCK_RE.findall(f.read_text())]
    return out


def shown(cls: str, quotes: list[str], bl: list[tuple[str, str]]) -> bool:
    for q in (norm(x) for x in quotes):
        if len(q) < 10:
            continue
        for lab, text in bl:
            inside = fuzz.partial_ratio(q, text) >= MIN
            starts = fuzz.partial_ratio(q[:60], text[:len(q[:60]) + 15]) >= MIN
            if cls == "header_or_footer_in_text" and inside and lab in ("Page-Header", "Page-Footer"):
                return True
            if cls in ("other", "wrong_kind") and (inside and lab in ("Footnote", "Section-Header", "Page-Header", "Page-Footer") or starts):
                return True
            if cls == "missed_turn" and starts:
                return True
            if cls == "text_missing" and inside:
                return True
    return False


def main() -> int:
    audit = json.loads((ROOT / "eval" / "segment_audit_round109.json").read_text())
    c, rows = Counter(), []
    for r in audit["results"]:
        for e in r["errors"]:
            cls, quotes = e["type"], QUOTE_RE.findall(e["detail"])
            bl = blocks(r["symbol"], r["page"])
            if not bl:
                verdict = "no reading"
            elif not quotes or cls not in ("header_or_footer_in_text", "other", "wrong_kind", "missed_turn", "text_missing"):
                verdict = "not testable"
            else:
                verdict = "shown" if shown(cls, quotes, bl) else "not shown"
            c[(cls, verdict)] += 1
            rows.append({"symbol": r["symbol"], "page": r["page"], "type": cls, "verdict": verdict, "detail": e["detail"][:200]})
    out = {"counts": {f"{k[0]}|{k[1]}": v for k, v in sorted(c.items())}, "errors": rows}
    (ROOT / "eval" / "round116_labels.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for k, v in sorted(c.items()):
        print(f"{k[0]:28} {k[1]:13} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
