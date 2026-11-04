#!/usr/bin/env python3
"""The sample for a blind review by hand of the preview (pipeline/preview_mixed.py) against the current database: is the vision
reader's database better where the two differ? eval/vlm_pilot/results_preview_mixed.md; the reviewer sees the scan and two
versions, A and B, in an order drawn per item, and does not know which is which.

Items (seed fixed):
- PAGES pages read by the vision reader on which the two databases divide the page differently (kind or speaker of the segments
  that start or run on it): the reviewer compares the two lists of turns with the scan;
- SPEAKERS speeches whose speaker changed within the same delegation (eval/preview_speakers.py, through the id map): the reviewer
  compares the two speakers with the opening on the scan;
- REPEATS of those items again, later in the order and with A and B swapped, to measure the reviewer's own consistency.
Written: eval/preview_review/items.json (what the page shows) and eval/preview_review/key.json (which version is the preview: not
shown by the page, read only by eval/preview_review_score.py).

  python3 eval/preview_review_build.py <copy> [--pages 35 --speakers 25 --repeats 6 --seed 2026]
  python3 eval/preview_review_build.py <copy> --pages 0 --speakers 30 --repeats 4 --seed 2027 --out eval/preview_review2 \
      --speakers-file eval/vlm_pilot/preview_speakers_2026-10-20_fixes.json --exclude eval/preview_review/items.json
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from segment import POSTTITLE_RE, SPEAKER_RE  # noqa: E402

OUT = ROOT / "eval" / "preview_review"
SEG_Q = ("SELECT seq, kind, coalesce(speaker, ''), coalesce(delegation, ''), page_start, page_end, text FROM segments "
         "WHERE symbol = ? AND ? BETWEEN page_start AND page_end AND kind NOT IN ('masthead', 'footnote') ORDER BY seq")


def flat(text: str) -> str:
    return " ".join(text.split())


def mask(text: str) -> str:
    """The name printed at a turn's opening, hidden: the common text is the vision reader's, whose names the preview's speakers
    were taken from, so a shown name would point to the preview. The reviewer reads the name on the scan."""
    m = SPEAKER_RE.match(text) or POSTTITLE_RE.match(text)
    if not m:
        return text
    a, b = m.span("name")
    return text[:a] + "▒▒▒" + text[b:]


def page_segments(con: sqlite3.Connection, symbol: str, page: int, page_text: str) -> list[dict]:
    """The segments that start or run on the page, each shown in the words of one common text of the page (the vision reader's):
    the current database's own text is the OCR vote's, and showing it would tell the reviewer which version is which. A segment
    is placed where its first words stand in the page's text (fuzzy, for the vote's garbled ones); one that runs on from the page
    before starts at the top."""
    from rapidfuzz import fuzz
    segs = [{"kind": k, "speaker": sp, "delegation": dl, "starts_here": ps == page, "_t": flat(t)}
            for _, k, sp, dl, ps, pe, t in con.execute(SEG_Q, (symbol, page))]
    pos = []
    for s in segs:
        if not s["starts_here"]:
            pos.append(0)
            continue
        head = s["_t"][:60]
        at = page_text.find(head[:40])
        if at < 0:
            al = fuzz.partial_ratio_alignment(head, page_text)
            at = al.dest_start if al and al.score >= 70 else None
        pos.append(at)
    for k, s in enumerate(segs):
        if pos[k] is None:
            s["text"] = "[the opening is not found in the page's text]"
        else:
            nxt = min([p for p in pos[k + 1:] if p is not None and p > pos[k]] or [len(page_text)])
            s["text"] = mask(page_text[pos[k]:nxt][:220])
        del s["_t"]
    return segs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("copy", type=Path)
    ap.add_argument("--pages", type=int, default=35)
    ap.add_argument("--speakers", type=int, default=25)
    ap.add_argument("--repeats", type=int, default=6)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--speakers-file", type=Path, default=ROOT / "eval" / "vlm_pilot" / "preview_speakers_2026-10-20.json")
    ap.add_argument("--exclude", type=Path, nargs="*", default=[], help="earlier rounds' items.json: none of their records is drawn again")
    args = ap.parse_args()
    seen = {it["symbol"] for f in args.exclude for it in json.loads(f.read_text())["items"]}
    rnd = random.Random(args.seed)
    old = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    new = sqlite3.connect(args.copy / "data" / "travaux.sqlite3")
    symbols = {s.replace("/", "_"): s for (s,) in old.execute("SELECT symbol FROM documents")}
    taken = json.loads((args.copy / "preview_manifest.json").read_text())["pages"]

    # pages divided differently
    pages = []
    for p in taken:
        safe, name = p.split("/")
        sym, page = symbols.get(safe), int(name[5:8])
        if not sym or sym in seen:
            continue
        text = flat((args.copy / "data" / "ocr" / safe / "vote" / name).read_text(encoding="utf-8"))
        a, b = page_segments(old, sym, page, text), page_segments(new, sym, page, text)
        if [(x["kind"], x["speaker"].upper()) for x in a] != [(x["kind"], x["speaker"].upper()) for x in b]:
            pages.append((sym, page, a, b))
    pages = rnd.sample(pages, min(args.pages, len(pages)))

    # speakers changed within the delegation
    sp = json.loads(args.speakers_file.read_text())["examples"]
    q0 = "SELECT symbol FROM segments WHERE id = ?"
    changes = [x for k in sorted(sp) for x in sp[k] if (old.execute(q0, (x["old_id"],)).fetchone() or [""])[0] not in seen]
    changes = rnd.sample(changes, min(args.speakers, len(changes)))
    q = "SELECT symbol, page_start, coalesce(speaker, ''), coalesce(delegation, ''), text FROM segments WHERE id = ?"

    items, key = [], {}
    for sym, page, a, b in pages:
        items.append({"kind": "page", "symbol": sym, "page": page, "versions": {"current": a, "preview": b}})
    for x in changes:
        o, n = old.execute(q, (x["old_id"],)).fetchone(), new.execute(q, (x["new_id"],)).fetchone()
        if not o or not n:
            continue
        # (one opening for both, the preview's text: the versions differ only in speaker and delegation)
        opening = mask(flat(n[4])[:300])
        items.append({"kind": "speaker", "symbol": n[0], "page": n[1], "opening": opening,
                      "versions": {"current": {"speaker": o[2], "delegation": o[3]},
                                   "preview": {"speaker": n[2], "delegation": n[3]}}})
    rnd.shuffle(items)
    for k, it in enumerate(items):
        it["id"] = f"{k + 1:03d}"
    repeats = [dict(it) for it in rnd.sample(items, min(args.repeats, len(items)))]
    shown = []
    for it in items:
        order = ["current", "preview"] if rnd.random() < 0.5 else ["preview", "current"]
        key[it["id"]] = {"A": order[0], "B": order[1]}
        shown.append({"id": it["id"], "kind": it["kind"], "symbol": it["symbol"], "page": it["page"], "opening": it.get("opening"),
                      "A": it["versions"][order[0]], "B": it["versions"][order[1]]})
    # the repeats in the last third, A and B swapped
    for r in repeats:
        rid = f"R{r['id']}"
        first = key[r["id"]]
        key[rid] = {"A": first["B"], "B": first["A"], "repeat_of": r["id"]}
        shown.insert(rnd.randint(2 * len(shown) // 3, len(shown)),
                     {"id": rid, "kind": r["kind"], "symbol": r["symbol"], "page": r["page"], "opening": r.get("opening"),
                      "A": r["versions"][key[rid]["A"]], "B": r["versions"][key[rid]["B"]]})
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "items.json").write_text(json.dumps({"seed": args.seed, "items": shown}, ensure_ascii=False, indent=1) + "\n")
    (out / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(f"{len(shown)} items ({sum(i['kind'] == 'page' for i in shown)} pages, {sum(i['kind'] == 'speaker' for i in shown)} speakers, "
          f"{len(repeats)} repeats) -> {out.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
