#!/usr/bin/env python3
"""Where a new reading of a page (the local model's, engine "chandra") and the OCR vote disagree, word by word: the
disputes of the vision-reader pilot's development sets (docs/vlm_pilot_plan.md), for pages with no reference text.

Each page's two readings are normalised (case, punctuation, line-end hyphens) and aligned with difflib; every stretch where
they differ is a dispute, with the words around it, and a note of which of the other OCR engines (layer, tess3, tess6,
vision) has the new reading's words nearby (support) and whether the stretch is the new reading's alone (an insertion no
engine has: the first thing to look at for invented text). A sample of disputes per page goes to readers of the page image
(a Workflow), who say which reading the scan has; their verdicts give an estimate of each reading's errors.

Also per page: the share of the vote's words found in the new reading in the same order (a page read in the wrong column
order or with a column missing scores low), and the length ratio.

  python3 eval/vlm_disputes.py eval/vlm_pilot/dev_set2.json --per-page 6 --out eval/vlm_pilot/disputes_dev2.json
"""
from __future__ import annotations

import argparse
import difflib
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402
from normalize import strip_furniture  # noqa: E402

OCR = ROOT / "data" / "ocr"
OTHERS = ["layer", "tess3", "tess6", "vision"]


def words(text: str) -> list[str]:
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)
    return [w for w in (re.sub(r"[^\w]", "", x).lower() for x in t.split()) if w]


def page_text(symbol: str, engine: str, page: int) -> str | None:
    p = OCR / safe_name(symbol) / engine / f"page-{page:03d}.txt"
    if not p.exists():
        return None
    return strip_furniture(p.read_text(encoding="utf-8"), first_page=page == 1)[0]


def supported(span: list[str], other: list[str]) -> bool:
    """The span's words occur together (in order, as one stretch) in another engine's reading."""
    if not span:
        return True
    s = " ".join(span)
    return f" {s} " in f" {' '.join(other)} "


def disputes_of(symbol: str, page: int, new: str, base: str = "vote") -> dict | None:
    a_text, b_text = page_text(symbol, base, page), page_text(symbol, new, page)
    if a_text is None or b_text is None:
        return None
    a, b = words(a_text), words(b_text)
    others = {e: words(t) for e in OTHERS if (t := page_text(symbol, e, page))}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        va, vb = a[i1:i2], b[j1:j2]
        if "".join(va) == "".join(vb):  # (the same letters, spaced differently: "humanrights" / "human rights")
            continue
        support_b = [e for e, o in others.items() if vb and supported(vb, o)]
        support_a = [e for e, o in others.items() if va and supported(va, o)]
        out.append({"op": tag, base: " ".join(va), new: " ".join(vb),
                    "before": " ".join(b[max(0, j1 - 6):j1]), "after": " ".join(b[j2:j2 + 6]),
                    f"support_{new}": support_b, f"support_{base}": support_a,
                    "alone": tag == "insert" and not support_b and len(vb) >= 1})
    matched = sum(m.size for m in sm.get_matching_blocks())
    return {"symbol": symbol, "page": page, "words": {base: len(a), new: len(b)},
            "in_order": round(matched / max(len(a), 1), 3), "length_ratio": round(len(b) / max(len(a), 1), 3),
            "disputes": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", type=Path)
    ap.add_argument("--new", default="chandra")
    ap.add_argument("--per-page", type=int, default=6, help="disputes per page sent to the readers")
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--judge-out", type=Path, help="the sampled disputes, blinded, grouped by page, for the readers")
    args = ap.parse_args()
    data = json.loads(args.pages.read_text())
    types = {(p["symbol"], p["page"]): p.get("type", "") for p in data.get("pages", [])}
    rnd = random.Random(args.seed)
    pages, sample = [], []
    for d in data["documents"]:
        for pg in d["pages"]:
            r = disputes_of(d["symbol"], pg, args.new)
            if r is None:
                continue
            r["type"] = types.get((d["symbol"], pg), "")
            pages.append(r)
            for k, x in enumerate(rnd.sample(r["disputes"], min(args.per_page, len(r["disputes"])))):
                sample.append({"key": f"{safe_name(d['symbol'])}-{pg}-{k}", "symbol": d["symbol"], "page": pg,
                               "image": str(OCR / safe_name(d["symbol"]) / "img" / f"page-{pg:03d}.png"), **x})
    # for the readers: each sampled dispute with its two readings as A and B in a random order (the key keeps which is which)
    for x in sample:
        flip = rnd.random() < 0.5
        x["A"], x["B"] = (x[args.new], x["vote"]) if flip else (x["vote"], x[args.new])
        x["A_is"] = args.new if flip else "vote"
    args.out.write_text(json.dumps({"pages": pages, "sample": sample}, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.judge_out:
        by_page: dict[str, list] = {}
        for x in sample:
            by_page.setdefault(f"{safe_name(x['symbol'])}-{x['page']}", []).append(
                {"key": x["key"], "before": x["before"], "A": x["A"], "B": x["B"], "after": x["after"]})
        items = [{"page_key": k, "symbol": v0["key"].rsplit("-", 2)[0], "image": next(x["image"] for x in sample if f"{safe_name(x['symbol'])}-{x['page']}" == k),
                  "disputes": v} for k, v in by_page.items() for v0 in v[:1]]
        args.judge_out.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(p["disputes"]) for p in pages)
    print(f"{len(pages)} pages, {n} disputes ({sum(x['alone'] for p in pages for x in p['disputes'])} insertions no engine "
          f"has), {len(sample)} sampled -> {args.out}", file=sys.stderr)
    for p in pages:
        print(f"  {p['symbol']:22} p{p['page']:<3} {p['type']:18} words {p['words']}  in order {p['in_order']}  "
              f"length {p['length_ratio']}  disputes {len(p['disputes'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
