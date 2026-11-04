#!/usr/bin/env python3
"""Candidate article tags from Schabas's index (preregistered in docs/devlog.md, 21 Oct 2026). PRIVATE INPUT; the output
holds only segment ids, article numbers and book page numbers, never the book's text.

Schabas's "Table of provisions" gives, for each UDHR article, the book pages where it is discussed
(data/private/schabas_provisions.json, from eval/schabas_index_check.py). A book page belongs to one or two UN documents
(their exact book pages: eval/private/reference/*.json pdf_pages - 127) and holds one or more of their UN pages
(data/private/schabas_pagemap.json, from eval/schabas_reference.py). The UN page's text, as Schabas reprints it, is cut
into sentence-sized pieces (eval/ocr_bench.py ref_segments) and each piece is located in the record's own text
(locate_span); a segment is on that UN page when a piece of it scores MIN_FOUND (88) or more there. The alignment of every
record is cached (data/private/schabas_alignment.json) for eval/schabas_coverage.py.

A candidate is an untagged speech over 150 characters on a page the index gives for an article. The gate (--jev):
- one candidate article: the Jev check (pipeline/jev_articles.py), "tag" at p >= 0.7 (the 1946-48 threshold);
- several: Jev's choice among them (cache data/cache/jev_schabas_choice.json), "tag" when the pick is one of them at
  p >= 0.9 and the check on the pick gives >= 0.7;
everything else is "possible" (metadata only). Written: data/concordance/schabas_candidates.csv.

  python3 eval/schabas_candidates.py             # alignment and candidates, counts (no Jev)
  python3 eval/schabas_candidates.py --jev       # the gate (sends the speeches to TypeSafe)
  python3 eval/schabas_candidates.py --sample 60 --seed 1 --out eval/schabas_check_sample.json   # acceptance sample
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "pipeline"))
from ocr_bench import MIN_FOUND, MIN_SEG, locate_span, norm, ref_segments  # noqa: E402

PRIVATE = ROOT / "data" / "private"
REF = ROOT / "eval" / "private" / "reference"
ALIGN = PRIVATE / "schabas_alignment.json"
OUT = ROOT / "data" / "concordance" / "schabas_candidates.csv"
CHOICE_CACHE = ROOT / "data" / "cache" / "jev_schabas_choice.json"
CHECK_MIN, CHOICE_MIN = 0.7, 0.9
FIELDS = ["segment_id", "symbol", "instrument", "final_article", "draft_article", "book_pages", "un_pages", "gate", "jev",
          "verdict", "note"]
# the records that have no tag at all and that the index covers densely (eval/schabas_index_check.py, 20 Oct)
UNTAGGED_DEBATES = ["A/C.3/SR.88", "A/C.3/SR.89", "A/C.3/SR.90", "A/C.3/SR.91", "A/C.3/SR.92", "A/C.3/SR.93", "A/PV.180",
                    "A/PV.181", "A/PV.182", "A/PV.183", "E/SR.215", "E/CN.4/SR.23", "E/CN.4/SUB.2/SR.10",
                    "E/CN.4/SUB.2/SR.11", "E/CN.4/SUB.2/SR.17"]


def doc_ranges() -> dict[str, list[tuple[int, int]]]:
    out = defaultdict(list)
    for f in REF.glob("*.json"):
        d = json.loads(f.read_text())
        out[d["symbol"]] += [(a - 127, b - 127) for a, b in d.get("pdf_pages", [])]
    return out


def align_record(con: sqlite3.Connection, symbol: str, ref_pages: dict[str, str]) -> dict[str, list[str]]:
    """UN page label -> ids of the record's segments that hold at least one of its pieces (score >= MIN_FOUND)."""
    rows = con.execute("SELECT id, text FROM segments WHERE symbol = ? ORDER BY seq", (symbol,)).fetchall()
    text, bounds = "", []
    for sid, t in rows:
        start = len(text)
        text += norm(t or "") + "   "
        bounds.append((start, len(text), sid))
    out = {}
    for label, page_text in ref_pages.items():
        hits = set()
        for piece in ref_segments({label: page_text}):
            if len(piece) < MIN_SEG:
                continue
            score, _, a, b = locate_span(piece, text)
            if score < MIN_FOUND:
                continue
            mid = (a + b) // 2
            for s0, s1, sid in bounds:
                if s0 <= mid < s1:
                    hits.add(sid)
                    break
        out[label] = sorted(hits)
    return out


