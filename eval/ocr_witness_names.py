#!/usr/bin/env python3
"""Names at turn openings, engine by engine, against the truth, for the test of the OCR witnesses (eval/ocr_witness_read.py;
the gate is in docs/devlog.md, 20 Oct, preregistered).

Truth, per page, as a set of names:
- the 40 gold pages: the speakers of the speech starts the three readers' majority gives (data/gold/segment_pages_models.json);
- dev set 1: the names the retyped reference prints at turn openings ("Mr. Wilson (United Kingdom)", eval/private/reference),
  each placed on a page when any engine reads an opening there with that delegation and a name at least 60 like it.
An engine's names are those it reads at turn openings and in officers' lines (pipeline/name_guard.py cues). A true name is read
"exact" when one of them has the same spelling without spaces, hyphens or accents, or the same last word; "garbled" when the
closest is at least 60 like it; "missed" otherwise. "Plausible wrong": a garbled reading that is itself a name known for that
delegation (the error the guard exists for). "Independence": of the true names no Tesseract engine (tess3, tess6; tess4 read only 5 of the pages) reads
exact, the share the engine reads exact. Only pages read by every engine are counted.

  python3 eval/ocr_witness_names.py [--engines ...] [--json eval/vlm_pilot/witness_names.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from name_guard import Guard, bare, cues  # noqa: E402

OCR = ROOT / "data" / "ocr"
TESS = ("tess3", "tess6")  # (tess4 read only 5 of the 60 pages)
ENGINES = ["layer", "tess3", "tess6", "vision", "vote", "chandra", "doctr", "pero", "paddle"]
REF_CUE = re.compile(r"\b(?:Mr|Mrs|Miss|Mme|Sir|Dr|M)\.?\s+((?:[A-Z][\w'’\-]+\s+){0,3}?[A-Z][\w'’\-]+)\s*\(([^()\n]{2,80})\)")


def exact(n: str, t: str) -> bool:
    a, b = bare(n), bare(t)
    return bool(a) and (a == b or bare(n.split()[-1]) == bare(t.split()[-1]))


def truth_pages(engines: list[str]) -> dict:
    out = {}
    gold = json.loads((ROOT / "data" / "gold" / "segment_pages_models.json").read_text())
    for k, v in gold.items():
        names = {(s["speaker"], s["delegation"]) for s in v["starts"] if s["kind"] == "speech" and s["speaker"] and s.get("votes", 3) >= 2}
        out[(v["symbol"], v["page"])] = {"set": "gold", "names": sorted(names)}
    dev = json.loads((ROOT / "eval" / "vlm_pilot" / "dev_set.json").read_text())
    for d in dev["documents"]:
        safe = d["symbol"].replace("/", "_")
        ref = ROOT / "eval" / "private" / "reference" / f"{safe}.json"
        if not ref.exists():
            continue
        text = "\n".join(json.loads(ref.read_text())["pages"].values())
        ref_names = {(m.group(1).upper(), m.group(2).strip()) for m in REF_CUE.finditer(text)}
        for p in d["pages"]:
            read = [c for e in engines if (OCR / safe / e / f"page-{p:03d}.txt").exists()
                    for c in cues((OCR / safe / e / f"page-{p:03d}.txt").read_text(encoding="utf-8"))]
            names = {(n, dl) for n, dl in ref_names
                     if any(fuzz.token_set_ratio(c["country"], dl) >= 80 and fuzz.ratio(bare(c["name"]), bare(n)) >= 60 for c in read)}
            out[(d["symbol"], p)] = {"set": "dev1", "names": sorted(names)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=ENGINES)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    guard = Guard()
    truth = truth_pages(args.engines)
    res = defaultdict(Counter)
    per_name = []
    pages = 0
    for (sym, p), t in sorted(truth.items()):
        safe = sym.replace("/", "_")
        files = {e: OCR / safe / e / f"page-{p:03d}.txt" for e in args.engines}
        if not all(f.exists() for f in files.values()):
            continue
        pages += 1
        read = {e: [c["name"] for c in cues(f.read_text(encoding="utf-8"))] for e, f in files.items()}
        for name, dl in t["names"]:
            row = {"symbol": sym, "page": p, "set": t["set"], "name": name, "delegation": dl, "read": {}}
            for e, ns in read.items():
                if any(exact(n, name) for n in ns):
                    k, got = "exact", name
                else:
                    best = max(ns, key=lambda n: fuzz.ratio(bare(n), bare(name)), default=None)
                    if best and fuzz.ratio(bare(best), bare(name)) >= 60:
                        k, got = "garbled", best
                        if guard.is_known(best, guard.delegation(dl) or dl):
                            k = "plausible wrong"
                    else:
                        k, got = "missed", None
                res[e][k] += 1
                row["read"][e] = [k, got]
            per_name.append(row)
    hard = [r for r in per_name if not any(r["read"][e][0] == "exact" for e in TESS if e in r["read"])]
    n = len(per_name)
    print(f"{pages} pages, {n} true names ({sum(r['set'] == 'gold' for r in per_name)} gold, {sum(r['set'] == 'dev1' for r in per_name)} dev1); "
          f"{len(hard)} read exact by no Tesseract engine", file=sys.stderr)
    print(f"  {'engine':9} {'exact':>6} {'garbled':>8} {'missed':>7} {'plaus.wrong':>12} {'indep.':>7}", file=sys.stderr)
    table = {}
    for e in args.engines:
        c = res[e]
        ind = sum(r["read"][e][0] == "exact" for r in hard) / len(hard) if hard else None
        table[e] = {**c, "exact_share": c["exact"] / n if n else None, "independence": ind}
        print(f"  {e:9} {c['exact']:6} {c['garbled']:8} {c['missed']:7} {c['plausible wrong']:12} "
              f"{(f'{ind:.0%}' if ind is not None else '-'):>7}", file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps({"pages": pages, "names": n, "hard": len(hard), "engines": table, "per_name": per_name},
                                        ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
