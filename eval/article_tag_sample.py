#!/usr/bin/env python3
"""Draw a stratified sample of article-tagged speeches for a hand check of tag precision.

For each speech: its tag (instrument, final article, draft number, stage), the line that set
the article (the heading or the chair/agenda passage before it), and the opening of the speech.
The checker decides whether the speech is about that final article, and records it in
data/gold/article_tags.jsonl (see eval/article_tag_precision.py).

Usage: python3 eval/article_tag_sample.py [--seed 7] > sample.txt
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# by corpus and numbering stage (the Third Committee 1948, the Commission 1948, the Covenants 1954-66)
STRATA = [("UDHR", "chr_3", None, 25), ("UDHR", "drafting_committee_2", None, 18), ("Covenants", None, None, 7)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--corpus", help="draw only from this corpus (UDHR, Covenants) ...")
    ap.add_argument("--body", help="... and this body (\"Commission on Human Rights\")")
    ap.add_argument("--stages", help="... and these numbering stages (comma-separated: \"geneva_draft,cassin_draft\")")
    ap.add_argument("--n", type=int, default=40, help="how many, with --corpus")
    args = ap.parse_args()
    strata = [(args.corpus, None, None, args.n)] if args.corpus else STRATA
    random.seed(args.seed)
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    con.row_factory = sqlite3.Row
    titles = {(r["instrument"], r["article"]): r["short_title"] for r in csv.DictReader((ROOT / "data/concordance/articles.csv").open())}
    out = []
    for corpus, stage, src, n in strata:
        q = ("SELECT s.*, d.stage FROM segments s JOIN documents d ON d.symbol = s.symbol WHERE s.kind='speech' "
             "AND s.final_article IS NOT NULL AND d.instrument = ?")
        params = [corpus]
        if stage:
            q += " AND d.stage = ?"
            params.append(stage)
        if args.body:
            q += " AND d.body = ?"
            params.append(args.body)
        if args.stages:
            q += f" AND d.stage IN ({','.join('?' * len(args.stages.split(',')))})"
            params += args.stages.split(",")
        if src:
            q += " AND s.article_mapping " + ("LIKE" if src == "context" else "NOT LIKE") + " '%chair or agenda%'"
        rows = con.execute(q, params).fetchall()
        for r in random.sample(rows, min(n, len(rows))):
            prev = con.execute("SELECT kind, text FROM segments WHERE symbol = ? AND seq < ? AND (kind = 'heading' OR "
                               "(kind IN ('chair','procedural','vote') AND lower(text) LIKE '%article%')) ORDER BY seq DESC LIMIT 1",
                               (r["symbol"], r["seq"])).fetchone()
            inst = r["article_instrument"].split("+")[0]
            out.append({"id": r["id"], "symbol": r["symbol"], "page": r["page_start"], "stratum": f"{corpus}/{stage or r['stage'] or (args.body and 'CHR 1949-50') or 'e2573'}/{src or 'any'}",
                        "tag": f"{r['article_instrument']} art. {r['final_article']} ({titles.get((inst, str(r['final_article'])), '')})",
                        "draft": r["draft_article"], "setter": (prev["kind"] + ": " + " ".join(prev["text"].split())[:220]) if prev else None,
                        "speech": f"{r['speaker']} ({r['delegation']}): " + " ".join(r["text"].split())[:520]})
    for i, x in enumerate(out, 1):
        print(f"[{i}] {x['id']} | {x['symbol']} p.{x['page']} | {x['stratum']} | {x['tag']} | draft {x['draft']}")
        print(f"    set by  {x['setter']}")
        print(f"    speech  {x['speech']}\n")
    (ROOT / "eval" / "article_tag_sample.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