def alignment(con: sqlite3.Connection, symbols: set[str], refresh: bool = False) -> dict[str, dict[str, list[str]]]:
    cache = json.loads(ALIGN.read_text()) if ALIGN.exists() and not refresh else {}
    todo = sorted(s for s in symbols if s not in cache)
    for k, sym in enumerate(todo, 1):
        f = REF / f"{re.sub(r'[^A-Za-z0-9._-]+', '_', sym).strip('_')}.json"
        cache[sym] = align_record(con, sym, json.loads(f.read_text())["pages"]) if f.exists() else {}
        if k % 25 == 0 or k == len(todo):
            ALIGN.write_text(json.dumps(cache))
            print(f"  aligned {k}/{len(todo)} records", file=sys.stderr, flush=True)
    return cache


def index_cells(held: set[str]) -> dict[tuple[str, str], dict[str, set]]:
    """(symbol, UN page label) -> {article: book pages} for every index reference that lands on a held document."""
    prov = json.loads((PRIVATE / "schabas_provisions.json").read_text())
    pagemap = json.loads((PRIVATE / "schabas_pagemap.json").read_text())
    ranges = doc_ranges()
    by_page = defaultdict(set)
    for sym, rs in ranges.items():
        if sym in held:
            for a, b in rs:
                for p in range(a, b + 1):
                    by_page[p].add(sym)
    cells = defaultdict(lambda: defaultdict(set))
    for art, pages in prov.items():
        if art == "preamble":
            continue
        for p in pages:
            for sym in by_page.get(p, ()):
                for label in pagemap.get(sym, {}).get(str(p), []):
                    cells[(sym, label)][int(art)].add(p)
    return cells


def drafts_by_stage() -> dict[tuple[str, int], str]:
    """(stage, final article) -> the stage's own number for it, where only one draft article maps to it."""
    from articles import load_concordance
    inv = defaultdict(set)
    for (stage, draft), (final, _) in load_concordance().items():
        if final:
            inv[(stage, int(final))].add(str(draft))
    return {k: next(iter(v)) for k, v in inv.items() if len(v) == 1}


def build(con: sqlite3.Connection) -> list[dict]:
    held = {s for (s,) in con.execute("SELECT symbol FROM documents WHERE instrument = 'UDHR'")}
    cells = index_cells(held)
    records = {sym for sym, _ in cells}
    al = alignment(con, records)
    segs = {sid: (sym, kind, fin, text, stage) for sid, sym, kind, fin, text, stage in con.execute(
        "SELECT s.id, s.symbol, s.kind, s.final_article, s.text, d.stage FROM segments s JOIN documents d USING(symbol) "
        "WHERE d.instrument = 'UDHR'")}
    drafts = drafts_by_stage()
    cand = defaultdict(lambda: {"book": set(), "un": set()})
    for (sym, label), arts in cells.items():
        for sid in al.get(sym, {}).get(label, []):
            s = segs.get(sid)
            if not s or s[1] != "speech" or s[2] is not None or len((s[3] or "").strip()) <= 150:
                continue
            for art, pages in arts.items():
                c = cand[(sid, art)]
                c["book"] |= pages
                c["un"].add(label)
    rows = []
    for (sid, art), c in sorted(cand.items()):
        sym, _, _, _, stage = segs[sid]
        rows.append({"segment_id": sid, "symbol": sym, "instrument": "UDHR", "final_article": art,
                     "draft_article": drafts.get((stage, art), "") if stage else "",
                     "book_pages": " ".join(map(str, sorted(c["book"]))), "un_pages": " ".join(sorted(c["un"], key=lambda x: int(x) if x.isdigit() else 0)),
                     "gate": "", "jev": "", "verdict": "", "note": ""})
    n_per = Counter(r["segment_id"] for r in rows)
    for r in rows:
        r["gate"] = "check" if n_per[r["segment_id"]] == 1 else "choice"
    return rows


