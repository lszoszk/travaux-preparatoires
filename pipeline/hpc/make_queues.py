#!/usr/bin/env python3
"""The queues of pages for the vision reader on PLGrid (preregistered in docs/devlog.md, 21 Oct 2026).

- data/logs/chandra_queue_plgrid.json: the 653 pages the laptop read with a quantized build of the model (read again with
  the original weights, first), then every page of data/logs/chandra_queue.json not yet read, in that queue's order;
- data/logs/chandra_queue_consistency.json: 50 random pages of the Kaggle run (seed 2032), read again for the comparison
  of the two GPU environments (eval/gpu_consistency.py).

  python3 pipeline/hpc/make_queues.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402

LOGS = ROOT / "data" / "logs"
OCR = ROOT / "data" / "ocr"


def rows(path: Path) -> list[dict]:
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    queue = json.loads((LOGS / "chandra_queue.json").read_text())["pages"]
    read = lambda x: (OCR / safe_name(x["symbol"]) / "chandra" / f"page-{x['page']:03d}.txt").exists()
    mlx = [{"symbol": r["symbol"], "page": r["page"]} for r in rows(LOGS / "vlm_local_bench.jsonl")
           if (OCR / safe_name(r["symbol"]) / "chandra" / f"page-{r['page']:03d}.txt").exists()]
    mlx = list({(x["symbol"], x["page"]): x for x in mlx}.values())
    left = [{"symbol": x["symbol"], "page": x["page"]} for x in queue if not read(x)]
    (LOGS / "chandra_queue_plgrid.json").write_text(json.dumps({"pages": mlx + left}))
    kaggle = {(r["symbol"], r["page"]) for r in rows(LOGS / "kaggle_chandra_run_v5.jsonl") if not r.get("error")}
    kaggle = sorted(k for k in kaggle if (OCR / safe_name(k[0]) / "chandra" / f"page-{k[1]:03d}.txt").exists()
                    and (k[0], k[1]) not in {(x["symbol"], x["page"]) for x in mlx})
    sample = random.Random(2032).sample(kaggle, 50)
    (LOGS / "chandra_queue_consistency.json").write_text(json.dumps({"pages": [{"symbol": s, "page": p} for s, p in sample]}))
    # every page the Kaggle runs read (V5 and V6), to be read again on Athena: the consistency test of 27 Oct found two names that
    # differ between the two environments, and the preregistered rule then reads the corpus in one (docs/devlog.md)
    runs = [r for f in ("kaggle_chandra_run_v5.jsonl", "kaggle_chandra_run_v6.jsonl") if (LOGS / f).exists() for r in rows(LOGS / f)]
    mlx_keys = {(x["symbol"], x["page"]) for x in mlx}
    again = list(dict.fromkeys((r["symbol"], r["page"]) for r in runs if not r.get("error")
                               and (OCR / safe_name(r["symbol"]) / "chandra" / f"page-{r['page']:03d}.txt").exists()
                               and (r["symbol"], r["page"]) not in mlx_keys))
    (LOGS / "chandra_queue_kaggle_again.json").write_text(json.dumps({"pages": [{"symbol": s, "page": p} for s, p in again]}))
    print(f"Kaggle pages to read again: {len(again)}", file=sys.stderr)
    print(f"PLGrid queue: {len(mlx)} quantized-build pages + {len(left)} unread = {len(mlx) + len(left)}; "
          f"consistency: 50 of {len(kaggle)} Kaggle pages", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
