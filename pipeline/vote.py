"""Voting across OCR engines.

The engines misread different things: where the text layer has "CEAUG- (Chim)", Tesseract
has "CHANG (China)"; where Tesseract has "ORIBH", Vision may be right. Reading the same
line through several engines and taking the majority fixes most errors without any model.

speaker_votes(): the readings of one speech's opening ("Mr. NAME (Delegation)") across
engines. The same opening is found on the same page of each engine's output by comparing
the words that follow the parenthesis.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

from common import safe_name
from normalize import strip_furniture
from segment import SPEAKER_RE

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "data" / "ocr"
VOTERS = ["layer", "tess4", "tess6", "tess6min", "tess3", "vision"]
_cache: dict[tuple[str, str, int], list[dict]] = {}


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def openings(symbol: str, engine: str, page: int) -> list[dict]:
    """Every speaker opening an engine read on one page: name, delegation, and the words after it."""
    key = (symbol, engine, page)
    if key in _cache:
        return _cache[key]
    path = OCR / safe_name(symbol) / engine / f"page-{page:03d}.txt"
    out: list[dict] = []
    if path.exists():
        body, _ = strip_furniture(path.read_text(encoding="utf-8"), first_page=page == 1)
        lines = body.splitlines()
        for i, line in enumerate(lines):
            # a delegation that wraps: "Mr. PavLov (Union of Soviet Socialist Re-" / "publics) pointed out"
            if "(" in line and ")" not in line[line.rfind("("):] and i + 1 < len(lines):
                nxt = lines[i + 1].lstrip()
                line = line[:-1] + nxt if line.endswith("-") else line + " " + nxt
            m = SPEAKER_RE.match(line)
            if m:
                rest = line[m.end():] + " " + " ".join(lines[i + 1:i + 3])
                out.append({"name": m.group("name").strip(), "country": m.group("country").strip(),
                            "tail": _flat(rest)[:90]})
    _cache[key] = out
    return out


def speaker_votes(symbol: str, seg: dict, engines: list[str] = VOTERS) -> list[dict]:
    """Readings of this speech's opening from every engine that has the page.

    A reading counts when the words after its parenthesis match the segment's (ratio >= 60),
    so a different speaker on the same page is not mistaken for this one; a reading that names
    another delegation than the segment's own text needs a close match (>= 80).
    """
    m = SPEAKER_RE.match(seg["text"])
    if not m:
        return []
    tail = _flat(seg["text"][m.end():])[:90]
    # a tail this short (a sponsor line, "Prof. CASSIN (France).") cannot tell two speeches apart: another delegation's
    # reading of the page's last opening would score 100 (E/CN.4/AC.1/SR.4)
    short = len(tail.strip(" .,;:")) < 15
    own_country = m.group("country")
    votes = []
    for e in engines:
        cands = openings(symbol, e, seg["page_start"])
        best = max(cands, key=lambda c: fuzz.ratio(c["tail"], tail), default=None)
        if not best:
            continue
        score = fuzz.ratio(best["tail"], tail)
        # the next speech's opening can resemble this one's words ("stated that her delegation had
        # voted ..."): a reading naming another delegation must match the words closely
        # whole-string comparison: a short name ("Peru") sits partly inside a long one ("... Republics")
        other = fuzz.ratio(_flat(best["country"])[:30], _flat(own_country)[:30]) < 60
        # and one that names another person of another delegation is another speech, however alike
        # the words ("Mr. PAVLOV ... requested that the vote be taken by roll-call" twice on a page)
        stranger = other and fuzz.ratio(_flat(best["name"]), _flat(m.group("name"))) < 50
        if score >= 60 and not (other and (score < 80 or short)) and not stranger:
            votes.append({"engine": e, "name": best["name"], "country": best["country"]})
    return votes


def majority(values: list[str], key=lambda v: v) -> tuple[str | None, int]:
    """Most frequent value (grouped by key), with its count; ties go to the first seen."""
    if not values:
        return None, 0
    counts = Counter(key(v) for v in values)
    top, n = counts.most_common(1)[0]
    first = next(v for v in values if key(v) == top)
    return first, n


# --- word-level voting for body text ------------------------------------------------

_WORDS: set[str] | None = None


def dictionary() -> set[str]:
    global _WORDS
    if _WORDS is None:
        _WORDS = {w.strip().lower() for w in Path("/usr/share/dict/words").read_text().splitlines()}
    return _WORDS


def _key(tok: str) -> str:
    """Comparison form of a token: lower case, letters and digits only."""
    return re.sub(r"[^\w]", "", tok.lower())


HONORIFICS = {"mr", "mrs", "miss", "mme", "mlle", "dr"}


def vote_page(texts: dict[str, str], pivot: str, weights: dict[str, float] | None = None) -> tuple[str, int]:
    """Majority reading of one page across engines, word by word.

    The pivot engine's text gives the line structure. Every other engine is aligned to it
    token by token (difflib on comparison forms); where a stretch of tokens is replaced
    one-for-one, each of those engine tokens votes for its position. Votes are counted on
    the comparison form (letters and digits), so "Mr." and "Mr," don't split the vote; the
    winning form is then written as the pivot writes it if the pivot agrees, else in its
    most-voted spelling. Ties go to a dictionary word, then to the pivot. Insertions and
    deletions are not voted on, so the pivot's wording and length are kept.
    Returns (text, number of tokens changed).
    """
    import difflib

    weights = weights or {}
    lines = texts[pivot].splitlines()
    ptoks = [(li, tok) for li, line in enumerate(lines) for tok in line.split()]
    pkeys = [_key(t) for _, t in ptoks]
    ballots: list[dict[str, float]] = [{t: weights.get(pivot, 1.0)} for _, t in ptoks]
    for eng, text in texts.items():
        if eng == pivot or not text:
            continue
        otoks = text.split()
        okeys = [_key(t) for t in otoks]
        sm = difflib.SequenceMatcher(None, pkeys, okeys, autojunk=False)
        w = weights.get(eng, 1.0)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op in ("equal", "replace") and (i2 - i1) == (j2 - j1):
                for k in range(i2 - i1):
                    tok = otoks[j1 + k]
                    ballots[i1 + k][tok] = ballots[i1 + k].get(tok, 0.0) + w
    words = dictionary()
    out_lines: list[list[str]] = [[] for _ in lines]
    changed = 0
    for (li, ptok), ballot in zip(ptoks, ballots):
        by_key: dict[str, float] = {}
        for tok, w in ballot.items():
            by_key[_key(tok)] = by_key.get(_key(tok), 0.0) + w
        pkey = _key(ptok)
        # an honorific read by any engine outweighs a common word in its place: "Mr." misread
        # as "My." or "Me," loses the speech opening, and summary records are full of them
        for k in by_key:
            if k in HONORIFICS:
                by_key[k] += 0.75
        win = max(by_key, key=lambda k: (round(by_key[k], 3), k in words, k == pkey))
        if win == pkey:
            best = ptok
        else:
            best = max((t for t in ballot if _key(t) == win), key=lambda t: ballot[t])
            changed += 1
        out_lines[li].append(best)
    return "\n".join(" ".join(ws) for ws in out_lines), changed