def gate(con: sqlite3.Connection, rows: list[dict]) -> None:
    import jev
    import jev_articles as ja
    texts, names = ja.final_texts(), ja.titles()
    check_cache, choice_cache = ja.load_cache(), (json.loads(CHOICE_CACHE.read_text()) if CHOICE_CACHE.exists() else {})
    seg_text = {sid: (t, seq) for sid, t, seq in con.execute("SELECT id, text, seq FROM segments WHERE kind = 'speech'")}
    # 1. several candidate articles on one speech: Jev's choice among them
    from jev_article_choice import INSTRUCTIONS_RECORD, NONE, options_record
    titles_str = {(k[0], str(k[1])): v for k, v in names.items()}
    by_seg = defaultdict(list)
    for r in rows:
        if r["gate"] == "choice":
            by_seg[r["segment_id"]].append(r)
    groups = defaultdict(list)
    for sid, rs in by_seg.items():
        if sid not in choice_cache:
            opts = tuple(sorted((r["final_article"], r["draft_article"]) for r in rs))
            groups[(rs[0]["symbol"], opts)].append(sid)
    n = 0
    for (sym, opts), sids in groups.items():
        options = options_record([("UDHR", int(a), d) for a, d in opts], titles_str)
        for k in range(0, len(sids), 15):
            chunk = sids[k:k + 15]
            state = {"articles_of_this_meeting": list(options.values()), "speeches": {}}
            for j, sid in enumerate(chunk):
                t, seq = seg_text[sid]
                prev = con.execute("SELECT text FROM segments WHERE symbol = ? AND seq < ? ORDER BY seq DESC LIMIT 1",
                                   (sym, seq)).fetchone()
                state["speeches"][f"S{j}"] = {"passage_before": " ".join((prev[0] if prev else "").split())[-500:],
                                              "speech": " ".join(t.split())[:1500]}
            qs = {f"S{j}": jev.choice(INSTRUCTIONS_RECORD.format(key=f"S{j}"), options) for j in range(len(chunk))}
            try:
                answers = jev.ask(state, qs, task="schabas_choice")
            except RuntimeError as exc:
                print(f"  {sym}: {exc}", file=sys.stderr)
                continue
            for j, sid in enumerate(chunk):
                a = answers.get(f"S{j}") or {}
                pick = a.get("choice")
                p = (a.get("probabilities") or {}).get(pick)
                choice_cache[sid] = {"pick": pick, "p": round(float(p), 3) if isinstance(p, (int, float)) else None}
            n += len(chunk)
        CHOICE_CACHE.write_text(json.dumps(choice_cache))
        print(f"  choice: asked {n}", file=sys.stderr, flush=True)
    # 2. the Jev check: single candidates, and the pick of each choice
    todo = {}
    for r in rows:
        art, d = int(r["final_article"]), r["draft_article"] or None
        if r["gate"] == "choice":
            c = choice_cache.get(r["segment_id"]) or {}
            if c.get("pick") != f"UDHR {art}" or (c.get("p") or 0) < CHOICE_MIN:
                continue
        k = ja.key(r["segment_id"], "UDHR", art, d)
        if check_cache.get(k) is None and k not in todo:
            t = seg_text[r["segment_id"]][0]
            todo[k] = {"key": k, "state": ja.item_state("UDHR", art, d, t, names.get(("UDHR", art), ""),
                                                        texts.get(("UDHR", art), ""))}
    items = list(todo.values())
    for k in range(0, len(items), 20):
        check_cache.update(ja.ask_batch(items[k:k + 20]))
        ja.CACHE.write_text(json.dumps(check_cache))
        print(f"  check: asked {min(k + 20, len(items))}/{len(items)}", file=sys.stderr, flush=True)
    # 3. verdicts
    for r in rows:
        art, d = int(r["final_article"]), r["draft_article"] or None
        p = check_cache.get(ja.key(r["segment_id"], "UDHR", art, d))
        pages = f"Schabas index p. {r['book_pages'].replace(' ', ', ')}"
        if r["gate"] == "choice":
            c = choice_cache.get(r["segment_id"]) or {}
            picked = c.get("pick") == f"UDHR {art}" and (c.get("p") or 0) >= CHOICE_MIN
            ok = picked and p is not None and p >= CHECK_MIN
            r["jev"] = f"{p:.3f}" if picked and p is not None else ""
            r["note"] = f"{pages}; Jev choice {c.get('pick')} ({c.get('p')})" + (f"; Jev check {p:.2f}" if picked and p is not None else "")
        else:
            ok = p is not None and p >= CHECK_MIN
            r["jev"] = f"{p:.3f}" if p is not None else ""
            r["note"] = f"{pages}; Jev check {p:.2f}" if p is not None else f"{pages}; not checked"
        r["verdict"] = "tag" if ok else "possible"


