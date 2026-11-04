#!/usr/bin/env python3
"""A copy of the project in which the vision reader's text (engine "chandra") stands in for the OCR vote wherever it passes
the guard, to see what the database would look like with the pages read so far, before anything changes here.

The copy (code and data, without the page images, the scans and the keys; data/raw is linked) gets, for each page with a
reading of the vision reader, that reading in data/ocr/<doc>/vote/page-NNN.txt, so that the pipeline's fixed engine "vote" reads
it unchanged, unless:
- the reading reached the token limit twice (a .failed marker: a runaway reading);
- the page is two-column (the segmenter keeps the English column by the vote's layout: pipeline/segment.py english_only);
- its length (without spaces) is outside LO-HI of the vote's (the guard of docs/vlm_pilot_plan.md: 0.85-1.15);
- the document is one whose text the hand-made tables anchor (the reports' sections and annexes, the drafts the concordance
  and the article histories are cut from): their anchors were copied from the OCR, and the cleaner reading misses them.
The names at turn openings and in the officers' lines go through pipeline/name_guard.py (unless --no-name-guard): a name not
known for its delegation is replaced by the OCR engines' reading of the same opening, or by the one close known name of the
session; replacements and unverified names are listed in the manifest.
Then, in the copy: python3 pipeline/resegment.py (segments again, moves every hand check and cached answer to the new ids,
rebuilds the database). The list of the pages taken and left is written to <out>/preview_manifest.json.

The OCR vote's page is kept in data/ocr/<doc>/vote_ocr/ before it is replaced (pipeline/dates.py reads every engine's first
pages, and the guard compares with the OCR vote), and a page no longer taken gets it back. --in-place does all this in the
project itself (the user's decision of 21 October 2026: the vision reader's text in the database, the speakers kept from the
OCR resolution by pipeline/speaker_carry.py); its manifest goes to data/logs/vision_merge_manifest.json.

  python3 pipeline/preview_mixed.py --out /path/to/travaux-preview [--lo 0.85 --hi 1.15]
  python3 pipeline/preview_mixed.py --in-place
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402

OCR = ROOT / "data" / "ocr"
ENGINES = ["layer", "tess3", "tess4", "tess6", "tess6min", "vision", "vote"]
EXCLUDE = [".git", ".env", "dist", "data/raw", "data/export", "data/ocr/*/img", "data/ocr/*/chandra-gpu", "__pycache__",
           "node_modules", ".claude"]


def compact(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def anchored_documents() -> set[str]:
    """The documents (as safe names) whose text the hand-made tables of data/concordance anchor."""
    import csv
    conc = ROOT / "data" / "concordance"
    out = set()
    for name in ("report_annex_sections.csv", "report_sections.csv"):
        out |= {r["symbol"] for r in csv.DictReader((conc / name).open(encoding="utf-8"))}
    for name in ("drafts.csv", "udhr_drafts_early.csv", "covenant_drafts.csv", "covenant_drafts_chr.csv", "covenant_drafts_tc.csv"):
        if (conc / name).exists():
            for r in csv.DictReader((conc / name).open(encoding="utf-8")):
                out |= {x.rstrip(".;,") for x in re.findall(r"[AE]/[A-Za-z0-9./]+", r.get("stage_symbol") or "")}
    return {safe_name(s) for s in out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("--in-place", action="store_true", help="in the project itself, not a copy")
    ap.add_argument("--lo", type=float, default=0.85)
    ap.add_argument("--hi", type=float, default=1.15)
    ap.add_argument("--no-name-guard", action="store_true")
    ap.add_argument("--pero-propose", action="store_true",
                    help="PERO's reading (where it has read the page) may replace a name in the guard, never keep one")
    args = ap.parse_args()
    if args.in_place == bool(args.out):
        sys.exit("give --out (a copy) or --in-place")
    out = ROOT if args.in_place else args.out.resolve()
    if not args.in_place:
        if out == ROOT or ROOT in out.parents:
            sys.exit("the copy must be outside the project")
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(["rsync", "-a", "--delete", *[f"--exclude={e}" for e in EXCLUDE], f"{ROOT}/", f"{out}/"], check=True)
        raw = out / "data" / "raw"
        if not raw.exists():
            raw.symlink_to(ROOT / "data" / "raw")

    def ocr_vote(doc: Path, name: str) -> Path:
        """The OCR vote's page: kept in vote_ocr/ once a reading of the vision reader has replaced it."""
        kept = doc / "vote_ocr" / name
        return kept if kept.exists() else doc / "vote" / name

    def restore(doc: Path, name: str) -> None:
        """A page not taken (now) keeps or gets back the OCR vote's text."""
        d = out / "data" / "ocr" / doc.name
        if (d / "vote_ocr" / name).exists():
            shutil.copy(d / "vote_ocr" / name, d / "vote" / name)
            (d / "vote" / name.replace(".txt", ".vision")).unlink(missing_ok=True)

    taken, left, names = [], Counter(), []
    guard = None if args.no_name_guard else __import__("name_guard").Guard()
    symbols = {safe_name(s): s for s in guard.session} if guard else {}
    keep_ocr = anchored_documents()
    for c in sorted(OCR.glob("*/chandra/page-*.txt")):
        doc = c.parent.parent
        if doc.name in keep_ocr:
            left["document anchored by hand"] += 1
            restore(doc, c.name)
            continue
        vote = ocr_vote(doc, c.name)
        if not vote.exists():
            left["no vote page"] += 1
            continue
        sel = json.loads((doc / "selection.json").read_text()) if (doc / "selection.json").exists() else {}
        if (c.parent / c.name.replace(".txt", ".failed")).exists():
            left["runaway"] += 1
            restore(doc, c.name)
            continue
        if sel.get(c.name, {}).get("two_column"):
            left["two-column"] += 1
            restore(doc, c.name)
            continue
        text = c.read_text(encoding="utf-8")
        ratio = compact(text) / max(compact(vote.read_text(encoding="utf-8")), 1)
        if not args.lo <= ratio <= args.hi:
            left["length outside the guard"] += 1
            restore(doc, c.name)
            continue
        if guard and doc.name in symbols:
            page = int(c.stem.split("-")[1])
            engines = {e: (doc / e / c.name).read_text(encoding="utf-8") for e in ENGINES if e != "vote" and (doc / e / c.name).exists()}
            engines["vote"] = vote.read_text(encoding="utf-8")
            if args.pero_propose and (doc / "pero" / c.name).exists():
                engines["pero"] = (doc / "pero" / c.name).read_text(encoding="utf-8")
            text, log = guard.check(symbols[doc.name], page, text, engines, frozenset({"pero"}))
            names.extend(log)
        d = out / "data" / "ocr" / doc.name
        if not (d / "vote_ocr" / c.name).exists():
            (d / "vote_ocr").mkdir(exist_ok=True)
            shutil.copy(d / "vote" / c.name, d / "vote_ocr" / c.name)
        (d / "vote" / c.name).write_text(text, encoding="utf-8")
        # (the mark that the page's text is the vision reader's: pipeline/entities.py takes its known names only there)
        (out / "data" / "ocr" / doc.name / "vote" / c.name.replace(".txt", ".vision")).write_text("")
        taken.append(f"{doc.name}/{c.name}")
    fixed = [x for x in names if x["now"]]
    manifest = {"guard": [args.lo, args.hi], "taken": len(taken), "left": dict(left),
                "names": {"replaced": len(fixed), "unverified": len(names) - len(fixed), "by": dict(Counter(x["by"].split(" (")[0] for x in fixed))},
                "name_log": names, "pages": taken}
    (out / "data" / "logs" / "vision_merge_manifest.json" if args.in_place else out / "preview_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n")
    print(f"{len(taken)} pages of the vision reader in the copy; left at the vote: {dict(left)}; names: {manifest['names']} -> {out}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
