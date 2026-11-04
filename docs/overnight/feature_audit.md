# UNHRDB feature audit for Travaux DB

Every UNHRDB feature is assessed critically: **port** (take as is, in the travaux data
model), **adapt** (same idea, changed for drafting records), or **skip** (does not fit, or
not worth it now). The source is generalcomments-repo/docs (index.html, app.js, app.css,
tokens.css) as of v19.x, 2026-09.

## Look
| UNHRDB | Decision | Why / how |
|---|---|---|
| Design tokens (paper, ink, garnet accent, Spectral / Source Serif 4 / JetBrains Mono), light and dark | **port** | Vendored unchanged into `site/assets/` (tokens.css, fonts.css, fonts/), so both tools read as one family. |
| Masthead: folio, serif title, italic subtitle, text nav, theme toggle | **port** | The folio carries the instrument and corpus counts. |
| Search bar: italic "Search." prompt, large serif input, result count as a folio | **port** | |
| Three columns: filters, results, dossier | **port** | The dossier becomes the record reader: travaux are read in sequence, and the speech before and after matters more than for a General Comment paragraph. |
| Results as margin / text / margin rows | **port** | Left margin: pinpoint (p. / ¶) and kind. Right margin: date and body. |

## Search and filters
| UNHRDB | Decision | Why / how |
|---|---|---|
| FTS5 BM25 search; phrases, AND/OR/NOT, prefix `*`; safe query builder | **port** | Already in `api/server.py::fts_query`, same semantics. |
| Syntax help popover, "Try" example queries | **port** | Examples from drafting debates ("freedom of thought", `religion AND change`, `propert*`). |
| Source scope (GC / JUR / SP) | **adapt** | Becomes **instrument** (UDHR / ICCPR / ICESCR) once the Covenants are in. Until then: document type (meeting record, report, draft, amendment). |
| Treaty, committee, country, year, label facets | **adapt** | Body, session, delegation, speaker, draft article → final article, year, and kind (speech / chair / vote). Labels (concerned groups) are **skipped**: they don't fit drafting records. |
| Result-count breakdown pills | **adapt** | Counts per instrument (later). |
| "Also try" synonyms when nothing matches | **skip for now** | Low value on a small corpus; revisit when ICCPR/ICESCR are in. |

## Reading and citing
| UNHRDB | Decision | Why / how |
|---|---|---|
| Dossier panel (paragraph, citation, context) | **adapt** | The record reader with the target speech highlighted, page breaks linked to the scan, and the OCR readings per speaker. |
| Documents tab (browse and read whole documents) | **port** | A **Records** view: sessions → meetings/documents, with speech counts, dates and the UN PDF. |
| Citation copy (symbol + ¶) | **port** | `E/CN.4/SR.60, p. 10 (Malik, Lebanon)`, or `para. N` where the record numbers paragraphs. |
| Export CSV / JSON / BibTeX / RIS / CSL-JSON / XLSX | **port** CSV, JSON, BibTeX, RIS; **skip** XLSX | XLSX needs a JS library, and CSV opens in Excel. |
| Copy link (permalink of the search state) | **port** | State in the URL hash, so a search or open record can be shared and reloaded. |
| Cited-by / cites graph | **adapt** | "Documents referred to": symbols mentioned in a speech (amendments E/CN.4/L…, A/C.3/…) are linked to those documents when they are in the corpus. |
| Related paragraphs (BGE embeddings) | **skip for now** | Needs an embedding pipeline. The article timeline covers "related" better for travaux. |
| OCR provenance banner | **port** | Per record: engine mix, and the pages where engines disagree. Also: "summary records paraphrase" and "draft numbering". |

## Research workspace
| UNHRDB | Decision | Why / how |
|---|---|---|
| Workspace: bookmarks, notes, Markdown export | **port** (lighter) | localStorage bookmarks with notes, exported as Markdown with citations. The user already works this way (unhrdb-workspace-*.md). |
| Save search | **port** | Kept in the workspace. |
| Citation checker (paste text, resolve citations, compare quotations) | **adapt, later batch** | Very useful for travaux: check "E/CN.4/SR.60, p. 10" citations and quoted words against the record text. |
| Ask (hybrid semantic retrieval, beta) | **skip for now** | Needs embeddings and an LLM, and summary records are paraphrases. Revisit after the three instruments are in. |

## Chrome
| UNHRDB | Decision | Why / how |
|---|---|---|
| Dark mode toggle | **port** | `data-theme` on `<html>`, remembered in localStorage. |
| Keyboard shortcuts (`/`, `Esc`, `?`) | **port** (minimal) | `/` focuses search, `Esc` clears. |
| Tour, welcome card | **skip** | A small tool with an About page. |
| Analytics consent, GA4 | **skip** | Local tool, no analytics. |
| Atom feeds | **skip** | A closed historical corpus: nothing new to announce. |
| Feedback → GitHub issue | **skip for now** | Only once the tool is public. |
| About / methodology | **port** | Sources, data policy, OCR method and measured error, what speeches are, draft numbering, coverage. |

## New travaux features (not in UNHRDB)
1. **Article timeline:** every stage of one article in order (draft texts, speeches, amendments, votes), across bodies and sessions.
2. **Vote table:** every recorded vote with outcome and counts, filterable by article and body.
3. **Delegation and speaker pages:** everything a delegation or delegate said, per article and session.
4. **Amendment tracker:** L-/A/C.3 amendment documents, who proposed them, where they were debated, how they were voted.
5. **Draft-text evolution:** one article's wording at each stage, with differences (once the concordance exists).
6. **Speech context:** the preceding and following speech in the dossier (who answered whom).
