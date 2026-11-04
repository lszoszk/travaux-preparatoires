#!/usr/bin/env python3
"""How well the records alone name an amendment's sponsors, measured on the sponsors the session reports list.

For each amendment in data/concordance/amendment_sponsors.csv (read from the reports, the disagreements
checked by hand) that the meeting records (SR, PV) cite, the sponsors the records' own citations give (counted
as api/server.amendments counts them): the same, overlapping (some sponsors missing or added), wrong (no sponsor in common), or
none. Also how many of the L-series documents the records cite have no sponsor at all.

  python3 eval/sponsor_eval.py [--show wrong|overlap|none]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
import server  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", choices=["wrong", "overlap", "none"])
    args = ap.parse_args()
    reports = dict(server.REPORT_SPONSORS)
    # the meeting records' own citations only (not the reports' paragraphs, which the reports' table was read from),
    # counted as api/server.amendments counts them: the sponsors named at least half as often as the commonest
    tally: dict[str, Counter] = {}
    for r in server.rows("SELECT r.ref_symbol, r.proposers FROM refs r JOIN segments s ON s.id = r.segment_id "
                         "WHERE r.amendment = 1 AND (s.symbol GLOB '*/SR.*' OR s.symbol GLOB '*/PV.*')"):
        tally.setdefault(r["ref_symbol"], Counter()).update(json.loads(r["proposers"] or "[]"))
    records = {}
    for sym, c_ in tally.items():
        top = c_.most_common(1)[0][1] if c_ else 0
        records[sym] = [w for w, k in c_.items() if k >= max(1, top // 2)]
    c, shown = Counter(), []
    for sym, rep in reports.items():
        if sym not in records or not rep:  # (no sponsor: a compilation)
            continue
        rec = set(records[sym])
        kind = "none" if not rec else "same" if rec == set(rep) else "overlap" if rec & set(rep) else "wrong"
        c[kind] += 1
        if kind == args.show:
            shown.append((sym, "|".join(rep), "|".join(sorted(rec))))
    n = sum(c.values())
    named = c["same"] + c["overlap"] + c["wrong"]
    print(f"{n} amendments the reports list and the records cite: same {c['same']}, overlapping {c['overlap']}, "
          f"wrong {c['wrong']}, none {c['none']}")
    print(f"  exact precision {c['same'] / named:.3f} (of those the records name), recall {c['same'] / n:.3f}")
    series = [s for s in records if "/L." in s and s.startswith(("A/C.3/", "E/CN.4/"))]
    print(f"L-series cited in the records: {len(series)}, without a sponsor from the records: "
          f"{sum(1 for s in series if not records[s])}; with the reports' table: "
          f"{sum(1 for s in series if not records[s] and s not in reports)}")
    for row in shown:
        print("  ", *row, sep=" | ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
