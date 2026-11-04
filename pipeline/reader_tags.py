#!/usr/bin/env python3
"""Article tags for the speeches the rules leave untagged, from readers of the whole record.

  prepare  python3 pipeline/reader_tags.py prepare --out DIR SYMBOL...   one JSON per record for the readers
  decide   python3 pipeline/reader_tags.py decide RESULTS.json [--jev]   the readers' answers -> the two tables

A reader (an agent) gets a meeting record whole: each segment with its speaker and delegation, the tags the pipeline
already gave, the headings and the chair's lines, the session's numbering of the articles (the draft number -> the
final article, and the final articles the session's report lists for the meeting) and the catalogue of final articles.
It gives each untagged speech the final article it is mainly about, or none, with its certainty. Two readers of
different models read each record without seeing each other's answer.

A wrong tag is worse than none. A speech is tagged only when both readers give the same article, neither as a guess
and at least one sure of it (the record itself shows it), and Jev (pipeline/jev_articles.py's question, same cache) says the speech is about it at JEV_MIN or more:
data/concordance/reader_tags.csv, which api/build_db.py applies to speeches with no tag (it never replaces a tag the
rules gave) and pipeline/resegment.py migrates. Every other article a reader gave goes to
data/concordance/possible_articles.csv: metadata only, used by no filter or count.

  retag    python3 pipeline/reader_tags.py retag RESULTS.json [--jev] [--out CANDIDATES.json]
  accept   python3 pipeline/reader_tags.py accept CANDIDATES.json IDS.json

A targeted re-read (the readers were asked only about two final articles, whatever tag a speech has: eval of UDHR 5 and 8)
can also move a speech from the article its debate was filed under to the one it is about (the Third Committee debated the
torture clause of E/800 article 4, and the Mexican remedy amendment inside the debate on article 7). `retag` sorts the
readers' answers: an untagged speech goes the reader_tags way; a speech tagged with the article its debate was filed
under (UDHR 4 -> 5, UDHR 7 -> 8) is a retag only if both readers are sure; a speech tagged otherwise (the Covenant
articles on the same subject, for instance) is left alone. Jev must say yes at JEV_MIN or more. `accept` writes what a
blind check by judges (their ids in IDS.json) let through: untagged speeches to reader_tags.csv, retags to
data/concordance/speech_retags.csv, which api/build_db.py applies last.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "api"))
TABLE = ROOT / "data" / "concordance" / "reader_tags.csv"
RETAGS = ROOT / "data" / "concordance" / "speech_retags.csv"
RETAG_FIELDS = ["segment_id", "instrument", "final_article", "previous", "jev", "note"]
# the article a debate was filed under -> the article a speech inside it may really be about
REFILED = {("UDHR", 4, 5), ("UDHR", 7, 8)}
POSSIBLE = ROOT / "data" / "concordance" / "possible_articles.csv"
FIELDS = ["segment_id", "instrument", "final_article", "draft_article", "jev", "note"]
JEV_MIN = 0.7


def numbering(con, doc) -> list[str]:
    import build_db  # noqa: E402
    from articles import load_concordance  # noqa: E402
    lines = []
    conc = load_concordance()
    cconc = build_db.load_covenant_concordance()
    st = doc["stage"]
    if st in getattr(build_db, "TWO_TEXT_STAGES", {}):
        decl, conv = build_db.TWO_TEXT_STAGES[st]
        for (s, d), (fin, _) in sorted(conc.items(), key=lambda kv: (int(re.match(r"\d+", kv[0][1]).group(0)), kv[0][1])):
            if s == decl and fin:
                lines.append(f"Declaration draft article {d} -> UDHR {fin}")
        for k, v in sorted(cconc.items(), key=lambda kv: str(kv)):
            if len(k) == 3 and k[0] == conv and isinstance(v, int):
                lines.append(f"Convention draft article {k[2]} -> final {k[1]} {v}")
    elif doc["instrument"] == "UDHR" and st and st not in build_db.STAGE_SYMBOL:
        for (s, d), (fin, _) in sorted(conc.items(), key=lambda kv: (int(re.match(r"\d+", kv[0][1]).group(0)), kv[0][1])):
            if s == st and fin:
                lines.append(f"draft article {d} -> UDHR {fin}")
    cst = st if st in build_db.STAGE_SYMBOL else (build_db.covenant_stage(doc["body"], doc["meeting_date"], doc["session"]) if doc["instrument"] == "Covenants" else None)
    if cst:
        for k, v in sorted(cconc.items(), key=lambda kv: str(kv)):
            if len(k) == 3 and k[0] == cst and isinstance(v, int):
                lines.append(f"{k[1]} draft article {k[2]} -> final {k[1]} {v}")
        m = re.search(r"/SR\.(\d+)", doc["symbol"])
        if m:
            for k, v in cconc.items():
                if len(k) == 4 and k[0] == cst and k[1] == "meetings" and int(m.group(1)) in v:
                    lines.append(f"the session's report lists this meeting among those on final {k[2]} {k[3]}")
    return lines


def catalogue() -> list[str]:
    from jev_articles import titles  # noqa: E402
    return [f"{i} {n}: {t}" for (i, n), t in sorted(titles().items())]


def prepare(out: Path, symbols: list[str]) -> None:
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    con.row_factory = sqlite3.Row
    out.mkdir(parents=True, exist_ok=True)
    for sym in symbols:
        doc = con.execute("SELECT * FROM documents WHERE symbol = ?", (sym,)).fetchone()
        segs = [{"id": s["id"], "seq": s["seq"], "kind": s["kind"], "page": s["page_start"],
                 "speaker": s["speaker"], "delegation": s["delegation"],
                 "tag": f"{s['article_instrument']} {s['final_article']}" if s["final_article"] else None,
                 "draft": s["draft_article"], "text": (s["text"] or "")[:1800]}
                for s in con.execute("SELECT * FROM segments WHERE symbol = ? AND kind != 'masthead' ORDER BY seq", (sym,))]
        todo = [s["id"] for s in segs if s["kind"] == "speech" and not s["tag"] and len(s["text"]) > 150]
        rec = {"symbol": sym, "body": doc["body"], "session": doc["session"], "date": doc["meeting_date"],
               "corpus": doc["instrument"], "stage": doc["stage"], "numbering": numbering(con, doc), "catalogue": catalogue(), "to_tag": todo, "segments": segs}
        (out / (sym.replace("/", "_") + ".json")).write_text(json.dumps(rec, ensure_ascii=False, indent=1))
        print(f"{sym}: {len(segs)} segments, {len(todo)} to tag, {len(rec['numbering'])} numbering lines", file=sys.stderr)


def label(a: dict | None) -> str:
    if not a or a.get("instrument") in (None, "none") or not a.get("final_article"):
        return "none"
    inst = a["instrument"]
    if a["final_article"] == 1 and inst in ("ICCPR", "ICESCR"):
        inst = "ICCPR+ICESCR"
    return f"{inst} {a['final_article']}"


def decide(results: Path, ask_jev: bool, note: str) -> None:
    """A tag needs: both readers give the same article, neither as a guess and one sure of it, and Jev says yes at
    JEV_MIN or more.
    Every other article a reader gave (not as a guess) goes to the table of possible articles, which nothing uses."""
    import jev_articles as ja  # noqa: E402
    res = json.loads(results.read_text())
    res = res.get("result", res) if isinstance(res, dict) else res
    by = {}
    for r in res:
        by.setdefault(r["file"], {})[r["model"]] = {x["id"]: x for x in (r["answers"] or [])}
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    texts, names, cache = ja.final_texts(), ja.titles(), ja.load_cache()
    agreed, possible = {}, {}
    for rec in by.values():
        a, b = rec.get("opus", {}), rec.get("sonnet", {})
        for sid in set(a) | set(b):
            la, lb = label(a.get(sid)), label(b.get(sid))
            sure = [x for x in (a.get(sid), b.get(sid)) if x and label(x) != "none" and x["certainty"] != "guess"]
            # (pilot, 12 records: of the tags two readers agreed on, the 30 where one was sure were all right on a blind
            # check; of the 24 where both were only "probable", 3 were wrong)
            if la == lb != "none" and len(sure) == 2 and "sure" in (a[sid]["certainty"], b[sid]["certainty"]):
                agreed[sid] = (la, a[sid])
            elif sure:
                possible[sid] = sorted({f"{label(x)} ({x['certainty']})" for x in sure})
    todo = []
    for sid, (lab, x) in agreed.items():
        inst, fin = lab.rsplit(" ", 1)
        k = ja.key(sid, inst, int(fin), x.get("draft_article"))
        if cache.get(k) is None:
            text = con.execute("SELECT text FROM segments WHERE id = ?", (sid,)).fetchone()[0]
            i1 = inst.split("+")[0]
            todo.append({"key": k, "state": ja.item_state(i1, int(fin), x.get("draft_article"), text,
                                                         names.get((i1, int(fin)), ""), texts.get((i1, int(fin)), ""))})
    if todo and not ask_jev:
        print(f"{len(todo)} agreed tags not yet checked by Jev: rerun with --jev (sends the speeches to TypeSafe)", file=sys.stderr)
        return
    for k in range(0, len(todo), 20):
        cache.update(ja.ask_batch(todo[k:k + 20]))
        ja.CACHE.write_text(json.dumps(cache))
    rows = {r["segment_id"]: r for r in csv.DictReader(TABLE.open())} if TABLE.exists() else {}
    poss = {r["segment_id"]: r for r in csv.DictReader(POSSIBLE.open())} if POSSIBLE.exists() else {}
    kept = 0
    for sid, (lab, x) in agreed.items():
        inst, fin = lab.rsplit(" ", 1)
        pj = cache.get(ja.key(sid, inst, int(fin), x.get("draft_article")))
        if pj is not None and pj >= JEV_MIN:
            rows[sid] = {"segment_id": sid, "instrument": inst, "final_article": fin, "draft_article": x.get("draft_article") or "",
                         "jev": f"{pj:.2f}", "note": f"{note}: {x.get('reason', '')[:140]}"}
            poss.pop(sid, None)
            kept += 1
        else:
            poss[sid] = {"segment_id": sid, "articles": f"{lab} (two readers; Jev {pj if pj is None else round(pj, 2)})"}
    for sid, labs in possible.items():
        if sid not in rows:
            poss[sid] = {"segment_id": sid, "articles": "; ".join(labs) + " (one reader, or two readers apart)"}
    for path, fields, data in ((TABLE, FIELDS, rows), (POSSIBLE, ["segment_id", "articles"], poss)):
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(sorted(data.values(), key=lambda r: r["segment_id"]))
    print(f"{len(agreed)} agreed by both readers; {kept} kept after Jev (>= {JEV_MIN}); table {len(rows)}; "
          f"possible articles {len(poss)}", file=sys.stderr)


def retag(results: Path, ask_jev: bool, out: Path) -> None:
    """The candidates of a targeted re-read, with Jev's answer; nothing is written to the tables (see `accept`)."""
    import jev_articles as ja  # noqa: E402
    res = json.loads(results.read_text())
    res = res.get("result", res) if isinstance(res, dict) else res
    by = {}
    for r in res:
        by.setdefault(r["file"], {})[r["model"]] = {x["id"]: x for x in (r["answers"] or [])}
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    texts, names, cache = ja.final_texts(), ja.titles(), ja.load_cache()
    cands, left = [], []
    for rec in by.values():
        a, b = rec.get("opus", {}), rec.get("sonnet", {})
        for sid in sorted(set(a) & set(b)):
            if a[sid]["article"] != b[sid]["article"]:
                continue
            art = a[sid]["article"]
            certs = (a[sid]["certainty"], b[sid]["certainty"])
            seg = con.execute("SELECT kind, article_instrument, final_article, article_mapping, text FROM segments WHERE id = ?", (sid,)).fetchone()
            if not seg or seg[0] != "speech":
                continue
            now = (seg[1], seg[2])
            if now == ("UDHR", art):
                continue
            if now[1] is None:
                mode = "tag"
                if "organisation of work" in (seg[3] or "") or "sure" not in certs:
                    left.append((sid, "untagged; judged procedural, or neither reader sure"))
                    continue
            elif (now[0], now[1], art) in REFILED and certs == ("sure", "sure"):
                mode = "retag"
            else:
                left.append((sid, f"tagged {now[0]} {now[1]}, readers say UDHR {art} ({'/'.join(certs)})"))
                continue
            k = ja.key(sid, "UDHR", art, None)
            cands.append({"id": sid, "mode": mode, "now": f"{now[0]} {now[1]}" if now[1] else "untagged", "article": art, "certainty": "/".join(certs),
                          "reason": a[sid].get("reason", ""), "key": k,
                          "state": ja.item_state("UDHR", art, None, seg[4], names.get(("UDHR", art), ""), texts.get(("UDHR", art), ""))})
    todo = [c for c in cands if cache.get(c["key"]) is None]
    if todo and not ask_jev:
        print(f"{len(todo)} candidates not yet checked by Jev: rerun with --jev (sends the speeches to TypeSafe)", file=sys.stderr)
        return
    for k in range(0, len(todo), 20):
        cache.update(ja.ask_batch([{"key": c["key"], "state": c["state"]} for c in todo[k:k + 20]]))
        ja.CACHE.write_text(json.dumps(cache))
    for c in cands:
        c["jev"] = cache.get(c["key"])
        del c["state"]
    ok = [c for c in cands if c["jev"] is not None and c["jev"] >= JEV_MIN]
    out.write_text(json.dumps({"candidates": ok, "jev_below": [c for c in cands if c not in ok], "left_alone": left}, indent=1))
    print(f"{len(cands)} candidates ({sum(c['mode'] == 'retag' for c in cands)} retags); {len(ok)} with Jev >= {JEV_MIN}; "
          f"{len(left)} left alone; -> {out}", file=sys.stderr)


