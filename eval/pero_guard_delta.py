#!/usr/bin/env python3
"""What PERO changes in the name guard (preregistered in docs/devlog.md, 20 Oct): on the pages of
eval/vlm_pilot/pero_guard_pages.json, the guard (pipeline/name_guard.py) runs on the vision reader's text twice, with the OCR
engines of pipeline/preview_mixed.py and with PERO added, rules unchanged. Each name the page prints at a turn opening or in an
officers' line gets an outcome: "kept" (known, or read the same by two engines), "replaced by X (how)", or "unverified"; the
names whose outcome differs (another name, not only another way to the same one) are listed, and a random sample (seed 2026) is written for judging on the scan.

  python3 eval/pero_guard_delta.py [--propose-only] [--pages FILE] [--sample 40] [--json eval/vlm_pilot/pero_guard_delta.json]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from name_guard import Guard, cues  # noqa: E402
from preview_mixed import ENGINES  # noqa: E402

OCR = ROOT / "data" / "ocr"


def outcomes(guard: Guard, symbol: str, page: int, text: str, engines: dict[str, str],
             proposers: frozenset[str] = frozenset()) -> list[dict]:
    _, log = guard.check(symbol, page, text, engines, proposers)
    logged = {}
    for x in log:
        logged.setdefault(x["read"], []).append(x)
    out, seen = [], Counter()
    for c in cues(text):
        k = seen[c["name"]]
        seen[c["name"]] += 1
        hit = logged.get(c["name"], [])
        x = hit[k] if k < len(hit) else None
        out.append({"read": c["name"], "country": c["country"], "line": c["line"],
                    "outcome": "kept" if x is None else f"replaced by {x['now']} ({x['by']})" if x["now"] else "unverified"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=40)
    ap.add_argument("--pages", type=Path, default=ROOT / "eval" / "vlm_pilot" / "pero_guard_pages.json")
    ap.add_argument("--propose-only", action="store_true", help="PERO may replace a name, never keep one")
    ap.add_argument("--json", type=Path, default=ROOT / "eval" / "vlm_pilot" / "pero_guard_delta.json")
    args = ap.parse_args()
    pages = [(d["symbol"], p) for d in json.loads(args.pages.read_text())["documents"]
             for p in d["pages"]]
    guard = Guard()
    changed, n_names, missing = [], 0, 0
    for sym, page in pages:
        d = OCR / sym.replace("/", "_")
        name = f"page-{page:03d}.txt"
        if not (d / "pero" / name).exists():
            missing += 1
            continue
        text = (d / "chandra" / name).read_text(encoding="utf-8")
        engines = {e: (d / e / name).read_text(encoding="utf-8") for e in ENGINES if (d / e / name).exists()}
        before = outcomes(guard, sym, page, text, engines)
        after = outcomes(guard, sym, page, text, {**engines, "pero": (d / "pero" / name).read_text(encoding="utf-8")},
                         frozenset({"pero"}) if args.propose_only else frozenset())
        pero_names = [c["name"] for c in cues((d / "pero" / name).read_text(encoding="utf-8"))]
        n_names += len(before)
        for b, a in zip(before, after):
            if b["outcome"].split(" (")[0] != a["outcome"].split(" (")[0]:  # (the name, not only how it was found)
                changed.append({"symbol": sym, "page": page, "line": b["line"], "read": b["read"], "delegation": b["country"],
                                "before": b["outcome"], "after": a["outcome"], "pero_names_on_page": pero_names})
    kinds = Counter((c["before"].split(" (")[0].split(" by ")[0], c["after"].split(" (")[0].split(" by ")[0]) for c in changed)
    print(f"{len(pages) - missing} pages read by PERO ({missing} not yet), {n_names} names; outcome changed for {len(changed)}: "
          + ", ".join(f"{a} > {b} {n}" for (a, b), n in kinds.most_common()), file=sys.stderr)
    sample = random.Random(2026).sample(changed, min(args.sample, len(changed)))
    args.json.write_text(json.dumps({"pages": len(pages) - missing, "names": n_names, "changed": changed, "sample": sample},
                                    ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
