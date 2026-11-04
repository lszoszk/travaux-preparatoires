#!/usr/bin/env python3
"""The article tags of the speeches before and after the vision reader's text (preregistered in docs/devlog.md, 21 Oct 2026).

Speeches are paired as pipeline/speaker_carry.py pairs them (a new speech continues the old speech whose opening it has; a
new turn split off an old speech has no old tag). Each pair's tag, (instrument, final article), is compared: same, new
(none before), changed (another article), dropped (none after); a new turn with a tag counts as new. Records whose
segments did not change are compared id by id. Writes the samples for the blind judges in the form of eval/audit_sample.py
(new or changed tags; dropped tags with the old tag), seeds fixed.

  python3 eval/merge_tag_changes.py OLD.sqlite3 --root COPY [--new 40] [--dropped 20] [--seed 2030] [--out eval/merge_tags]
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from speaker_carry import match  # noqa: E402

COLS = "id, symbol, seq, kind, speaker, delegation, speaker_method AS method, text, page_start, final_article, article_instrument, " \
       "draft_article, article_mapping"


def segments(db: Path) -> dict[str, list[dict]]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out = defaultdict(list)
    for r in con.execute(f"SELECT {COLS} FROM segments ORDER BY symbol, seq"):
        out[r["symbol"]].append(dict(r))
    return out


def tag(s: dict) -> tuple | None:
    return (s["article_instrument"], s["final_article"]) if s and s["final_article"] is not None else None


def item(s: dict, st: str, titles: dict, finals: dict, tagged: dict, setter: str, context: str) -> dict:
    inst = (tagged["article_instrument"] or "").split("+")[0]
    who = f"{s['speaker']} ({s['delegation']}): " if s["speaker"] else ""
    return {"id": s["id"], "symbol": s["symbol"], "page": s["page_start"], "stratum": st, "kind": "P",
            "tag": f"{tagged['article_instrument']} art. {tagged['final_article']} ({titles.get(inst, {}).get(str(tagged['final_article']), '')})",
            "draft": tagged["draft_article"], "final_text": finals.get(inst, {}).get(str(tagged["final_article"]), "")[:700],
            "setter": setter, "before": context[-600:], "speech": (who + (s["text"] or ""))[:1800]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--new", type=int, default=40)
    ap.add_argument("--dropped", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2030, help="the new tags' sample; the dropped tags' is the next")
    ap.add_argument("--out", type=Path, default=ROOT / "eval" / "merge_tags")
    args = ap.parse_args()
    old, new = segments(args.old), segments(args.root / "data" / "travaux.sqlite3")
    conc = args.root / "data" / "concordance"
    titles = defaultdict(dict)
    import csv
    for r in csv.DictReader((conc / "articles.csv").open(encoding="utf-8")):
        titles[r["instrument"]][r["article"]] = r["short_title"]
    sys.path.insert(0, str(ROOT / "api"))
    import server
    finals = {i: server.final_texts(i) for i in ("UDHR", "ICCPR", "ICESCR")}
    n, new_items, dropped_items = Counter(), [], []
    for sym, segs in new.items():
        before = old.get(sym, [])
        if [(s["id"], s["text"]) for s in segs] == [(s["id"], s["text"]) for s in before]:
            pairs = [(k, k, "same text") for k, s in enumerate(segs) if s["kind"] == "speech"]
        else:
            pairs, _ = match(before, segs)
        for k, i, how in pairs:
            s, o = segs[k], (before[i] if i is not None and how in ("continues", "same text") else None)
            a, b = tag(o), tag(s)
            ctx = segs[k - 1]["text"] if k else ""
            if how not in ("continues", "same text"):
                kind = "new turn, tagged" if b else "new turn, untagged"
            else:
                kind = "same" if a == b else "new" if not a else "dropped" if not b else "changed"
            n[kind] += 1
            if kind in ("new", "changed", "new turn, tagged"):
                new_items.append(item(s, f"merge/{kind}", titles, finals, s, s["article_mapping"] or "", ctx))
            elif kind == "dropped":
                dropped_items.append(item(s, "merge/dropped", titles, finals, o, f"before: {o['article_mapping']}; now: "
                                          f"{s['article_mapping'] or 'no tag'}", ctx))
    for k, v in n.most_common():
        print(f"  {k}: {v}", file=sys.stderr)
    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    sample = rng.sample(new_items, min(args.new, len(new_items)))
    (args.out / "sample_new.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1) + "\n")
    rng = random.Random(args.seed + 1)
    sample_d = rng.sample(dropped_items, min(args.dropped, len(dropped_items)))
    (args.out / "sample_dropped.json").write_text(json.dumps(sample_d, ensure_ascii=False, indent=1) + "\n")
    (args.out / "counts.json").write_text(json.dumps(dict(n), indent=1) + "\n")
    print(f"samples: {len(sample)} new or changed of {len(new_items)}, {len(sample_d)} dropped of {len(dropped_items)} -> {args.out}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
