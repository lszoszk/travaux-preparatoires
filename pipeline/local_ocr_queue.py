#!/usr/bin/env python3
"""The order in which the local vision model (eval/vlm_local_bench.py, engine "chandra") reads the whole corpus, a few
hundred pages a night: the pages where it gains most first (docs/vlm_pilot_plan.md, the development sets and block B).

1. single-column pages of the meeting records (/SR., /PV.): the typescripts, where the OCR vote reads 4-6 times more words
   wrong than the model;
2. single-column pages of the other documents (the L-series, the reports, A/2929);
3. two-column pages other than the Third Committee's (the bilingual 1946-48 plenary, other printed records);
4. the Third Committee's printed two-column records (1948 EN/FR and 1950-66), where the vote is already about as good.
Within each group the pages with the lowest OCR agreement score come first. Pages already read are skipped by the reader,
so the run can be stopped and resumed at will (touch data/logs/chandra.STOP to stop after the current page).

  python3 pipeline/local_ocr_queue.py            # -> data/logs/chandra_queue.json
  caffeinate -is python3 eval/vlm_local_bench.py --sample data/logs/chandra_queue.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "data" / "ocr"
OUT = ROOT / "data" / "logs" / "chandra_queue.json"


def main() -> int:
    rows = []
    for sel_path in sorted(OCR.glob("*/selection.json")):
        safe = sel_path.parent.name
        meta = sel_path.parent / "meta.json"
        symbol = json.loads(meta.read_text()).get("symbol", safe) if meta.exists() else safe
        record = bool(re.search(r"_(?:SR|PV)\.\d", safe))
        for name, v in json.loads(sel_path.read_text()).items():
            m = re.match(r"page-(\d+)\.txt$", name)
            if not m or v.get("engine") == "translation":
                continue
            page = int(m.group(1))
            if not (sel_path.parent / "img" / f"page-{page:03d}.png").exists():
                continue
            two = bool(v.get("two_column"))
            group = (4 if two and safe.startswith("A_C.3_SR.") else 3 if two else 1 if record else 2)
            scores = v.get("scores") or {}
            score = scores.get(v.get("engine")) if scores else None
            rows.append((group, score if score is not None else 1.0, symbol, page))
    rows.sort()
    done = sum((OCR / r[2].replace("/", "_") / "chandra" / f"page-{r[3]:03d}.txt").exists() for r in rows)
    OUT.write_text(json.dumps({"pages": [{"symbol": s, "page": p, "group": g} for g, _, s, p in rows]}, indent=0))
    print(f"{len(rows)} pages in the queue ({done} already read) -> {OUT.relative_to(ROOT)}; by group: "
          + ", ".join(f"{g}: {n}" for g, n in sorted(Counter(r[0] for r in rows).items())), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
