# UDHR build status

*As of 23 September 2026. The full UDHR corpus is built; the Articles 18–19 pilot that preceded it is kept below.*

## Full UDHR build (milestone)

| | |
|---|---|
| Documents | **811** (268 meeting records, 543 other documents) from the UN Library guide (701 symbols) and the UN symbols Schabas cites that the guide lacks (193). Downloaded from documents.un.org at one request per 6 s. |
| Segments | 29,743: **6,245 speeches**, 2,158 chair interventions, 615 vote lines, 15,683 document paragraphs, 3,900 headings |
| Speakers | 99.7% of UDHR speeches attributed, including organisations and Secretariat officials taken as printed; one spelling per delegate across sessions (checked against every engine's reading) and one name per delegation or organisation (`data/gazetteer/organizations.csv`) |
| Completeness against Schabas (`eval/completeness.py`) | 657 of the 728 documents he reproduces are in the database; **97.3% of his sentences are found in our text**. 69 are not available from ODS (they need the UN Digital Library, which is behind a bot check, so fetch them by hand). |
| OCR (`eval/ocr_bench.py`, 626 documents) | Character error after voting: **1.5%** overall (was 1.8% with the pilot's weights). Typed summary records 1.6%, typed documents and reports 2.0%, printed 1948 records 0.9%. Engine weights chosen on the full benchmark in two halves (`eval/tune_vote.py`); choosing the best engine sentence by sentence would reach 1.0%. |
| Votes (`pipeline/decisions.py`) | **1,119 decisions** read from the records: what was put to the vote, the outcome, figures for 802, 61 unanimous. **59 roll-calls** with each delegation's vote; 18 of their lists agree exactly with the figures, the others are marked "check the scan". 284 name the proposing delegation. |
| Amendments | 372 documents cited as amendments or proposals, with the delegation the record names with them, the articles they were debated under and the votes that name them. |
| Articles | Draft-to-final concordance for five stages built from the UN texts (`data/concordance/drafts.csv`). **1,896 speeches (30%)** and 428 decisions are tagged with a final article; see below for why not more. |

**Speakers.** Both silver references now come out complete: CHR 3rd session 128 right / 0 wrong / 0 missed; 1947 and 1950 records 49 / 0 / 0 (the four speeches missed before had "Mr. CASSIN: (France)" or OCR debris before the name).

**Why only 30% of speeches carry an article.**
- Most untagged speeches are general debate, procedure or other agenda items, and should stay untagged.
- In meetings held before May 1948 (the Drafting Committee's two sessions and the Commission's second), the draft Declaration and the draft Covenant were discussed together, each with its own article numbers. A test showed that tagging there went wrong more often than right. `eval/article_topic_check.py` asks whether a speech is close to its article's text; for those meetings, 10–35% of tags passed, against about 60% where the numbering is known.
- So these meetings are tagged only where a heading or the chair names the Declaration. Their draft article number is still stored and searchable.

**Frontend** (`python3 api/server.py`, port 8430):
- search, the record reader and the workspace, as in the pilot;
- **Articles**: each article's text at each stage with the changes marked, where it was debated, who spoke, the votes and the amendments;
- **Delegations**: delegates, sessions, articles, amendments proposed and roll-call votes;
- **Votes**: every decision, filterable, with roll-calls;
- **Amendments**: amendments and proposals, with their votes.

### Gates, full UDHR

| Gate | Target | Now |
|---|---|---|
| Body-text CER, 1947–48 typed pages | ≤ 3% | **1.6%** records, **2.0%** documents: met |
| Speaker-turn detection | F1 ≥ 0.95 | silver recall 1.00 (177/177); a hand-split gold set is still needed |
| Speaker/state accuracy | ≥ 98% | 0 wrong on the silver sets; 99.7% of corpus speeches attributed |
| Article-tag precision | ≥ 95% | **96%** (48 of 50 tagged speeches checked by hand, fresh sample; 95% interval 87–99%). It was 62% at the first check; the fixes are in `data/gold/article_tags.jsonl` and `eval/article_tag_precision.py`. Covenants (1955-63): **95%** (38 of 40, round 7; 87-88% before the procedural and off-topic fixes). |

### Open items

1. The documents not available from ODS (111 with the Covenants so far): `docs/missing_documents.md` lists them with the file name and a Digital Library link; `pipeline/missing_documents.py --add` takes in the PDFs saved by hand.
2. Twenty documents are below 50% coverage against Schabas; most are ECOSOC 1946 records whose symbols the book uses differently, or weak scans.
3. Delegate lists for sessions without one (Third Committee 1948: garbled names such as "AZICOUL").
4. A hand-checked gold set: 10 meetings, speakers and article tags against the page images.
5. Earlier drafting stages: the Secretariat outline and the first Drafting Committee draft match the final text only weakly (16 and 13 of about 40 articles).

---

# Pilot: UDHR Articles 18–19

*As of 23 September 2026. Phase 1 of the plan: 28 documents, 10 of them meeting records.*

## Pipeline

| Step | Script | What it does |
|---|---|---|
| UDHR document list | `pipeline/build_udhr_manifest.py` | **701 symbols** from the UN Library guide (220 meeting records, 212 with a meeting date). Gaps in the meeting series are recorded for the coverage check. |
| Pilot selection | `pipeline/build_pilot_manifest.py` | 28 documents: the Art. 18–19 debates (found through Schabas's index, used privately; only UN symbols are kept), the records verified in the book wiki, and 5 scan-type controls. |
| Download | `pipeline/harvest.py` | 28/28 PDFs from documents.un.org, one request every 6 s, with a provenance log (URL, sha256, pages, producer). |
| OCR | `pipeline/ocr.py`, `bin/vision_ocr` | 6 local engines per page: the UN text layer, Tesseract in 4 modes, Apple Vision. About 1.7 s per page (8 parallel processes). |
| Engine choice + voting | `pipeline/ocr_select.py --vote`, `pipeline/vote.py` | Two-column printed pages (blank gutter in the image) use Tesseract layout mode. Other pages pick the engine with the best dictionary words × agreement with the others. That page is then corrected **word by word by the weighted majority of the engines** (UN layer 1.5, each Tesseract variant 0.5, Vision 1). |
| Page furniture | `pipeline/normalize.py` | Running heads and catchwords are removed, including their OCR variants. |
| Speech splitting | `pipeline/segment.py` | Speech / chair / vote / article heading / masthead, with page range and printed paragraph number (1950 on: "¶ 8", including OCR-mangled "8,", "- 33,", "bd,"). Votes are parsed. |
| Speakers | `pipeline/entities.py`, `pipeline/vote.py` | Each speech opening is read by **all engines**. The speaker is the attendee that best fits all readings, name and delegation together. Candidates come from the session's delegate list (`data/gazetteer/delegates.csv`); without one, from the pooled attendance lists. A clean name that two or more engines agree on but that the list lacks is kept and flagged, so the list gets completed. |
| Jev (optional) | `entities.py --jev`, `pipeline/jev.py` | Off by default. It checks weak matches and settles leftovers. The pilot no longer needs it (see below). |

## Measurements

**OCR** (`eval/ocr_bench.py`; character error rate against Schabas's retypeset text, used privately; on the pages every engine read):

| Scan type | UN layer | Best single engine | Per-page choice | **Word-level vote** | Ceiling* |
|---|---|---|---|---|---|
| 1948 printed records (A/C.3/SR, EN/FR columns) | 2.4% | 0.7% (Tesseract layout) | 0.7% | **0.6%** | 0.4% |
| 1947–48 typed summary records | 13.6%† | 3.0% | 2.3% | **1.9%** | 1.5% |
| 1947–48 typed documents and reports | 4.4% | 3.1% | 2.8% | **2.4%** | 1.8% |
| All | 7.6% | 2.0% | 1.6% | **1.4%** | 1.1% |

\* best engine sentence by sentence.
† E/CN.4/AC.1/SR.40 has almost no usable text layer (76% error); the other records' layers are 1.3–3.6%.

Caveats:
- The voting weights were chosen on this same benchmark (three settings tried), so the vote column may be slightly optimistic. The full UDHR run has many more Schabas references to confirm them.
- Schabas occasionally corrects typing errors, so part of what's measured is editorial.
- Sentences no engine found closely (match score below 88) are left out.

**Speakers, no Jev** (`eval/speaker_eval.py`). There are two SILVER references, checked against the OCR text but not yet against the page images:

| Reference | Run on UN layer | Run on voted text |
|---|---|---|
| CHR 3rd session, E/CN.4/SR.60–64, 128 speeches | 128 right, 0 wrong | 126 right, 0 wrong, 2 not split out; +12 real speeches the reference lacks |
| 1947 and 1950 records (SR.1, AC.1/SR.1, AC.1/SR.31, SR.164), 49 speeches | 49 right, 0 wrong | 47 right, 0 wrong, 2 not split out; +35 real speeches |

**Pilot records in total:** the voted text yields **261 speeches against 181 from the UN layer**.
- E/CN.4/AC.1/SR.31: 29 speeches against 7.
- E/CN.4/AC.1/SR.40, the Art. 18 record with an unusable layer: 41 speeches.
- All 261 are attributed: 252 by the joint vote, 9 by the attendance list. **0 are flagged for review.**
- The 47 speeches beyond the references, and all of SR.40, were checked by eye: every attribution is correct.

**How the hard cases were solved.** The UN layer reads "CEAUG- (Chim)", "SOKES (UNITED KINGDOM)", "MDQRE (AUSTRALIA)" and "OIGXIHHEAU (Frecioe)". Tesseract and Vision read CHANG (China), DUKES, MOORE and ORDONNEAU (France), and the majority wins. Scoring name and delegation together matters: four engines read "CHANG (Chine)", and "Chine" is as close to Chile as to China.

**Why the delegate list matters.** With only MALIK listed for Lebanon at the Drafting Committee's 2nd session, the one-delegate fallback turned "AZKOUL (Lebanon)" into MALIK. Now a clean name read by two or more engines overrides that fallback and is flagged. Azkoul, Heyward (Australia) and Wu (China) were added this way.

**Jev compared with voting.**
- On the CHR 3rd session, Jev also identified every speaker, at about 1,330 input and 800 output tokens per question. It is now optional because:
  - it can only choose among the options it is given, so it can't fix spelling (it confirmed "SOKES" for DUKES);
  - it was confidently wrong once, on a garbled option that fused two attendees;
  - cross-engine voting got all of these right, free and the same on every run.
- It remains available as `--jev`, e.g. as a second opinion when a session has no delegate list.

**End-to-end check:** the wiki's pinpoints are found. On E/CN.4/SR.60 pp. 10–13 the Malik amendment, Pavlov, Cassin, Fontaina, Chang and Wilson all come out as separate, correctly attributed speeches, under draft art. 16.

## Against the go/no-go gates

| Gate | Target | Now |
|---|---|---|
| Body-text CER, 1947–48 typed pages | ≤ 3% | **1.9%** records, **2.4%** reports: met |
| Speaker-turn detection | F1 ≥ 0.95 | against the silver references: 173/177 found (0.98 recall), plus 47 real speeches they lack. A proper F1 needs hand-split meetings. |
| Speaker/state accuracy | ≥ 98% | **0 wrong** in 261 speeches (177 against references, the rest checked by eye): met, pending image check |
| Article-tag precision | ≥ 95% | not started |

## To do

1. **Confirm `data/gazetteer/delegates.csv`.** 79 names across 5 sessions. They were written from the majority OCR readings and the E/800 attendance list, and are marked "claude … to confirm".
2. **Article tagging.**
   - Headings ("Article 16") are captured, but in draft numbering. Fill `data/concordance/drafts.csv` from the primary texts (e.g. CHR 3rd session, E/CN.4/95 numbering: draft art. 16 → UDHR art. 18, per E/CN.4/SR.60 p. 10).
   - The 1948 Third Committee records name articles in running text rather than headings.
3. **1948 printed records: English only.** Tesseract's layout mode keeps the columns apart but also outputs the French column. It needs a language filter per block before splitting into speeches.
4. **The 4 reference speeches the voted text doesn't split out** (E/CN.4/SR.62 pp. 5, 10; E/CN.4/SR.1 p. 4; E/CN.4/SR.164).
5. **A real gold set:** 10 meetings split by hand and checked against the page images.
