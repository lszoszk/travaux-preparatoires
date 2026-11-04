#!/usr/bin/env python3
"""Draw the sample of a quality-audit round (the design of rounds 43 and 53), for blind judges.

Precision: tagged speeches drawn from every kind of record (eval/quality_audit.py's strata) in proportion to its tags,
at least two per kind; and report paragraphs tagged from the reports' sections and annexes read by hand ("/reports/");
and, apart from the audit, paragraphs of the L-series drafts and amendments ("Covenants/l-series/check").
Coverage: untagged speeches over 150 characters, R1 from records with at least one tag, R2 from records with none.

Each item carries what a judge needs: the tag (instrument, final article, title), the record's draft number, the final
text, the heading or chair's line before it, and the speech or paragraph. Writes the sample to --out (JSON), outside the
repository; the judges' answers go to data/gold/ through eval/audit_record.py.

Usage: python3 eval/audit_sample.py --round 65 --out /tmp/audit65.json [--speeches 126 --reports 30 --lseries 10 --r1 50 --r2 60]
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
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "api"))
from quality_audit import EARLY, LONG, stratum as _stratum  # noqa: E402


def stratum(corpus, stage, symbol, body, session, art_instr) -> str:
    """quality_audit's strata, with the early UDHR records named by their stage so that the audit counts them ("/audit")."""
    st = _stratum(corpus, stage, symbol, body, session, art_instr)
    return f"UDHR/{EARLY[symbol]}/early/audit" if st == "UDHR early (other)" else st
import server  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--speeches", type=int, default=126)
    ap.add_argument("--reports", type=int, default=30)
    ap.add_argument("--lseries", type=int, default=10)
    ap.add_argument("--r1", type=int, default=50)
    ap.add_argument("--r2", type=int, default=60)
    args = ap.parse_args()
    rng = random.Random(args.round)
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    con.row_factory = sqlite3.Row
    titles = {i: server.article_titles(i) for i in ("UDHR", "ICCPR", "ICESCR")}
    finals = {i: server.final_texts(i) for i in ("UDHR", "ICCPR", "ICESCR")}

    def setter(r) -> str:
        b = con.execute("SELECT kind, text FROM segments WHERE symbol = ? AND seq < ? AND (kind = 'heading' OR (kind IN "
                        "('chair', 'procedural', 'vote') AND lower(text) LIKE '%article%')) ORDER BY seq DESC LIMIT 1",
                        (r["symbol"], r["seq"])).fetchone()
        return f"{b['kind']}: {b['text'][:500]}" if b else ""

    def item(r, st, **extra) -> dict:
        inst = (r["article_instrument"] or "").split("+")[0]
        tag = f"{r['article_instrument']} art. {r['final_article']} ({titles.get(inst, {}).get(str(r['final_article']), '')})" if r["final_article"] else None
        who = f"{r['speaker']} ({r['delegation']}): " if r["speaker"] else ""
        return {"id": r["id"], "symbol": r["symbol"], "page": r["page_start"], "stratum": st, "tag": tag, "draft": r["draft_article"],
                "final_text": (finals.get(inst, {}).get(str(r["final_article"]), "")[:700] if r["final_article"] else ""),
                "setter": setter(r), "speech": (who + (r["text"] or ""))[:1800], **extra}

    rows = con.execute("SELECT s.*, d.instrument corpus, d.stage, d.body, d.session FROM segments s JOIN documents d USING(symbol) "
                       "WHERE s.kind = 'speech'").fetchall()
    tagged = defaultdict(list)
    for r in rows:
        if r["final_article"] is not None:
            tagged[stratum(r["corpus"], r["stage"], r["symbol"], r["body"], r["session"], r["article_instrument"])].append(r)
    total = sum(len(v) for v in tagged.values())
    alloc = {s: max(2, round(args.speeches * len(v) / total)) for s, v in tagged.items()}
    sample = []
    for s, v in sorted(tagged.items()):
        rng.shuffle(v)
        sample += [item(r, s, kind="P") for r in v[:alloc[s]]]
    # the reports' paragraphs, tagged from the sections and annexes read by hand
    rep = con.execute("SELECT s.*, d.instrument corpus FROM segments s JOIN documents d USING(symbol) WHERE s.kind != 'masthead' "
                      "AND s.final_article IS NOT NULL AND s.article_mapping LIKE '%read by hand)%'").fetchall()
    rep = list(rep)
    rng.shuffle(rep)
    sample += [item(r, f"{r['corpus']}/reports/audit", kind="P") for r in rep[:args.reports]]
    lser = con.execute("SELECT s.*, d.instrument corpus FROM segments s JOIN documents d USING(symbol) WHERE s.kind != 'masthead' "
                       "AND s.final_article IS NOT NULL AND s.article_mapping LIKE '%the debates that cite it%' AND length(s.text) > 80").fetchall()
    lser = list(lser)
    rng.shuffle(lser)
    sample += [item(r, "Covenants/l-series/check", kind="P") for r in lser[:args.lseries]]
    # coverage: untagged long speeches, in records with tags (R1) and without (R2)
    with_tags = {r["symbol"] for r in rows if r["final_article"] is not None}
    un = [r for r in rows if r["final_article"] is None and len(r["text"] or "") > LONG]
    for name, pool, n in (("R1", [r for r in un if r["symbol"] in with_tags], args.r1), ("R2", [r for r in un if r["symbol"] not in with_tags], args.r2)):
        rng.shuffle(pool)
        for r in pool[:n]:
            m = r["article_mapping"] or ""
            why = "Jev" if m.startswith("not tagged: Jev") else (m.split(":")[0] if m else "no article context")
            sample.append(item(r, stratum(r["corpus"], r["stage"], r["symbol"], r["body"], r["session"], r["article_instrument"]),
                               kind="R", sample=name, untagged_because=why))
    args.out.write_text(json.dumps(sample, ensure_ascii=False, indent=1))
    by = defaultdict(int)
    for x in sample:
        by[x["kind"] + ":" + (x.get("sample") or x["stratum"])] += 1
    print(len(sample), dict(sorted(by.items())), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
