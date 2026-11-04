#!/usr/bin/env python3
"""Meeting dates that contradict the order of the meetings (see pipeline/dates.py).

Usage: python3 eval/date_order.py [--show 20]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from dates import out_of_order  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=20)
    args = ap.parse_args()
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    dates = dict(con.execute("SELECT symbol, meeting_date FROM documents"))
    dated = sum(1 for s, d in dates.items() if d and ("/SR." in s or "/PV." in s))
    undated = sum(1 for s, d in dates.items() if not d and ("/SR." in s or "/PV." in s))
    bad = out_of_order(dates)
    print(f"{dated} dated meeting records ({undated} without a date); {len(bad)} with a date out of their series' order")
    for sym, (before, after) in list(bad.items())[:args.show]:
        print(f"   {sym} {dates[sym]} (between {before} and {after})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
