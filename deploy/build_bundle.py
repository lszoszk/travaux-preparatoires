#!/usr/bin/env python3
"""Assemble the deployment bundle for the API: what the container needs, and nothing else.

  python3 deploy/build_bundle.py [--out dist/travaux-bundle] [--no-db] [--public]

The bundle holds the Dockerfile and docker-compose.yml, api/server.py, the small data files the server reads
(data/concordance, data/gold, eval/*.json), the database (data/travaux.sqlite3, which docker-compose mounts
read-only) and the site (site/, static, with a config.js written from deploy/site_config.json: nginx serves it,
deploy/nginx-snippet.conf). It does not hold the scans (data/raw), the OCR (data/ocr), the pipeline or eval/private
(the printed compilations used to measure the OCR). Copy the folder to the VM (deploy/README.md).

--public refuses to build while the site has no author, affiliation or contact, or while LICENSE and CITATION.cff still
carry their <AUTHOR> and <DATE-RELEASED> placeholders: a public site must say who answers for it.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONCORDANCE = ["articles.csv", "udhr_final.json", "covenants_final.json", "amendment_sponsors.csv"]
GOLD = ["audit.json", "article_tags.jsonl", "speakers_chr3.jsonl", "speakers_early.jsonl", "speakers_images.jsonl"]
EVAL = ["ocr_bench.json", "completeness_udhr.json", "coverage.json", "ledger.json", "what_went_wrong.md"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "travaux-bundle")
    ap.add_argument("--no-db", action="store_true", help="leave the database out (for a test, or when it is copied apart)")
    ap.add_argument("--public", action="store_true", help="refuse to build without an author, affiliation, contact and licence holder")
    ap.add_argument("--site-config", type=Path, default=ROOT / "deploy" / "site_config.json")
    args = ap.parse_args()
    cfg = json.loads(args.site_config.read_text()) if args.site_config.exists() else {}
    missing = [k for k in ("author", "affiliation", "contact", "url") if not str(cfg.get(k) or "").strip() or "<" in str(cfg.get(k))]
    open_marks = [f for f in ("LICENSE", "CITATION.cff", "DATA_LICENSE.md")
                  if re.search(r"<(?:AUTHOR|DATE-RELEASED|URL)>", (ROOT / f).read_text(encoding="utf-8"))]
    if missing or open_marks:
        msg = (f"the site config ({args.site_config.name}) lacks {', '.join(missing)}" if missing else "") + \
              ("; " if missing and open_marks else "") + (f"{', '.join(open_marks)} still carry placeholders" if open_marks else "")
        if args.public:
            sys.exit(f"not a public bundle: {msg}")
        print(f"warning: {msg} (fine for a test; --public refuses)", file=sys.stderr)
    out = args.out
    if out.exists():
        shutil.rmtree(out)
    for f in ("Dockerfile", "docker-compose.yml", "nginx-snippet.conf", "README.md", "env.example", "nginx_patch_vm.py", "open_vm.py"):
        (out).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "deploy" / f, out / f)
    (out / "api").mkdir()
    shutil.copy2(ROOT / "api" / "server.py", out / "api" / "server.py")
    (out / "mcp").mkdir()
    shutil.copy2(ROOT / "mcp" / "travaux_mcp.py", out / "mcp" / "travaux_mcp.py")
    for sub, names, base in (("data/concordance", CONCORDANCE, ROOT / "data" / "concordance"),
                             ("data/gold", GOLD, ROOT / "data" / "gold"), ("eval", EVAL, ROOT / "eval")):
        (out / sub).mkdir(parents=True)
        for n in names:
            if not (base / n).exists():
                sys.exit(f"missing {base / n}")
            shutil.copy2(base / n, out / sub / n)
    (out / "eval" / "model_bench").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "eval" / "model_bench" / "results.json", out / "eval" / "model_bench" / "results.json")
    # the site, with the settings of this deployment
    shutil.copytree(ROOT / "site", out / "site")
    settings = {"api": cfg.get("api", "/travaux-api"), "scans": "un", "label": cfg.get("label", "working edition v0.9.1"), "title": "",
                "version": cfg.get("version", "v0.9.1"), "author": cfg.get("author", ""), "affiliation": cfg.get("affiliation", ""),
                "contact": cfg.get("contact", ""), "url": cfg.get("url", ""),
                # usage counts (site/assets/analytics.js): the GoatCounter endpoint and path prefix, and a GA4 measurement ID or ""
                "analytics": cfg.get("analytics", {})}
    # the site's own address in the page's metadata (canonical, og:image, JSON-LD), robots.txt, sitemap.xml and llms.txt
    site_url = cfg.get("url", "") or "./"
    for name in ("index.html", "robots.txt", "sitemap.xml", "llms.txt"):
        f = out / "site" / name
        f.write_text(f.read_text(encoding="utf-8").replace("{{SITE_URL}}", site_url), encoding="utf-8")
    (out / "site" / "config.js").write_text("// written by deploy/build_bundle.py from deploy/site_config.json\nwindow.TRAVAUX = "
                                            + json.dumps(settings, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
    for f in ("LICENSE", "DATA_LICENSE.md", "CITATION.cff"):
        shutil.copy2(ROOT / f, out / f)
    (out / "data").mkdir(exist_ok=True)
    if not args.no_db:
        db = ROOT / "data" / "travaux.sqlite3"
        if not db.exists():
            sys.exit("data/travaux.sqlite3 missing: run pipeline/build_all.py first")
        shutil.copy2(db, out / "data" / "travaux.sqlite3")
    banned = [p for p in out.rglob("*") if "private" in p.relative_to(out).parts or p.suffix == ".pdf"]
    if banned:
        sys.exit(f"the bundle must not hold {banned[:3]}")
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"bundle: {out} ({size / 1e6:.0f} MB, {sum(1 for p in out.rglob('*') if p.is_file())} files)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
