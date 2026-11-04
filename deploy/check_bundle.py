#!/usr/bin/env python3
"""Last look at a built bundle before it leaves the laptop.

  python3 deploy/check_bundle.py [dist/travaux-bundle]

Fails (exit 1) when the bundle holds anything that must not be public: a private folder, a scan, a git folder, an .env
file, a local path (/Users/..., this project's folder), an API key or the author's private address, in any text file or
in the database. The author's address is allowed only where deploy/site_config.json names it as the contact.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD_PARTS = {"private", ".git", "__pycache__", "raw", "ocr", "segments", "cache", "logs"}
BAD_SUFFIX = {".pdf", ".pyc", ".log", ".env"}
LEAKS = [(re.compile(r"/Users/[A-Za-z0-9._-]+"), "a local path"), (re.compile(r"Desktop/AI"), "a local path"),
         (re.compile(r"/private/(?:tmp|var)/"), "a temp path"),
         (re.compile(r"(?i)\b(?:TYPESAFE|JEV)[_-]?API[_-]?KEY\s*[=:]\s*\S{8,}"), "an API key"),
         (re.compile(r"\b(?:sk|ts|tsk)[-_][A-Za-z0-9]{24,}\b"), "a key-like token")]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TEXT = {".js", ".html", ".css", ".json", ".csv", ".md", ".txt", ".py", ".yml", ".yaml", ".cff", ".conf", ".svg", ".example", ""}


def main() -> int:
    bundle = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "travaux-bundle"
    if not bundle.is_dir():
        sys.exit(f"{bundle} is not a folder: run deploy/build_bundle.py first")
    cfg_path = ROOT / "deploy" / "site_config.json"
    contact = str(json.loads(cfg_path.read_text()).get("contact", "")) if cfg_path.exists() else ""
    allowed = set(EMAIL.findall(contact))
    problems: list[str] = []
    files = [p for p in bundle.rglob("*") if p.is_file()]
    for p in files:
        rel = p.relative_to(bundle)
        if BAD_PARTS & set(rel.parts[:-1]) or p.suffix in BAD_SUFFIX or p.name == ".env":
            problems.append(f"{rel}: must not be in a public bundle")
        if p.suffix in TEXT and p.name != "travaux.sqlite3":
            text = p.read_text(encoding="utf-8", errors="replace")
            for rx, what in LEAKS:
                m = rx.search(text)
                if m:
                    problems.append(f"{rel}: {what} ({m.group(0)[:40]})")
            for addr in set(EMAIL.findall(text)) - allowed:
                problems.append(f"{rel}: an address that is not the configured contact ({addr})")
    db = bundle / "data" / "travaux.sqlite3"
    if db.exists():
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%fts%'"):
            for col in [r[1] for r in con.execute(f"PRAGMA table_info({table})")]:
                for rx, what in LEAKS:
                    pat = rx.pattern
                    n = 0
                    for (v,) in con.execute(f"SELECT {col} FROM {table} WHERE typeof({col}) = 'text' AND {col} LIKE '%/%'"):
                        if rx.search(v):
                            n += 1
                    if n:
                        problems.append(f"database {table}.{col}: {what} in {n} rows ({pat[:30]})")
    for line in problems:
        print("FAIL", line, file=sys.stderr)
    print(f"{len(files)} files checked in {bundle}: {len(problems)} problems", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
