#!/usr/bin/env python3
"""The sample of the publication audit: speeches drawn at random from the database, by kind of record, each checked on the
scan in every field at once (eval/pub_audit.py; the annotators' guide is docs/audit_guide_pl.md).

Strata (by symbol and date): the Commission and its committees 1946-48; the Third Committee's printed records of 1948; the
Commission 1949-54; the Third Committee 1949-66; the plenaries (A/PV, E/PV); other bodies. Each gets a share of the sample
proportional to its speeches, and at least --min. An item carries what the database says (speaker, delegation, pages, the
article and its final text, the question of a general debate, the text) and the neighbouring segments for context.

  python3 eval/pub_audit_sample.py --n 300 --seed S --out eval/pub_audit/<name>     (the real draw: after the last merge)
  python3 eval/pub_audit_sample.py --n 6 --seed 1 --out eval/pub_audit/dev          (a try of the panel)
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
import server  # noqa: E402

STRATA = ["Commission and committees 1946-48", "Third Committee 1948 (printed)", "Commission 1949-54", "Third Committee 1949-66",
          "plenaries (A/PV, E/PV)", "other bodies"]


def stratum(symbol: str, date: str | None) -> str:
    year = int(date[:4]) if date else 0
    if "/PV." in symbol:
        return STRATA[4]
    if symbol.startswith("A/C.3/SR."):
        return STRATA[1] if year and year <= 1948 else STRATA[3]
    if symbol.startswith("E/CN.4/"):
        return STRATA[0] if year and year <= 1948 else STRATA[2]
    return STRATA[5]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--min", type=int, default=20, help="at least this many from each stratum (all of it, if it is smaller)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    con = sqlite3.connect(f"file:{server.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    segs = defaultdict(list)
    for r in con.execute("SELECT s.*, d.meeting_date, d.n_pages FROM segments s JOIN documents d ON d.symbol = s.symbol "
                         "WHERE s.kind != 'masthead' ORDER BY s.symbol, s.seq"):
        segs[r["symbol"]].append(dict(r))
    topics = dict(con.execute("SELECT id, topic FROM segment_topics").fetchall())
    labels = dict(con.execute("SELECT topic, label FROM topics").fetchall())
    titles = {(r["instrument"], str(r["article"])): r["short_title"] for r in
              __import__("csv").DictReader((ROOT / "data" / "concordance" / "articles.csv").open(encoding="utf-8"))}
    finals = {i: server.final_texts(i) for i in ("UDHR", "ICCPR", "ICESCR")}
    pool = defaultdict(list)
    for sym, rows in segs.items():
        for k, s in enumerate(rows):
            if s["kind"] == "speech":
                pool[stratum(sym, s["meeting_date"])].append((sym, k))
    total = sum(len(v) for v in pool.values())
    alloc = {st: min(len(pool[st]), max(args.min, round(args.n * len(pool[st]) / total))) for st in STRATA if pool[st]}
    rng = random.Random(args.seed)
    items = []
    for st in STRATA:
        for sym, k in sorted(rng.sample(pool[st], alloc.get(st, 0))):
            rows = segs[sym]
            s = rows[k]
            inst = (s["article_instrument"] or "").split("+")[0]
            items.append({
                "id": s["id"], "symbol": sym, "stratum": st, "date": s["meeting_date"], "pages_in_record": s["n_pages"],
                "page_start": s["page_start"], "page_end": s["page_end"], "pinpoint": server.pinpoint(s),
                "speaker": s["speaker"], "delegation": s["delegation"],
                "article": f"{s['article_instrument']} art. {s['final_article']}" if s["final_article"] else None,
                "article_title": titles.get((inst, str(s["final_article"])), "") if s["final_article"] else "",
                "final_text": finals.get(inst, {}).get(str(s["final_article"]), "")[:900] if s["final_article"] else "",
                "draft_article": s["draft_article"], "topic": topics.get(s["id"]),
                "topic_label": labels.get(topics.get(s["id"]), topics.get(s["id"])),
                "text": s["text"], "before": rows[k - 1]["text"][-500:] if k else "",
                "after": rows[k + 1]["text"][:300] if k + 1 < len(rows) else ""})
    # (in random order, so that an annotator who stops early leaves a random sample of every stratum, not the first strata)
    rng.shuffle(items)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "items.json").write_text(json.dumps({"seed": args.seed, "n": len(items), "allocation": alloc,
                                                     "database_built": __import__("datetime").date.fromtimestamp(server.DB.stat().st_mtime).isoformat(),
                                                     "items": items}, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(items)} speeches -> {args.out}/items.json; " + ", ".join(f"{k} {v}" for k, v in alloc.items()), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
