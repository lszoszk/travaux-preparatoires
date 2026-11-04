#!/usr/bin/env python3
"""Pick the best OCR engine per page, without a reference.

Two signals, after removing page furniture:
- words: share of word tokens that are English words (/usr/share/dict/words plus the
  names and terms of the records). A page with no usable text layer
  (E/CN.4/AC.1/SR.40) scores ~0 on "layer" and falls to another engine.
- agreement: mean similarity of the page to the other engines' readings of it. Engines
  that read two-column printed pages straight across (English and French interleaved)
  still produce English words, but they disagree with the engines that keep the
  columns apart, which agree with each other.
Score = words x agreement.

Two-column pages (the 1948-66 printed Official Records) are detected first, from a blank
gutter down the middle of the page image, and take Tesseract's layout mode (tess3): on
the 1948 Third Committee records it measured 0.7% CER against 2.4% for the text layer
and 3.3% for Vision (eval/ocr_bench.json). Scoring doesn't work there: engines that
read straight across interleave English and French, still produce English words, and
agree with each other.

Writes data/ocr/<doc>/best/page-NNN.txt and data/ocr/<doc>/selection.json. With --vote,
also data/ocr/<doc>/vote/page-NNN.txt: the selected engine's page corrected word by word
by the majority of the engines (pipeline/vote.py); on two-column pages only the
column-aware engines vote.

Usage: python3 pipeline/ocr_select.py data/manifest/harvest_pilot_udhr_18_19.json [--engines ...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from PIL import Image
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402
from normalize import strip_furniture  # noqa: E402
from spellfix import fix_text  # noqa: E402
from vote import vote_page  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "data" / "ocr"
CANDIDATES = ["layer", "tess6min", "tess6", "tess4", "tess3", "vision"]
# Engine families: the Tesseract variants share most errors, so together they weigh about
# as much as the text layer. Chosen on the pilot benchmark (3 settings tried): typed
# records 2.3% -> 1.9% CER, typed reports 2.8% -> 2.4%. Voting with only layer, tess6,
# tess3 and vision gives the same figures, at half the OCR time.
# Equal weights: on the full benchmark (eval/tune_vote.py, 626 documents in two halves) they beat
# the pilot's 1.5/.5/.5/1 (layer/tess6/tess3/vision) on both halves and in every scan group.
DEFAULT_WEIGHTS = {"layer": 1.0, "tess4": 1.0, "tess6": 1.0, "tess6min": 1.0, "tess3": 1.0, "vision": 1.0}
FULL_RUN_ENGINES = ["layer", "tess6", "tess3", "vision"]
COLUMN_AWARE = {"layer", "tess3", "vision"}


def two_column(img_path: Path) -> bool:
    """True if the page has a blank vertical gutter in its middle fifth.

    Ink per pixel column over the text area; a gutter is a run of columns in the 40-60%
    band with under a tenth of the typical ink of text columns. Checked over the whole
    text area and over its lower half, because a first page opens with a full-width
    heading above the columns.
    """
    with Image.open(img_path) as img:
        g = img.convert("L").resize((400, 520))
    return any(_gutter(g, top, 0.9) for top in (0.1, 0.5))


def _gutter(g: Image.Image, top: float, bottom: float) -> bool:
    w, h = g.size
    px = g.load()
    ink = [sum(1 for y in range(int(h * top), int(h * bottom)) if px[x, y] < 128) for x in range(w)]
    text_cols = sorted(v for v in ink[int(w * 0.1):int(w * 0.9)] if v > 0)
    if not text_cols:
        return False
    typical = text_cols[len(text_cols) // 2]
    band = ink[int(w * 0.4):int(w * 0.6)]
    run = best = 0
    for v in band:
        run = run + 1 if v < typical * 0.1 else 0
        best = max(best, run)
    if best < 3:
        return False
    # Both sides of the gutter must carry text: a short typed page with a narrow block on
    # the left also has a blank middle (one-page amendments were taken for two columns).
    left, right = sum(ink[int(w * 0.1):int(w * 0.45)]), sum(ink[int(w * 0.55):int(w * 0.9)])
    total = left + right
    return total > 0 and min(left, right) / total >= 0.3
# Words the dictionary lacks but the records use constantly.
EXTRA = """commission rapporteur covenant covenants unesco ussr byelorussian ukrainian soviet
socialist republics amendment amendments delegation delegations secretariat drafting
cassin malik pavlov roosevelt humphrey chang mehta""".split()


def load_words() -> set[str]:
    words = {w.strip().lower() for w in Path("/usr/share/dict/words").read_text().splitlines()}
    return words | set(EXTRA)


def score(text: str, words: set[str]) -> tuple[float, int]:
    """(share of alphabetic tokens that are words, number of such tokens)."""
    toks = re.findall(r"[A-Za-z]+", text)
    toks = [t.lower() for t in toks if len(t) > 1]
    if not toks:
        return 0.0, 0
    hits = sum(1 for t in toks if t in words or (t.endswith("s") and t[:-1] in words))
    return hits / len(toks), len(toks)


def vote(symbol: str, engines: list[str], weights: dict[str, float]) -> int:
    """Word-level majority for every page that has a selection; returns tokens changed."""
    d = OCR / safe_name(symbol)
    choice = json.loads((d / "selection.json").read_text())
    out_dir = d / "vote"
    out_dir.mkdir(parents=True, exist_ok=True)
    changed = 0
    for name, c in choice.items():
        voters = [e for e in engines if (not c.get("two_column") or e in COLUMN_AWARE) and not (c.get("tess3_across") and e == "tess3")]
        texts = {e: strip_furniture((d / e / name).read_text(encoding="utf-8"), first_page=name == "page-001.txt")[0]
                 for e in voters if (d / e / name).exists()}
        if c["engine"] not in texts:
            continue
        text, n = vote_page(texts, c["engine"], weights)
        if not c.get("two_column"):
            # typed pages: misreadings every engine shares ("thet" for "that"), corrected from the
            # corpus's word frequencies; the printed two-column records gain nothing from it
            text, fixed = fix_text(text)
            n += fixed
        (out_dir / name).write_text(text, encoding="utf-8")
        changed += n
    return changed


def tess3_across(d: Path, name: str) -> bool:
    """True if Tesseract's automatic layout read this two-column page across its columns.

    The front page of a 1954-66 record sets a narrow contents column beside the text, and the mode reads a line across
    both ("CONTENTS ARTICLE 26 OF THE DRAFT COVENANT ..."), so the columns interleave. The text layer and Vision keep
    them apart. Two signs, from the readings already made: tess3 agrees with neither of the others (under 70) while
    they agree with each other (85 or more); or more than a quarter of its lines run past 90 characters.
    """
    first = name == "page-001.txt"
    body = {}
    for e in ("tess3", "vision", "layer"):
        f = d / e / name
        if f.exists():
            text, _ = strip_furniture(f.read_text(encoding="utf-8"), first_page=first)
            body[e] = text
    if "tess3" not in body:
        return False
    lines = [l for l in body["tess3"].splitlines() if l.strip()]
    if len(lines) >= 8 and sum(len(l) > 90 for l in lines) / len(lines) > 0.25:
        return True
    # or it lost lines: more than 15% of the words both the others read are not in it (E/CN.4/AC.1/20)
    if "vision" in body and "layer" in body:
        toks = {e: Counter(re.findall(r"[a-z]{4,}", body[e].lower())) for e in ("tess3", "vision", "layer")}
        both = toks["vision"] & toks["layer"]
        if sum(both.values()) >= 80 and sum((both - toks["tess3"]).values()) / sum(both.values()) > 0.15:
            return True
    flat = {e: " ".join(t.lower().split()) for e, t in body.items()}
    if len(flat) < 3 or min(len(t) for t in flat.values()) < 300:
        return False
    return (fuzz.ratio(flat["vision"], flat["layer"]) >= 85 and fuzz.ratio(flat["tess3"], flat["vision"]) < 70
            and fuzz.ratio(flat["tess3"], flat["layer"]) < 70)


def select(symbol: str, engines: list[str], words: set[str]) -> dict:
    d = OCR / safe_name(symbol)
    pages = sorted({p.name for e in engines for p in (d / e).glob("page-*.txt")})
    out_dir = d / "best"
    out_dir.mkdir(parents=True, exist_ok=True)
    choice = {}
    for name in pages:
        first = name == "page-001.txt"
        img = d / "img" / name.replace(".txt", ".png")
        cols2 = img.exists() and two_column(img)
        across = cols2 and (d / "tess3" / name).exists() and tess3_across(d, name)
        if cols2 and (d / "tess3" / name).exists() and not across:
            (out_dir / name).write_text((d / "tess3" / name).read_text(encoding="utf-8"), encoding="utf-8")
            choice[name] = {"engine": "tess3", "two_column": True, "scores": {}}
            continue
        # (a page tess3 read across its columns is chosen from the text layer and Vision, which keep them apart)
        pool = [e for e in engines if e in COLUMN_AWARE and not (across and e == "tess3")] if cols2 else engines
        scored, bodies = {}, {}
        for e in pool:
            f = d / e / name
            if f.exists():
                body, _ = strip_furniture(f.read_text(encoding="utf-8"), first_page=first)
                bodies[e] = " ".join(body.split()).lower()
                ratio, n = score(body, words)
                # too little text for the page size means the engine missed most of it
                scored[e] = (ratio if n >= 40 else ratio * n / 40, n)
        if not scored:
            continue
        for e in scored:
            others = [fuzz.ratio(bodies[e], bodies[o]) / 100 for o in bodies if o != e]
            agree = sum(others) / len(others) if others else 1.0
            scored[e] = (scored[e][0] * agree, scored[e][1])
        best = max(scored, key=lambda e: (round(scored[e][0], 3), scored[e][1]))
        (out_dir / name).write_text((d / best / name).read_text(encoding="utf-8"), encoding="utf-8")
        choice[name] = {"engine": best, "two_column": cols2,
                        "scores": {e: round(v[0], 3) for e, v in scored.items()}, **({"tess3_across": True} if across else {})}
    (d / "selection.json").write_text(json.dumps(choice, indent=1), encoding="utf-8")
    tally: dict[str, int] = {}
    for c in choice.values():
        tally[c["engine"]] = tally.get(c["engine"], 0) + 1
    return tally


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("harvest_log", type=Path)
    ap.add_argument("--engines", nargs="+", default=CANDIDATES)
    ap.add_argument("--vote", action="store_true", help="also write word-level majority pages to vote/")
    ap.add_argument("--weights", default="", help="engine weights for voting (default DEFAULT_WEIGHTS)")
    args = ap.parse_args()
    weights = {k: float(v) for k, v in (kv.split("=") for kv in args.weights.split(",") if kv)} or DEFAULT_WEIGHTS
    words = load_words()
    log = json.loads(args.harvest_log.read_text())
    for symbol, entry in sorted(log.items()):
        if entry.get("status") == "ok" and (OCR / safe_name(symbol)).exists():
            tally = select(symbol, args.engines, words)
            extra = f", {vote(symbol, args.engines, weights)} tokens changed by vote" if args.vote else ""
            print(f"  {symbol}: {tally}{extra}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