def accept(candidates: Path, ids: Path, note: str) -> None:
    """Write what the blind check let through: untagged -> reader_tags.csv, retags -> speech_retags.csv."""
    cands = {c["id"]: c for c in json.loads(candidates.read_text())["candidates"]}
    keep = [cands[i] for i in json.loads(ids.read_text()) if i in cands]
    tags = {r["segment_id"]: r for r in csv.DictReader(TABLE.open())} if TABLE.exists() else {}
    retags = {r["segment_id"]: r for r in csv.DictReader(RETAGS.open())} if RETAGS.exists() else {}
    for c in keep:
        if c["mode"] == "tag":
            tags[c["id"]] = {"segment_id": c["id"], "instrument": "UDHR", "final_article": str(c["article"]), "draft_article": "",
                             "jev": f"{c['jev']:.2f}", "note": f"{note}: {c['reason'][:140]}"}
        else:
            retags[c["id"]] = {"segment_id": c["id"], "instrument": "UDHR", "final_article": str(c["article"]), "previous": c["now"],
                               "jev": f"{c['jev']:.2f}", "note": f"{note}: {c['reason'][:140]}"}
    for path, fields, data in ((TABLE, FIELDS, tags), (RETAGS, RETAG_FIELDS, retags)):
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(sorted(data.values(), key=lambda r: r["segment_id"]))
    print(f"{len(keep)} accepted ({sum(c['mode'] == 'tag' for c in keep)} new tags, {sum(c['mode'] == 'retag' for c in keep)} retags); "
          f"reader_tags {len(tags)}, speech_retags {len(retags)}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("symbols", nargs="+")
    q = sub.add_parser("decide")
    q.add_argument("results", type=Path)
    q.add_argument("--jev", action="store_true", help="ask Jev about the agreed tags (sends the speeches to TypeSafe)")
    q.add_argument("--label", default="two readers of the record agree, Jev confirms")
    r = sub.add_parser("retag")
    r.add_argument("results", type=Path)
    r.add_argument("--jev", action="store_true", help="ask Jev about the candidates (sends the speeches to TypeSafe)")
    r.add_argument("--out", type=Path, required=True)
    t = sub.add_parser("accept")
    t.add_argument("candidates", type=Path)
    t.add_argument("ids", type=Path)
    t.add_argument("--label", default="re-read for UDHR 5 and 8: two readers sure, Jev confirms, a blind check agrees")
    args = ap.parse_args()
    if args.cmd == "prepare":
        prepare(args.out, args.symbols)
    elif args.cmd == "retag":
        retag(args.results, args.jev, args.out)
    elif args.cmd == "accept":
        accept(args.candidates, args.ids, args.label)
    else:
        decide(args.results, args.jev, args.label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
