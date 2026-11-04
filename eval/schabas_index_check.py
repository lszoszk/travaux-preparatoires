#!/usr/bin/env python3
"""Schabas's index against our article tags, record by record (UDHR, 1946-48). PRIVATE INPUT, counts only out.

Schabas (2013) closes with a "Table of provisions of the Universal Declaration": for each article (and its paragraphs) the
pages of the book where it is discussed. Its pages map to the UN documents the book reproduces by each document's exact
book pages (eval/private/reference/*.json, pdf_pages - 127; a page shared by two documents counts for both). For each article and each UN record we hold, two answers: does Schabas index the article in it,
and does our database tag at least one speech or paragraph of it with the article (final_article, UDHR). Their agreement is
a check of our tags at record level; the pairs only Schabas has are candidates for tags we miss, to be verified on the UN text.
The parsed table stays in data/private (gitignored); nothing of the book's text is used.

  python3 eval/schabas_index_check.py [--json eval/schabas_index_check.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = Path(os.environ.get("SCHABAS_PDF", "/Users/lszoszk/Downloads/ William A. Schabas - The Universal Declaration Of Human "
                          "Rights_ The Travaux Préparatoires 3-Vol Set (2013, Cambridge University Press).pdf"))
TABLE_PAGES = range(3226, 3232)  # 0-based PDF pages of the Table of provisions
OUT_PRIVATE = ROOT / "data" / "private" / "schabas_provisions.json"


def expand(tok: str) -> list[int]:
    """'2889–924' -> 2889..2924, '1160–1' -> 1160..1161, '17' -> [17]; roman numerals (the introduction) are dropped."""
    tok = tok.strip()
    m = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", tok)
    if m:
        a, b = m.group(1), m.group(2)
        b = a[: len(a) - len(b)] + b if len(b) < len(a) else b
        return list(range(int(a), int(b) + 1))
    return [int(tok)] if tok.isdigit() else []


def provisions() -> dict[str, list[int]]:
    doc = fitz.open(PDF)
    text = " ".join(doc[i].get_text() for i in TABLE_PAGES)
    text = re.sub(r"\s+", " ", text.replace("Table of provisions of the Universal Declaration of Human Rights", " "))
    out, current = defaultdict(set), None
    # entries: "Preamble, ...", "Article 18, ...", "Paragraph 2, ..." (a paragraph of the article before it)
    for m in re.finditer(r"(Preamble|Article \d+|Paragraph \d+)\s*,\s*(.*?)(?=(?:Preamble|Article \d+|Paragraph \d+)\s*,|$)", text):
        head, pages = m.group(1), m.group(2)
        if head.startswith("Paragraph"):
            if current is None:
                continue
            key = current
        else:
            current = key = "preamble" if head == "Preamble" else head.split()[1]
        for tok in pages.split(","):
            out[key].update(expand(tok))
    return {k: sorted(v) for k, v in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    prov = provisions()
    OUT_PRIVATE.write_text(json.dumps(prov, indent=1))
    # (the documents' exact book pages, from the reference files: the table of documents misses ~194 documents that the book
    # reproduces inside others' runs)
    ranges = []
    for f in (ROOT / "eval" / "private" / "reference").glob("*.json"):
        d = json.loads(f.read_text())
        ranges += [(a - 127, b - 127, d["symbol"]) for a, b in d.get("pdf_pages", [])]
    def docs_of(page: int) -> set[str]:
        return {sym for a, b, sym in ranges if a <= page <= b}
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    held = {s for (s,) in con.execute("SELECT symbol FROM documents")}
    ours = defaultdict(set)
    for sym, art in con.execute("SELECT symbol, final_article FROM segments WHERE final_article IS NOT NULL "
                                "AND coalesce(article_instrument, 'UDHR') = 'UDHR'"):
        ours[sym].add(str(art))
    theirs = defaultdict(set)
    for art, pages in prov.items():
        if art == "preamble":
            continue
        for p in pages:
            for d in docs_of(p):
                if d in held:
                    theirs[d].add(art)
    docs = sorted(set(theirs) | {d for d in ours if d in {sym for _, _, sym in ranges}})
    both = only_s = only_o = 0
    per_art = defaultdict(lambda: [0, 0, 0])
    for d in docs:
        for a in theirs[d] | ours[d]:
            k = 0 if a in theirs[d] and a in ours[d] else 1 if a in theirs[d] else 2
            per_art[a][k] += 1
            both += k == 0; only_s += k == 1; only_o += k == 2
    print(f"Table of provisions: {sum(len(v) for v in prov.values())} page references for {len(prov)} entries; "
          f"{len(docs)} records held that either source ties to an article", file=sys.stderr)
    print(f"article-record pairs: both {both}, Schabas only {only_s}, ours only {only_o}; "
          f"our recall of Schabas's pairs {both / (both + only_s):.0%}, Schabas's of ours {both / (both + only_o):.0%}", file=sys.stderr)
    for a in sorted(per_art, key=lambda x: int(x)):
        b, s, o = per_art[a]
        print(f"  art {a:>2}: both {b:3}  Schabas only {s:3}  ours only {o:3}", file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps({"pairs": {"both": both, "schabas_only": only_s, "ours_only": only_o},
                                         "per_article": per_art}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
