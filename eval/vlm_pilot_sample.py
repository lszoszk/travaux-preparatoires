#!/usr/bin/env python3
"""The sample of the vision-reader pilot (docs/preregistration_vlm_pilot.md, section 3.1): 300 page images in four blocks,
drawn with the seed fixed in the preregistration (2026).

- A: the 40 annotated pages of eval/gold_pages/pages.json;
- B: 60 pages with a reference text (eval/private/reference): 20 typewritten summary records, 20 typewritten documents,
  20 printed two-column pages (A/C.3/SR. of 1948); 15 of the 40 typewritten pages from the lowest decile of the OCR
  agreement score of the typewritten candidates;
- C: 170 pages of 1949-66 without a reference: for each of the three series (CHR 1949-54, Third Committee 1950-61 and
  1962-66) its single-column pages by tercile of the agreement score (about 14 a cell), and 45 two-column pages; a cell with
  too few pages is filled from the same series;
- D: 30 single-column pages with an agreement score below 0.5, any year, not already drawn.

Excluded everywhere: the documents of the first development set (eval/vlm_pilot/dev_set.json) and the pages of the second
(dev_set2.json); a page must have its image. Output eval/vlm_pilot/sample.json (one item per page: block, cell, symbol,
page, image, score, two_column, and for block B the reference document).

  python3 eval/vlm_pilot_sample.py [--seed 2026] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
from common import safe_name  # noqa: E402
from segment_audit_sample import stratum  # noqa: E402

OCR = ROOT / "data" / "ocr"
REF = ROOT / "eval" / "private" / "reference"
PILOT = ROOT / "eval" / "vlm_pilot"


def pages_of(symbol: str) -> list[tuple[int, bool, float | None]]:
    """(page, two-column, the chosen engine's agreement score) for each page with an image."""
    sel_path = OCR / safe_name(symbol) / "selection.json"
    if not sel_path.exists():
        return []
    out = []
    for name, v in json.loads(sel_path.read_text()).items():
        m = re.match(r"page-(\d+)\.txt$", name)
        if not m or not (OCR / safe_name(symbol) / "img" / f"page-{int(m.group(1)):03d}.png").exists():
            continue
        scores = v.get("scores") or {}
        out.append((int(m.group(1)), bool(v.get("two_column")), scores.get(v.get("engine")) if scores else None))
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    rnd = random.Random(args.seed)
    dev1 = {d["symbol"] for d in json.loads((PILOT / "dev_set.json").read_text())["documents"]}
    dev2 = {(p["symbol"], p["page"]) for p in json.loads((PILOT / "dev_set2.json").read_text())["pages"]}
    gold = json.loads((ROOT / "eval" / "gold_pages" / "pages.json").read_text())
    taken = {(p["symbol"], p["page"]) for p in gold}
    items = [{"block": "A", "cell": "gold", "symbol": p["symbol"], "page": p["page"]} for p in gold]

    def ok(sym: str, page: int) -> bool:
        return sym not in dev1 and (sym, page) not in dev2 and (sym, page) not in taken

    def take(block: str, cell: str, pool: list, n: int, extra: dict | None = None) -> None:
        pool = [c for c in pool if ok(c[0], c[1])]
        for sym, page, two, score, *rest in rnd.sample(pool, min(n, len(pool))):
            taken.add((sym, page))
            items.append({"block": block, "cell": cell, "symbol": sym, "page": page, "two_column": two, "score": score,
                          **({"reference": rest[0]} if rest else {}), **(extra or {})})

    # B: pages with a reference text
    ref_pool = defaultdict(list)
    for f in sorted(REF.glob("*.json")):
        ref = json.loads(f.read_text())
        sym, keys = ref["symbol"], set(ref["pages"])
        kind = "printed" if sym.startswith("A/C.3/SR.") else "record" if "/SR." in sym else "document"
        for page, two, score in pages_of(sym):
            if str(page) in keys and (kind == "printed") == two:
                ref_pool[kind].append((sym, page, two, score, f.stem))
    typed = [c for k in ("record", "document") for c in ref_pool[k] if c[3] is not None]
    cut = sorted(c[3] for c in typed)[len(typed) // 10] if typed else 0
    low = [c for c in typed if c[3] <= cut]
    for kind in ("record", "document"):  # 15 of the 40 from the lowest decile: 8 records, 7 documents
        k_low = 8 if kind == "record" else 7
        take("B", f"{kind}, lowest decile", [c for c in low if c in ref_pool[kind]], k_low)
        take("B", kind, ref_pool[kind], 20 - k_low)
    take("B", "printed", ref_pool["printed"], 20)

    # C: 1949-66 without a reference
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    series = defaultdict(list)
    for sym, instr, body, session in con.execute("SELECT symbol, instrument, body, session FROM documents"):
        st = stratum(instr, body, session, sym)
        if st in ("CHR 1949-54", "Third Committee 1950-61", "Third Committee 1962-66"):
            for page, two, score in pages_of(sym):
                if page > 1:  # (the masthead is not the question)
                    series[st].append((sym, page, two, score))
    for st, pool in sorted(series.items()):
        single = sorted([c for c in pool if not c[2] and c[3] is not None], key=lambda c: c[3])
        thirds = [single[:len(single) // 3], single[len(single) // 3:2 * len(single) // 3], single[2 * len(single) // 3:]]
        short = 0
        for t, cell in zip(thirds, ("low", "middle", "high")):
            before = len(items)
            take("C", f"{st}, score {cell} third", t, 14 + (1 if cell == "high" and st == "CHR 1949-54" else 0))
            short += 14 - (len(items) - before)
        if short > 0:  # (the printed Third Committee records have few single-column pages: the rest of the series fills)
            take("C", f"{st}, filling", [c for c in pool if not c[2]] or pool, short)
    two_col = [c for st in series for c in series[st] if c[2]]
    take("C", "two-column", two_col, 45)
    n_c = sum(1 for x in items if x["block"] == "C")
    if n_c < 170:
        take("C", "filling", [c for st in series for c in series[st]], 170 - n_c)

    # D: the worst single-column pages, any year
    worst = []
    for (sym,) in con.execute("SELECT symbol FROM documents"):
        for page, two, score in pages_of(sym):
            if not two and score is not None and score < 0.5:
                worst.append((sym, page, two, score))
    take("D", "score below 0.5", worst, 30)

    for x in items:
        x["id"] = f"{x['symbol']} p{x['page']}"
        x["image"] = str((OCR / safe_name(x["symbol"]) / "img" / f"page-{x['page']:03d}.png").relative_to(ROOT))
    print(Counter((x["block"], x["cell"]) for x in items), file=sys.stderr)
    print(f"{len(items)} pages: " + ", ".join(f"{b} {n}" for b, n in sorted(Counter(x['block'] for x in items).items())),
          file=sys.stderr)
    if not args.dry_run:
        (PILOT / "sample.json").write_text(json.dumps({"seed": args.seed, "pages": items}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
