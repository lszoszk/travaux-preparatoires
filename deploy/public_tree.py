"""The tree of the public repository (the user's decision of 4 Nov 2026: a new repository without this one's history; code,
tests, the method's documentation and aggregate results; the corpus stays behind the API and the MCP server).

Every file git tracks here goes, except: the internal documents (INTERNAL), this machine's settings, and any file that holds
text of the records, found by its 8-word runs against a sample of the database's own text (evaluation samples, gold sets,
judges' inputs). Code is never dropped for that reason (a test may quote a sentence); the treaty texts the pipeline needs
(TREATY_TEXTS) are the adopted UDHR and Covenants, not records, and the concordance files (the drafts' texts and mappings)
are what the pipeline reads. Names of annotators other than the author are replaced.

  python3 deploy/public_tree.py --dry                     # what would go and what would not, and why
  python3 deploy/public_tree.py --out ../travaux-public   # copy the tree there (the folder must not exist)
"""
import argparse
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERNAL = ("docs/handover.md", "docs/project_brief_", "docs/un_library_", "docs/audit_guide_pl.md", "docs/dla_studentki_",
            "docs/plgrid_grant_wniosek.md", "docs/tester_guide.md", "docs/codex_task_", "docs/overnight/STATE.md",
            "docs/presentation_examples.md", ".claude/", "deploy/site_config.json")
TREATY_TEXTS = ("data/concordance/udhr_final.json", "data/concordance/covenants_final.json")
METHOD_DOCS = ("docs/quality_audit.md",)   # its quotations are examples of errors, as in a methods paper
CODE = (".py", ".js", ".css", ".html", ".sh", ".yml", ".yaml", ".toml", ".cff", ".txt", ".svg")
NAMES = {"Magda": "the second annotator", "magda": "annotator2"}
PUBLIC_NOTE = """> **This repository** holds the code (pipeline, API, MCP server, site), the tests and the documentation of the method of the
> database at https://150.254.115.204/travaux/. The corpus itself (the records' text, the database file, the evaluation samples
> and gold sets that quote it) is not here: read it in the site, or, from a program or an AI assistant, through the MCP server
> (see the site's About → MCP). The commentaries and compilations used privately to measure the work are not here either.

"""


def runs(text: str, n: int = 8, step: int = 1) -> set:
    w = re.findall(r"[a-z]+", text.lower())
    return {hash(" ".join(w[i:i + n])) for i in range(0, max(0, len(w) - n + 1), step)}


def corpus_sample() -> set:
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    out = set()
    for (t,) in con.execute("SELECT text FROM segments WHERE kind IN ('speech', 'chair', 'vote', 'procedural') AND length(text) > 120"):
        out |= runs(t, step=12)
    return out


def plan():
    files = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
    sample = corpus_sample()
    keep, drop = [], []
    for f in filter(None, files):
        p = ROOT / f
        if not p.is_file():
            continue
        if f.startswith(INTERNAL):
            drop.append((f, "internal document or local setting"))
            continue
        if f.endswith(CODE) or f in TREATY_TEXTS or f in METHOD_DOCS or f.startswith("data/concordance/") or p.suffix in (".png", ".woff2", ".zip", ".xlsx"):
            keep.append(f)
            continue
        hits = len(runs(p.read_text(errors="ignore")) & sample)
        if hits >= 30:  # (a sampled run in twelve: about 360 words of the records, a few speeches; a quotation is fine)
            drop.append((f, f"holds record text ({hits} runs)"))
        else:
            keep.append(f)
    return keep, drop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    keep, drop = plan()
    size = sum((ROOT / f).stat().st_size for f in keep)
    print(f"public: {len(keep)} files, {size / 1e6:.1f} MB; left out: {len(drop)}")
    for f, why in drop:
        print(f"  - {f}: {why}")
    if a.dry or not a.out:
        return
    if a.out.exists():
        sys.exit(f"{a.out} exists: choose a new folder")
    for f in keep:
        dst = a.out / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        if f.endswith((".md", ".json", ".jsonl", ".csv", ".txt", ".py")):
            text = (ROOT / f).read_text(errors="ignore")
            for k, v in NAMES.items():
                text = re.sub(rf"\b{k}\b", v, text)
            if f == "README.md":
                text = PUBLIC_NOTE + text.replace("; handover: `docs/handover.md`", "")
            dst.write_text(text)
        else:
            shutil.copy2(ROOT / f, dst)
    wf = a.out / ".github" / "workflows" / "pages.yml"   # the site on GitHub Pages, the app shell only
    wf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "deploy" / "github-pages-workflow.yml", wf)
    print(f"copied to {a.out}")


if __name__ == "__main__":
    main()
