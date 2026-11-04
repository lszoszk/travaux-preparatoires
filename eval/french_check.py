#!/usr/bin/env python3
"""French text left in the database (preregistered in docs/devlog.md, 22 Oct 2026): the French and English function words
of every document that is not a machine translation, in two builds, and the gates of the fix (French down by at least
70%; English no more than 0.5% lost overall and no record losing more than 3%).

  python3 eval/french_check.py OLD.sqlite3 [NEW.sqlite3]
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from normalize import EN_WORDS, FR_WORDS  # noqa: E402


def counts(db: Path) -> dict[str, list[int]]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    mt = {s for (s,) in con.execute("SELECT symbol FROM documents WHERE machine_translated = 1")}
    out = defaultdict(lambda: [0, 0])
    for sym, text in con.execute("SELECT symbol, text FROM segments WHERE kind != 'masthead'"):
        if sym in mt:
            continue
        words = [w for w in re.findall(r"\b[a-zàâçéèêëîïôûùüÿœ']+", text or "") if w == w.lower()]
        out[sym][0] += sum(w in EN_WORDS for w in words)
        out[sym][1] += sum(w in FR_WORDS for w in words)
    return out


def main() -> int:
    old = counts(Path(sys.argv[1]))
    new = counts(Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "travaux.sqlite3")
    en0, fr0 = sum(v[0] for v in old.values()), sum(v[1] for v in old.values())
    en1, fr1 = sum(v[0] for v in new.values()), sum(v[1] for v in new.values())
    losers = sorted(((old[s][0] - new.get(s, [0, 0])[0]) / old[s][0], s) for s in old if old[s][0] >= 50)
    worst = [(x, s) for x, s in losers if x > 0.03]
    print(f"French function words {fr0:,} -> {fr1:,} ({(fr0 - fr1) / max(fr0, 1):.0%} fewer; gate 70%)")
    print(f"English function words {en0:,} -> {en1:,} ({(en0 - en1) / max(en0, 1):.2%} lost; gate 0.5%)")
    print(f"records losing more than 3% of their English: {len(worst)}" + "".join(f"\n  {s}: {x:.1%}" for x, s in worst[-10:]))
    ok = (fr0 - fr1) >= 0.7 * fr0 and (en0 - en1) <= 0.005 * en0 and not worst
    print("gates:", "passed" if ok else "not passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
