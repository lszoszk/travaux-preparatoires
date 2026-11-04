"""Correct the misreadings every OCR engine shares, from the corpus's own word frequencies.

A worn typewriter face makes all engines read "that" as "thet", "freedoms" as "freeadons",
"logically" as "logicully": voting cannot fix what every engine gets wrong. A word is
corrected when it is not an English word and a word that differs from it only by the usual
confusions (vowels a/e/o/u/c/s, r/n, l/i/t, h/b, m/rn ...) is far
more common (at least RATIO times as frequent and seen MIN_COMMON times). Capitalised
words keep their capital; words in capitals (surnames) and words with digits are left alone.

The frequency table is built once from the voted text of every document
(data/cache/wordfreq.json) and rebuilt with --rebuild.

Usage: python3 pipeline/spellfix.py --rebuild     (then pipeline/ocr_select.py --vote applies it)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREQ = ROOT / "data" / "cache" / "wordfreq.json"
RATIO = 50
MIN_COMMON = 30
# what a letter can be misread as (one-for-one substitutions)
CONFUSE = {
    "a": "eoucs", "e": "aocs", "o": "aeuc", "u": "aon", "c": "eoa", "s": "ae",
    "r": "n", "n": "ru", "l": "it", "i": "lt", "t": "li", "h": "b", "b": "h",
    "m": "n", "w": "v", "v": "w", "d": "a", "f": "t", "g": "q", "q": "g",
}
MULTI = [("rn", "m"), ("m", "rn"), ("cl", "d"), ("d", "cl"), ("vv", "w"), ("ii", "u")]
WORD_RE = re.compile(r"[A-Za-z]+")

_freq: Counter | None = None


def build_freq() -> Counter:
    c: Counter = Counter()
    for p in (ROOT / "data" / "ocr").glob("*/vote/page-*.txt"):
        c.update(w.lower() for w in WORD_RE.findall(p.read_text(encoding="utf-8")))
    FREQ.parent.mkdir(parents=True, exist_ok=True)
    FREQ.write_text(json.dumps(c), encoding="utf-8")
    return c


def freq() -> Counter:
    global _freq
    if _freq is None:
        _freq = Counter(json.loads(FREQ.read_text())) if FREQ.exists() else Counter()
    return _freq


def _variants(w: str, depth: int = 2):
    """Words reachable from w by up to `depth` confusions."""
    seen = {w}
    frontier = {w}
    for _ in range(depth):
        nxt = set()
        for x in frontier:
            for i, ch in enumerate(x):
                for alt in CONFUSE.get(ch, ""):
                    nxt.add(x[:i] + alt + x[i + 1:])
            for a, b in MULTI:
                k = x.find(a)
                while k >= 0:
                    nxt.add(x[:k] + b + x[k + len(a):])
                    k = x.find(a, k + 1)
        nxt -= seen
        seen |= nxt
        frontier = nxt
    return seen - {w}


_dict: set[str] | None = None


def dictionary() -> set[str]:
    global _dict
    if _dict is None:
        _dict = {w.strip().lower() for w in Path("/usr/share/dict/words").read_text().splitlines()}
    return _dict


@lru_cache(maxsize=1)
def protected() -> frozenset[str]:
    """The words of state names and adjectives (data/gazetteer/states.csv): never "corrected" to a commoner word
    ("Uganda" is not "agenda", "Malian" not "mation")."""
    from decisions import ADJECTIVES, STATES
    return frozenset(w.lower() for n in (*STATES, *ADJECTIVES) for w in re.findall(r"[A-Za-z]+", n))


@lru_cache(maxsize=200_000)
def correction(w: str) -> str | None:
    """The common word a lower-case non-word stands for, or None. A real word is never
    changed ("end" may be "and", but may be "end")."""
    f = freq()
    own = f.get(w, 0)
    if len(w) < 3 or w in dictionary() or w in protected():
        return None
    best, best_n = None, 0
    for v in _variants(w, 2 if len(w) >= 5 else 1):
        n = f.get(v, 0)
        if n > best_n:
            best, best_n = v, n
    if best and best_n >= MIN_COMMON and best_n >= RATIO * max(own, 1):
        return best
    return None


def fix_token(tok: str) -> str:
    m = WORD_RE.search(tok)
    if not m or tok.isupper() or any(ch.isdigit() for ch in tok):
        return tok
    w = m.group(0)
    if w.isupper() or (len(w) > 1 and any(ch.isupper() for ch in w[1:])):
        return tok
    c = correction(w.lower())
    if not c:
        return tok
    c = c.capitalize() if w[0].isupper() else c
    return tok[:m.start()] + c + tok[m.end():]


def fix_text(text: str) -> tuple[str, int]:
    """(corrected text, number of words changed); line structure kept."""
    changed = 0
    out_lines = []
    for line in text.split("\n"):
        toks = line.split(" ")
        new = [fix_token(t) for t in toks]
        changed += sum(a != b for a, b in zip(toks, new))
        out_lines.append(" ".join(new))
    return "\n".join(out_lines), changed


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        c = build_freq()
        print(f"{len(c)} word forms, {sum(c.values())} tokens -> {FREQ.relative_to(ROOT)}", file=sys.stderr)
    sample = "Mr. Nilson thet the render should Imow from the outaet thet the rights end freeadons. Logicully, the moro"
    print(fix_text(sample), file=sys.stderr)
