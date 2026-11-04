#!/usr/bin/env python3
"""Export the database as a dataset: JSON Lines tables, the concordance, and the documentation.

data/export/ (generated, gitignored; a release is archived on Zenodo, docs/dataset/RELEASE.md):
  documents.jsonl   one line per UN document: symbol, instrument, body, session, date, links, machine translation
  segments.jsonl    speeches, chair interventions, votes, headings and document paragraphs,
                    with speaker, delegation, pinpoint, article tags, topic and text
  decisions.jsonl   votes: subject, outcome, figures, roll-calls, proposers, article
  amendments.jsonl  documents cited as amendments or proposals
  concordance/      draft-to-final article tables (UDHR, ICCPR, ICESCR)
  DATASHEET.md      docs/dataset/DATASHEET.md with this build's counts and quality figures
  FIELDS.md, CHANGELOG.md, DATA_LICENSE.md, CITATION.cff   copied as they are
  manifest.json     version, date, code commit, row counts and the SHA-256 of every file

Usage: python3 api/export_dataset.py [--out data/export] [--version v0.9] [--doi 10.5281/zenodo.N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sqlite3
import string
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
import server  # noqa: E402

DB = ROOT / "data" / "travaux.sqlite3"
OUT = ROOT / "data" / "export"
DOCS = ROOT / "docs" / "dataset"


def write_jsonl(path: Path, rows) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--version", default=None, help="default: the version in CITATION.cff")
    ap.add_argument("--doi", default=None, help="the Zenodo DOI, once reserved (docs/dataset/RELEASE.md)")
    args = ap.parse_args(argv)
    out = args.out
    version = args.version or re.search(r'^version:\s*"?([^"\n]+)', (ROOT / "CITATION.cff").read_text(), re.M).group(1)
    out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    counts = {}

    def docs():
        for r in con.execute("SELECT * FROM documents ORDER BY instrument DESC, meeting_date, symbol"):
            yield {"symbol": r["symbol"], "instrument_corpus": r["instrument"], "body": r["body"], "session": r["session"],
                   "meeting_date": r["meeting_date"], "doc_type": r["doc_type"], "pages": r["n_pages"],
                   "un_link": f"https://undocs.org/{r['symbol']}", "pdf_url": r["pdf_url"] or None,
                   "source_language": r["source_language"] or None, "machine_translated": bool(r["machine_translated"]),
                   "translation_model": r["translation_model"] or None}
    counts["documents"] = write_jsonl(out / "documents.jsonl", docs())

    def segs():
        # (the document's translation fields, so that a machine-translated segment's citation says so; the general debates'
        # question from segment_topics)
        for r in con.execute("SELECT s.*, d.machine_translated, d.source_language, d.translation_model, t.topic, t.p AS topic_p "
                             "FROM segments s JOIN documents d ON d.symbol = s.symbol LEFT JOIN segment_topics t ON t.id = s.id "
                             "WHERE s.kind != 'masthead' ORDER BY s.symbol, s.seq"):
            h = dict(r)
            yield {"id": r["id"], "symbol": r["symbol"], "seq": r["seq"], "kind": r["kind"],
                   "page_start": r["page_start"], "page_end": r["page_end"], "para_start": r["n"], "para_end": r["n_end"],
                   "pinpoint": server.pinpoint(h), "citation": server.citation(h),
                   "speaker": r["speaker"], "delegation": r["delegation"], "speaker_method": r["speaker_method"],
                   "article_instrument": r["article_instrument"], "article": r["final_article"],
                   "draft_article": r["draft_article"], "article_mapping": r["article_mapping"],
                   "article_confidence": r["article_confidence"], "topic": r["topic"], "topic_confidence": r["topic_p"],
                   "vote": json.loads(r["vote"]) if r["vote"] else None, "review": r["review"], "text": r["text"]}
    counts["segments"] = write_jsonl(out / "segments.jsonl", segs())

    def decs():
        for r in con.execute("SELECT c.*, d.meeting_date FROM decisions c JOIN documents d ON d.symbol = c.symbol "
                             "ORDER BY d.meeting_date, c.symbol, c.seq"):
            yield {"segment_id": r["segment_id"], "symbol": r["symbol"], "meeting_date": r["meeting_date"],
                   "subject": r["subject"], "outcome": r["outcome"], "yes": r["yes"], "no": r["no"],
                   "abstentions": r["abstentions"], "unanimous": bool(r["unanimous"]),
                   "proposers": json.loads(r["proposers"] or "[]"), "documents_named": json.loads(r["refs"] or "[]"),
                   "roll_call": json.loads(r["roll_call"]) if r["roll_call"] else None,
                   "article_instrument": r["article_instrument"], "article": r["final_article"],
                   "draft_article": r["draft_article"]}
    counts["decisions"] = write_jsonl(out / "decisions.jsonl", decs())
    counts["amendments"] = write_jsonl(out / "amendments.jsonl", ({**a, "articles": [list(x) for x in a["articles"]]}
                                                                 for a in server.amendments({})))
    conc = out / "concordance"
    conc.mkdir(exist_ok=True)
    for name in ("drafts.csv", "udhr_drafts_early.csv", "udhr_early_meetings.csv", "overrides.csv", "covenant_drafts.csv",
                 "covenant_drafts_chr.csv", "covenant_drafts_tc.csv", "report_sections.csv", "report_annex_sections.csv", "amendment_sponsors.csv", "articles.csv", "udhr_final.json", "covenants_final.json"):
        src = ROOT / "data" / "concordance" / name
        if src.exists():
            shutil.copy(src, conc / name)
    for name in ("FIELDS.md", "CHANGELOG.md"):
        shutil.copy(DOCS / name, out / name)
    for name in ("DATA_LICENSE.md", "CITATION.cff"):
        shutil.copy(ROOT / name, out / name)
    today = dt.date.today()
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    figures = datasheet_figures(con)
    (out / "DATASHEET.md").write_text(string.Template((DOCS / "DATASHEET.md").read_text()).substitute(
        version=version, date=today.isoformat(), year=today.year, commit=commit, doi=f"https://doi.org/{args.doi}" if args.doi else "DOI not yet assigned",
        built=dt.date.fromtimestamp(DB.stat().st_mtime).isoformat(), **{k: f"{v:,}" for k, v in counts.items()}, **figures),
        encoding="utf-8")
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json")
    (out / "manifest.json").write_text(json.dumps({
        "title": "UN Travaux Préparatoires: a speech-level database of the drafting records of the UDHR, ICCPR and ICESCR",
        "version": version, "exported": today.isoformat(), "commit": commit, "doi": args.doi, "rows": counts,
        "files": {str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in files}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"-> {out}: " + ", ".join(f"{k} {v}" for k, v in counts.items()), file=sys.stderr)
    return 0


def pct(x: float, digits: int = 0) -> str:
    return f"{100 * x:.{digits}f}%"


def datasheet_figures(con: sqlite3.Connection) -> dict:
    """The counts and the quality figures the datasheet quotes, from the database and the evaluations' outputs."""
    one = lambda sql: con.execute(sql).fetchone()
    speeches, attributed = one("SELECT COUNT(*), SUM(speaker IS NOT NULL) FROM segments WHERE kind = 'speech'")
    tagged = one("SELECT COUNT(*) FROM segments WHERE kind = 'speech' AND final_article IS NOT NULL")[0]
    by_corpus = dict(con.execute("SELECT instrument, COUNT(*) FROM documents GROUP BY 1").fetchall())
    hosts = [(u or "") for (u,) in con.execute("SELECT pdf_url FROM documents")]
    first, last = one("SELECT MIN(meeting_date), MAX(meeting_date) FROM documents")
    # (the pages whose text is the vision reader's: pipeline/preview_mixed.py marks them vote/page-NNN.vision)
    marks = list((ROOT / "data" / "ocr").glob("*/vote/page-*.vision"))
    audit = json.loads((ROOT / "data" / "gold" / "audit.json").read_text())
    prec, cov, rep = audit["precision"], audit["coverage"]["pooled"], audit["reports"]
    spk = [json.loads(x) for x in (ROOT / "data" / "gold" / "speakers_audit.jsonl").read_text().splitlines() if x.strip()]
    bench = json.loads((ROOT / "eval" / "ocr_bench.json").read_text())["overall"]
    fam = json.loads((ROOT / "eval" / "coverage.json").read_text())
    cited = fam["cited"]["families"]
    date_of = lambda checked: checked.split(",")[0]
    return {
        "first_date": first, "last_date": last,
        "vision_pages": f"{len(marks):,}", "vision_records": f"{len({m.parent.parent for m in marks}):,}",
        "udhr_docs": f"{by_corpus.get('UDHR', 0):,}", "cov_docs": f"{by_corpus.get('Covenants', 0):,}",
        "speeches": f"{speeches:,}", "attributed": pct(attributed / speeches, 1),
        "tagged": f"{tagged:,}",
        "topics": f"{one('SELECT COUNT(*) FROM segment_topics')[0]:,}",
        "mt_docs": one("SELECT COUNT(*) FROM documents WHERE machine_translated")[0],
        "src_ods": f"{sum('documents.un.org' in u for u in hosts):,}", "src_uva": sum("uvallsc" in u for u in hosts),
        "src_hand": sum(not u for u in hosts),
        "records_pct": fam["records"]["pct"],
        "cited_pct": round(100 * sum(f["held"] for f in cited) / sum(f["distinct"] for f in cited)),
        "citations_pct": round(100 * sum(f["citations_to_held"] for f in cited) / sum(f["citations"] for f in cited)),
        "tag_precision": f"{pct(prec['weighted'], 1)} ± {100 * prec['half_interval']:.1f}",
        "tag_correct": prec["correct"], "tag_checked": prec["checked"],
        "tag_round": f"round {audit['round']}, {date_of(audit['checked'])}",
        "coverage_overall": pct(cov["overall"]), "coverage_within": pct(cov["within_tagged_records"]),
        "reports_correct": rep["correct"], "reports_checked": rep["checked"],
        "speaker_correct": sum(r["right"] for r in spk), "speaker_checked": len(spk),
        "speaker_pct": pct(sum(r["right"] for r in spk) / len(spk), 1),
        "speaker_round": f"round {spk[0]['round']}, {date_of(spk[0]['checked'])}",
        "cer_vote": pct(bench["cer"]["vote"], 1), "cer_chars": f"{bench['chars']:,}", "cer_docs": bench["docs"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
