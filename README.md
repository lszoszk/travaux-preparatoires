[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23940406.svg)](https://doi.org/10.5281/zenodo.23940406)

> **This repository** holds the code (pipeline, API, MCP server, site), the tests and the documentation of the method of the
> database at https://150.254.115.204/travaux/. The corpus itself (the records' text, the database file, the evaluation samples
> and gold sets that quote it) is not here: read it in the site, or, from a program or an AI assistant, through the MCP server
> (see the site's About → MCP). The commentaries and compilations used privately to measure the work are not here either.

# Travaux DB

A speech-level database of the travaux préparatoires of the Universal Declaration of
Human Rights (1946–48), the International Covenant on Civil and Political Rights and the
International Covenant on Economic, Social and Cultural Rights (1947–66).

Sibling project of [UNHRDB](https://lszoszk.github.io/generalcomments/): same stack
(SQLite FTS5 + a small API + static site), same citation discipline (UN symbol + pinpoint).

**Status (November 2026):** 2,160 documents (836 on the Declaration, 1,324 on the Covenants), 86,039 segments, 29,694 speeches (each with a speaker and a delegation; 17 of 18 changed attributions right in the blind check of round 128), 12,935 of them
tagged with the article under debate (95.3% ± 3.5% weighted precision, 91% within-tagged-records coverage / 86% overall) and 2,302 with a cross-cutting question of general debate, plus 6,768 decisions (302 with roll-calls) and 2,716 cited amendment and proposal symbols. Hosted at `https://150.254.115.204/travaux/`; quality figures: `docs/quality_audit.md`.

## Data policy

- Built from UN originals only. Every segment carries its UN document symbol and page
  or paragraph pinpoint, and links back to the UN copy.
- Printed compilations (Schabas 2013, Saul 2016, Bossuyt 1987) are copyrighted. They
  are used privately, as finding aids and as ground truth for measuring OCR accuracy.
  Nothing from them is committed or published (`data/private/` and `eval/private/`
  are gitignored).
- The UN documents were downloaded in September 2026 (one request every 6 s). The UN Dag
  Hammarskjöld Library's terms ask for approval of automated downloads, so the Library is told
  what was done and how the text will be used, under its terms for non-commercial use and with
  its credit line (`docs/un_library_permission_request.md`). No further automated download.

## Licence

The code is under the PolyForm Noncommercial License 1.0.0 (`LICENSE`): research, education, non-profit and personal use
are permitted; commercial use needs a separate licence from the author. What the database adds to the UN documents is under
CC BY-NC-SA 4.0 (`DATA_LICENSE.md`); the text of the UN documents stays under the UN's terms. See `NOTICE`. (v0.9 was
released under MIT for the code and CC BY-NC 4.0 for the data.)

## Layout

```
pipeline/   manifest builders, harvest, OCR, normalisation, segmentation, tagging
data/       manifest/ (committed)  concordance/  gazetteer/  gold/
            raw/ ocr/ cache/ private/ (gitignored)
api/        database build and a JSON API (standard library) over SQLite FTS5
site/       static frontend (search, reader, articles, delegations, votes, amendments)
eval/       OCR, completeness, speaker and tagging evaluations
tests/      unit tests for the parsers and the API
docs/       project documents
```

## Pipeline

```bash
# 1. What to fetch
python3 pipeline/build_udhr_manifest.py        # UN Library guide -> data/manifest/udhr.json (701 symbols)
python3 pipeline/build_udhr_supplement.py      # UN symbols Schabas cites that the guide lacks
python3 pipeline/build_covenant_manifest.py    # Covenant records 1949-66 (series ranges + known reports)

# 2. Fetch, one request every >= 6 s, with a provenance log (data/manifest/harvest_<name>.json)
python3 pipeline/harvest.py data/manifest/udhr.json --delay 6

# 3. OCR: UN text layer, Tesseract (4 modes), Apple Vision; best engine per page, then a word-level vote
swiftc -O pipeline/vision_ocr.swift -o bin/vision_ocr          # once
python3 pipeline/ocr_all.py data/manifest/harvest_udhr.json     # follows a running harvest
#   --manifest data/manifest/covenants.json   skip records whose agenda is not about the Covenants
#   --shard i/k                               run k in parallel

# 4. Speeches, speakers, votes, database
python3 pipeline/build_concordance.py            # UDHR draft -> final articles (data/concordance/drafts.csv)
#   the 1947-48 texts are read by hand instead: data/concordance/udhr_drafts_early.csv, and which text
#   each 1947-48 meeting worked from, data/concordance/udhr_early_meetings.csv
python3 pipeline/early_draft_texts.py            # the 1947 texts for the article histories, cut from the OCR by
#   hand-set anchors (data/concordance/draft_text_anchors.json); they replace the automatic cut where both exist
python3 pipeline/build_covenant_concordance.py   # E/2573 drafts -> ICCPR/ICESCR articles
python3 pipeline/build_all.py data/manifest/harvest_*.json   # segment, resolve speakers, rebuild the DB
```

What each step does:

| Step | Module |
|---|---|
| Page furniture, French column in bilingual records | `pipeline/normalize.py` |
| Speeches, chair, votes, headings, paragraph numbers | `pipeline/segment.py` |
| Speakers: attendance lists pooled per session, cross-engine reading of each speech opening | `pipeline/entities.py`, `pipeline/vote.py` |
| Bodies and sessions (from the guide, else from the symbol and the meeting date) | `pipeline/sessions.py` |
| Decisions: subject, outcome, figures, roll-calls, proposers | `pipeline/decisions.py` |
| Which article a passage is about (draft numbering -> final) | `pipeline/articles.py`, `api/build_db.py` |

Speakers are resolved against `data/gazetteer/delegates.csv` (checked delegate lists per
session) where one exists, else against the pooled attendance lists. Names that the engines
agree on but the list lacks are flagged in the segment's `review` field. Jev (TypeSafe) is an
optional second opinion (`entities.py --jev`, needs `TYPESAFE_API_KEY` in `.env`).

## Local frontend

```bash
python3 api/server.py      # http://localhost:8430 (serves the local scans: local use only)
```

- **Search** over speeches and document paragraphs (FTS5, BM25), filters by record, delegation,
  speaker, instrument, article and kind; the record reader with the scan; exports (CSV, JSON,
  BibTeX, RIS); a workspace of saved passages.
- **Articles** (UDHR, ICCPR, ICESCR): each article's text at each drafting stage with the changes
  marked, where it was debated, who spoke, the votes and the amendments.
- **Delegations**: delegates, sessions, articles, amendments proposed and roll-call votes.
- **Votes**: every decision the records report, with figures and roll-calls.
- **Amendments**: documents cited as amendments or proposals, with their proposers and votes.

## MCP server & Claude Skill

The database exposes six read-only Model Context Protocol (MCP) tools:
- `search_travaux`: full-text FTS5 and filter search over speeches, chair turns, votes and paragraphs
- `lookup_travaux`: read a passage in full, or a meeting record's speech-by-speech sequence
- `article_history_travaux`: draft text evolution, meetings, general debate topics, votes, amendments and speaking delegations for any UDHR (1–30), ICCPR (1–53) or ICESCR (1–31) article
- `delegation_travaux`: a state or organisation's delegates, sessions, articles, amendments proposed and roll-call votes
- `decisions_travaux`: query votes and roll-calls by instrument, article, delegation and outcome
- `amendments_travaux`: query cited L-series amendments and proposals by instrument, article, proposer and symbol

### Remote connector (Streamable HTTP)

`api/server.py` serves Stateless Streamable HTTP MCP at `/mcp` and `/api/mcp` (`https://150.254.115.204/travaux-api/mcp`):

```bash
claude mcp add --transport http travaux https://150.254.115.204/travaux-api/mcp
```

### Local stdio

`mcp/travaux_mcp.py` reads `data/travaux.sqlite3` directly over stdio (zero external dependencies):

```bash
claude mcp add --scope user travaux -- python3 /ABSOLUTE/PATH/TO/travaux/mcp/travaux_mcp.py
```

### Claude Skill (`travaux-research`)

`site/skills/travaux-research/SKILL.md` (and packaged `site/skills/travaux-research.zip`, also mirrored in `mcp/skills/travaux-research/SKILL.md`) teaches Claude the database's final-numbering concordance, general debate topic keys, summary-vs-verbatim citation rules, and multi-step travaux research workflows.

## Dataset

```bash
python3 api/export_dataset.py   # data/export/: documents, segments, decisions, amendments (JSON Lines), datasheet, manifest
```

The documentation of the dataset is in `docs/dataset/`: the datasheet (a template the export fills with the build's counts and
quality figures), the fields, the changelog and the release checklist (Zenodo, DOI, citation). `data/export/` is generated and
gitignored; a release is archived on Zenodo.

## Evaluation

The OCR and completeness checks need the private references in `eval/private/`.

```bash
python3 eval/ocr_bench.py --engines layer tess6 tess3 vision vote      # character error by scan type
python3 eval/completeness.py                                           # our text against Schabas's
python3 eval/speaker_eval.py chr3 E/CN.4/SR.60 E/CN.4/SR.61 E/CN.4/SR.62 E/CN.4/SR.63 E/CN.4/SR.64 --engine vote
python3 eval/speaker_eval.py early E/CN.4/SR.1 E/CN.4/AC.1/SR.1 E/CN.4/AC.1/SR.31 E/CN.4/SR.164 --engine vote
python3 eval/speaker_eval.py images A/C.3/SR.128 E/CN.4/SR.300 A/C.3/SR.290 A/C.3/SR.150 --engine vote   # checked on the page images
python3 eval/geneva_plenary_check.py     # Geneva plenary 1947 (SR.34-42): tags against the verified maps of the meetings
python3 eval/attribution_consistency.py                                # attributions that contradict the printed opening
python3 eval/article_topic_check.py                                    # are article tags plausible?
python3 -m pytest tests/                                               # parsers and API
```
