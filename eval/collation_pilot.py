#!/usr/bin/env python3
"""Pilot of collation for the article histories (preregistered in docs/devlog.md, 20 Oct): the texts of one UDHR article at
each drafting stage (draft_texts) as witnesses of one text, collated with CollateX; every place where the stages do not all
read the same is a branch of the variant graph, to be judged by hand (a real change of wording, a change of structure, or OCR
noise; eval/collation_pilot/judgments.json).

Each stage's text is the database's (the OCR's), or the vision reader's text of the same passage where it has read the page
(found by fuzzy alignment, score >= 80); normalised: an editorial note opening the text ("(formerly Article 8)", "(Geneva
text)") and paragraph numbers dropped, quotation marks and punctuation removed, lower case.

Runs in its own environment (CollateX): ~/.venvs/collate/bin/python eval/collation_pilot.py [--articles 1 4 18 24]
Writes eval/collation_pilot/art-NN.json (witnesses, sources, branches), art-NN.txt (the alignment table), art-NN.tei.xml.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

from collatex import Collation, collate
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "collation_pilot"
STAGES = ["secretariat_outline", "cassin_draft", "drafting_committee_1", "e_cn4_57", "geneva_draft", "drafting_committee_2",
          "chr_3", "a777"]
SIGLA = {"secretariat_outline": "Sec", "cassin_draft": "Cassin", "drafting_committee_1": "DC1", "e_cn4_57": "WG57",
         "geneva_draft": "Geneva", "drafting_committee_2": "DC2", "chr_3": "CHR3", "a777": "A777"}
NOTE = re.compile(r"^\W*(?:\([^)]{0,140}\)|[A-Za-z]+ te[xr]t\))\s*")
PARA = re.compile(r"(?:(?<=\s)|^)(?:para\.?\s*)?\d{1,2}\s*[.,]\s+", re.I)


def norm(text: str) -> str:
    t = " ".join(text.split())
    t = NOTE.sub("", t)
    t = PARA.sub(" ", t)
    t = t.replace("’", "'").replace("‘", "'").replace("“", " ").replace("”", " ")
    t = re.sub(r"[^\w\s'-]", " ", t.lower())
    t = re.sub(r"(?<!\w)['-]|['-](?!\w)", " ", t)
    return " ".join(t.split())


def from_reader(symbol: str, page: int, text: str) -> str | None:
    f = ROOT / "data" / "ocr" / symbol.replace("/", "_") / "chandra" / f"page-{page:03d}.txt"
    if not f.exists():
        return None
    page_text = " ".join(f.read_text(encoding="utf-8").split())
    t = " ".join(text.split())
    al = fuzz.partial_ratio_alignment(t.lower(), page_text.lower())
    if not al or al.score < 80:
        return None
    a, b = al.dest_start, al.dest_end
    while a > 0 and page_text[a - 1].isalnum():
        a -= 1
    while b < len(page_text) and page_text[b].isalnum():
        b += 1
    return page_text[a:b]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--articles", nargs="+", type=int, default=[1, 4, 18, 24])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    for art in args.articles:
        rows = con.execute("SELECT stage, stage_symbol, draft_article, page, text FROM draft_texts "
                           "WHERE instrument = 'UDHR' AND final_article = ? ORDER BY rowid", (art,)).fetchall()
        by_stage = {}
        for stage, sym, draft, page, text in rows:
            by_stage.setdefault(stage, []).append((sym, draft, page, text))
        wits, sources = [], {}
        c = Collation()
        for stage in STAGES:
            if stage not in by_stage:
                continue
            parts, src = [], []
            for sym, draft, page, text in by_stage[stage]:
                r = from_reader(sym, page, text)
                parts.append(r or text)
                src.append({"symbol": sym, "draft_article": draft, "page": page, "text_from": "vision reader" if r else "OCR"})
            sig = SIGLA[stage]
            t = norm(" ".join(parts))
            c.add_plain_witness(sig, t)
            wits.append({"sigil": sig, "stage": stage, "text": t})
            sources[sig] = src
        order = [w["sigil"] for w in wits]
        table = json.loads(collate(c, output="json", segmentation=True))
        cols = list(zip(*table["table"]))
        branches = []
        for k, col in enumerate(cols):
            readings = {}
            for sig, cell in zip(order, col):
                r = " ".join(tok["t"].strip() for tok in cell) if cell else ""
                readings[sig] = r
            if len(set(readings.values())) > 1:
                groups = {}
                for sig, r in readings.items():
                    groups.setdefault(r, []).append(sig)
                branches.append({"n": len(branches) + 1, "column": k, "readings": [{"text": r or "(none)", "stages": s} for r, s in groups.items()]})
        (OUT / f"art-{art:02d}.json").write_text(json.dumps({"article": art, "witnesses": wits, "sources": sources,
                                                             "branches": branches}, ensure_ascii=False, indent=1) + "\n")
        (OUT / f"art-{art:02d}.txt").write_text(str(collate(c, output="table", segmentation=True, layout="vertical")) + "\n")
        (OUT / f"art-{art:02d}.tei.xml").write_text(collate(c, output="tei", segmentation=True, indent=True) + "\n")
        n_reader = sum(s["text_from"] == "vision reader" for v in sources.values() for s in v)
        print(f"article {art}: {len(wits)} stages ({n_reader} texts from the vision reader), {len(branches)} branches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