def report(rows: list[dict]) -> None:
    kind = lambda s: "A/PV" if s.startswith("A/PV.") else "A/C.3/SR" if s.startswith("A/C.3/SR.") else "typed record"
    segs = {r["segment_id"] for r in rows}
    print(f"{len(rows)} candidate (speech, article) pairs on {len(segs)} speeches in {len({r['symbol'] for r in rows})} records; "
          f"gate: {dict(Counter(r['gate'] for r in rows))}; verdicts: {dict(Counter(r['verdict'] or 'pending' for r in rows))}",
          file=sys.stderr)
    by = defaultdict(Counter)
    for r in rows:
        by[kind(r["symbol"])][r["verdict"] or "pending"] += 1
    for k, c in sorted(by.items()):
        print(f"  {k:12} {dict(c)}", file=sys.stderr)
    tagged = defaultdict(set)
    for r in rows:
        if r["verdict"] == "tag":
            tagged[r["symbol"]].add(r["segment_id"])
    for sym in UNTAGGED_DEBATES:
        rs = [r for r in rows if r["symbol"] == sym]
        print(f"  {sym:20} pairs {len(rs):3}  speeches {len({r['segment_id'] for r in rs}):3}  tagged speeches {len(tagged[sym]):3}",
              file=sys.stderr)


def sample(rows: list[dict], con: sqlite3.Connection, n: int, seed: int, out: Path) -> None:
    """Acceptance sample, in eval/audit_record.py's item shape."""
    tags = [r for r in rows if r["verdict"] == "tag"]
    pick = random.Random(seed).sample(tags, min(n, len(tags)))
    names = {(r["instrument"], int(r["article"])): r["short_title"] for r in csv.DictReader((ROOT / "data/concordance/articles.csv").open())
             if r["article"].isdigit()}
    items = []
    for r in pick:
        sym, page, seq, text = con.execute("SELECT symbol, page_start, seq, text FROM segments WHERE id = ?", (r["segment_id"],)).fetchone()
        prev = con.execute("SELECT text FROM segments WHERE symbol = ? AND seq < ? ORDER BY seq DESC LIMIT 1", (sym, seq)).fetchone()
        items.append({"id": r["segment_id"], "symbol": sym, "page": page, "stratum": "UDHR/schabas/check",
                      "tag": f"UDHR art. {r['final_article']} ({names.get(('UDHR', int(r['final_article'])), '')})",
                      "draft": r["draft_article"], "setter": r["note"],
                      "before": " ".join((prev[0] if prev else "").split())[-400:], "speech": " ".join(text.split())[:2000]})
    out.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(items)} items -> {out}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", action="store_true", help="run the gate (sends the speeches to TypeSafe)")
    ap.add_argument("--refresh", action="store_true", help="align the records again")
    ap.add_argument("--sample", type=int)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    if args.sample:
        rows = list(csv.DictReader(OUT.open()))
        sample(rows, con, args.sample, args.seed, args.out)
        return 0
    if args.refresh and ALIGN.exists():
        ALIGN.unlink()
    rows = build(con)
    if args.jev:
        gate(con, rows)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
