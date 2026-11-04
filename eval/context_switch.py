#!/usr/bin/env python3
"""Round 113: tags whose context a passing mention switched (docs/devlog.md, 30 Oct 2026).

  search            the A-B-A runs: the context article turns from A to B at a chair's, vote or procedural segment that names
                    article B with no words of taking it up, and returns to A after the run (E/CN.4/SR.171-0023: the chair
                    named article 20 of the Universal Declaration during the debate on draft article 19)
  decide RESULTS    the judges' answers (the workflow's result: per record, opus, sonnet and a third on splits): a tag stays if
                    two judges give its article; else it is refused (data/concordance/tag_rejections.csv), and a speech is
                    retagged (speech_retags.csv) when two judges give the same other article, neither as a guess and one sure,
                    and Jev says JEV_MIN or more (--jev sends those speeches to TypeSafe). Gold rows: stratum context113/check.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "pipeline"))
DB = ROOT / "data" / "travaux.sqlite3"
CONC = ROOT / "data" / "concordance"
JEV_MIN = 0.7
CHECKED = "2026-10-30, round 113 (context switched by a passing mention; two blind judges, opus and sonnet, a third on splits)"


def search(out: Path, remaining: bool = False, inputs_dir: Path | None = None) -> None:
    import build_db as b
    from reader_tags import catalogue, numbering
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    if not remaining:
        runs = []
        for (sym,) in con.execute("SELECT symbol FROM documents WHERE symbol LIKE '%/SR.%' OR symbol LIKE '%/PV.%'"):
            segs = con.execute("SELECT id, kind, draft_article, final_article, text FROM segments WHERE symbol = ? ORDER BY seq", (sym,)).fetchall()
            ctx = [s for s in segs if s[2]]
            for a in range(1, len(ctx)):
                s, prev = ctx[a], ctx[a - 1]
                if s[2] == prev[2] or s[1] not in ("chair", "vote", "procedural"):
                    continue
                A, B, e = prev[2], s[2], a
                while e + 1 < len(ctx) and ctx[e + 1][2] == B:
                    e += 1
                if not (e + 1 < len(ctx) and ctx[e + 1][2] == A):
                    continue
                ms = list(re.finditer(r"\barticles?\s+%s\b" % re.escape(B.split(".")[0]), s[4], re.I))
                taken = any(b.TAKES_UP_RE.search(s[4][max(0, m.end() - 90):m.end()]) or b.EXAMINATION_RE.search(s[4][max(0, m.end() - 90):m.end()])
                            or b.AMENDMENT_TO_RE.search(s[4][max(0, m.end() - 130):m.end()]) for m in ms)
                run = ctx[a:e + 1]
                runs.append({"symbol": sym, "start": s[0], "A": A, "B": B, "named": bool(ms), "taken": taken,
                             "ids": [x[0] for x in run], "tagged": [x[0] for x in run if x[3]]})
        sel = [r for r in runs if r["named"] and not r["taken"] and r["tagged"]]
        print(f"A-B-A runs {len(runs)}; named without taking up, with tags: {len(sel)} runs, {sum(len(r['tagged']) for r in sel)} tags, "
              f"{len({r['symbol'] for r in sel})} records", file=sys.stderr)
        out.write_text(json.dumps(sel, indent=1))
        return

    judged = set()
    for rno in (113, 122):
        rp = ROOT / "eval" / f"round{rno}" / "results.json"
        if rp.exists():
            judged |= {x["id"] for rec in json.loads(rp.read_text())["result"]
                       for m in ("opus", "sonnet") for x in (rec.get(m) or [])}
    g1, g2, g3 = set(), set(), set()
    by_sym: dict[str, set[str]] = {}
    for (sym,) in con.execute("SELECT symbol FROM documents WHERE symbol LIKE '%/SR.%' OR symbol LIKE '%/PV.%'"):
        segs = con.execute("SELECT id, kind, draft_article, final_article, article_instrument, article_mapping, text "
                           "FROM segments WHERE symbol = ? ORDER BY seq", (sym,)).fetchall()
        d_to_fin = {}
        for s in segs:
            if s[2] and s[3] and ("chair or agenda" in (s[5] or "") or "meeting" in (s[5] or "")):
                d_to_fin[s[2].split(".")[0]] = (s[4], s[3])
        ctx = [s for s in segs if s[2] and "blind check found" not in (s[5] or "")]
        for a in range(1, len(ctx)):
            s, prev = ctx[a], ctx[a - 1]
            A, B, e = prev[2], s[2], a
            A0, B0 = A.split(".")[0], B.split(".")[0]
            if A0 == B0 or s[1] not in ("chair", "vote", "procedural"):
                continue
            while e + 1 < len(ctx) and ctx[e + 1][2] == B:
                e += 1
            if not (e + 1 < len(ctx) and ctx[e + 1][2].split(".")[0] == A0):
                continue
            fin_A = d_to_fin.get(A0) or (prev[4], prev[3])
            for x in ctx[a:e + 1]:
                if x[3] and (x[4], x[3]) != fin_A and x[0] not in judged:
                    g1.add(x[0])
                    by_sym.setdefault(sym, set()).add(x[0])
        tagged = [s for s in segs if s[3] is not None]
        i = 1
        while i < len(tagged) - 1:
            if tagged[i][1] in ("chair", "vote", "procedural"):
                j = i
                while j + 1 < len(tagged) and tagged[j + 1][1] in ("chair", "vote", "procedural"):
                    j += 1
                fin_A = (tagged[i - 1][4], tagged[i - 1][3])
                if j + 1 < len(tagged) and (tagged[j + 1][4], tagged[j + 1][3]) == fin_A:
                    for s in tagged[i:j + 1]:
                        if (s[4], s[3]) != fin_A and s[0] not in judged:
                            g2.add(s[0])
                            by_sym.setdefault(sym, set()).add(s[0])
                i = j + 1
            else:
                i += 1
        i = 0
        while i < len(segs):
            if not segs[i][2]:
                i += 1
                continue
            d0, j = segs[i][2].split(".")[0], i
            while j + 1 < len(segs) and (not segs[j + 1][2] or segs[j + 1][2].split(".")[0] == d0):
                j += 1
            block = segs[i:j + 1]
            speeches = {(s[4], s[3]) for s in block if s[1] == "speech" and s[3] is not None}
            if speeches:
                for ns in block:
                    if ns[1] in ("chair", "vote", "procedural") and ns[3] is not None and (ns[4], ns[3]) not in speeches and ns[0] not in judged:
                        g3.add(ns[0])
                        by_sym.setdefault(sym, set()).add(ns[0])
            i = j + 1
    sel = [{"symbol": sym, "to_judge": sorted(ids)} for sym, ids in sorted(by_sym.items())]
    print(f"remaining context-switch & stranded tags: g1={len(g1)}, g2={len(g2)}, g3={len(g3)}, "
          f"union={sum(len(r['to_judge']) for r in sel)} in {len(sel)} records", file=sys.stderr)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sel, indent=1))
    if inputs_dir:
        inputs_dir.mkdir(parents=True, exist_ok=True)
        cat = catalogue()
        for r in sel:
            sym, ids = r["symbol"], set(r["to_judge"])
            doc = con.execute("SELECT * FROM documents WHERE symbol = ?", (sym,)).fetchone()
            all_segs = con.execute("SELECT id, seq, kind, page_start, speaker, delegation, text FROM segments "
                                   "WHERE symbol = ? AND kind != 'masthead' ORDER BY seq", (sym,)).fetchall()
            hit_ix = [idx for idx, s in enumerate(all_segs) if s["id"] in ids]
            keep_ix = {k for idx in hit_ix for k in range(max(0, idx - 12), min(len(all_segs), idx + 5))}
            win = [{"id": all_segs[k]["id"], "kind": all_segs[k]["kind"], "page": all_segs[k]["page_start"],
                    "speaker": all_segs[k]["speaker"], "delegation": all_segs[k]["delegation"],
                    "text": (all_segs[k]["text"] or "")[:1800]} for k in sorted(keep_ix)]
            rec = {"symbol": sym, "body": doc["body"], "session": doc["session"], "date": doc["meeting_date"],
                   "corpus": doc["instrument"], "numbering": numbering(con, doc), "catalogue": cat,
                   "note": "Only parts of the record are given (the segments listed, in order); a gap in the order means segments left out.",
                   "to_judge": sorted(ids), "segments": win}
            (inputs_dir / (sym.replace("/", "_") + ".json")).write_text(json.dumps(rec, ensure_ascii=False, indent=1))


def label(a: dict | None) -> str:
    from reader_tags import label as rl
    return rl({**a, "final_article": a.get("final_article")}) if a else "none"


def decide(results: Path, ask_jev: bool, round_no: int = 113) -> None:
    import jev_articles as ja
    res = json.loads(results.read_text())
    res = res.get("result", res) if isinstance(res, dict) else res
    con = sqlite3.connect(DB)
    retags = {r["segment_id"]: r for r in csv.DictReader((CONC / "speech_retags.csv").open())}
    rejected = {(r["segment_id"], r["instrument"], r["final_article"]) for r in csv.DictReader((CONC / "tag_rejections.csv").open())}
    texts, names, cache = ja.final_texts(), ja.titles(), ja.load_cache()
    checked_str = (CHECKED if round_no == 113 else
                   f"2026-10-31, round {round_no} (remaining A-B-A context switches and non-speech tags stranded by speech retags; "
                   f"two blind judges, opus and sonnet, a third on splits)")
    stratum = f"context{round_no}/check"
    rows, todo = [], []
    for rec in res:
        by = {m: {x["id"]: x for x in (rec.get(m) or [])} for m in ("opus", "sonnet", "third")}
        for sid in sorted(set(by["opus"]) | set(by["sonnet"])):
            seg = con.execute("SELECT kind, symbol, page_start, speaker, delegation, text, article_instrument, final_article, draft_article "
                              "FROM segments WHERE id = ?", (sid,)).fetchone()
            if not seg or not seg[7]:
                continue
            current = f"{seg[6]} {seg[7]}"
            answers = [by[m].get(sid) for m in ("opus", "sonnet", "third") if by[m].get(sid)]
            labs = [label(a) for a in answers]
            keep = labs.count(current) >= 2
            other = Counter(l for l in labs if l not in ("none", current))
            target, t_draft = None, None
            if not keep and seg[0] == "speech" and other:
                lab, n = other.most_common(1)[0]
                firm = [a for a in answers if label(a) == lab and a["certainty"] != "guess"]
                if n >= 2 and len(firm) >= 2 and any(a["certainty"] == "sure" for a in firm):
                    target = lab
                    inst, fin = target.rsplit(" ", 1)
                    d_row = con.execute("SELECT draft_article FROM segments WHERE symbol = ? AND article_instrument = ? "
                                        "AND final_article = ? AND draft_article IS NOT NULL LIMIT 1",
                                        (seg[1], inst, int(fin))).fetchone()
                    d0 = d_row[0].split(".")[0] if d_row and d_row[0] else ""
                    t_draft = d0 if d0.isdigit() else None
            rows.append({"id": sid, "seg": seg, "current": current, "labels": labs, "keep": keep,
                         "target": target, "t_draft": t_draft, "answers": answers})
            if target:
                inst, fin = target.rsplit(" ", 1)
                prefix = f"{sid}|{inst}|{int(fin)}|"
                if not any(k.startswith(prefix) and v is not None for k, v in cache.items()):
                    i1 = inst.split("+")[0]
                    k_d = ja.key(sid, inst, int(fin), t_draft)
                    todo.append({"key": k_d, "state": ja.item_state(i1, int(fin), t_draft, seg[5], names.get((i1, int(fin)), ""), texts.get((i1, int(fin)), ""))})
    if todo and not ask_jev:
        print(f"{len(todo)} retags not yet checked by Jev: rerun with --jev (sends the speeches to TypeSafe)", file=sys.stderr)
        return
    for k in range(0, len(todo), 20):
        cache.update(ja.ask_batch(todo[k:k + 20]))
        ja.CACHE.write_text(json.dumps(cache))
    new_rej, n_retag = [], 0
    date_label = "30 October 2026" if round_no == 113 else "31 October 2026"
    with (ROOT / "data" / "gold" / "article_tags.jsonl").open("a") as gold:
        for r in rows:
            sid, seg = r["id"], r["seg"]
            note = "; ".join(f"{m}: {label(a)} ({a['certainty']}): {a['reason']}" for m, a in zip(("opus", "sonnet", "third"), r["answers"]))
            gold.write(json.dumps({"id": sid, "symbol": seg[1], "page": seg[2], "stratum": stratum, "tag": r["current"],
                                   "draft": seg[8], "setter": "context: a chair's, vote or procedural segment named the article in passing",
                                   "speech": f"{seg[3] or seg[0].upper()} ({seg[4] or ''}): {seg[5]}"[:1500], "correct": r["keep"],
                                   "note": note[:600], "round": round_no, "checked": checked_str}, ensure_ascii=False) + "\n")
            if r["keep"]:
                continue
            inst, fin = r["current"].rsplit(" ", 1)
            jp = None
            if r["target"]:
                t_inst, t_fin = r["target"].rsplit(" ", 1)
                prefix = f"{sid}|{t_inst}|{int(t_fin)}|"
                jp = cache.get(ja.key(sid, t_inst, int(t_fin), r["t_draft"]))
                if jp is None:
                    jp = next((v for k, v in cache.items() if k.startswith(prefix) and v is not None), None)
            if r["target"] and jp is not None and jp >= JEV_MIN:
                old = retags.get(sid)
                previous = old["previous"] if old else r["current"]  # (a retag of a retag keeps the context tag it replaces)
                retags[sid] = {"segment_id": sid, "instrument": t_inst, "final_article": t_fin, "previous": previous, "jev": f"{jp:.2f}",
                               "note": f"a blind check (two judges, a third on splits), {date_label}, round {round_no} (context switched by a passing "
                                       f"mention): the speech is about {r['target']}, not {r['current']}; Jev confirms"}
                n_retag += 1
            elif (sid, inst, fin) not in rejected:
                new_rej.append([sid, inst, fin, f"a blind check (two judges, a third on splits, round {round_no}), {date_label}: the context "
                                                 f"had turned to this article on a passing mention; judges: {', '.join(r['labels'])}"])
    with (CONC / "speech_retags.csv").open("w", newline="") as f:
        fields = ["segment_id", "instrument", "final_article", "previous", "jev", "note"]
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(retags.values())
    with (CONC / "tag_rejections.csv").open("a", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(new_rej)
    kept = sum(r["keep"] for r in rows)
    print(f"judged {len(rows)}: kept {kept}, retagged {n_retag}, refused {len(new_rej)}; "
          f"third judge on {sum(len(r['answers']) == 3 for r in rows)}", file=sys.stderr)
    print(json.dumps(Counter((r["seg"][0], r["keep"]) for r in rows).most_common()), file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--remaining", action="store_true")
    s.add_argument("--inputs-dir", type=Path)
    d = sub.add_parser("decide")
    d.add_argument("results", type=Path)
    d.add_argument("--jev", action="store_true")
    d.add_argument("--round", type=int, default=113)
    a = ap.parse_args()
    if a.cmd == "search":
        search(a.out, a.remaining, a.inputs_dir)
    else:
        decide(a.results, a.jev, a.round)
    return 0


if __name__ == "__main__":
    sys.exit(main())
