#!/usr/bin/env python3
"""OCR benchmark: character error rate (CER) per engine against the private Schabas references.

For each document, the reference (Schabas's retypeset text, eval/private/reference/) is
split into sentence-sized segments. Each segment is located in each engine's OCR output
(rapidfuzz partial alignment, then the end points are refined to minimise the edit
distance) and scored with Levenshtein distance. A segment counts only if at least one
engine locates it with a match score >= MIN_FOUND: this drops passages that Schabas
omits or that fall on pages not OCR'd, and uses the same segments for every engine.

Running heads and catchwords are stripped first (pipeline/normalize.py), as they will be
in production. Comparison is case-insensitive (Schabas prints speakers as "Mr. Pavlov", the records as
"Mr. PAVLOV"), with quotes, dashes, whitespace and line-end hyphenation normalised.

Reports: CER per engine per document, per scan group, and an "oracle" row, the best engine
per segment, which bounds what any combination of engines could reach.

Usage: python3 eval/ocr_bench.py [--engines layer tess6min ...] [--json eval/ocr_bench.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from normalize import strip_furniture  # noqa: E402

REF = ROOT / "eval" / "private" / "reference"
OCR = ROOT / "data" / "ocr"
# Segments that share vocabulary with a different sentence score ~70-80 against it
# ("Mr. Pavlov (USSR) supported..." vs "Mr. Pavlov (USSR) said..."); true matches at
# a few percent CER score above 90.
MIN_FOUND = 88
MIN_SEG = 40


def norm(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = t.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                                   "–": "-", "—": "-", "­": ""}))
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)  # line-end hyphenation
    return re.sub(r"\s+", " ", t).strip().lower()


def ref_segments(pages: dict[str, str]) -> list[str]:
    """Sentence-sized pieces of the reference, split at sentence ends and at elisions."""
    text = "\n".join(pages.values())
    # Schabas's own document header (symbol, date, "Original Text: French") is laid out
    # differently from the UN masthead; it is not OCR'd text to compare.
    text = re.sub(r"\A\s*\S+/\S+\s*\n[^\n]*\d{4}\s*\n(?:\s*Original Text:[^\n]*\n)?", "", text)
    text = re.sub(r"\[[^\]]{0,120}\]", " ", text)  # editorial insertions: [sic], [of the Drafting Committee]
    text = norm(text)
    parts = re.split(r"(?<=[.;:?!])\s+|\s*(?:…|\. \. \.)\s*", text)
    segs, buf = [], ""
    for p in parts:
        buf = f"{buf} {p}".strip() if buf else p
        if len(buf) >= MIN_SEG:
            segs.append(buf)
            buf = ""
    return [s for s in segs if len(s) >= MIN_SEG]


def locate_span(seg: str, hyp: str) -> tuple[float, int, int, int]:
    """Best match score of seg in hyp, the edit distance of the refined window, and the window (start, end) in hyp."""
    al = fuzz.partial_ratio_alignment(seg, hyp)
    if al is None or al.score == 0:
        return 0.0, len(seg), 0, 0
    s0, e0 = al.dest_start, al.dest_end
    best = Levenshtein.distance(seg, hyp[s0:e0])
    # refine end, then start, within +-15 chars
    best_e, best_s = e0, s0
    for e in range(max(s0 + 1, e0 - 15), min(len(hyp), e0 + 15) + 1):
        d = Levenshtein.distance(seg, hyp[s0:e])
        if d < best:
            best, best_e = d, e
    for s in range(max(0, s0 - 15), min(best_e - 1, s0 + 15) + 1):
        d = Levenshtein.distance(seg, hyp[s:best_e])
        if d < best:
            best, best_s = d, s
    return al.score, best, best_s, best_e


def locate(seg: str, hyp: str) -> tuple[float, int]:
    """Best match score of seg in hyp and the edit distance of the refined window."""
    return locate_span(seg, hyp)[:2]


def group_of(symbol: str) -> str:
    if symbol.startswith("A/C.3/SR."):
        return "1948 printed (GAOR, EN/FR columns)"
    if "/SR." in symbol:
        return "1947-48 typed summary records"
    return "1947-48 typed documents/reports"


def common_pages(doc_dir: Path, engines: list[str]) -> list[str]:
    """Pages every engine has: the long reports were OCR'd on a sample of pages only,
    while the text layer covers them all."""
    sets = [{p.name for p in (doc_dir / e).glob("page-*.txt")} for e in engines]
    return sorted(set.intersection(*sets)) if sets and all(sets) else []


def engine_text(doc_dir: Path, engine: str, pages: list[str]) -> str | None:
    """The given OCR'd pages of one engine, running heads and catchwords removed, normalised."""
    d = doc_dir / engine
    if not d.exists() or not pages:
        return None
    texts = [strip_furniture((d / name).read_text(encoding="utf-8"), first_page=name == "page-001.txt")[0]
             for name in pages]
    return norm("\n".join(texts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=["layer", "tess4", "tess6", "tess6min", "tess3", "vision"])
    ap.add_argument("--json", type=Path, default=ROOT / "eval" / "ocr_bench.json")
    args = ap.parse_args()

    rows = []
    for ref_path in sorted(REF.glob("*.json")):
        ref = json.loads(ref_path.read_text())
        doc_dir = OCR / ref_path.stem
        pages = common_pages(doc_dir, args.engines)
        hyps = {e: engine_text(doc_dir, e, pages) for e in args.engines}
        hyps = {e: h for e, h in hyps.items() if h}
        if not hyps:
            continue
        missing = [e for e in args.engines if e not in hyps]
        if missing:
            print(f"  {ref['symbol']}: no output for {missing}, skipped", file=sys.stderr)
            continue
        dist = defaultdict(int)
        oracle = 0
        chars = 0
        n = 0
        for seg in ref_segments(ref["pages"]):
            res = {e: locate(seg, h) for e, h in hyps.items()}
            if max(score for score, _ in res.values()) < MIN_FOUND:
                continue
            n += 1
            chars += len(seg)
            for e, (_, d) in res.items():
                dist[e] += d
            oracle += min(d for _, d in res.values())
        if not chars:
            continue
        row = {"symbol": ref["symbol"], "group": group_of(ref["symbol"]), "segments": n, "chars": chars,
               "cer": {e: dist[e] / chars for e in hyps}, "oracle": oracle / chars}
        rows.append(row)
        best = min(row["cer"], key=row["cer"].get)
        print(f"  {ref['symbol']:22} {n:4} segs  " + "  ".join(f"{e} {row['cer'][e]:.3f}" for e in hyps)
              + f"  | oracle {row['oracle']:.3f}  best={best}", file=sys.stderr)

    def pooled(sel: list[dict]) -> dict:
        tot = sum(r["chars"] for r in sel)
        out = {e: sum(r["cer"][e] * r["chars"] for r in sel) / tot for e in args.engines}
        out["oracle"] = sum(r["oracle"] * r["chars"] for r in sel) / tot
        return {"chars": tot, "docs": len(sel), "cer": out}

    groups = {g: pooled([r for r in rows if r["group"] == g]) for g in sorted({r["group"] for r in rows})}
    overall = pooled(rows) if rows else {}
    print("\nCER by scan group (lower is better):", file=sys.stderr)
    header = f"  {'group':40} {'docs':>4} " + " ".join(f"{e:>9}" for e in args.engines + ["oracle"])
    print(header, file=sys.stderr)
    for g, v in list(groups.items()) + [("ALL", overall)]:
        print(f"  {g:40} {v['docs']:4} " + " ".join(f"{v['cer'][e]:9.3f}" for e in args.engines + ["oracle"]),
              file=sys.stderr)
    args.json.write_text(json.dumps({"min_found": MIN_FOUND, "groups": groups, "overall": overall,
                                     "documents": rows}, indent=1), encoding="utf-8")
    print(f"\n-> {args.json.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
