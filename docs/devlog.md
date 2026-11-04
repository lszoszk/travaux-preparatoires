# Build log

Material for a write-up of how the database was built: the time it took, the AI work it used, and what went wrong.
The numbers come from `eval/ledger.py`, which counts the Claude Code transcripts of the project, and from git. Re-run
the ledger at each milestone, and add an entry below at the end of each round. The list of mistakes that changed a
result is in `eval/what_went_wrong.md`, and the measured quality, round by round, in `docs/quality_audit.md`.

## The figures on 13 October 2026

| | |
|---|---|
| Period | 22 September to 13 October 2026: 17 days with model work, 83 hours (UTC) with at least one model turn |
| Prompts typed by the author | 186 |
| Model turns (API responses) | 26,857 |
| Agents | 4,868, of which almost all ran inside 117 workflows (blind judges, page-image readers, research checks) |
| Tokens generated | 14.3 million (Opus 5.5 10.8M, Sonnet 5.5 3.4M, Haiku 4.5 0.12M, Fable 5.1 0.06M) |
| Tokens processed | 4.08 billion, of which 3.86 billion cache reads (the same context read again at every turn) and 205 million cache writes |
| Jev (TypeSafe) | 3,146 calls, 46,735 questions, 29.3M input and 2.5M output tokens (article checks, procedural filter, article choice, general-debate questions, speakers) |
| Sources | 2,771 PDFs fetched, 22,443 pages OCR'd locally (Tesseract, Apple Vision, the text layer) |
| Code | 177 commits, about 15,900 lines of Python and 2,300 of site code, 128 tests; about 52,000 words of documentation |
| Database | 28,274 speeches (28,149 with a speaker), 11,241 tagged by article, 1,571 with a question of general debate, 5,803 decisions, 1,066 footnotes |

What the numbers leave out: the planning session of 22 September, held in another folder; the author's own time
(decisions, reading, letters, testing); the cost, which depends on the plan the work ran under and is not computed.
The split of tokens by kind of work is a keyword approximation (`eval/ledger.py`):

| Kind of work | Model turns | Tokens generated |
|---|---|---|
| Direction and engineering (main session) | 4,532 | 5.1M |
| Quality checks (blind judges, audits) | 10,851 | 4.0M |
| Tagging and extraction | 2,777 | 2.2M |
| Reading reports and texts by hand | 2,801 | 1.7M |
| Research checks on articles | 5,450 | 1.1M |
| Sources and translation | 327 | 0.1M |

## Day by day

Dates are UTC (the ledger's); commits are counted by local date.

| Day | Prompts | Model turns | Generated (k tokens) | Commits | What happened |
|---|---|---|---|---|---|
| 22 Sep | 6 | 403 | 518 | – | Plan; feasibility; letter to the UN Library drafted |
| 23 Sep | 26 | 3,012 | 3,127 | 70 | Overnight autonomous run (15 iterations): pilot on UDHR arts 18-19 at 01:39, full UDHR at 10:26, the Covenants by 16:00; first hand check of the tags 62%, then 96% |
| 24 Sep | 12 | 1,340 | 994 | 9 | Third Committee 1955-66 tagged from its reports' meeting lists; first overall audit (round 31) |
| 25 Sep | 8 | 2,105 | 698 | 6 | Coverage: Jev's choice among a meeting's articles; research check on ICCPR 6 |
| 26 Sep | 5 | 644 | 355 | 4 | Reports tagged by section; amendment sponsors from the reports |
| 28 Sep | 30 | 4,938 | 1,931 | 28 | An offline tagger written by another model (Codex) as an experiment; research checks on UDHR/ICCPR 18 and 19; decisions in other wordings |
| 29 Sep | 17 | 1,592 | 589 | 9 | Missing records added by hand; ten French-only documents machine-translated and flagged |
| 30 Sep | 18 | 756 | 534 | 7 | L-series drafts and amendments; the UVA collection; deploy bundle; this ledger; a model benchmark |
| 2 Oct | 3 | 42 | 37 | 2 | A 30-second teaser video built from the running app |
| 3 Oct | 12 | 7,312 | 3,630 | 16 | Audits on page images (rounds 65-67); dates of 454 documents read by two readers; reader tags |
| 4 Oct | 15 | 93 | 134 | 9 | Launch-readiness fixes; deploy to the university VM behind a password |
| 6-7 Oct | 7 | 1,485 | 589 | 6 | Author details, a tester kit, segmentation round 68, a handover document |
| 13 Oct | 24 | 3,127 | 1,180 | 11 | Data on a second disk of the VM; rounds 69-78 (tag audit, general-debate questions, five segmentation rounds, a fresh audit on random pages, a vote audit) |

## How the work was organised

- One long Claude Code session, resumed after each pause; the author directs in short Polish prompts ("lecisz z
  kolejnym punktem"), the model plans, writes the code, runs it and commits locally. Nothing is pushed.
- Every change to the data is measured before it is kept: blind judges (Opus and Sonnet, a third on splits) on every
  changed article tag, paired audits on page images (the same pages before and after), speaker evaluations that
  must stay at 128/128, 49/49 and 29/29, and 128 tests.
- Jev (TypeSafe) answers calibrated multiple-choice questions where a rule cannot decide; its answers are cached and
  kept only above a threshold measured on a blind check.
- The rule for tags: no tag is better than a wrong one.

## Entries

### 13 October 2026

- The VM's data moved to a second disk; the deploy now takes the database folder from `TRAVAUX_DATA_DIR`.
- Round 69: the tag audit after the resegmentation, 95.4% ± 3.5.
- Round 70: Jev gives 1,571 untagged speeches a question of general debate (self-determination, one covenant or two,
  implementation, ...), kept at p ≥ 0.9 (87 of 90 right on a blind check).
- Rounds 72-75 and 77: segmentation (roll-calls, results, headings, running heads, hidden turns, footnotes), each
  checked on the page images of the changed pages.
- Round 76: a fresh audit on 120 random pages. Pages without error went from 41% to 44%, which is not significant. The
  earlier rounds had reported their gains on the changed pages only, which overstated them for the corpus as a whole.
- Round 78: a vote audit on 68 decisions read against the page images: outcome 63/64, figures 51/64, the clause voted
  on 51/64, roll-calls 5/8, article 21/21; proposers missing in 18 cases.
- Round 78, the fixes: the parser now reads the figures in those forms, ties "The amendment" to the sentence that put it to
  the vote, and recognises decisions taken without a vote. Proposers went from 1,701 to 2,043 decisions, decisions without a
  vote from 50 to 152. A blind check of 138 changes on the page images: proposers right in 61 of 75 (the old values in 7),
  without a vote 20/20, figures 16/20. Before the convention "25 votes, with 10 abstentions" = none against went in, 15 such
  votes were read on the scans (none prints a figure against; the French column says "contre zéro").
- Round 79, the leftovers of the votes: the text an amendment is to is no longer taken for its proposer, "sub-amendments"
  count, OCR-garbled adjectives are matched ("Teyptian" Egypt); a roll-call list with more names than the figures is moved to
  the vote it fits (9 of 12 such lists were attached to the wrong vote of a pair). Proposers 2,043 -> 2,075; blind check of
  every change: 52 of 59 right (old values 4).
- 14 October, round 80: a second audit on 120 fresh random pages: 54% without error (the round 76 sample gave 44%; most of the
  gap is the pages, as round 76 had shown). The typed Commission records hid turns inside others ("Major DUKES", "Tho CHAIRMAN
  said", "In reply to ..., Mr. JUVIGNY (France)" / "formally proposed"): 128 segments more; on the changed pages, speeches inside
  another 41 -> 11. The first build moved 52 article tags and the judges preferred the old tag in 40. Two causes were found and
  fixed in the tagging (a chair speaking as a delegate; readers' tags against the context), each measured against two
  alternatives first; after them 20 right changes, 10 right tags lost, 6 wrong ones rejected.
- 14 October, round 81: the agenda item above the first turn set apart from the masthead (834 records), and the page numbers,
  printers' lines and garbled "Page 13"s in the middle of a column taken out (882 pieces, all read before writing). Tags did
  not move, by design: the tagging still reads the heading with the masthead. Paired audit on 30 changed pages: pages without
  error 5 -> 15, none worse.
- 14 October, round 82: the last open items. A 1947 meeting had the Vice-Chairman in the chair because the OCR read
  "Chaixman"; documents' titles over two lines joined; the printers' job numbers off the page foot. One fix first moved the
  tags of a document (its title's second line named "Measures of Implementation"); the tag comparison caught it before commit.
- 14 October, round 83: the documents' footnotes set apart, the reports' lists of documents one entry per paragraph (with its
  symbol where the columns' counts agree), archive stamps taken out. The first build moved 1,500 article tags: the hand-read
  section maps of 39 reports anchor on lines of footnotes. Those reports keep their footnotes in the text; after that no tag
  moved (65,242 segments compared). Paired audit on 20 document pages: errors 62 -> 54.
- 14 October, round 84: a third audit on 120 fresh random pages: 59% without error (50-68%). Against the first such audit
  (round 76, 44%) the gain is significant; against round 80 (54%) it is not. The typed records of 1947-54 remain the weak part.
- 15 October, round 85: the typed records of 1947-54. A delegate named a second time without the country ("Mr. WILSON
  suggested ...") now opens a turn where a sentence has ended, and the underlined results ("The Commission adopted the Chinese
  proposal by ten votes to one") stand apart: 93 speeches and 67 results more, and the speakers named without a country take the
  delegation from the meeting's list. Paired audit on 30 changed pages: errors 83 -> 57. The first build changed 31 article tags
  and the judges preferred the old tag in 21 (a chair's turn split off a tagged speech lost its tag; procedure split off took the
  debate's article); the old tags were restored and the wrong ones rejected, after which 10 changes remained, all right.
- 15 October, round 86: what round 85 left, in one round at the author's request: results labelled "DECISION:" or with the
  verb misread ("wes rejected") stand apart, turns opened by "In reply to a question by ..." start where the phrase does, the
  typed pages' garbled running heads are dropped, and four speakers get the name the page prints (Braña, Santa Cruz, van
  Kleffens, Davies; 19 speeches in all). Paired audit on 30 changed pages: pages without error 3 -> 10, errors 52 -> 34. Two
  first versions were caught before the build: a running-head rule that also took "persons." and a heading "Article 10", and a
  speaker rule that renamed 67 speakers, many for the worse. The judges preferred the old article tag in 63 of 93 changes (the
  chair's newly found turns move the debate's article); one cause was fixed, the other tags restored or rejected.
- 15 October, round 87: turns the OCR's marks hid ("3°. | Mr.", "Mrs.» MEHTA", "* MI. BERNSTEIN" with the verb on the next line,
  the printed records' "Mr: Morozov (...)" inside a line): 35 speeches more. Paired audit on 30 changed pages: errors 58 -> 34,
  pages without error 1 -> 12, none worse. Overnight the scratch folder had been emptied by the system, so the comparison scripts
  were written again from the record of the earlier rounds.
- 15 October, round 88: results the OCR misspelled ("adonted", "DEOISTON:", "Paragvoph"), the figures of misspelled
  rejections the right way round, and 339 decisions without a vote that had lost their subject; procedural ones take no article.
  Decisions 5,874 -> 6,220. Read on the page images: 77 of 79 decisions right; paired audit errors 61 -> 41.
- 15 October, round 89: the catchwords at the foot of the typed pages, each result of a run its own segment, the headings
  after them. A first heading rule moved 1,239 tags in the reports and was narrowed before the build; splitting the runs of results
  first left the votes on amendments without their article, until they took the one the run's adoption names. Paired audit:
  errors 37 -> 31.
- 15 October, round 90: turns behind the OCR's marks ("; “Mrs.", "Mp.", "D’SOUZA"), the next column's headings, the figures the OCR
  garbled ("to_one", "b; 8 votes to k"). Paired audit errors 50 -> 33. A session limit stopped 51 of the audit's 60 readers and 8 of
  the decision checks; the audit was resumed from its journal.
- 15 October, round 91: a rule meant to stop the hand restorations of the last rounds (a chair's turn moving the debate's
  article by an aside) was measured before it was kept: on a blind sample of 60 of its 608 changes the judges preferred the old
  tags 35 to 21, and it was dropped. Three small fixes remain (an OCR form of CHAIRMAN, "ves adopted", the next column's headings).
  The round 90 deploy waited a while: the VM could not be reached from the author's VPN.
- 15 October, round 92: a fourth fresh audit on 120 random pages: 65% without error (56-74%), errors 69 (85 in round 84),
  speeches inside another 4.8% (6.3%). The gain since the first such audit (44%, round 76) is significant; since round 84 it is not.
  The audit also found a delegate of Mali filed under Malta in 8 speeches, from one OCR reading; fixed at the source.
- 15 October, round 93: the plenary of 1946 (the President behind a garbled role, the agenda's items after a decision, a masthead
  that had run to page 7) and a title after the name inside a line. Paired audit: errors 58 -> 35, none worse. Finished from a
  train: the round was committed before the author left and audited when the connection came back.
- 15 October, round 94: the plenary's agenda items and the typed records' headings after a result. Paired audit on the 12
  changed pages: errors 22 -> 10. A first version took the President's numbered list for headings; caught by the segment map.
- 15 October, round 95: results without figures ("Both suggestions were adopted."), the Rapporteur's turns as speeches named
  from the masthead (29), and "the Secretary-General" inside a sentence no longer a chair's turn. Paired audit on 30 changed
  pages: errors 79 -> 53, 2 worse. A first version also merged the Secretary-General's own plenary speech (A/PV.1496) into the
  President's; fixed before the commit.
- 15 October, round 96: the body's decisions inside a turn ("At the request of Dr. CHANG (China), the Commission decided ..."),
  garbled labels and roles ("IECISION:", "GHAIRMAN", "RAPPORITUR"), the chair named from the list of officers in 25 more
  records, and names with "DE LA". Paired audit on 30 changed records: errors 47 -> 31. A first version of the paragraph
  heading took "Article 3, paragraph 2" for article 3 and moved 9 speeches from UDHR 7 to UDHR 2 (the tag diff caught it: the
  heading now keeps its paragraph); one read "Chairman: Rapporteur: Mr. AZKOUL" as the chair's name; the Rapporteur's OCR
  variants first split a masthead into eleven speeches.
- 15 October, round 97: votes on the chair's ruling ("The Chairman's ruling was upheld by ..."), counts alone ("There were 6
  votes in favour, ..."), "Mo," for "Mr." and the chair's role with a sign for a letter ("CHAIRM‘N"). Paired audit on 27 changed
  records: errors 48 -> 33. The judges took votes on a ruling for procedure, and such votes lost their article; a first version
  let the chair's "in view of the provisions of article 2" move eight passages to another article.
- 15 October, round 98: OCR debris before a turn ("Bie Mr. MALIK", "viet) Mr, SCHWELB"; 15 turns) and the chair behind an
  opening phrase as the OCR misreads him ("After an exchange of views, the CHATRMAN proposed"; 8 turns). Paired audit on 22
  changed records: errors 58 -> 49. A first version of a guard took a paragraph's own number for the end of a sentence and
  merged turns in 63 records; undoing it in the next pass did not bring back three cached classifier answers, which the hand
  files now keep at their tags before the round. Lesson: before a second pass, keep a copy of data/cache.
- 16 October, round 99: a fifth fresh audit on 120 random pages (56% without error, against 65% in round 92: not significant,
  and, on reading, none of its errors from the rules of rounds 93-98); 91 paragraph numbers read again from their neighbours (30 of 30 right
  on the scans); 103 chair's turns named behind an opening phrase; an office no longer matched to a state's delegate (DAS of the
  Secretariat had been DAES of Greece); the close of a meeting without an article. A mistake on the way: a run of the entity
  step (pipeline/build_all.py --no-db) also segments, and it carried a segmentation change past the id migration; the earlier
  segmentation was rebuilt (85,318 segments, every text at its id) and the change run again through pipeline/resegment.py.
- 16 October, a look back: the rounds had stopped paying. Five fresh audits of 120 random pages (rounds 76-99) gave 53, 65,
  71, 78 and 67 pages without an error, the missed turns 25, 31, 29, 22 and 28; the paired audits always improved because
  they score the pages each rule was written for. segment.py had grown from 219 lines to 1,468 (about 175 patterns), and
  the remaining errors are the OCR's own garbling of the cues the rules read. No vision model had been tried as a reader,
  while three of them reading the gold scans agreed on 37 of 40 pages. Decision: no more rule rounds; a pilot of a
  vision-model page reader (text and turns at once, the OCR kept as a guard against invented text), 300 pages and a
  go/no-go gate (docs/vlm_pilot_plan.md), after the API credits renew; meanwhile a free local model (Chandra OCR 2 on
  Apple MLX) on the 60 pages with a reference text.
- 16 October, the local model: Chandra OCR 2 (an open vision model, 5-bit, run on the laptop with Apple's MLX) read a
  development set of 20 pages with a reference text in about 85 s a page. Character error rate 0.56% against 2.56% for the
  four-engine vote on the same pages; on the typewritten records 0.41% against 2.51%. A preregistration of the pilot was
  drafted first (docs/preregistration_vlm_pilot.md, to go to OSF with an embargo), and the development set was drawn apart
  from the preregistered sample and disclosed in it, so that this early look does not spend the test.
- 16 October, the second development set: 62 pages of the kinds the first did not cover, without a reference text. The
  local model and the vote were compared where they disagree, by blind readers of the scan, first checked on the first set
  against the reference (they agreed with it on 104 of 118 disputes, and most of the rest were the reference match's own
  errors). Words read wrong per 1,000: CHR typescripts 1949-54 40 for the vote against 7 for the model; the worst pages 120
  against 22; the plenary 20 against 2; but on the clean printed Third Committee records 1950-66 both read 1-2 wrong words in
  1,000 and the model adds nothing. Two faults found and fixed (a page cut at the token limit; descriptions of pictures
  written into the text).
- 16 October, block B of the pilot (the first preregistered test, scored after the timestamp): on the 39 typewritten pages
  the local model read 7.98% of characters wrong against 8.67% for the vote, lower as H4 predicts but with an interval that
  includes zero. Behind it, one failure: on E/CN.4/SR.8 p. 1 the model ran away (8,000 tokens of repetition) and lost the
  page; the guard's length test catches it, and with the guard the typewritten records go from 1.48% to 0.35%. The
  development sets had not shown this failure. Also found: a long document whose repeated wording fools the per-page
  measure (every engine 50.7% on one page).
- 17 October (night), block C read by the local model (170 pages of 1949-66, exploratory for this model): on the Commission's
  typewritten records 34-40 wrong words per 1,000 for the vote against 5-7 for the model; on the printed Third Committee
  records 3-4 against 2-3. The preregistration's timestamp got its Bitcoin proof (blocks 971759-971775). Then the corpus
  queue started (18,492 pages, typescripts first); its first page, the corpus's worst, ran away, and a bug in marking it
  stopped the run once (fixed, resumed).
- 17 October, morning: the corpus run, stopped by hand at 08:11, read 219 pages overnight (75 s a page on average), 531 of
  the 18,492 in all so far; two pages ran away and are marked failed (about 1 in 100 of the worst pages).
- The build log itself: `eval/ledger.py` now counts Jev's tokens and the active hours. Jev's usage log also held calls from
  two other projects (ECHR, UNHRDB), about 55,000 of 58,000 lines; they are filtered out.
- Things that went wrong: a `| head` on a Jev run killed it (SIGPIPE) and it had to be re-run; a rule dropping lines
  that held only a date also dropped real text and was replaced; 74 audit readers stopped on a session limit and the
  workflow was resumed from its journal; a judges' workflow was launched with a placeholder in place of its field map and
  stopped; three versions of the vote parser were measured on the corpus before the fourth was kept (the first lost a
  decision because a longer clause took in "pointed out" from the speech before, the second gave proposers to the base text).

## 18 Oct 2026: the corpus reading on Kaggle, and the GPU build against the laptop's

- Kaggle (two T4s, free, 30 GPU-hours a week) runs the original Chandra OCR 2 in fp16 through vLLM 0.31.0. Getting it to start took
  four tries: Kaggle's torchaudio and torchcodec are built for another PyTorch (removed); FlashAttention 2 does not run on the T4
  (vLLM falls back); the first start compiles Triton kernels for the T4 for about 12 minutes with no log line, which I twice took
  for a hang and interrupted. Settings that start: eager mode, no custom all-reduce, NCCL P2P off, the server in its own process group.
- Run 1 (Version 2, 17-18 Oct, after 4 h in Kaggle's queue): 1,961 pages in 10.5 h (~20 s a page with 16 in flight; ~4.5 times the
  laptop), 25 timeouts at the OpenAI client's 600 s default (now 30 min), no runaway reading. Merged into data/ocr: 540 -> 2,501
  pages read by the model. Run 2 started 18 Oct with run 1's output as input.
- The check before using them: both builds read development set 1 (20 pages). 7,231 of 7,233 words identical (two one-letter
  differences in garbled tokens); CER against the retyped reference 0.56% for both (vote 2.56%). The 5-bit quantisation of the
  laptop build costs nothing measurable here, and the GPU readings count as the same reader (eval/vlm_pilot/results_gpu_vs_mlx_dev1.md).
- Kaggle run 2 (Version 3, 18 Oct): 2,051 pages in 10.5 h (~19 s a page), 9 answers still over the 30-min timeout, 3 runaway
  readings (token limit reached twice). 4,552 of 18,510 pages are now read by the model (540 laptop, 4,012 Kaggle). Two free
  sessions a week (30 GPU-hours) read ~4,000 pages; the rest of the corpus needs about three more weeks or a PLGrid grant.
- Blind review by hand of the preview (20 Oct): before the model's readings go anywhere near the database, a person judges on the
  scan where the preview and the current database differ. 66 items drawn with a fixed seed (eval/preview_review_build.py): 37
  pages the two databases divide differently, 29 speeches whose speaker changed within the delegation, and 6 of them shown again
  later with A and B swapped (the reviewer's own consistency). Both versions are shown in one common text (the model's reading of
  the page) with the name at each turn's opening hidden: the current database's own text and the printed names would otherwise
  tell which version is the preview. The key stays out of the page (eval/preview_review.py, local on 8433); scored by
  eval/preview_review_score.py.
- Preregistered (20 Oct, before any reading): a third OCR witness for the name guard. The vision reader's typical error is a
  fluent, plausible name (ADRI for AZMI); the guard trusts a name that at least two OCR engines read the same, and those engines
  are Tesseract three times over (tess3/4/6) plus Apple Vision, so their errors are correlated. Three local, non-generative
  (CTC) line readers are tried: PP-OCRv5 (PaddleOCR 3, engine `paddle`), docTR with the CRNN recognizer (`doctr`) and PERO OCR
  with its published printed model (`pero`), each with its defaults; the only code of ours is the reading order (lines by
  height, a page whose lines fall into two columns read left column then right). Pages: dev set 1 (20 pages, Schabas
  reference) and the 40 gold pages (1946-66, all strata). Measures: CER on dev set 1 (eval/vlm_local_dev_cer.py); names at
  turn openings against the truth (the gold majority's speakers, the reference's printed names), counted per page: exact
  (spelling without spaces, hyphens or accents; or the last word), garbled, missed, and wrong-but-plausible (another known
  name); independence: of the true names no Tesseract engine reads exactly, the share the witness reads exactly.
  Gate per engine: (1) CER on the typed summary records of dev set 1 <= 2.0% (vote 2.51%); (2) exact names >= the best single
  Tesseract engine; (3) independence >= 25%; (4) wrong-but-plausible names <= 1 in all 60 pages; (5) <= 10 s a page on the
  M3. The winner is the passing engine with most exact names (ties: lower CER) and becomes an engine of the guard; if none
  passes, the result is recorded and nothing changes.
- Kaggle run 3 (Version 5, 19-20 Oct, 5 h of reading): 932 pages read, 5 timeouts, 4 runaway readings; median answer 274 s
  with 16 in flight (~19 s a page, as before). The client's closing line in the notebook said "13936 pages": the counter of
  the dataset's code copy, not the pages read (the run log has 937 rows). 5,524 of 18,510 pages are now read by the model;
  the week's GPU quota is spent.
- Preregistered (20 Oct): a pilot of collation (CollateX) for the article histories. The stages' texts of an article
  (draft_texts: UDHR 8 stages, ICCPR 13, ICESCR 4) are witnesses of one text; a variant graph shows at which stage each
  wording changed, and the records of the same sessions can say who proposed it. Pilot: UDHR articles 1, 4, 18 and 24, all
  eight stages in chronological order (Secretariat outline, Cassin draft, E/CN.4/21, E/CN.4/57, E/600, E/CN.4/95, E/800,
  A/777); each stage's text as in draft_texts, with the vision reader's text of the same passage where it has read the page;
  normalised (case, punctuation, quotation marks, paragraph numbers and editorial notes such as "(formerly Article 8)"
  dropped). Output: the alignment table, the graph (SVG) and TEI per article. Judged by hand, branch by branch: a real change
  of wording, or OCR noise. Gate: at least 80% of the branches real; if passed, every article mapped one to one, and the graph
  joins the article history; if not, the noise is recorded and the stages' texts are cleaned first.
- OCR witnesses, result (20 Oct; eval/vlm_pilot/results_ocr_witness.md): no engine passes the preregistered gate, so nothing
  changes. PERO passes four of five (CER on typed records 1.82%, vote 2.51%; 116 of 133 names exact, best Tesseract 102;
  57% of the names no Tesseract reads; no plausible wrong name) and fails speed: 10.7 s a page at the median on the M3's CPU
  against the 10 s limit (its GPU models are CUDA-only). docTR fails CER (3.91%), PP-OCR (now a v6 recognizer by default)
  fails CER and speed (65 s). PERO is nevertheless the best non-generative reader we have; using it is a new decision.
- Collation pilot, result (20 Oct; eval/collation_pilot/results.md): gate not passed, 29 of 117 branches real (25%). The main
  cause is alignment, not OCR: where a stage rewrites an article (art. 4, 18), CollateX's word alignment pairs coincidental
  "the/of/and/to" and shows moved words as dropped (66 artifacts); noise makes 22 (A/777's OCR, paragraph markers, and an
  extraction error in the database: E/CN.4/95's art. 1 holds an editorial note and the next article's limitations clause).
  Where consecutive stages are close, the branches are real ("men" > "human beings" and "by nature" dropped). Proposed: the
  stage documents read by the vision reader, the E/CN.4/95 error fixed, and stage-to-stage changes instead of one graph.
- Preregistered (20 Oct): stage-to-stage comparison of the article texts, instead of one graph over all stages (the collation
  pilot failed on alignment). For each UDHR article, each stage against the next one that has it (the eight stages, then the
  adopted text, A/RES/217(III), from data/concordance/udhr_final.json). Texts: the vision reader's reading of the passage
  (the 73 pages of the stage documents read locally for this), else the OCR's; editorial notes cut as in
  build_concordance.cut_notes. Each text split into clauses (sentences, semicolons, numbered paragraphs); clauses paired
  across the two stages by similarity (one to one, order free, so a moved clause is a move, not a drop and an add); within a
  pair, word differences (case and punctuation ignored); an unpaired clause is added or dropped. Every difference is a change,
  judged by hand by the pilot's rule: real, noise (OCR, notes, extraction) or artifact (a pairing or alignment that reports
  a change that is not there). Development on the pilot's articles 1, 4, 18 and 24; then frozen and run on held-out articles
  3, 12, 17 and 20. Gate, on the held-out articles: at least 80% of the changes real. If passed: all UDHR articles, then the
  Covenants' stages, and the changes join the article history.
- Stage-to-stage comparison, held-out result (20 Oct; eval/stage_changes/results.md): gate not passed, 65 of 96 changes real
  (68%; 72% counting real changes carrying a stray number). Far better than the one graph (25%): artifacts 11 instead of 66,
  and no OCR misreadings with the vision reader's text (73 stage pages read for this). The noise left is systematic: article
  numbers at a text's edge (12), catchwords repeated at a page break (3), cuts a few words off in the database (4), one text in
  French. An estimate, not a result: without numbers and catchwords about 81%, to be tested on new held-out articles.
- Preregistered (20 Oct, before the run): the stage-to-stage comparison again, with the systematic noise of the first run
  removed: article numbers and a spilled heading at a text's edges, catchwords repeated at a page break ("/placed placed"),
  the vision reader's passage widened to the text's first and last words, and the texts as the corrected concordance cuts
  them (E/CN.4/95's notes, E/CN.4/AC.1/3's English pages, damaged capital headings; until the database is rebuilt, read from
  data/segments/_draft_texts*.json). Development on the eight articles already seen (1, 3, 4, 12, 17, 18, 20, 24); then
  frozen and run on new held-out articles 6, 9, 13 and 22. Same rule, same gate: at least 80% of the changes real.
- Stage-to-stage comparison, second held-out run (20 Oct; eval/stage_changes/results.md): gate passed narrowly, 76 of 92
  changes real (82.6%), no noise left; the 16 artifacts are moved words and the leftovers of rewritten sentences. Six calls are
  borderline; counted against, 76.1%. The judge built the method: a second reader should judge the 92 changes. Fixed on the
  way, in the concordance (tests added, 131 pass): E/CN.4/95's notes, E/CN.4/AC.1/3's articles 1-5 read from the French page
  (now English, mapped 2>29, 4>5, 5>3), damaged capital headings ending a text.
- Preregistered (20 Oct): PERO in a limited role, as a further engine of the name guard on the pages where the guard is
  least sure: 558 pages of the preview (5,319 model pages) with a name left unverified (422) or replaced by the session
  roster (292). PERO reads them (eval/ocr_witness_read.py, its defaults); the guard runs again with PERO among the engines,
  rules unchanged (a name read the same by at least two engines besides the vote is kept; the engines' known reading
  replaces it). Every outcome PERO changes (unverified > kept, unverified > replaced, roster replacement > kept as read or
  > another name) is listed; up to 40, drawn at random (seed 2026), are judged on the scan. Gate: at least 95% right
  (at most 2 wrong of 40) and no wrong name that the guard would otherwise have left alone. If passed, PERO joins the guard
  for these pages in the pipeline (behind the same flag as the vision reader's text).
- PERO in the name guard, result (20 Oct; eval/vlm_pilot/results_pero_guard.md): gate not passed. On 558 uncertain pages PERO
  changes 36 of 2,076 names: 21 right, 5 wrong (a damaged H or L read the same by PERO and another engine keeps the garble
  over the roster's right correction: LOUIFI, WEITLAM, WHITIAM, MEETA, EDARE), 10 the typist's own misspelling kept over the
  person's name (SORENSON, SOERENSEN, RAMANDAN...). PERO is independent of Tesseract, not of the vision reader on damaged type.
  Its 5 replacements of unverified garbles were all right: "PERO may propose, never confirm" is a new rule to preregister.
- Preregistered (20 Oct): "PERO may propose, never confirm" (pipeline/name_guard.py proposers; preview_mixed.py
  --pero-propose). On the development pages (the 558 already judged) it changes 6 names, all 6 right by the earlier
  judgments (KURAL, MEHTA twice, MALIK, HOARE, QUIJANO), and none of the 15 losses. Held-out test: the pages the next Kaggle
  runs add, where the guard leaves a name unverified or takes the roster's; PERO reads them; every name the rule changes is
  judged on the scan. Such changes are rare (6 in 2,076 names, about one per 1,000 model pages), so the test runs until 10
  changes are judged or the corpus is read; gate: at most 1 wrong. Until then the rule is used in the preview only.
- Decided by the user (20 Oct): where the typist misspelt a name (SORENSON, RAMANDAN, DIAZ-CASANEUVA), the text keeps the
  page's spelling (it is a quotation) and the speaker field takes the person's usual name.
- Blind review by hand, result (20 Oct; the user, 66 items, 6 repeats all consistent): pages, preview better in 28 of 29
  decided (97%); speakers, 15 of 24 (62%). The speaker losses are the guard's leftovers and the resolution's: garbles read
  alike by tess3 and tess6 (one engine family) pass as confirmed, unverified printed names beat the engines' vote, and
  "Charles MALIK" escapes the canonical spelling. Fixes to make and test before the vision reader's text goes anywhere near
  the database.
- Preregistered (20 Oct): fixes to the speaker resolution with the vision reader's text (all behind
  TRAVAUX_TRUST_PRINTED_NAMES=1): (1) a printed name counts as confirmed only when two engine families read it (Tesseract's
  variants are one family; HASRE, HOPGSCN); (2) a printed name with a first name ("Charles MALIK") takes the known canonical
  spelling, never its own; (3) the user's decision: a typist's spelling close to one delegate of the delegation in this
  session (ratio >= 80, ten points ahead) is that person (SORENSON, MOROSOV, DOWIE); (4) names taken from a speech's text,
  not from a list, are not offered to the joint pick of name and delegation (a BACPAPI from one meeting outvoted BAGDADI in
  the next). Development: the 24 speaker items the user decided. Test: a new blind review by the user of 30 speaker changes
  drawn from the rebuilt preview (seed 2027, none from the records of the first sample). Gate: the preview better in at
  least 85% of the decided items, and no garbled name (a spelling no attendance list or gazetteer has) judged worse than the
  current one more than once.
- Speaker fixes, development (20 Oct): three rounds on the 24 speaker items the user decided. Added on the way: a gazetteer
  variant is its delegate (HANSA MEHTA is MEHTA); names from a speech's text stay in the joint pick when known (the printed
  records' BEGTRUP, HABIB); a delegate one engine reads exactly, and no other, comes before a garbled text name (BAGDADI).
  After round 3 every loss the user found is back (BAGDADI, CORBET, LOPEZ, ARUTIUNIAN, HABIB, HODGSON), the preview's gains
  stay (HEYWOOD, WINANT, ORIBE, VAN DER MANDELE, MOROZOV), and printed variants take the usual name (MALIK, MEHTA, SORENSEN,
  BOWIE, LOUTFI). Frozen; the test round (eval/preview_review2, 30 items + 4 repeats) is with the user.
- Blind review round 2, result (20 Oct): the speaker fixes do not pass, 21 of 28 decided (75%, gate 85%) and five garbled
  names judged worse (LURD, LOND, MURUSUV, CAZE, JEXXS). Damaged type in typed records makes all readers agree on a garble,
  which the engine-family confirmation then takes; a one-family majority outvotes the vision reader in the organisations'
  path; the vision reader's own misreading becomes a name where no engine finds the opening. The "Ronald MACDONALD" the
  user flagged as a hallucination came from the current pipeline, not the language model.
- Preregistered (20 Oct): speaker fixes, second set (TRAVAUX_TRUST_PRINTED_NAMES=1): (1) in typed records the two-family
  confirmation of a printed name applies only when the session lists no delegate of that delegation (otherwise the roster
  decides, as in the current pipeline: LORD, MOROZOV); (2) a majority of one engine family does not outvote the vision
  reader's reading (JEXXS against JENKS); (3) a name only the vision reader reads (no engine finds the opening) does not
  become a new name: the speech is left without a speaker rather than given a wrong one (CAZE). Development: round 2's items.
  Test: round 3, 30 new speaker changes + 4 repeats (seed 2028, no record of rounds 1 and 2), same gate (85% of decided,
  at most one garbled preview name judged worse).
- Speaker fixes, second set, development (20 Oct): on rounds 1-2's items every garble the user judged worse is gone (LURD,
  LOND, MURUSUV, JEXXS back to LORD, LORD, MOROZOV, JENKS; CAZE now no speaker), the gains stay. Cost: 84 more speeches
  without a speaker (unresolved 90 > 174), the names only the vision reader reads. Frozen; round 3 (eval/preview_review3,
  30 + 4 repeats, seed 2028) with the user.
- Blind review round 3, result (20 Oct): 58% of 26 decided, gate not passed and worse than round 2. The one-family rule took
  the OCR vote's text for the vision reader's on pages it never read (Gancta-Sayan, RAARAR, MONEW), its garbles entered the
  session pool (LINPSTRÉM), and the no-engine rule dropped two right names. Lesson recorded: three rounds of case-by-case
  fixes each made new losses; proposed a minimal rule instead (the current resolution everywhere, the vision reader's name
  only on its own pages and only when it is a known person of the delegation).
- Minimal speaker rule (20 Oct, the user's choice after round 3): the current resolution everywhere; with the vision reader's
  text, and only on a page it read (marked in the copy, vote/page-NNN.vision), its printed name is taken when it is a known
  person of the delegation (canonical spelling, gazetteer variants to their delegate) or the one delegate of the session
  close to it. Everything else of the three rounds is withdrawn (two-family confirmation, the joint-pick exclusion, the exact
  delegate rule, the one-family rule, the no-engine rule, and the unify_speakers exception). Check first on the 84 items the
  user judged in rounds 1-3 (development, not a test); then round 4 on new records as the test (same gate).
- Decided by the user (20 Oct): publication no longer waits for the UN Library's approval. The records are public UN
  documents, the project is non-commercial, and the Library's terms allow free non-commercial use with its credit line; only
  the automated download needed approval (a terms-of-service point). The letter (draft 6) is now a notice: what was
  fetched and how, use under the non-commercial terms, deletion if the Library objects, and a request for the 1,435
  documents ODS does not serve. Opening planned for early 2027; an objection received before then is followed.

## 21 October 2026

- Schabas's index as a measure, a source and an audit of the UDHR article tags (the user's decision, 20 Oct; plan in
  ~/.claude/plans and below). Step 1 done: eval/schabas_reference.py now also writes which UN page(s) each book page holds
  (data/private/schabas_pagemap.json, private: 728 documents, 3,567 book pages, 1.83 UN pages per book page; the reference
  files are unchanged). eval/ocr_bench.py gains locate_span() (the matched window; locate() unchanged). The record-level
  check now maps index pages by each document's exact book pages instead of the table of documents: both 701, Schabas only
  3,149, ours only 183 (was 513 / 2,220 / 186); 79% of our (record, article) pairs in records Schabas covers are in his
  index. The index is a mentions index, so its "only" pairs are candidates, not errors.
- Preregistered (21 Oct), before any candidate is built:
  - Source. Candidates: (article, book page) -> document -> UN page -> our speeches on it (text alignment, MIN_FOUND 88),
    untagged speeches over 150 characters. Gate: one candidate article -> the Jev check (p >= 0.7, the 1946-48 threshold);
    several -> Jev's choice among them (p >= 0.9) and the check on the pick (>= 0.7). Passing = "tag", the rest "possible"
    (metadata). The source enters the database only behind a flag, after the acceptance test.
  - Acceptance test: a random 60 of the "tag" rows (seeded), stratum UDHR/schabas/check, two blind judges and a third on
    splits, the user on disputes. Gate: at least 57 of 60 right (95%). Below it the source stays "possible" only.
  - Measure: page-level coverage of the index by our tags (covered / possible / missed / page not aligned), per article
    and per record type, before and after; never counting our tags the index lacks as wrong.
  - Audit: a random 40 of the (record, article) pairs only we tag in records the index covers, same judges; reported as
    k/40 with a Wilson interval; wrong ones go to tag_rejections.csv.
- Schabas candidates through the Jev gate (21 Oct; data/concordance/schabas_candidates.csv): of 5,275 candidate pairs on
  1,467 untagged speeches, 129 pass (68 single candidates with the check >= 0.7; 61 picks of Jev's choice >= 0.9 confirmed
  by the check), 5,146 stay possible. Jev's choice on 993 speeches with several candidates: none 561, another article 169,
  one of them 263 (76 at >= 0.9). The general debates give almost nothing: in the 15 untagged records only E/CN.4/SUB.2/
  SR.11 (9 speeches) and SR.17 (1) pass; the Commission's general debate, the Third Committee's and the plenary's speeches
  are, for Jev, general statements on several articles at once, which is what the rule wants left untagged. The passing
  tags sit mostly in the Sub-Commission (SUB.2/SR.5-11) and in Commission records whose debates our rules filed under
  another article (E/CN.4/SR.67). Next: the preregistered acceptance test on a random 60 of the 129.
- Schabas index, acceptance test (round 100, 21 Oct): **gate not passed**. Of the 60 sampled tags the two blind judges
  agree that 39 are right and 12 wrong; 9 split. Even with every split right it would be 48/60 (80%), under 57/60, so the
  splits were not settled and SCHABAS_TAGS_LIVE stays False: the 5,275 candidates stay possible articles (metadata). The
  errors sit in the single-candidate path (Jev check >= 0.7 on the one article the index gives: 18 right, 10 wrong, 8 split
  of 36); the choice path did far better (21 right, 2 wrong, 1 split of 24). Typical errors: the Sub-Commission's
  "article 6" of the Drafting Committee's text (non-discrimination, final art. 2) tagged final art. 6 or 7, where the
  record has no stage and Jev was not told the numbering; a French-text correction or a procedural resolution on a page
  the index gives for an article. A narrower rule (choice path only, numbering known) would be a new preregistered test.
- Audit of the pairs only we tag (round 101, 21 Oct): the judges agree on 38 of 40: 28 right, 10 wrong (70%; Wilson 95%
  interval about 55-82%), 2 splits settled by the user on the scan, both right (final: 30 right, 10 wrong of 40). So where the index does not confirm us, our tags are clearly weaker
  than the published 95%: the wrong ones are mostly paragraphs of reports and government comments (E/CN.4/102, 104, 112,
  148/Add.1, A/C.3/326) that the concordance gave an article by text similarity. The 10 go to tag_rejections.csv. As a
  measure, "not in Schabas's index" marks the tags to audit first.
- Database rebuilt with the Schabas candidates as possible articles (flag off) and the 10 rejections (21 Oct): 1,467
  speeches carry "Schabas index p. ..." among their possible articles; tagged speeches 11,332 -> 11,331 (the other nine
  rejections are report paragraphs); 133 tests pass. Coverage of the index, page level (eval/schabas_coverage.json,
  "after-possible"): covered unchanged at 1,368 cells (16% of aligned), possible 46 -> 2,339; in the general debates
  1,723 of 1,891 aligned cells are now at least possible, against 15 before. A researcher filtering by article still
  sees only the tags; the possible articles are in the record's JSON and the export would need them added to be usable.
- A/C.3/266 (21 Oct, found with the user on the scan): the second page's heading ".:.Article 25 :." was not read as a
  heading (a speck read as dots and colons), so Mexico's amendment to E/800 art. 25 (final 27, the author's moral and
  material interests) ran on into the art. 23 paragraph and carried final 26. segment.py's ARTICLE_HEAD_RE now allows up to
  four dots or colons before "Article" (46 such lines in the corpus). Resegmented (id map data/id_maps/2026-10-21-1017.json):
  31 records changed, 35 segments split, none lost; 85,313 -> 85,392 segments; A/C.3/266 art. 25 now its own heading and
  paragraph on p. 2, final 27. Speaker evals chr3 128/128, early 49/49, images 29/29; 134 tests pass.
- Preregistered (21 Oct): a narrower Schabas rule, suggested by round 100 (the choice path did far better than the check):
  a Schabas tag only when (1) the speech had several candidate articles and Jev's choice picked one at p >= 0.9, confirmed
  by the check at >= 0.7, and (2) the record's stage numbering gives the article's draft number (Jev was told it). This
  keeps 29 of the 129 tags; 10 were in round 100 (development: 9 right, 1 split), so the test is the other 19, all of them.
  Two blind judges as before, a third or the user on splits. Gate: at least 18 of 19 right (95% of 19 rounds to 18). If
  passed, the source goes live for these 29 only (a rule in build_db, not the whole CSV). A small population: whatever
  the result, it adds at most 29 tags (0.1% of the speeches); the point is whether the index can be trusted at all as a
  source.
- The narrower Schabas rule, result (round 102, 21 Oct): **gate not passed**, 12 of 19 right (the two judges agree on all
  19; gate 18). Five of the seven errors are one meeting, E/CN.4/SUB.2/SR.11, where the Sub-Commission debated the
  minorities text (ethnic, linguistic or religious groups, "differential treatment"): the index lists non-discrimination
  (art. 2) on those pages, Jev picked it from the list, and the speeches are about minorities, which the Declaration left
  out. The other two: Carton de Wiart on the duties of States (A/C.3/SR.95), Loutfi on deleting the minorities article
  (E/CN.4/SR.73). Conclusion: Schabas's index is not a source of tags, in any form tried. It stays a measure (the tags it
  does not confirm are the ones to audit first: 30/40 right against 95% overall) and a possible article in the metadata.
  SCHABAS_TAGS_LIVE stays False; nothing more is built on it as a source.
- 21 October, afternoon: the 21 October database deployed to the test server; `possible_article` (the readers' weaker
  suggestions and the Schabas index pages) is no longer served by the API (the user: not shown). The PLGrid grant
  (PLG/2026/020181, Athena, 400 GPU-hours) is accepted from 27 October; the vision reader's job for it is ready
  (`pipeline/hpc/athena_*`), 12,895 pages left.
- 21 October: the dataset's documentation for the release (`docs/dataset/`): a datasheet after Gebru et al. (2021), filled
  by the export with the build's counts and the latest audit figures rather than typed in; the fields of every file; a
  changelog with the versioning rule; the release checklist (Zenodo, DOI, citation). Writing the field list found two
  gaps in the export: the general debates' questions and the machine-translation flag were served by the API but not
  exported, and the citation of a machine-translated segment did not say so. Both added; a test now fails when a field is
  written but not described, or described but not written.
- Blind review round 4, the test of the minimal speaker rule, result (21 Oct; the user, 30 items + 4 repeats, all 4
  consistent): preview better 13, current better 15, both wrong 2; **13 of 28 decided (46%), gate (85%) not passed**, and
  three garbled preview names were judged worse (ÇOX for COX, BACPAPI for BAGDADI, LAWSOM for LAWSON; the gate allows one).
  Eight of the 15 losses are one person: the Australian member of the Drafting Committee's second session, whom the
  attendance lists print as "E. J. R. Heywood" (SR.22, SR.29) and "E.J.R. HEYWARD" (SR.35, 42, 43); the typists wrote
  HEYWOOD in SR.22-33, 36, 38 and 41 and HEYWARD from SR.34 on (the vision reader and the OCR vote agree on each page). The
  preview gave HEYWARD everywhere (the gazetteer's entry, "OCR majority; to confirm"); the user judged by the spelling on
  the page. Under the decision of 20 October (the speaker field takes the person's usual name) those eight would go to the
  preview if the person is Heyward; the test fails either way (22 of 29, 76%, and the three garbled names). Two other
  losses (LABEYRIE for LAMARLE, E/SR.157 pp. 2-3) are on pages the vision reader did not read: the preview resolves a
  record's speakers as a whole, so a name read on one page moves names on others.
  Four rounds: rules that let the vision reader's text name the speaker do not pass (62%, 75%, 58%, 46%), while its text
  and its division of the pages did (28 of 29 pages better, round 1). Not used; what follows is the user's decision.
- 21 October, the user's decisions after round 4: (1) the vision reader's text and division into speeches go into the
  database, the speakers stay with the OCR engines' resolution (names and attendance lists read as now); (2) the Australian
  member of the Drafting Committee's second session is HEYWARD everywhere (the usual name; the text keeps HEYWOOD where the
  page prints it). Done for (2): HEYWOOD is the variant of the gazetteer's HEYWARD for the session (now confirmed from the
  attendance lists). The variant also pulled SR.21's one speech of Mr. J. D. L. Hood (Australia, another person, on SR.21's
  attendance list) to HEYWARD; adding Hood to the session's list instead loosened the joint pick and let two new garbles
  through (HWYWOOD, BRYWOOD), so Hood's speech is a hand fix, as are the two OCR garbles of the name the user judged on the
  scan (IVOOD, BEYWOOD; data/gazetteer/speaker_fixes.csv). Result: 15 speeches HEYWOOD -> HEYWARD, nothing else in the
  database changed; speaker evaluations 128/128, 49/49, 29/29.
- Preregistered (21 Oct, before the build): the vision reader's text with the speakers of the OCR engines (the user's
  decision (1)). Build: pipeline/preview_mixed.py into a new copy (the name guard on the text as before, no PERO), then
  pipeline/resegment.py there **without** TRAVAUX_TRUST_PRINTED_NAMES (the pipeline's resolution: names from the six OCR
  engines' readings of each opening and the attendance lists from the scan's text layer; the vision text only segments the
  pages and is the fallback reading). Measure, against the current database (eval/preview_speakers.py and a word alignment
  of each changed record): (a) speeches that continue an old speech (their opening is the old speech's opening) and got
  another speaker or delegation; (b) new turns (a speech the vision text splits off an old one); (c) old speeches merged.
  Rule: every (a) is carried back from the current database, so that the speakers stay as now by construction; (b) keep the
  resolution's speaker and are counted, and go into the publication audit's sample frame. Gate before the merge reaches the
  database: the speaker evaluations unchanged (128/128, 49/49, 29/29) and no (a) left after the carry-back.
- Preregistered (21 Oct, before the tags are compared): the article tags under the vision reader's text. After the Jev checks
  of the new and changed segments (jev_articles, jev_procedure_check, jev_article_choice, topics, as after any
  resegmentation), every speech whose tag (instrument, final article) differs from the current database's is listed by
  kind: new tag, changed article, dropped tag (through the word alignment of pipeline/speaker_carry.py). A random sample of
  40 new or changed tags (seed 2030) goes to two blind judges (opus, sonnet), a third on splits, recorded with
  eval/audit_record.py. Gate: at least 36 of 40 right; under it the merge does not reach the database. Dropped tags: a sample
  of 20, judged the same way, reported as coverage (a right tag dropped is a loss, not an error). Also before the merge: the
  hand-anchored documents stay at the OCR (done), the resegmentation's lost segments are listed (38: an address block in
  French, "The meeting rose" lines, stray stops, four headings).
- 21 October, late evening: **the vision reader's text is in the database** (the user's decision (1)). Results of the two
  preregistered checks, on a copy first and then in place: speakers, 172 carried back from the OCR resolution (none left
  after), 1,187 new turns with a speaker of their own, evaluations 128/128, 49/49, 29/29 (gate passed); article tags,
  27,994 speeches the same, 470 new turns tagged, 172 new, 54 changed, 164 dropped; the blind check of 40 new or changed
  tags found **37 right** (two judges agreed on 39, the third settled one; gate 36, passed), the three wrong ones are in
  tag_rejections.csv (gold round 103); of 20 dropped tags 17 had been right (coverage, about 140 right tags lost against
  about 650 gained). Before the merge: the report annexes' anchors found as before and only on a miss a close match and no
  hold-up (the old text unchanged, 0 segments); the hand-anchored documents (reports, the drafts the concordance and
  histories are cut from) stay at the OCR, 113 pages; the OCR vote's pages kept in data/ocr/*/vote_ocr (dates, undo).
  In place: 5,282 pages of the vision reader in 588 records; the copy and the database identical after the merge
  (checksum of ids, speakers, tags); five meeting dates now read from the cleaner text, all five better (E/CN.4/SR.104/Corr.1
  1946 -> 1949, SR.131/Corr.1 August -> June 1949, three filled in). One consequence for the re-read tags: E/CN.4/SR.155,
  where the vision reader reads the heading "Article 13" the OCR had lost, gave no tag to the speeches after it, because
  E/1681's footnotes do not list the meeting for draft 13; meeting 155 is added to its meetings (the record's heading and
  the blind check of round 69), and the test of the re-read tags now states the rule (a re-read speech never keeps the tag
  it corrected). After the Jev checks of the new tags: 29,584 speeches (+1,024), 29,462 with a speaker, 11,722 with an
  article (+391), 6,736 decisions (+508), 1,647 with a question; published precision 95.5% +/- 3.4 (was 95.4).
- 21 October, after the merge: eval/ocr_bench.py on the database's text (the "vote" pages, now the vision reader's where it
  was taken), against the records retypeset in Schabas: characters read wrong 1.45% -> 1.14% overall; typed summary records
  of 1947-48 1.45% -> 0.64%; printed records of 1948 0.91% -> 0.79%; typed documents and reports 1.95% -> 1.94% (most of them
  hand-anchored, so still the OCR's). The cleaner text also lets more of the reference be found (626 -> 640 documents,
  5.63 -> 5.79 million characters), so the two figures are not on exactly the same set. eval/ocr_bench.json now holds the
  new measure; the datasheet describes the text as OCR plus the vision reader's reading where it passed the checks.
- Preregistered (21 Oct, for the first PLGrid jobs on 27 Oct): one reader for the whole corpus. (a) 653 pages were read on
  the laptop by a 5-bit quantized build of the model (1qh/chandra-ocr-2-oq5-mlx, data/logs/vlm_local_bench.jsonl), the
  other 4,944 on Kaggle by the original weights (datalab-to/chandra-ocr-2, vLLM 0.31.0, fp16 on two T4s). The 653 are
  read again on Athena with the original weights and replace the quantized readings, whatever the comparison shows (the
  differences are reported). (b) The first, test job reads 50 random pages of the Kaggle run again (seed 2032; vLLM 0.31.0,
  bf16 on one A100; pipeline/hpc/make_queues.py, eval/gpu_consistency.py). Measured per page: characters that differ
  between the two readings (Levenshtein distance over the longer, after the benchmark's normalisation), runaway readings,
  and the names at turn openings and in the officers' lines (pipeline/name_guard.py cues) that differ. Rule: if at least
  45 of the 50 pages differ by 0.5% of characters or less and no name differs, the Kaggle readings stay; otherwise the
  Kaggle pages are read again on Athena (about 40 GPU-hours, the grant's line for reading the corpus in one environment).
- 21 October, night: A/C.3/L.1355 (Netherlands, amendments to part IV of the draft Covenant on Civil and Political Rights,
  17 October 1966, with a new article on petitions from individuals; priority 1, cited 56 times in the Third Committee's
  1966 records and A/6546) downloaded by the user from the Digital Library, where it exists only in French. Taken in as the
  eleventh machine translation, by the procedure of 29 September: claude-fable-5-1 from the scans, claude-sonnet-5-5's check
  (2 errors, both legal terms rendered by the Covenant's official English instead of the French: "utilisés", "instance";
  5 minor), the translator settled 5 and kept 2 with reasons (data/translations/A_C.3_L.1355.json). Resegmented: no other
  record changed; its 7 paragraphs carry no article (each is about another article of part IV, and the petitions article
  went into the Optional Protocol). The attachment to the UN Library notice notes that the English is still wanted.
- 21 October, night: a zip the user's own web search assembled ("odnalezione_w_internecie": 67 files). Taken in: the UN's
  scans of ECOSOC resolutions E/RES/118(VI) and 120(VI) (documents.un.org, under the resolutions' own symbols; the finding
  aids cite their parts 118(VI)B and 120(VI)C, which ODS does not serve), OCR'd as usual (two-column, the English column
  kept). Part 116(VI)F was already held in E/RES/116(VI). The three parts are off the list of missing documents (1,430 ->
  1,427; the notice's figures updated). Not taken: 56 "Yale reprints", page extracts of Schabas (2013), whose full text Yale
  hosts (the project's rule: nothing of a printed compilation's text in the database; the book is already used privately,
  and its reproductions are in eval/private), a copy of the whole book, and page 130 of the UN Yearbook 1947-48 (a reprint,
  not the documents). Found on the way: pipeline/ocr_all.py had OCR'd the ten French-only documents again (their OCR
  folders were missing) and overwritten their translated text; pipeline/translations.py laid the translations out again
  before the rebuild (checked). 2,160 documents.
- 22 October, after midnight: why 168 tags were dropped by the merge (speeches that continue an old one, tagged before,
  untagged after; the blind check of 20 of them found 17 right). Three causes. (1) **82: a split.** The vision text found a
  turn inside an old speech; resegment.py gives an old segment's id-keyed data (the readers' tags, the re-read tags, Jev's
  answers) to the new segment holding most of its words, which is often the new turn of another speaker, so the speech
  that keeps the old opening loses them (judged: 10 of 11 were right tags). (2) **63: the context rules met headings the
  OCR had garbled.** For instance E/CN.4/SR.258's agenda heading on self-determination, now legible, resets the article the
  report's meeting list gives the whole record; E/CN.4/SR.61's "Articles 21 and 22", read as "Articles .1 and 22" before,
  no longer matches the concordance's entry (judged: 6 of 7 right). (3) **23: Jev's check on the new text** (2 judged, one
  each way). To do, each preregistered with a blind check before it reaches the database: for (1), the speech-level hand
  tables and answers of a split speech go to the part with its opening (pipeline/speaker_carry.py's match), then the Jev
  checks; for (2), the heading rules case by case (63 speeches); (3) stays.
- Found the same night: French text in 227 segments (0.26%; A/125, the printed Third Committee records of 1948, E/CN.4
  documents of 1947), almost all on pages not marked two-column, because a printed rule between the columns hides the
  gutter from ocr_select.two_column (the merge did not cause it: French function words 10,625 -> 9,844). To do: detect the
  columns by the page's language as well, preregistered, with the usual checks.
- Preregistered (22 Oct, before the change): the French column on pages not marked two-column. pipeline/segment.py drops
  the French lines (normalize.english_only) also on a page that is not marked two-column when its own text is bilingual:
  at least 15 French function words, and at least 20% of the page's English and French function words French. Measured
  against the database before the change, over the documents that are not machine translations: French function words
  (gate: down by at least 70%), English function words (gate: no more than 0.5% lost overall, and no record losing more than
  3%), the speaker evaluations unchanged (128/128, 49/49, 29/29), eval/ocr_bench.py not worse; the tags compared as after the
  merge (eval/merge_tag_changes.py), with a blind check of 20 changed tags if more than 20 change.
- French-column fix, result (22 Oct): **gates not passed, reverted.** French function words 9,844 -> 3,572 (64%; gate 70%);
  English 0.02% gained overall, but two records lost more than 3% of theirs: A/C.3/L.1417 (9.6%), a list of corrections to
  the language versions ("8. French, first and second line, replace «dans l'exercice ...»"), whose English instructions
  around French quotations the rule took for a French column, and E/CN.4/AC.1/3/Add.2 (3.1%). The French left (3,572 words)
  is spread thin (at most 83 in a document, A/2929): mostly French wording quoted in English text, which should stay. So
  the first gate also measured something the fix must not remove. The database, the segments and Jev's caches restored (the
  same checksum as before; no check missing). A second version, if any, needs a measure of French runs (several French
  lines in a row) rather than French words, and its own preregistration.
- Preregistered (22 Oct, before the change): the speech-level data of split speeches. When the vision text split an old
  speech (491 cases in the merge), resegment.py gave its id-keyed data to the larger new part, often another speaker's
  turn. Fix: (1) the hand tables that judge a speech (reader_tags, tag_rejections, the tagger's accepted proposals,
  possible_articles, schabas_candidates) go to the part that keeps the old speech's opening, row by row as they were before
  the merge; Jev's cached answers about the old, run-together text are dropped for both parts, and Jev is asked about each
  part afresh (articles, procedure, choice, topics); (2) resegment.py does the same in future: for a split, speech-level
  tables follow the opening and Jev's answers are dropped. Measured by id against the database before the change: tags
  new, changed and dropped; how many of the 82 dropped tags come back. Gate: a blind check of 20 new or changed tags (seed
  2033; two judges, a third on splits) finds at least 18 right; under it the change is reverted.
- Split speeches' data, result (22 Oct): 55 new tags, 32 dropped, none changed; 42 of the 168 tags the merge had dropped
  are back. Blind check of 20 new tags (seed 2033): the two judges agree on 18 right and 1 wrong, split on 1 (third judge
  pending): **gate (18/20) passed**. But the 32 dropped tags were judged too (for the report, not the gate): 29 and 30 of
  32 right by the two judges. These are the larger parts, which lost the readers' tag of the old run-together speech; the
  old speech was mostly about one article, so the readers' tag fits both parts.
- Preregistered (22 Oct, before the change): a second version. The tables that give a speech an article (reader_tags,
  speech_retags, the tagger's accepted proposals, possible_articles, schabas_candidates) are copied to both parts of a
  split speech, each part's tag checked by Jev on its own text as any tag is; the speaker tables and the rejections stay
  with the opening (version one). Expected and checked by id against version one: the 32 dropped tags come back (the same
  tag on the same text the judges saw, 29-30 of 32 right), nothing else changes; if anything else changes, 20 of those
  changes go to the judges (gate 18/20).
- Split speeches' data, final (22 Oct): the third judge settled the split item wrong, so version one's sample stands at
  18 of 20 (gate met); the two wrong tags are in tag_rejections.csv (gold round 104). Version two as preregistered: 22 of
  the 32 tags come back (Jev's check drops the other 10 on the shorter text of the larger part), nothing else changes. In
  all, 11,722 -> 11,765 speeches with an article; published precision 95.5% +/- 3.5 (unchanged); speaker evaluations
  1.000; 138 tests. resegment.py now does this itself (SPEECH_TABLES follow the opening, ARTICLE_TABLES go to both parts,
  Jev's answers about a split segment are dropped), so the PLGrid merge will not repeat it.
- Preregistered (25 Oct, before the change): the heading rules after the merge. Of the tags the merge dropped, 93 are still
  untagged and not by Jev; 39 are two records. E/CN.4/SR.258 (24): the cleaner text shows the chair taking up a revised
  amendment to the draft resolution on self-determination, so the rule that tags a whole meeting by the report's list (only
  when the chair takes up nothing else) declines; that is the rule working as meant, and it stays. E/CN.4/SR.61 (15): the
  passage "The Commission decided to postpone the examination of article 20 until articles on implementation had been
  drafted", now a segment of its own, switches the instrument to the measures of implementation (a passage naming one
  instrument with "examination"), so "Articles 21 and 22" is read as implementation articles. Fix: a passage that postpones
  or makes a condition ("postpone", "defer", "until", "pending") does not switch the instrument. Measured by id against the
  database before: SR.61's tags; every other change listed, and if more than 5 change elsewhere, 20 of them (or all) go to
  the blind judges (gate: at least 90% right); otherwise reverted.
- Instrument switch, result (25 Oct): the "postpone" exception first put in the wrong rule (the passage-level switch)
  changed nothing in SR.61 and tagged 5 speeches elsewhere: reverted. A trace showed the switch came from the chair's line
  before it ("not to examine the text of article 20 relating to petitions until articles on implementation had been
  drafted"): the rule that reads the instrument in the 90 characters after an article's number took "implementation" from
  the condition. Fix: that window ends at "until", "pending", "unless", "before", "after" or "once". A first version also
  cut at a full stop and dropped six right-looking UDHR 14 tags in E/CN.4/AC.1/SR.9 ("Article 32 could be left to
  Conventions. She agreed that the Declaration ...": the whole window names both, so no switch); without the stop, only
  SR.61 changes: 15 speeches tagged again (UDHR 20-22 as before the merge), nothing else. 138 tests.
- One reader for the whole corpus, result of (b) (27 Oct, the first PLGrid job): Athena's A100 (vLLM 0.31.0, bf16; job
  3416175, after three environmental fixes, below) read the 50 Kaggle pages again: 50 read, no error, none truncated or
  run away; 47 identical character for character, all 50 within 0.5% (largest 0.21%, E/CN.4/Sub.2/SR.11 p. 17); but two
  pages differ in a name at a turn opening: E/CN.4/SR.323 p. 13 (Kaggle VALENZUELA, Athena VALLENZUELA) and E/CN.4/SR.217
  p. 5 (Kaggle ROSSSEL, Athena ROSSEL), one wrong in each environment. **Rule: not met** (it asks for no name that differs),
  so by the preregistration the Kaggle pages are to be read again on Athena; that run waits for the user's go-ahead
  (eval/vlm_pilot/gpu_consistency.json; the A100 readings in data/logs/consistency_a100, not committed). Speed: 50 pages in
  0.03 h with 32 requests at once (about 2 s a page; 51 s a request on average), and 200 s for the server to start.
  The fixes (pipeline/hpc/athena_setup.sh, athena_chandra.sbatch): PyPI's torchcodec 0.17.0 is a CUDA 13 build that stops
  `vllm serve` (removed; it decodes audio and video only); torch's compiler calls `nvcc --version` and on the GPU nodes a
  non-executable nvcc on PATH raises PermissionError (CUDA 12.8's bin put first on PATH, without its libraries); vLLM's
  kernel warmup imports a MiniMax M3 Triton kernel whose source Python 3.10 cannot read (the import guarded; the warmup
  does nothing for Chandra). Kaggle's environment needed none of these, so the comparison is between environments, not
  just GPUs and precisions.
- 27 Oct, the main queue on Athena (job 3416250, array 0-3, one A100 each; 11,270 pages: the 653 quantized-build pages, then
  every unread page): 1,464 pages in its first 10 minutes, no error, one truncated, i.e. about 1.6 GPU-seconds a page and
  about 5 GPU-hours for the queue (of 400). At that speed a re-read of the 7,222 Kaggle pages, which the rule above asks
  for, would take about 3.5 GPU-hours, not the 40 the preregistration assumed.
- 27 October, the consistency rule applied: the user agreed to read the Kaggle pages again (the rule was not met by two
  names). 7,222 pages (Kaggle V5 and V6, without the 653 the quantized build had read, which are in the main queue) queued as
  job 3417868 on Athena, after the main array 3416250 (SLURM dependency), into the same results/; about 3.5 GPU-hours.
- 28 October, night: both Athena arrays done. Job 3417868 (the Kaggle pages again) waited in the queue for five hours (the
  partition full, 23 A100 nodes in repair, the account's fair-share near zero after the main array); with the time limit
  cut from 24 h to 2.5 h it was backfilled from 23:52 and read 7,222 pages in 4 x 48 minutes, no error, 11 truncated. In all
  on Athena: 18,492 pages (11,270 + 7,222), about 9.5 GPU-hours of the 400.
- Preregistered (28 Oct, before the copy reaches data/ocr): the Athena readings into the corpus. (1) Reported, no rule (the
  re-read replaces the old readings whatever it shows, as preregistered on 21 Oct): for the 7,222 Kaggle pages and the 653
  quantized-build pages, eval/gpu_consistency.py's measures (pages within 0.5% of characters, pages with a name that
  differs, runaways). The old readings are kept in a tar under data/logs before they are overwritten. (2) The merge as on
  21 Oct, with the same two checks and the same gates: pipeline/preview_mixed.py --in-place, pipeline/resegment.py without
  TRAVAUX_TRUST_PRINTED_NAMES, the Jev checks, pipeline/speaker_carry.py against the database before the merge; gate on
  speakers: the speaker evaluations unchanged (128/128, 49/49, 29/29) and no continued speech with another speaker after
  the carry-back; gate on tags: a random sample of 40 new or changed tags (seed 2034) to two blind judges (opus, sonnet), a
  third on splits, at least 36 of 40 right; dropped tags: a sample of 20, reported as coverage. Under either gate the
  database is restored from the backup and the merge does not reach it. Also reported: eval/ocr_bench.py before and after.
- The Athena readings, results (28 Oct). (1) Against the old readings: of the 7,222 Kaggle pages 6,955 identical, 7,119
  within 0.5% of characters (median 0), 62 with a name that differs (e.g. E/CN.4/SR.245 p. 20 HODOSOV / HOROSOV, SR.250
  p. 12 DUPONT-MILLERIN / DUPONT-ILLERIN), 21 differing by more than 5% (5 of them runaways); of the 653 quantized-build
  pages 515 identical, 612 within 0.5%, 28 with a name that differs (eval/vlm_pilot/athena_vs_kaggle.json,
  athena_vs_mlx.json). All 18,492 pages of data/ocr/*/chandra are now Athena's (7,875 replaced, 10,617 new; the old ones in
  data/logs/chandra_before_athena_2026-10-28.tgz, not committed). (2) The merge: the guard took 10,348 pages (was 5,282; left
  at the OCR: 6,095 two-column, 1,945 in hand-anchored documents, 85 outside the length guard, 19 runaways); 29,584 ->
  29,649 speeches; speakers 11 carried back, none left after, evaluations 128/128, 49/49, 29/29 (gate passed). Tags: 29,468
  speeches the same, 36 new turns tagged, 12 new, 27 changed, 24 dropped; the two judges agree that 8 of the 40 new or
  changed tags are wrong (opus 28 right, sonnet 32; 4 splits), so at most 32 of 40: **gate (36) not met**, the merge
  restored from the backup (database, segments, caches, vote pages and the tables, checked identical; 138 tests); the third
  judge was not asked, the gate failing either way (eval/merge_tags_athena/). Characters read wrong on the merged text
  (eval/ocr_bench.py, reported only): 1.14% -> 0.74% (typed documents and reports 1.94% -> 0.98%, typed summary records
  0.64% -> 0.45%, printed 0.79% unchanged). Cause of most wrong tags: the vision reader writes the diacritics of names in
  capitals ("Mr. JEVREMOVIĆ (Yugoslavia)"), which the segmenter's turn openings (ASCII capitals) do not take, so in
  E/CN.4/SR.351 Jevremović's speech ran into the chair's line, whose "article 34" then switched the context for the speeches
  after it (5 of the 8 and 1 split). The vision reader's text has 1,266 such openings on 681 pages (PÉREZ 401, JIMÉNEZ 160,
  JEVREMOVIĆ 135, RÖSSEL 126, GARCÍA 85, INGLÉS 78 ...). Two others are new turns of E/CN.4/SR.389 on the Chilean additional
  article that Jev's check passed (before, untagged by Jev), one a hand-read draft article in E/CN.4/AC.1/SR.15. Also fixed
  on the way: pipeline/speaker_carry.py wrote speaker_kept.csv anew and so dropped the 172 rows of 21 Oct (in force in both
  databases, they show no difference): it now keeps them; eval/merge_tag_changes.py takes --seed.
- Preregistered (28 Oct, before the code changes): turn openings with capitals beyond ASCII. The fix: in pipeline/segment.py
  the surname of a turn opening ("Mr. JEVREMOVIĆ (Yugoslavia) said", the wrapped and joint forms, "AZMI Bey", "Mr. X said"
  without a country) takes capitals with diacritics (Latin-1 and Latin Extended-A: É, Ö, Ø, Ñ, Ć, Š, Ł ...), and NAME takes
  the letters of Latin Extended-A as well as Latin-1. The 25 Oct database already has 259 such openings on 237 pages (the
  Kaggle readings merged on 21 Oct: SØRENSEN 48, JEVREMOVIĆ 55 with its misreadings, RÖSSEL 30 ...), so the fix changes it
  too. (1) On the current text, before any merge: pipeline/resegment.py --dry-run. Gates: every changed record holds such an
  opening, and every new segment boundary is one (anything else is a bug, fixed before going on); the speaker evaluations
  unchanged (128/128, 49/49, 29/29); the tests pass. Reported: records changed, segments split, merged. (2) The Athena merge
  again from the 25 Oct backup, as preregistered on 28 Oct (same steps, same two gates: speakers unchanged and none left
  after the carry-back; tags at least 36 of 40 right to two blind judges, a third on splits), with the fix in, so that the
  tag sample (fresh seed 2036; dropped tags seed 2037, 20, reported) covers both the fix and the new text against the 25 Oct
  database. Under either gate the database is restored from the backup.
- Turn openings with capitals beyond ASCII, step (1) on the current text (28 Oct): 54 records change, 76 segments split, none
  merged or lost; every new boundary is such an opening (81: JEVREMOVIĆ and its misreadings 77, AZKOUŁ 2, INGLEŠ/INGLEŚ 3,
  ARÉCHAGA 1, counted on the opening's surname) or follows from one (9: a heading or a vote line that ran into the speech now
  set apart, as in E/CN.4/SR.156, SR.251, SR.355, SR.410; the lead-in forms "In reply to the CHAIRMAN, Mr. SØRENSEN
  (Denmark) said" in SR.247, SR.366, SR.367). No speaker changes; 39 more records differ only in the vision reader's vote
  now counted among the witnesses ("KETRZYŃSKI (Poland) [vision]"). Speakers 128/128, 49/49, 29/29; tests 138. Gate passed.
- The Athena readings, merge again with the fix (28 Oct, as preregistered): the guard took the same 10,348 pages; names
  replaced 658 (were 638: the session rosters now hold the speakers the fix splits off). Speakers: 11 carried back, none
  left after, evaluations 128/128, 49/49, 29/29 (gate passed). Tags against the 25 Oct database: 29,506 speeches the same,
  79 new turns tagged (124 untagged), 13 new, 11 changed, 25 dropped; of 40 new or changed tags (seed 2036) the two judges
  agree on 39 right or wrong, the third settled the one split: **38 right** (gate 36, passed); the two wrong ones are in
  tag_rejections.csv (gold round 105): E/CN.4/SR.36's explanation of vote on article 8 of the draft Declaration, tagged
  with the Covenant's article (the meeting took both drafts), and E/CN.4/AC.1/SR.15's speech on the science article under
  the work article (the hand-read draft numbering, as in the first attempt). Of 20 dropped tags 17 had been right
  (coverage: about 21 right tags lost against about 98 gained). The E/CN.4/SR.389 new turns on the Chilean article are
  not in this sample. In the database: 29,584 -> 29,758 speeches, 29,462 -> 29,636 with a speaker, 11,780 -> 11,840 with
  an article, 6,736 -> 6,768 decisions, 1,647 -> 1,656 with a question; published precision 95.5% +/- 3.4 (unchanged).
  Characters read wrong (eval/ocr_bench.py, five engines): 1.14% -> 0.74% (typed documents and reports 0.98%, typed
  summary records 0.45%, printed 0.79%), as in the first attempt. Tests 138.
- Preregistered (28 Oct, before the code changes): E/CN.4/SR.389 and the agenda's sub-items in the 1951-53 records. SR.389
  takes up (i) Chile's additional article (E/CN.4/L.247, withdrawn), (ii) article 58 (ICCPR 45), (iii) article 59 (no final
  article read with confidence, "former-59"); its first two speeches, on the Chilean article, carry ICCPR 45. Two causes.
  (A) api/build_db.py opens the meeting on the first article its CONTENTS name ("(11) Article 58 ... 10 - 13"), skipping the
  first item, which names none; fix: the contents' first article counts only when it is the first item. (B) the sub-item
  headings between the turns, "(ii) Article 58 and United Kingdom amendment thereto (E/CN.4/L.227)", "(1) Additional
  article proposed by the Chilean delegation", "(3) New article proposed by the United States delegation", are not read as
  headings (the item marker "(ii)", "(2)" and the words "proposed by the ... delegation" stop pipeline/segment.py's
  sub-heading rule) and run onto the end of the turn before: 27 such ends in the records of 1951-53. Fix: the segmenter sets
  them apart as headings, with the article when one draft article is named, else as an agenda heading that names a new
  article, which ends the article in force (api/build_db.py). Checks: pipeline/resegment.py --dry-run, every new boundary
  such a heading (anything else fixed first); speakers 128/128, 49/49, 29/29; tests. Then the rebuild with the Jev chain and
  eval/merge_tag_changes.py against the database before: all new or changed tags if 40 or fewer, else 40 at random (seed
  2038), to two blind judges (opus, sonnet), a third on splits; gate: at least 90% right (36 of 40); dropped tags judged the
  same way, reported as coverage. Under the gate the database, segments and tables are restored from the backup.
- E/CN.4/SR.389 and the agenda's sub-items, results (28 Oct). Resegmentation: 18 records, 26 segments split, none merged or
  lost; every new boundary is a heading: 21 sub-items of 1951-53 ("(2) Article 33 and the United Kingdom amendment thereto",
  18 with their article, three new articles: SR.354's Philippine, SR.355's and SR.390's United States articles) and 7 other
  headings of new articles or proposals the same rule now reads ("Proposed additional articles", E/CN.4/SR.130; "(iii)
  Proposal by Chile for a new article on the equal rights of men and women", SR.371; "New article (E/CN.4/L.324)", SR.424;
  also SR.240, 373, 409, SUB.2/SR.8); the turns before them lose only the heading at their end. Speakers unchanged (none
  carried back; 128/128, 49/49, 29/29); tests 138. Tags against the database before: 29,741 speeches the same, 13 new, 4
  dropped, none changed; the two judges agree all 13 new are right (gate 90%, passed; gold round 106); of the 4 dropped,
  SR.389's two speeches on the Chilean article had been wrong (both judges), the other two right: E/CN.4/SR.373's
  explanation of vote on article 3, whose Jev choice fell from 0.98 to 0.84 (threshold 0.9) once the heading after it was cut
  off, and SR.346's speech on the Committee's size, which Jev's procedure check now calls the organisation of work (p = 0.86).
  SR.389 now: (i) the Chilean article untagged, (ii) article 58 = ICCPR 45 from its heading, (iii) article 59 untagged
  ("former-59", as before); one speech on the annual report (Díaz Casanueva, SR.389-0017) stays untagged by the rule that a
  Covenant speech with no drafting word is off the article. Speeches with an article 11,840 -> 11,849; precision 95.5%
  +/- 3.4 (unchanged).
- Preregistered (28 Oct, before the change): the French-column fix, second version. After the Athena readings the French
  left in the text is almost all in long runs of French lines: measured by the new eval/french_runs.py on the lines that
  reach the segmenter (2,149 documents, machine translations left out; each line labelled by its own function words,
  normalize.line_evidence, factored out of english_only with no change), 285 runs hold 9,677 French function words, the
  100 runs of at least three French lines 8,838 of them, and 70 runs of at least five lines and 40 words 8,327 (86%). Three
  sources: the French column of printed pages not marked two-column (A/125, the Third Committee's 1948 records, E/PV.84,
  E/SR.157, E/SR.215), French pages facing English ones (E/CN.4/21's annexes, E/CN.4/AC.1/3 and Add.2, the end of
  E/CN.4/SR.366, E/2152's calendar), and the French half of the bilingual sheets of 1947-48 (E/CN.4/47, 76, 105, 107). The
  short runs are mostly quotations, which stay: A/C.3/L.1417's corrections (one or two lines each; the first version cut
  9.6% of its English), E/CN.4/AC.1/SR.26's French texts of article 16, A/3525's statement on 'travailleur' (six lines,
  opened in the English line before). Rule: on a page not marked two-column, pipeline/segment.py drops a run with at least
  five French lines and either at least 40 French function words, or 20 when it is not a quotation (its first line opens
  with a quotation mark, or the line before leaves one open); the lines without evidence before and after a run stay.
  Gates: (1) French words in runs of three or more French lines down by at least 90% (eval/french_runs.py --before);
  (2) English function words in the database (eval/french_check.py) no more than 0.5% lost overall and no record losing
  more than 3%; (3) every dropped run to two blind judges (opus, sonnet), with the page: the French version of text the
  document gives in English, or French that belongs to the English text (a quotation, an original with no English
  version), and does the run hold any English (a heading or a line of the English column)? A third judge on splits; gate:
  at most one run that belongs to the text and none with English text lost; (4) speakers 128/128, 49/49, 29/29,
  eval/ocr_bench.py not worse, tests; (5) after pipeline/resegment.py and the Jev chain, eval/merge_tag_changes.py against
  the database before: new or changed tags all if 40 or fewer, else 40 at random (seed 2040), two blind judges and a third
  on splits, at least 90% right; dropped tags judged the same way, reported as coverage. Under any gate the database,
  segments and tables are restored from the backup.
- Amended (28 Oct, after the dry run, before any gate was judged): (a) on a page with no English line (a French page facing
  an English one), a dropped run takes the whole page: the first rule left the French headings above the runs ("ARTICLE 6"
  at the top of E/CN.4/21's p. 12, "Article 14" of p. 56), which then took the article of the English section before them;
  (b) data/concordance/report_annex_sections.csv loses its 88 rows anchored on E/CN.4/21's French pages (annexes A and D
  in French), whose text is gone: left in, they kept the English pages' anchors after them from being found (277 not
  found, the English annexes untagged). Gate (1) and the dry run are run again; the gates are otherwise unchanged.
- French-column fix v2, results (28 Oct). (1) French words in runs of three or more French lines 8,838 -> 328 (96.3%
  fewer; gate 90%, passed): 77 runs gone on 77 pages (8,510 French words, 21 English function words inside French lines),
  29 records changed; what is left is short runs, the quotations among them (A/C.3/L.1417's corrections, A/3525's
  statement, E/CN.4/AC.1/SR.26's French texts) untouched. (2) English function words: 0.02% more overall (Mrs.
  Roosevelt's speech in A/C.3/SR.89 and Mr. Aquino's in A/C.3/SR.148 had been cut off by the French column and are whole
  again: Roosevelt's 2,597 -> 8,573 characters); as preregistered one record is over 3%, E/CN.4/AC.1/3/Add.2 at 4.1%, but its
  four lost words are "as" and "on" that eval/french_check.py's tokeniser cut out of the French "Pas" and "Non" (the same
  flaw is in the first version's 3.1% for this record); with the tokeniser made to start words at a word boundary no record
  loses English (French words 7,845 -> 1,960 in the database, 75% fewer). Gate passed on the corrected measure; the
  preregistered number is recorded here. (3) All 77 pages' removed text (75 distinct; the shared pages of SR.88/89,
  SR.129/130, SR.137/138, SR.93/94 read twice) to two blind judges with the page files: opus 75 A, sonnet 75 A (French
  version of text the document gives in English), no run that belongs to the English text, no English line among the
  removed (gate passed; eval/french_runs_judged.json). (4) Speakers 128/128, 49/49, 29/29; eval/ocr_bench.json identical;
  tests 139 (one added). (5) After resegment.py and the Jev chain: all 29,758 speech tags the same (none new, changed or
  dropped, so nothing to judge); 29,636 with a speaker, 11,849 with an article, published precision unchanged. Document
  paragraphs and headings with an article 11,339 -> 11,227: the 112 gone are the French pages' paragraphs and headings
  (E/CN.4/21's annexes A and D in French); on the English text, aligned in order, three changes: E/CN.4/21's article 12
  ("Every one has the right to a legal personality"), till now in one segment with the French article 11, is UDHR 6 by a
  new hand-read row (report_annex_sections.csv, the 88 French rows out); its "CHAPTER 2." takes the article before it as
  "CHAPTER 3." already did; E/CN.4/107's separator "-----" carries the document's UDHR 17. E/CN.4/76 lost its masthead
  (its English lines are all short, so the masthead rule found no first paragraph; the date comes from the guide and is
  unchanged), and its amendment, inside the masthead before, is now a paragraph. Segments 86,324 -> 86,039; gold rows
  2 fewer (round 50's two rows on French paragraphs of E/CN.4/21).
- Preregistered (28 Oct, before the change): the rule that a Covenant speech with no drafting word is off the article
  (api/build_db.py, added 23 Sept for the Third Committee's debates of 1955-66, where it took out "took the Chair",
  referrals and complaints about the hall) also holds in the Commission's records of 1949-54 and drops substantive speeches
  that happen to use none of its words: E/CN.4/SR.389-0017 (Díaz Casanueva on the annual report of article 58), E/CN.4/SR.159's
  answer on forced confessions, SR.156's on "reasonable doubt". Measured by building without the rule (then restored): 478
  speeches would take the article of their debate (295 Commission 1949-54, 183 Third Committee; 157 under 20 words, 176 of
  20-39, 104 of 40-79, 41 longer), a mixture of the substantive and of other business (the cost of interpretation at
  Geneva, deadlines, the Rapporteur); a word list cannot tell them apart. Change: such a speech is no longer skipped; it
  keeps the article in force only when Jev's article check (pipeline/jev_articles.py) says yes at 0.7, the stricter
  threshold the 1947-48 records use where the context is the only evidence (0.5 elsewhere), and Jev's choice among the
  meeting's articles does not apply to it (without the block, four speeches on self-determination in E/CN.4/SR.253 and
  SR.261 that two readers tagged ICCPR+ICESCR 1 would take the choice's ICESCR 1); the procedure check applies as to any
  tagged speech. Gate: after the Jev chain, eval/merge_tag_changes.py against the database before; new or changed tags all
  if 40 or fewer, else 40 at random (seed 2042), to two blind judges (opus, sonnet), a third on splits: at least 90% right
  (36 of 40); dropped tags (none expected) judged the same way. Speakers unchanged, tests. Under the gate the database and
  caches are restored. SR.389-0017's outcome is reported, not a gate.
- Amended (28 Oct, after the Jev chain, before the judges): six tags dropped where none was expected, all hand-checked
  (two readers, or the blind judges of a resegmentation): the skip had kept Jev's check off these speeches, so the readers'
  tag stood; now Jev's no on the debate's article also keeps the readers' same article off them. For three Jev said p
  0.55-0.63, under the new 0.7 but over the usual 0.5: the stricter threshold now only withholds the debate's article and
  does not count as Jev's no against the readers (below 0.5 it does, as for any speech). The other three (p 0.21-0.47) go
  as any speech's would; reported as coverage.
- The no-drafting-word rule, results (28 Oct). Jev asked about the 478 (with the procedure check on the short ones): 126
  speeches now take their debate's article, none changed, 3 dropped (the hand-checked tags whose speeches Jev's check now
  turns down at p 0.21-0.47, as the amendment above says). Of the 126, 40 at random (seed 2042) to two blind judges (opus,
  sonnet; no split): **39 right** (gate 36, passed; gold round 107); the wrong one, E/CN.4/SR.348-0047, is about the
  majority the Court would need to elect the Committee (final art. 30), not its composition (31), now in
  tag_rejections.csv. The three dropped were right (both judges): coverage, a loss of three right tags against about 122
  gained. The four speeches on self-determination keep the readers' ICCPR+ICESCR 1. E/CN.4/SR.389-0017 (Díaz Casanueva)
  is ICCPR 45 (Jev p = 0.92); E/CN.4/SR.159's answer on confessions and SR.156's on "reasonable doubt" are ICCPR 14 (p 0.84,
  0.91). Speakers
  128/128, 49/49, 29/29; tests 139. Speeches with an article 11,849 -> 11,971; published precision 95.5% (+/- 3.5, was 3.4:
  the Commission stratum's weight grew with its 89 new tags).
- Coverage, the two cheap rules of docs/handover.md 5.3 measured (29 Oct; no change made, nothing preregistered). (a) The
  contents' page ranges of the Commission's records of 1951-53 ("(2) Article 40 ... 11-15"): in 27 records with two or more
  ranged items, the 108 tagged speeches on pages that one single-article item covers agree with it on the final article
  105 times; but of the 52 untagged speeches there, 23 Jev already turned down for that same article, and the other 28 are
  untagged on purpose: SR.389's article 59 (10, no final counterpart read with confidence), SR.390's United States article
  51 bis (4, a new article), SR.354's article 44 (7, no final counterpart), and procedural turns (7: withdrawals, "accepted
  that suggestion"). Since the sub-item headings of 28 Oct the ranges add nothing. (b) The Drafting Committee's 1948
  headings "DISCUSSION OF ARTICLE n" already set the article (36 such headings, all but three tagged); the speeches left
  untagged after them are Jev's or the procedural rules'. So handover 5.3's first two sources are spent. Where the speeches
  stand: tagged 42.8% (UDHR) and 39.3% (Covenants); no article in force or procedural 47.0% and 48.9%; a general-debate
  topic 3.4% and 6.3%; Jev's no 6.2% and 4.7%. 2,308 untagged speeches carry a possible article (the readers' weaker
  suggestions, the Schabas pages). What is left for coverage needs readers or judges (whole-record readers; a check of the
  possible articles; the topics at 0.8-0.9), each to be priced on a pilot first.
- Preregistered (29 Oct, before the draw): a pilot of judging the possible articles. Population: the untagged speeches whose
  possible_article holds a readers' suggestion (the Schabas pages left out: round 102 closed them as a source), one pair per
  (speech, suggested article): 972 speeches, 982 pairs (a first count of 1,132 split the readers' notes at their own "; "). Sample: 100 pairs at random (seed 2044; eval/possible_pilot.py),
  each shown as in the tag checks (the article, its final text, the passage before, the speech; the setter given only as
  "a candidate article") to two blind judges (opus, sonnet). Measured: the share of pairs both judges call right, with its
  Wilson interval, the projected number of tags for the whole population, and the tokens the judges spent per right pair;
  Jev's article probability, where cached, reported beside. Nothing reaches the database from the pilot. Decision rule, set
  now: the full pass is proposed to the user only if the projection is at least 200 tags (lower end of the interval at
  least 15%), as a rule "tag when both judges call it right", whose precision the next random audit measures.
- The possible-articles pilot, result (29 Oct). Of 100 pairs both judges call 84 right (95% 76-90%), 6 both wrong, 10
  split; projected for the 982 pairs: about 825 tags (742-883), well over the bar set (200, lower end 15%), so the full
  pass goes to the user. Half the splits (5) are speeches on whether to have a federal clause at all, under ICCPR 50: the
  project files that question as a general-debate topic, and the "both right" rule leaves them out. The both-wrong pairs
  are other articles of the same debate (the Committee's majority under its composition, reservations under article 2)
  or the agenda item on recommendations for self-determination. Cost: about 270,000 tokens for the two judges (about
  3,200 per right pair; the whole population about 2.7 million). Judgments in eval/possible_pilot/.
- Preregistered (29 Oct, the user: go): the full pass over the possible articles. The 882 pairs the pilot did not draw, in
  ten batches, to the same two blind judges with the same prompt. A pair both call right becomes a tag (the pilot's 84
  too): data/concordance/reader_tags.csv, note "judged right by two blind judges (round 108)", which api/build_db.py
  applies to an untagged speech as the readers' rows, but not blocked by Jev's no on the same article (a hand check is
  not overridden by a classifier, as for the tagger's accepted proposals); a speech with two such pairs takes neither.
  Checks: every new tag in eval/merge_tag_changes.py against the database before is one of these pairs; speakers, tests.
  Their precision is measured by the next random audit (the published figure), not by these judges.
- The possible articles, full pass, result (29 Oct; round 108). Of the 882 pairs both judges call 768 right (87%), 46
  wrong, 68 split; with the pilot's 84, 852 pairs on 850 speeches; two speeches with two such pairs take neither, so 848
  rows go to reader_tags.csv. The database: 827 new tags, none changed or dropped, every one a judged pair with its
  article; the other 21 are held back by the rules the readers' rows meet too: 14 that Jev's procedure check calls the
  organisation of work, 7 whose article an earlier blind check rejected (tag_rejections.csv keeps the last word). The
  splits are mostly the general questions under an article (the federal clause under ICCPR 50; the 1948 debate on the
  Declaration's minorities article, suggested as ICCPR 27). Speeches with an article 11,971 -> 12,798 (40.2% -> 43.0%);
  speakers 128/128, 49/49, 29/29; tests 139; published precision 95.5% (+/- 3.4), which the next random audit measures
  with these tags in it. Judge tokens: about 2.4 million for the pass (20 judges). Judgments in eval/possible_full/.
- Preregistered (29 Oct, the user: go): the topics at 0.8-0.9. The untagged speeches whose Jev topic pick (pipeline/topics.py)
  is a question of topics.csv or "general" at 0.8 <= p < 0.9: 510 (round 70 judged 40 of 54 right in this band). All to two
  blind judges (opus, sonnet) in six batches: the question's label and description, the list of all questions, the passage
  before, the speech; is the speech mainly about that question? A speech both call right takes the topic
  (data/concordance/topic_accepted.csv, applied by api/build_db.py below the threshold, migrated by resegment.py);
  topic_rejections.csv keeps the last word. No pilot: the band's rate is known. Checks: every new topic in segment_topics is
  an accepted row; speakers, tests. The next random audit's topic stratum measures them.
- The topics at 0.8-0.9, result (29 Oct). Of 510 speeches both judges call 434 right (85%), 27 both wrong, 49 split (opus
  the stricter: 65 and 68 right in two batches of 85 against sonnet's 79 and 81). The database: 434 new topics, every one an
  accepted row, none changed or dropped; speeches with a topic 1,588 -> 2,022 (self-determination 119, implementation 107,
  petitions 54, general 52, one covenant or two 47, form of the bill 23, reservations 11, territorial clause 11, federal
  clause 10). Article tags unchanged (12,798); tests 139 (the topic test now allows a topic under the threshold only as an accepted row). Judge tokens about 1.4 million (12 judges). Judgments in
  eval/topic_band/judgments.json.
- Preregistered (29 Oct, the user: go): the topics at 0.7-0.8. The same as for 0.8-0.9: the untagged speeches whose Jev
  topic pick is a question of topics.csv or "general" at 0.7 <= p < 0.8: 473 (round 70 judged 30 of 54 right at 0.6-0.8,
  so fewer than at 0.8-0.9 are expected). All to two blind judges (opus, sonnet) in six batches with the same prompt
  (eval/topic_band_07/); a speech both call right takes the topic (rows added to topic_accepted.csv; the 0.8-0.9 rows stay).
  Added because the band is weaker: a random 40 of the both-right rows (seed 7) to a third blind judge (opus, fresh, the
  same prompt); gate at least 36 of 40 right, else none of the band's rows is applied and the result is recorded as a
  negative. Checks as before: every new topic an accepted row, article tags unchanged, speakers, tests.
- The topics at 0.7-0.8, result (29 Oct). Of 473 speeches both judges call 311 right (66%), 101 both wrong, 61 split
  (sonnet the stricter this time in batches 1 and 5, opus in 3 and 6). Weakest: implementation 59 of 126 (the 1962
  Cypriot resolution on preparing the implementation debate, the racial discrimination convention's implementation and
  the Greek interim-measures proposal L.592 are other agenda items), territorial clause 7 of 18 (the Nationality of
  Married Women convention's clause); then general 53/70, self-determination 97/116, petitions 41/64, one covenant or two
  32/46, form of the bill 11/17, federal clause 6/8, reservations 5/8. The third judge (opus, fresh) on 40 of the 311
  (seed 7): 40 of 40 right, gate 36 passed (eval/topic_band_07/third_judge.json; it names seven close calls). The
  database: 311 new topics, every one an accepted row, none changed or dropped; speeches with a topic 2,022 -> 2,333.
  Article tags unchanged (12,798, no field of any tag changed); speakers 128/128, 49/49, 29/29; tests 139. Judge tokens
  about 1.7 million (13 judges). Judgments in eval/topic_band_07/judgments.json. No lower band: round 70 had 56% right
  at 0.6-0.8, and this band's yield already falls to two thirds.
- Preregistered (29 Oct, the user: an audit like the earlier ones, model judges only, no hand review now): round 109, the
  audit repeated after the Athena merge, the French fix, rounds 105-108 and the topics. (1) Tags, the design of rounds 43-69
  (eval/audit_sample.py --round 109, default sizes): tagged speeches per kind of record, 30 report paragraphs, 10 L-series
  (apart), 110 untagged speeches for coverage (50 R1, 60 R2); two blind judges per item (opus, sonnet "be strict"), a third
  (opus) on splits; the same prompts as round 69, but larger batches (about 25 items a judge instead of 12, to keep the
  number of agents down). Recorded with eval/audit_record.py; eval/quality_audit.py then publishes round 109's precision in
  place of round 69's (95.4% +/- 3.5). Wrong tags afterwards to tag_rejections.csv, as in round 69. (2) Topics, new
  stratum: 20 random speeches from each of the three topic groups (p >= 0.9; accepted at 0.8-0.9; accepted at 0.7-0.8;
  seed 109), the topic judges' prompt, two judges and a third on splits; reported per group and weighted by the groups'
  sizes (1,588 / 434 / 311), against round 70's 97% at p >= 0.9. (3) Pages, the fresh audit of rounds 76-99: two new random
  samples (eval/segment_audit_sample.py --per 12, seeds 108 and 109; 120 page images), the same reader instructions, one
  opus reader per 10 pages instead of one per page; reported as pages without error, errors, turns inside another,
  against round 99 (67 of 120, 86 errors, 28 turns inside another of 514). No gates: measurements; no hand review this
  round (the publication audit with the student stays the reference).
- Round 109, result (29 Oct; docs/quality_audit.md). Tags: precision 95.3% +/- 3.5 (126 of 132; round 69 95.4%), reports
  30/30, L-series 10/10, coverage 91% within records with tags and 85% overall (round 69: 83%, 76%); 9 items settled by the
  third judge; the 6 wrong tags refused. Topics: 19/20 at p >= 0.9, 19/20 accepted at 0.8-0.9, 16/20 accepted at 0.7-0.8,
  93% weighted (round 70: 97% at p >= 0.9 alone); the 6 wrong refused; the MCP instructions now say about 93%. Pages: 77 of
  120 without error (round 99: 67; z = 1.3), 64 errors (86), turns inside another 7 of 412 (28 of 514), with the caveat of one
  reader per 10 pages. The database after the refusals: 12,792 speeches with an article, 2,327 with a question; tests 139.
  Judge tokens about 4 million (37 judges).
- Preregistered (30 Oct, the user: go): round 110, the readers of whole records (pipeline/reader_tags.py, the design of the
  reader rounds: two readers per record, opus and sonnet, blind to each other; a tag only when both give the same article,
  neither as a guess and one sure, and Jev says yes at 0.7 or more; every other non-guess answer to possible_articles.csv,
  metadata only). Population: the meeting records (SR, PV) with untagged speeches over 150 characters that no reader round
  has read (none of their speeches in reader_tags.csv or in the readers' possible articles): 828 records. Two strata, run in
  this order: (A) the 274 with at least one tag (1,220 speeches to tag; round 109's R1 put 24% of such speeches on one
  article), (B) the 554 with none (R2: 8%). Each stratum's new tags are checked before they are applied: 40 at random (seed
  110 for A, 111 for B), two blind judges (opus, sonnet) and a third on splits, the tag-check prompt; gate at least 36 of 40
  right, else none of that stratum's tags is applied (its rows leave reader_tags.csv; its possible articles stay as
  metadata). Reported: records read, speeches answered, agreed, kept after Jev, the gate, coverage before and after, and the
  tokens. Expected from the handover's estimate: 300-500 tags, about 50 million tokens.
- Round 110, stratum A, result (30 Oct). 274 records read by 548 readers (9 in a first run, 265 in a second; no reader
  failed), about 33.7 million tokens (60 thousand a reader: the B stratum would cost about 66 million, not the 25 the
  handover's 50 million implied, so B waits for the user). Of the 1,220 speeches, both readers gave the same article for 173,
  Jev confirmed 124 (>= 0.7); 112 became tags (the others held by the procedure check or earlier rejections), none lost;
  13 speeches move from a general-debate topic to an article (the topic yields to a tag by design). Blind check of 40
  (eval/readers110_check, seed 110): 40 of 40 right (opus 40, sonnet 39, the one split settled right by a third): gate 36
  passed, the rows stay. Speeches with an article 12,792 -> 12,904 (43.4%); topics 2,327 -> 2,314; tests 139.
- Preregistered (30 Oct, the user: a pilot first): round 110, stratum B as a pilot. The full stratum (554 records with no
  tag) would cost about 66 million tokens for an expected low yield, so 40 of its records are drawn at random (seed 111,
  scratchpad readers110B_pilot.json) and read with the stratum-A design unchanged (two readers, opus and sonnet; the same
  decision rule and Jev at 0.7). Check: every new tag if there are 40 or fewer, else 40 at random (seed 111); two blind
  judges and a third on splits; gate at least 90% right (36 of 40, or 90% of a smaller set rounded up), else none of the
  pilot's tags is applied. Reported: tags per record and per 1,000 speeches, the tokens, and the projection to the other
  514 records (tags and tokens), on which the user decides whether to read them.
- Round 110, stratum B pilot, result (30 Oct): negative. 40 records, 80 readers (none failed, every id answered), 827
  speeches, about 5.0 million tokens. Zero tags: opus put 1 of its 827 answers on an article, sonnet 12 (11 of them
  'probable', 1 'sure'); the two readers agreed on one speech (E/CN.4/SR.131/Corr.1, ICESCR 6), both only 'probable', so
  no tag by the rule. Nothing to check (gate not reached); 11 answers went to possible_articles.csv as metadata (1,322 ->
  1,333); the DB's tags and topics are unchanged (12,904; 2,314); tests 139. What the readers saw: these records are on
  other agenda items (the Palestine refugees, the order of work, the self-determination resolutions of the General
  Assembly, the capital punishment study, the Commission's reports), which round 109's R2 judges, reading one speech
  with little context, partly put on an article (8%). Projection to the other 514 records (about 10,600 speeches): 0
  expected, at most about 39 by the rule of three (3/827), for about 64 million tokens. Not run further.
- Preregistered (30 Oct, the user: do the fixes from round 109): round 111, small fixes of segmentation, speakers and one
  tag. (a) The election lines ("Miss Imru (Ethiopia) was elected Vice-Chairman by acclamation"), read as a turn because
  'was' is one of the turn's verbs: a line whose speaker is followed by 'was (unanimously) (re-)elected' opens a procedural
  segment. Measured: speech segments opening with such a line, 39 now, expected 0; none of them carries a tag. (b) BADAWI
  Bey (Egypt), matched by the roster to Mr. BAGDADI (Egypt), another delegate of 1948: the 10 speeches whose opening prints
  BADAWI Bey get the name by data/gazetteer/speaker_fixes.csv (as SR.102-0023 already has); BAGDADI's speeches 22 -> 12.
  (c) Page furniture in the text, the narrow part of round 109's 13 'page element' errors: the running head of the 1960s
  plenary ('6 General Assembly - Twenty-first Session - Plenary Meetings'), the Third Committee's head when the OCR splits
  it over two lines ('352 General Assembly-Sixth' / 'Session-Third Comunittee'), the head 'date page' ('29 October 1957
  167'), the printer's line as the OCR misreads it ('Litho 1n U.N,', 'M-77301-December 1955} 875', '7791-June 1960-2,025'),
  all whole lines and in meeting records only; and the first page's masthead run into a speech ('THIRD COMMITTEE, 954th
  MEETING Thursday, 12 November 1959, at 10.50 a.m, NEW YORK'). Footnotes and decisions or headings inside speeches (round
  109's 3 footnote and 17 'other' errors) are not touched: each would need its own rule. Measured: the number of lines each
  rule removes in the corpus, and of round 109's 13 errors how many are gone. Checks: speaker_eval chr3 128/128, early
  49/49, images 29/29 must not fall; tags must not be lost (the id map's lost segments listed); a random 40 of the segments
  whose text or kind changed, old and new side by side, judged by two blind judges (a third on splits) for whether the change
  is right (only furniture removed, the kind right); gate 38 of 40, else the rule behind a wrong change is reverted. (d)
  E/CN.4/SR.171-0034 (refused as ICCPR 26 in round 109; both judges said association): the tag ICCPR 22 if two blind judges
  both say it is right, through the reader table, else nothing.
  Amended before (d) ran (30 Oct): the cause is the record's context, not the one speech. In E/CN.4/SR.171 the chair (0023)
  names 'article 20' of the Universal Declaration during the debate on draft article 19 (association) and the context turns
  to draft 20 (ICCPR 26) until the chair's next turn (0036): 13 segments, 0023-0035, of which rounds 103 and 109 already
  refused two (0032, 0034). Each of the 13 is judged blind by two judges (a third on splits): which final article it is
  mainly about, given the record. A speech both (or the third) put on ICCPR 22 gets it through speech_retags.csv (previous
  ICCPR 26; the reader table cannot replace a context tag); a segment put on neither 26 nor 22 is refused as ICCPR 26
  (tag_rejections.csv); the chair's turn cannot be retagged, so if it is not 26 it is only refused.
- Round 111, result (30 Oct). Resegmented (data/id_maps/2026-10-30-1631.json): 115 records changed, no segment lost or
  split, no id moved, no tag changed; speaker_eval chr3 128/128, early 49/49, images 29/29; ocr_bench unchanged; tests 139.
  (a) Elections: 41 speeches became procedural (the 39 counted, and two the count's pattern missed, 'Mr. Lépez (Philippines)'
  and 'Mrs Sychrava. (Czechoss idvakia)'); one spelling moved with them (LOPES -> LOPEZ, Philippines, the same person). (b)
  BADAWI Bey: 10 speeches renamed, BAGDADI's 22 -> 12. (c) Furniture: 178 segments changed in all, by rule: the masthead
  run into a speech 91, the 1960s plenary's head 16, the date with the page 13, the Third Committee's split head 10, the
  printer's line 6; of round 109's 13 page-element errors 10 are gone (the 3 footnotes stay, as planned). The blind check
  of 40 changed segments (seed 111, eval/round111_check): sonnet 39 right, opus 37, a third judge on the 2 splits: 37 of 40,
  under the gate of 38. The three wrong: two masthead removals that left work undone (a hyphenated word not rejoined, 'meet-
  @ ing'; the masthead's first words left, 'prin- THIRD COMMITTEE S83rd ciples', the OCR's S for 8), no speech text lost; and
  the date-with-page rule on a first page, where it took the record's own issue date out of the masthead ('20 May 1949 59').
  As preregistered, the two rules behind them (the masthead run, the date with the page) are reverted; the others stay. (d)
  E/CN.4/SR.171-0023..0035: both judges put all 13 on ICCPR 22 (sure, one probable); Jev on the 12 speeches 0.92-0.99. The
  12 speeches are retagged ICCPR 26 -> 22 (speech_retags.csv; two of them had no tag after the refusals of rounds 103 and
  109), the chair's turn 0023 refused as 26; gold stratum SR171-context/check. Speeches with an article 12,904 -> 12,906.
- Preregistered (30 Oct): round 112, the two reverted rules mended. The masthead run: the meeting number as the OCR reads its
  figures ('S83rd'), and a word that the masthead split ('prin- ... ciples', 'meet- @ ... ing') joined again; the date with
  the page: not on a record's first page. Check: of the segments these two rules change against the database before round
  111, 40 at random (seed 112), the same two blind judges and prompt, a third on splits; gate 38 of 40, else the rule behind
  a wrong change stays out.
- Round 112, result (30 Oct): negative for the masthead, positive for the date with the page. Against the database before
  round 111 the two mended rules changed 97 segments (the masthead 91, the date with the page 6, down from 13: no first
  pages). Blind check of 40 (seed 112, eval/round112_check): sonnet 40 right, opus 35, a third judge on the 5 splits: all 5
  wrong, so 35 of 40, under the gate of 38. All five are masthead removals that left the masthead's first words in the
  speech, as the OCR reads them ('THIRD COMMITTER 769th', 'THIRD COMMITTEE 863rd - MEETING', 'Se THIRD COMMITTEE, 1398th
  MEETING Ny', a page number before them), and with them a split word not joined; no speech text was lost in any. The
  masthead rule stays out (two rounds failed on the same class; 43 speeches still carry the masthead's first words, and the
  91 the rule would have cleaned keep the whole masthead); the date with the page stays in (its 3 items right). Resegmented
  without it: against the database before round 111, 41 kinds, 51 speakers, 39 texts and 13 tags changed in all; speaker_eval
  128/128, 49/49, 29/29; tests 139.
- Preregistered (30 Oct, the user: search for the SR.171 case and judge it): round 113, context switched by a passing
  mention. Search (no model): in the meeting records, a run of segments whose context article turns from A to B at a
  chair's, vote or procedural segment and returns to A after it (A-B-A), where that segment names article B with no words
  of taking it up (TAKES_UP_RE, EXAMINATION_RE, AMENDMENT_TO_RE of api/build_db.py): 134 runs in 95 records, 763 tagged
  segments (E/CN.4/SR.171 among them; of all 280 A-B-A runs, 22 more start with a taking-up and 21 do not name B). Judges:
  for each record, the segments from 12 before each run to 4 after it, without the tags, the session's numbering and the
  catalogue; two blind judges (opus, sonnet) say for each tagged segment of the runs which final article it is mainly about
  (or none), and how sure; a third (opus) only where the two differ. Rule: the tag stays if at least two judges give its
  article; otherwise it is refused (tag_rejections.csv), and a speech is retagged (speech_retags.csv) when two judges give
  the same other article, neither as a guess and one sure, and Jev says 0.7 or more. Reported: tags kept, refused, retagged,
  per run type, and the share wrong (with its interval) as an estimate for this class of context; tokens.
- Round 113, result (30 Oct). 95 records, 203 judges (190 and 13 thirds; none failed, every id answered), about 12.2
  million tokens (the estimate was 5: the judges read the windows several times). Of the 763 tags, 606 kept (two judges or
  more give their article), 157 not: 18 speeches retagged (two judges on the same other article, one sure; Jev 0.82-0.98;
  e.g. E/CN.4/SR.54-0040..0048 UDHR 7 -> 10, E/CN.4/AC.2/SR.2-0038..0041 UDHR 1 -> 29, E/CN.4/SR.121-0024..0025 ICCPR 4 -> 21,
  E/CN.4/SR.351-0045, 0050 ICCPR 29 -> 34) and 139 refused (one more retag candidate had Jev under 0.7). Wrong in this class:
  157/763 = 20.6% (Wilson 95%: 17.9-23.6); by kind, speeches 59/428 = 13.8% (10.8-17.4), the chair's turns 66/191 = 34.6%
  (28.2-41.5: mostly procedure, which the judges put on no article), votes 18/119 = 15.1% (9.8-22.6). Gold: stratum
  context113/check (763 rows, not part of the published precision). Speeches with an article 12,906 -> 12,865 (43.3%);
  topics unchanged 2,314; tests 139. eval/context_switch.py (search, decide), eval/round113/ (candidates, inputs, results).
  The class is not closed: the 22 runs that open with a taking-up and the 21 that do not name B were not judged, nor the
  rule in api/build_db.py that lets a passing mention set the context (a change there would move other tags).
- Preregistered (31 Oct, the user: go on with 1-3): round 114, the passing mention at the rule. Two variants of the
  chair's, vote and procedural branch of api/build_db.py (built side by side, nothing applied yet): v1, a named article
  with no words of taking it up moves nothing when an article is already in force, unless a decision follows it ('adopted',
  'rejected', 'carried', 'approved') or the segment puts something to the vote; v2, the same only when another instrument is
  named near the mention (the Declaration, the Charter, a convention, a covenant, a resolution). Measured on the gold
  (data/gold/article_tags.jsonl): of the judged-right tags in the database (3,519), how many a variant changes (lost); of
  the judged-wrong (486, most already refused), how many lose the wrong context (fixed: another tag, or another context
  article); and how many tags change outside the gold. Choice: the variant with more fixed among those that lose at most
  1% of the right (35); none if neither. Then a blind check of 40 of its changed tags outside the gold (seed 114): two
  judges and a third on splits give the article of each segment; a change is better if the new state is right and the old
  was not, worse if the old was right and the new is not. Applied if worse <= 4 of 40 and better >= 3 times worse.
- Round 114, result (31 Oct): negative, nothing applied. On the gold: v1 lost 27 of the 3,519 right tags and fixed 148 of
  the 486 wrong contexts, changing 528 tags (412 outside the gold); v2 lost none but fixed 7 (76 changed): v1 chosen. On
  round 113's judged set alone v1 scored 50 better against 21 worse. The blind check of 40 of its changes outside the gold
  (seed 114, eval/round114: two judges in batches of ten, a third on 1 split, about 0.9 million tokens): better 17, worse
  22, neither 1, against the gate of worse <= 4. The worse ones are the switches the rule was right to make: a debate that
  had moved on (draft article 34 of 1966 that has no final article, E/CN.4/AC.1/SR.34's emergency clause, E/CN.4/SR.70,
  SR.91), a chair's turn that opens the next article without the words of taking it up, and speeches on the order of the
  articles that the old context had left untagged. A mention without those words is as often the next subject as an
  aside: the record's wording does not separate them, so the context rule stays as it is and round 113's per-tag judging
  is the way to correct this class. The variant switch was removed from api/build_db.py; eval/context_rule_eval.py kept.
- Preregistered (31 Oct): round 115, the tags of the chair's turns, the votes and the procedural lines, which the precision
  audits (speeches only) never sampled. Population: the tagged segments of these kinds in the meeting records (chair 3,169,
  vote 1,771, procedural 425). Sample: 30 chair, 20 vote, 10 procedural at random (seed 115), each with its stretch of the
  record (12 segments before, 3 after), the tags hidden; two blind judges (opus, sonnet) give the article it is mainly about,
  a third (opus) where they differ; a tag is right if two judges give its article. Reported: right per kind with Wilson
  intervals and the precision weighted by the population; the wrong tags are refused (tag_rejections.csv), as in the audits;
  stratum <kind>/round115/check in the gold (not the published precision). No gate: a measurement; a kind under 90% gets
  its own round.
- Preregistered (31 Oct): round 116, a measurement without models. The vision reader's pages (data/ocr/*/chandra/*.html)
  carry layout labels nothing uses yet (Text, Section-Header, Page-Header, Page-Footer, Footnote). For round 109's 64 page
  errors: how many the labels would show, by class: the leaked head or foot inside a Page-Header or Page-Footer block, the
  footnote inside a Footnote block, the heading or decision inside a block of its own (Section-Header or a Text block that
  begins with it), a missed turn's opening at the start of a block, the missing text present in the reading. Matched by the
  quoted words of each error's description, fuzzy (rapidfuzz partial_ratio >= 85), on the page and its neighbours. It
  decides whether a label-based step in the segmenter is worth a round, not anything in the database.
- Round 115, result (31 Oct). 60 judged (14 judges in batches of ten, 6 thirds, about 1.1 million tokens): the chair's
  turns 25/30 right = 83% (Wilson 66-93), votes 19/20 = 95% (76-99), procedural lines 4/10 = 40% (17-69); weighted by the
  population 83.8%, against about 95% for the speeches. The 12 wrong: the chair on the order of work, time-limits or
  relevance (5), a vote on a point of order (1), attendance lists with the agenda title (3), decisions on the order of work
  or adjournment (2), one decision on the next article (UDHR 21 for 13). All refused; gold strata chair|vote|procedural/
  round115/check. The chair's turns and the procedural lines are under 90%: each gets its own round (the procedural lines
  with a tag are 419, of which about 36 attendance lists by their opening words).
- Round 116, result (31 Oct, no models; eval/chandra_labels_audit.py, eval/round116_labels.json). Of round 109's 64 page
  errors, 57 testable by their quoted words: the vision reader's labels show 46 (header or footer in the text 9/13, inside
  a Page-Header or Page-Footer block; decisions, headings and footnotes inside segments 14/17, as a Footnote, a
  Section-Header or a block of their own; wrong kinds 8/10; missed turns 6/7, the turn's opening at the start of a block;
  missing text present 9/10). The match is lenient (a spot check of 17 found one or two false hits), so about 4 in 5 is an
  upper bound. The speakers and delegations (7) are not testable this way. The labels exist for all 18,492 pages, the
  two-column ones whose text stays the OCR vote included.
- Preregistered (31 Oct, the user: a, b, c in turn): round 117, the vision reader's labels in the segmenter. In
  pipeline/segment.py load_lines, meeting records only, before the furniture rules: a line of the page's text that the
  vision reader put in a Page-Header or Page-Footer block (rapidfuzz partial_ratio >= 92 on the normalised words, the line
  at least 8 characters, not longer than the block by more than 10, at least 40% of it or 20 characters) is dropped, on a
  first page only after the first turn (the masthead above it is left to the masthead's reading); lines put in a Footnote
  block (at least 20 characters) go to the page's footnotes, one footnote segment per block. Measured: lines dropped and
  moved; segments changed, lost and split (the id map); tags changed; the speaker evals (must stay 128/128, 49/49, 29/29);
  meeting dates (must not change); how many of round 109's 13 head-or-foot errors and its footnote errors are gone; and
  the masthead residues (speeches with 'THIRD COMMITT' in capitals, 43 now). Check: 40 changed segments at random (seed
  117), old and new side by side, two blind judges and a third on splits, the furniture prompt of round 111 (a moved
  footnote is right if what moved is the page's footnote); gate 38 of 40, else the step is reverted.
- Round 117, result (31 Oct): negative, reverted. A first version's dry run lost 37 article headings ('Article 22' near a
  typed page's catchword 'Article 29', which the reader labels Page-Footer) and merged 51 segments: guards added before
  anything was judged (no line the segmenter reads as a heading, turn or closing; the line's numbers in the block; no
  catchword block; a running head is at most 150 characters; a footnote moved whole or not at all, after the French column
  is dropped). The sample of seed 117 was read by me while fixing, so the check used a fresh one (seed 1171). The final
  version: 332 records changed, no segment lost, 54 split, 443 more footnote segments, the (record, document) pairs 11,538
  -> 11,546, 5 more speeches, dates unchanged, one speech tag lost (E/CN.4/SR.388-0007, its Jev choice dropped with the
  split), speaker_eval 128/128, 49/49, 29/29, tests 139; of round 109's 13 head-or-foot errors 11 gone (2 were the step's,
  the others the rules of rounds 111-112), and the footnotes in A/C.3/SR.404-0015 and SR.1015-0014. Blind check of 40
  (eval/round117_check): 36 right, under the gate of 38. Wrong: a footnote with an unread marker ('!/Official Records')
  dropped as a page foot; a quoted ECOSOC resolution, set in like a footnote, moved to a footnote segment; a running head's
  symbol line left with a split word; a date line put back into a masthead (a head line taken next to it, so the rule that
  drops a running head with its date no longer saw the pair). The data were restored to the state before round 117.
- Preregistered (31 Oct): round 118, the same step with three guards for those errors, and the last try for this step: a
  line is not dropped as a head or foot if it reads as a citation ('Official Records', 'Supplement', 'Ibid', 'See',
  'document'); a footnote is moved only if its first line opens like one (a marker, as the OCR reads it, or 'See', 'Ibid',
  'Official Records', 'Subsequently', 'Indicates', 'United Nations publication', 'Item'); no line next to a line that is only a
  date is dropped. Same measures; check of 40 changed segments, fresh seed 118, the same judges and prompt; gate 38 of 40,
  else the step is reverted for good.
- Preregistered (31 Oct): round 119, the procedural lines' tags (round 115: 4 of 10 right). In api/build_db.py a procedural
  segment loses its tag when it is: an attendance list ('Chairman: ... Members: ...', 'Present:'; 32 of the 419 tagged); a
  decision on the order of work (ORDERS_WORK_RE; 27); a member taking or resuming the chair (23); the meeting suspended,
  resumed or risen (17); a bare 'It was so decided / agreed' (under 80 characters) after a turn that does not speak of the
  text (DRAFTING_DECISION_RE, as for the decisions without a vote; 73). Measured: tags removed by group; the procedural gold
  rows lost and fixed. Check: 40 of the removed tags at random (seed 119), the segment with its stretch of the record, two
  blind judges and a third on splits give the article (the prompt of round 115); a removed tag was right if two judges give
  its article. Applied if at most 12 of the 40 were right (at least 70% of what goes was wrong), else not.
- Round 118, result (31 Oct): negative; the step is reverted for good (pipeline/segment.py as before round 117, the data
  restored to the state before it). The guarded version changed 293 records (no segment lost, 41 split, 363 more footnote
  segments, the pairs 11,538 -> 11,546, two speech tags lost to splits, speakers and dates unchanged). Blind check of 40
  (seed 118, drawn and judged without my reading it first; eval/round118_check): 33 right, 11 splits settled by a third,
  under the gate of 38. The 7 wrong are partial moves: a footnote's tail, a masthead's words or a running head left behind
  or put into the wrong segment, a split word not joined ('representapage 23, tive'), a decision that lost its kind. With
  both versions the moved footnotes were right in nearly every case; what fails is the boundary work line by line on text
  that is not the reader's own: the labels belong to the vision reader's reading, and mapping them onto the OCR vote's lines
  goes wrong at the edges often enough to fail a 95% gate. A sound use of the labels would segment the vision reader's own
  text (its blocks), i.e. a new segmenter path, not a filter on the vote: not attempted here. eval/round117_check and
  eval/round118_check keep the samples, verdicts and id maps.
- Preregistered (31 Oct): round 120, the chair's tags (round 115: 25 of 30 right, the wrong ones about the order of work).
  Jev's procedure question (eval/jev_procedure_check.py, the one that drops short speeches at 0.8) is asked of the tagged
  chair's turns under 200 words too (--kind chair; same cache, same prompt), and api/build_db.py applies the same threshold
  to them. Measured: the chair's tags dropped; on the gold rows still tagged, how many judged right are dropped. Check: 40
  of the dropped at random (seed 120), two blind judges and a third on splits give the article (round 115's prompt); a
  dropped tag was right if two judges give its article. Applied if at most 12 of the 40 were right, else not.
- Round 120, result (31 Oct): applied. Jev answered for 3,099 of the 3,164 tagged chair's turns (3,037 asked, about 150
  calls); 612 at 0.8 or more lose their tag (3,164 -> 2,552); on the gold rows still tagged it drops 11 of 197 judged right.
  Blind check of 40 of the 612 (seed 120, eval/round120; 9 judges, about 0.8 million tokens): 9 of 40 right (22.5%), under
  the limit of 12; the 9 are the chair opening an article or a ruling about one article's vote, which Jev counts as
  procedure; the 31 are time-limits, suspensions, rulings on procedure, calls to order. Projected from round 115's 25/30, the
  chair's tags go from about 83% right to about 95%, with wide intervals (both samples are small). The context the chair
  sets for the speeches after it is untouched (the drop is of the chair's own tag). Gold stratum chair/round120/check.
- Round 119, result (31 Oct): applied. The rule takes 157 of the 419 procedural tags (419 -> 262); on the gold rows still
  tagged it drops 1 of 23 judged right. Blind check of 40 of the 157 (seed 119, eval/round119; 8 judges, about 0.7 million
  tokens): 0 of 40 right (all order of work, suspensions, members taking the chair, bare decisions on procedure), against
  the limit of 12. Gold stratum procedural/round119/check. Tests 139; the speeches' tags unchanged (12,865).
- Round 121 (31 Oct, no models: audit of eval/jev_article_choice.py, pipeline/reader_tags.py and the remaining A-B-A runs of
  round 113). (1) In eval/jev_article_choice.py, the 895 unasked candidates (todo) were all artefacts of later rounds: 864 in
  records already read whole by two readers in rounds 96-110A, where the readers' tags in the database caused candidates_1948
  and candidates_records to treat the meeting as having headings-or-chair articles (arts[sym]), and 31 whose context tag
  round 113's blind check had already refused ('blind check found' in article_mapping). Excluding reader tags from arts[sym]
  and skipping speeches refused by a blind check leaves 2,840 candidates and 0 to ask. (2) In pipeline/reader_tags.py,
  numbering(con, doc) returned [] for two-text records (geneva_plenary, E/CN.4/SR.34-42) and for 1948 Drafting Committee
  meetings on the Covenant (stage e600, whose document instrument is UDHR), and skipped alphanumeric UDHR draft numbers (15A,
  31A, 35A); fixed so that both texts' tables, e600's table and alphanumeric draft numbers are emitted. (3) Of the 42 A-B-A
  runs left out of round 113 (22 opening with a taking-up, 20 not naming B), 25 keep the same base draft article (A and B
  differ only in a paragraph suffix and never change the final article; in round 113 the 477 judged segments in same-base-draft
  runs were 95.4% right, against 52.8% in the 286 where the base draft article changed), leaving 17 runs (60 tagged segments)
  that switch base draft articles; comparing base draft articles (A.split('.')[0]) also uncovers 13 runs (56 tagged segments)
  that round 113 missed because A carried a paragraph suffix on one side of B and not the other (e.g. 8.1 -> 2 -> 8 in
  E/CN.4/SR.56, 5.1 -> 13 -> 5 in SR.149, 9 -> 4 -> 9.5 in SR.102).
- Preregistered (31 Oct): round 122, closing the context-switch and stranded-context class (eval/context_switch.py --remaining).
  Population (no model): the union of (g1) the 75 tagged segments not judged in round 113 in A-B-A base-draft-article switches
  (A0 != B0) whose current tag differs from A's final article, (g2) the 39 unjudged chair, vote and procedural segments whose
  final-article tag differs from A in a non-speech run between two tagged segments on A, and (g3) the 28 unjudged chair, vote
  and procedural segments in a contiguous draft_article block whose tag disagrees with every tagged speech in that block
  (stranded when the speeches around them were retagged by readers or Jev): 114 segments in 30 meeting records
  (eval/round122/input/). Judges and rule: as in round 113 (two blind judges per record with the window from 12 segments before
  to 4 after, the tags hidden, the session's numbering and the catalogue; a third judge on splits; kept if at least two judges
  give the current tag, else refused in tag_rejections.csv, or retagged in speech_retags.csv when two judges give the same other
  article, neither as a guess and one sure, and Jev says 0.7 or more). Gold: stratum context122/check.
- Round 122, result (31 Oct): applied; the context-switch and stranded-context class is closed (0 remaining across g1, g2, g3).
  30 records, 6 blind judges in batches of 10 records (0 splits across all 114 segments, so 0 thirds needed). Of the 114 tags,
  37 kept and 77 not: 8 speeches retagged (both judges on the same other article, at least one sure, Jev 0.86-0.98:
  E/CN.4/AC.1/SR.32-0056 ICCPR 9 -> 12, E/CN.4/SR.149-0055..0056 ICCPR 14 -> 6, E/CN.4/SR.229-0042..0043 ICESCR 14 -> 13,
  E/CN.4/SR.56-0006 UDHR 29 -> 11, E/CN.4/SR.71-0057..0058 UDHR 22 -> 25) and 69 refused (3 speeches on voting order in
  A/C.3/SR.1420-0007, 0011 and E/CN.4/SR.102-0015, and 66 chair, vote and procedural segments whose context tag had switched
  or been left behind when surrounding speeches were retagged). Wrong in this class: 77/114 = 67.5% (Wilson 95%: 58.5-75.4);
  by kind, speeches 11/27 = 40.7% (24.5-59.3), chair's turns 41/53 = 77.4% (64.5-86.5), votes 22/29 = 75.9% (57.9-87.8),
  procedural 3/3 = 100% (43.8-100), headings 0/2 = 0% (0.0-65.8). Gold: stratum context122/check (114 rows). Speeches with an
  article 12,865 -> 12,862 (43.3%); topics unchanged 2,314; speaker_eval 128/128, 49/49, 29/29; tests 139. eval/round122/
  (candidates, input, results).
- Round 123 (31 Oct, no models: audit of the remaining context-tag sub-classes, named officers resuming the chair, procedural
  attendance/chair-resumption tags, and L-series dates and sessions). (1) Checked the two remaining sub-classes of Lever #3:
  (a) for context tags vs report meeting lists, covenant_article() already filters every article whose report meeting list omits
  the meeting; the only chr6 exceptions (E/CN.4/SR.174, 175, 196, 200) are the 4 draft articles (21, 23, 24, 26 -> ICCPR 20, 48,
  50, 51) that had no entry in E/1681 annex I's footnotes because draft 21 was deleted at SR.174-175 and the final clauses were
  debated at SR.196 and 200; (b) for speeches mentioning their article number only as another instrument's, every unjudged case
  is either an ICCPR article whose number matches the corresponding UDHR article on the same right (9, 18, 19), a 1947 speech
  calling E/CN.4/56 the Convention, or the 5 speeches in E/CN.4/SR.352 on ICCPR 33 (draft 18) comparing the Human Rights
  Committee election procedure to Article 18 of the ICJ Statute (Jev 0.97-1.00). (2) In pipeline/chairs.py (TOOK_RE) and
  pipeline/segment.py (TOOK_CHAIR_RE), a named officer resuming the chair ('Mr. Malik (Lebanon) resumed the Chair.', 'Mrs.
  Roosevelt (United States of America) resumed the Chair.') was not matched because TOOK_RE had only (?:took|occupied) and
  TOOK_CHAIR_RE had only took (while CHAIR_NOTE_RE in segment.py is anchored at ^ for post-speaker text). Adding resumed fixes
  38 chair turns across 10 meetings (29 turns where the Vice-Chairman or temporary Chairman stayed on as speaker after the
  Chairman resumed the chair, e.g. 13 turns of Mr. Malik in A/C.3/SR.126 given to Mrs. Begtrup and 6 turns of Mrs. Roosevelt in
  E/CN.4/SR.136 given to Mr. Laugier, and 9 turns left unnamed in E/CN.4/SR.100, SR.127 and A/PV.1495; named chair turns in DB
  5,843 -> 5,852) and drops the 5 remaining tagged 'resumed the Chair' procedural lines in api/build_db.py; widening
  ATTENDANCE_RE for OCR punctuation ('Chairman;', 'Chairmen:', 'Chadrman:', 'Members;') drops the 5 remaining tagged opening
  attendance lists (tagged procedural segments 259 -> 249; 0 gold rows lost). (3) Audited all L-series dates and sessions: of
  the 5 L-series rows without a date or session, 4 (A/C.3/L.71/Rev.1, A/C.3/L.104, A/C.3/L.1379/Rev.1/Corr.1, E/CN.4/L.635) are
  1-page ODS 404 placeholder PDFs, and 1 (E/CN.4/L.58) is dated 28 April 1952 on page-001.png (added to dates_read.csv -> 8th
  session (1952)); monotonicity and masthead-session checks also caught 3 L-series amendments whose year had a 1-digit OCR or
  stencil error contradicted by their printed session, job number and neighbours (E/CN.4/L.124 1957-05-19 -> 1952-05-19, 8th
  session; A/C.3/L.654 1954-11-18 -> 1957-11-18, 12th session; A/C.3/L.1245 1955-10-21 -> 1965-10-21, 20th session; added to
  date_overrides.csv). speaker_eval 128/128, 49/49, 29/29; tests 139.
- Round 124 (31 Oct, no models: presiding-officer attribution, speaker and delegation resolution and unification, and document
  dates, sessions and doc_type). (1) In pipeline/chairs.py: widened OFFICER_RE to match plural and OCR forms ('Chairmen:',
  'CHAIRMEN:', 'Chatrman:', 'Chai rman:', 'Chaiman:', 'Temporary Chairman:', 'Acting Chairman:') and bare surname lines without
  honorific ('Chairman: P. C. Chang (China)'); added a two-column masthead fallback (COL_CHAIR_RE) for 1947-48 E/CN.4/ and
  E/AC.7/ records where 'Chairman:' is separated from the officer's name by an adjacent column cell, and an OCR-page fallback
  reading pages 1-3 of data/ocr/<slug>/ when block segmentation dropped the 'Chairman:' line; taught parse_person to recognise
  unbracketed countries at the end of a masthead line ('Mrs. Franklin D. ROOSEVELT United States of America'); expanded VARIANTS
  and KNOWN_CHAIRS with verified session officers; and scoped UNSURE_RE in the body so a single 'Who took the Chair' line resets
  the current speaker rather than blanking the rest of the meeting. Named chair turns in DB: 5,852 / 7,878 -> 7,764 / 7,877
  (98.6%; +1,912 named turns). (2) Cleaned data/gazetteer/speaker_kept.csv (183 -> 33 genuine carry-back rows), removing 150
  rows that overwrote clean DB speakers with OCR garbles ('KI30P', 'MSOP', 'KALIK', 'SONGS', 'CRIEZ', 'MUSTAPHIADES', 'MONOSOV',
  'SURRENGEN') or wiped resolved speakers with empty strings; added 119 page-image-verified speaker and delegation fixes to
  data/gazetteer/speaker_fixes.csv and 19 UN Secretariat, specialised-agency and NGO variants to
  data/gazetteer/organizations.csv; moved speaker_kept.csv and speaker_fixes.csv before unify_speakers() in api/build_db.py and
  taught unify_speakers() to merge rare non-printed spellings whose segment speaker_raw matches the canonical delegate; and in
  api/build_db.py reclassified 10 'General debate/discussion/statements/clause (continued)' headings from speech to heading, 19
  opening attendance-table/corrections fragments and chair-taking notes from speech to procedural, and copied speaker/delegation
  onto 13 mid-sentence 'General Assembly (...)' false splits. Result: 0 of 29,682 speech segments lack a speaker or delegation
  (100.0% resolved; distinct speakers 1,846 -> 1,694, distinct delegations 167 -> 155). (3) Read and verified dates from page
  images and text for all 36 undated real documents (added to data/concordance/dates_read.csv; only the 4 ODS 404 placeholder
  PDFs remain undated), fixed 2 ECOSOC resolution dates in data/concordance/date_overrides.csv (E/RES/84(V) -> 1947-08-08,
  E/RES/349(XII) -> 1951-02-23), completed SESSIONS_1946_48 in pipeline/sessions.py and SESSION_OVERRIDES in pipeline/entities.py
  so all 2,156 non-placeholder documents carry their canonical session (documents missing session 102 -> 4), and fixed
  api/build_db.py's second pass to read others.get(symbol) for doc_type (restoring summary_record, verbatim_record, resolution and
  working_paper across 1,656 records outside udhr.json, including E/CN.4/SR.266 and A/PV.46). speaker_eval 128/128, 49/49, 29/29;
  tests 139.
- Round 125 (31 Oct, no models: article tag hygiene on masthead and procedural segments, and L-series amendment concordance).
  (1) In api/build_db.py, cleared final_article, article_instrument, article_confidence and article_mapping on kind = 'masthead'
  after the masthead has set the meeting's opening context (as already done for kind = 'closing'; tagged masthead segments 263 -> 0).
  (2) Scoped the Round 124 opening-attendance filter in api/build_db.py to Mr. EVANS (ILO) and Mr. WEISS/WEIS (IRO) attendance
  lines so 12 early speeches mentioning the ILO stay kind = 'speech' (total speeches 29,682 -> 29,694; 0 missing speaker or
  delegation), and extended ATTENDANCE_RE, ORDERS_WORK_RE and procedural_off_article() to strip article tags from 37 remaining
  off-article procedural segments (the 5 ILO/IRO attendance lines, E/CN.4/SR.111/Corr.1's masthead, 1-char OCR noise 'f' in
  E/CN.4/SR.424-0009, the chair's sympathy statement in A/C.3/SR.815-0004, and 29 order-of-work/scheduling decisions and bare
  'It was so decided' lines after procedural proposals, while preserving restored rows judged right on the page image; tagged
  procedural segments 260 -> 216, 0 gold rows lost). (3) Audited all 104 untagged L-series documents: added A/C.3/L.1355
  (multi-article Netherlands amendments to Part IV) to data/concordance/l_series_readers.json so 100% of L-series base documents
  are covered; fixed key() in pipeline/l_series_articles.py to normalise common Article 1 (ICCPR 1 / ICESCR 1 -> ICCPR+ICESCR 1)
  and recognise the identical federal-State clause (ICESCR 28 = ICCPR 50), adding E/CN.4/L.22, E/CN.4/L.22/Rev.1 (ICCPR+ICESCR 1)
  and E/CN.4/L.230 (ICESCR 28) to data/concordance/l_series_articles.csv (116 -> 118 base documents); and in api/build_db.py
  tagged page 1 of E/CN.4/L.93 (the Lebanon-US amendment to article 20 = ICESCR 6) while clearing the running article heading on
  pages 2-26 (the bound compilation of later L-series documents). speaker_eval 128/128, 49/49, 29/29; tests 139.
- Preregistered (31 Oct): round 126, the remaining possible-article pairs added after round 108 (mostly from round 110's
  whole-record readers and speeches whose context tag rounds 113 and 122 refused). Population: all 210 unjudged (speech,
  suggested_article) pairs on 205 untagged speeches in possible_articles.csv (excluding Schabas index pages), formatted as in
  eval/possible_pilot.py in three batches of 70 (eval/round126/batch01..03.json). Judged by two blind judges per batch (Judge A,
  strict Judge B) with the round 108 prompt and rule: a pair both call right goes to data/concordance/reader_tags.csv (note
  'judged right by two blind judges (round 126): ...'); a speech with two both-right pairs takes neither.
- Round 126, result (31 Oct): applied. Of the 210 pairs, both blind judges call 83 right (39.5%, on 79 speeches), 95 both wrong
  (45.2%: procedural points of order, right of reply, other agenda items), and 32 split (15.2%, e.g. the 13 speeches on the right
  of asylum in E/CN.4/SR.317 suggested under ICCPR 13). Four speeches in E/CN.4/AC.1/SR.27 (0022-0025, on draft article 20 of the
  1948 Geneva draft Covenant) had two both-right pairs (ICCPR 2 and ICCPR 26) and take neither by rule; 75 rows go to
  data/concordance/reader_tags.csv (2,270 -> 2,345). In the database: 73 new speech tags (2 held back by Jev's procedure check at
  p >= 0.8: A/C.3/SR.787-0011 and E/CN.4/SR.52-0054), 0 dropped, 0 changed; speeches with an article 12,862 -> 12,935 (43.6%);
  topics 2,314 -> 2,302 (12 speeches move from a general-debate topic to an article tag). Coverage (eval/quality_audit.py): 91%
  within records with tags, 86% overall (pooled over rounds 66, 69, 109: 88% within, 82% overall). speaker_eval 128/128, 49/49,
  29/29; tests 139. eval/round126/ (batch01..03.json, judgments.json).
- Round 127 (31 Oct, no models: pre-release audit, documentation sync, dataset export and bundle build). Ran eval/quality_audit.py
  (updating data/gold/audit.json), eval/coverage.py (updating eval/coverage.json and docs/coverage.md), api/export_dataset.py
  (updating data/export/: 2,160 documents, 83,935 non-masthead segments, 6,768 decisions, 2,716 amendments), and
  deploy/build_bundle.py (updating dist/travaux-bundle); synchronised README.md and docs/quality_audit.md with the final counts and
  audit summaries after rounds 110-126. speaker_eval 128/128, 49/49, 29/29; tests 139.
- Release work (Gemini 4 Argon in Antigravity, 1-2 Nov; committed by Claude on 2 Nov after review): the site's search sort and
  field prefixes, article and delegation filters, CSV/JSON exports of votes and amendments, citation styles and Markdown/JSON
  export in the workspace, the project citation on About; MCP with 6 tools over stdio and over HTTP in api/server.py (/mcp,
  /api/mcp; behind the VM's password like the rest: 401 from outside); the travaux-research skill (mcp/skills, site/skills);
  eval/ledger.py counting Antigravity sessions and eval/model_bench with Gemini 4 Argon. tests/test_mcp.py updated for the two
  new tools (141 tests). docs/handover.md, rewritten by Argon, was corrected: its architecture, commands and deployment named
  files, options and a systemd service that do not exist (pipeline/tag_articles.py, whole_record_readers.json,
  speech_overrides.json, resegment.py --save-maps/--apply-maps, travaux.service on port 8781), and some quality figures that
  are not in the record (page audits "R80/R91/R96/R102/R106 64-65%", "150 tests"); the VM runs the Docker container as before.
- Preregistered (2 Nov, the user: check round 124): round 128, a blind check of the speaker changes of rounds 121-127 (in
  practice 123-124, made without a blind check). Population: speech and chair segments whose speaker or delegation differs
  between the database before round 120 (scratchpad copy, same ids and texts) and today's: chair turns named where they had no
  name 1,947; chair turns renamed 108; speeches with another speaker 184; speeches given a speaker 105; speeches with another
  delegation only 34 (2,378). Sample (seed 128): 16, 6, 8, 6, 4 from these strata. Each item: the record's masthead, its notes
  on who takes the chair, and the stretch from 12 segments before to 3 after, with every speaker and delegation field hidden;
  two blind judges (opus, sonnet) say who speaks (for a chair's turn: who presides), surname and delegation, or that the page
  does not tell; a third (opus) where their surnames differ. An attribution is right when the agreed surname matches it
  (fuzzy, ratio >= 85) and, for a speech, the delegation too. Reported: right per stratum with Wilson intervals, weighted by
  the population; better/worse against the old attribution. Gate: at least 90% right weighted; on failure the stratum or rule
  behind the wrong ones is reverted.
- Round 128, result (2 Nov): gate missed; the rule behind the wrong ones reverted. 40 judged (11 judges, about 0.8 million
  tokens; eval/round128). Speeches with another speaker 8/8 right, speeches given a speaker 6/6, delegation only 3/4 (Mrs.
  Roosevelt given "United States of America" where she spoke as Chairman of the Commission on Human Rights), chair's turns newly
  named 13/16 (one wrong, CASSIN where the masthead's Chairman is ROOSEVELT; two the judges could not settle from the masthead
  given), chair's turns renamed 3/6 (AMJAD ALI scored right by hand: the automatic name match missed "Ali"; the 3 wrong are turns
  round 124 left without a name, KASLIWAL, NOSEK, CISELET, which the judges confirm). Weighted by the strata: 84% counting the two
  unsettled as wrong (gate 90%), 92% over the settled. The 29 chair's turns round 124's rules left unnamed in 8 opening
  meetings (A/C.3/SR.458, 484, 575, 576, 685, 906, 1060, 1136) get back the masthead's chairman they had before
  (data/gazetteer/chair_kept.csv, applied in api/build_db.py after chairs.assign only where a turn is still unnamed): named chair's
  turns 7,764 -> 7,793 of 7,877 (98.9%). The rest of round 124 stays: every stratum where the judges could decide is at 93-100%.
  Not reverted, for the author to decide: the one CASSIN turn and the Roosevelt delegation. Tests 141; speaker_eval 128/128,
  49/49, 29/29.
- Preregistered (2 Nov, the user: the pre-publication steps in order): round 129, a fresh full audit after rounds 110-128, the
  design of round 109 unchanged so the figures compare, plus speakers on the page images (last measured in round 67). (1)
  Tags: eval/audit_sample.py --round 129 (default sizes: tagged speeches per kind of record, 30 report paragraphs, 10
  L-series apart, 50 R1 and 60 R2 untagged speeches for coverage); round 69's prompts and judges (opus; sonnet "be strict";
  opus on splits), batches of about 25; eval/audit_record.py, then eval/quality_audit.py publishes round 129 in place of
  round 109; wrong tags to tag_rejections.csv. (2) Topics: 20 at random from each group (p >= 0.9; accepted 0.8-0.9;
  accepted 0.7-0.8; seed 129), round 70's prompt, two judges and a third on splits, weighted by the groups' sizes. (3) Pages:
  eval/segment_audit_sample.py --per 12, seeds 129 and 1290 (120 page images), round 109's reader instructions, one opus
  reader per 10 pages; pages without error, errors by class, turns inside another, against round 109 (77/120, 64, 7 of 412).
  (4) Speakers: eval/speaker_audit.py sample --per 30 --seed 129, two readers of the page image per item (opus, sonnet) who
  do not see the database's answer, a verifier on disputes, eval/speaker_audit.py record --round 129; against round 67 (96%).
  No gates: measurements, to be published on the About page. Expected cost about 6-8 million tokens.
- Round 129, result (2 Nov; eval/round129). 79 agents for the tags, topics, pages and speakers, plus one verifier; about 6.5
  million tokens. (1) Tags: 126 of 133 right, 94.6% +/- 3.7 weighted (round 109: 95.3% +/- 3.5); reports 29/30; coverage 86%
  within records with tags and 84% overall (round 109: 91%, 86%; pooled over rounds 69, 109, 129: 87%, 82%); misses: no
  article context 17, Jev 5. The 9 wrong items (7 speeches: procedure, a ratification-count amendment under the signature
  article, a Declaration article taken for the Covenant's in the Geneva plenary; 1 report paragraph; 1 L-series footnote)
  refused; speeches with an article 12,935 -> 12,928. (2) Topics: 18/20 at p >= 0.9, 19/20 accepted 0.8-0.9, 19/20 accepted
  0.7-0.8; 91.6% weighted (round 109: 93%). (3) Pages: the two seeds overlap on 3 pages, so 117 pages: 82 without error (70%;
  round 109: 77/120, 64%), 63 errors (other 21, missed turn 14, text missing 14, head or foot 4, other column 3, wrong
  speaker 3, wrong kind 2, false split 1, wrong delegation 1); turns inside another 14 of 517 (2.7%; round 109: 7 of 412,
  1.7%). (4) Speakers on the page images: 147 of 150 (98.0%; round 67: 96%): every stratum 30/30 but the 1946-48 plenary
  27/30 (YAZICR for YAZICI, BATACUZR for BALAGUER, a line of a members' list taken for a speech); weighted by the strata's
  speeches about 99.9%. The About page shows the speaker and page figures; data/gold/audit.json the tags. Tests 141.
- Preregistered (2 Nov, the user: the publication audit, by himself, tomorrow): round 130, the publication audit by a person.
  eval/pub_audit_sample.py --n 150 --min 10 --seed 130 (database of round 129, checksum cc4c78cf; the items now shuffled, so
  an annotator who stops early leaves a random sample of every stratum), annotated in eval/pub_audit.py by the author alone on
  the scans, every field (boundaries, speaker, delegation, page, article, topic, page furniture) as docs/audit_guide_pl.md says.
  Reported per field, weighted by the strata's speeches, with Wilson intervals, for however many items are done (at least 100
  planned); compared with the model audits of round 129 on the fields both measure. No gate: the measurement for the dataset's
  description. A second annotator (the student) may later judge some of the same items, for agreement. (The draw gave 165
  items: the minimum of 10 lifts the three small strata.)
- 3 Nov (the user: the About page says too much; be transparent without undermining or overwhelming): About rewritten. The main
  page (about 900 words, was 3,700) has what a user needs, in this order: what it is and that it is not the UN's; read with
  care (paraphrase, machine-read text, final numbering and the tags' error rate, speech boundaries, the missing amendments,
  the translations); how reliable it is (one table: speakers 98%, speech boundaries 97% of turns, tags 95% and about 84%
  coverage, topics 92%, OCR), with a note that model judges measured it and a check by people is under way; what is in it;
  how it is made, in one paragraph that says AI models built it under the author's direction with every change measured
  blind; a link to the AI-assistant instructions; acknowledgements, licence, citation. The detail moved, unchanged in
  substance, to two pages of the About view: #view=about&part=methods (every quality figure, how each layer is made, the
  sources, the build ledger, the model benchmark, what went wrong) and #view=about&part=mcp (old #sec=mcp links land there).
  Argon's errors corrected on the way: the general-debate topic keys on the MCP page and in the travaux-research skill
  (pol_rights, federal_colonial, economic_social do not exist; the nine real ones listed); the skill's list of French-only
  documents (invented symbols; the database's 11 listed), its OCR figure ("0.5% across 22,443 pages", never measured) and its
  draft-numbering examples (UDHR 18 was article 20 of the Drafting Committee's June 1947 draft, not 14; ICCPR 19 was article 14
  of the 1951 draft, not 1950); "100.0% speaker attribution" in the skill and the MCP server's description; in
  docs/quality_audit.md, "raised non-speech tag precision above 94%" (never measured), "verified speaker and delegation" and
  "verified" dates (not checked by a second reader), and the precision figure dated. "How it is made" now says the vision model
  read the pages (it described only the OCR engines). Ten French-only documents -> eleven (A/C.3/L.1355 was added on 21 Oct).
- 4 Nov (the user: a second annotator, the second annotator, on the AMU server behind a password; part of her items shared, part new): round
  130's second set, eval/pub_audit/round130b/items.json: the first 40 items of the author's set (in his order, so that both
  judge them: agreement between two people) and 120 new ones (eval/pub_audit_sample.py --n 130 --min 8 --seed 131, those
  already in round 130 left out), 160 in all; reported like round 130, and the 40 shared items as agreement per field (the share
  of equal answers and Cohen's kappa). The panel runs on the VM in a container of its own (deploy/docker-compose.yml, service
  travaux-audit, profile "audit"), passed through by api/server.py at /audit/ (TRAVAUX_AUDIT_URL), so it sits behind the
  site's tester login and its own password (AUDIT_PASSWORD in the VM's .env, not in the repository; a form, then a cookie);
  its files, the 481 scans of the sample and the answers are in /mnt/data2/travaux/audit, outside the bundle. eval/pub_audit.py:
  relative addresses, HOST, AUDIT_OCR, AUDIT_PASSWORD (it will not serve beyond the machine without one).
- Preregistered (4 Nov, the user: semantic search with the paid Voyage API, compared with what we have, on the travaux that the
  ICCPR and ICESCR commentaries cite): round 131, a retrieval benchmark. Material: the notes of Nowak's CCPR Commentary (2005;
  the book wiki's OCR) and of Saul, Kinley and Mowbray's ICESCR Commentary (2014; OPIL print) that cite a meeting record we
  hold (eval/semantic_extract.py: Nowak 304 notes, Saul 280). A model (sonnet) restates the claim each note supports as the
  query a researcher would type (6-25 words; no symbol, meeting number, date or page; the books' text and the queries stay in
  eval/private/semantic/, only counts and scores leave it); notes that support no claim about the drafting are dropped by the
  model, with a reason. Relevant: the cited records; for the pinpoint score, the segments of a cited record that hold the cited
  paragraph (§ n, [n]) or, in the typed records (E/CN.4/...), the cited page ±1 (the printed pages of A/C.3/SR are not ours).
  Units: every segment of kind speech, chair, vote, procedural and paragraph, embedded as "symbol, speaker (delegation): text".
  Systems: (1) the site's search as it is (api/server.py fts_query and bm25 weights); (2) BM25 over the same index with the
  query's words joined by OR (the lexical baseline a semantic search must beat); (3) voyage-3-large; (4) voyage-law-2; (5, 6)
  each of the two fused with (2) by reciprocal rank fusion (k = 60); (7) (5) re-ranked by Voyage rerank-2.5 on its top 100.
  Nothing is tuned on the queries. Scores per set and pooled: record Hit@10 (primary: a top-10 segment comes from a cited
  record), Hit@1, MRR@10, pinpoint Hit@10; differences by paired bootstrap (10,000) and McNemar. The cited record is only one of
  the places a claim can be checked (a vote is also in the report), so every score is a lower bound, the same for all systems.
  Gate for proposing semantic search on the site: the best Voyage system beats (2) on pooled record Hit@10 by at least 10 points
  with the 95% interval above 0, and is not below (2) on either set. If it fails, it is a negative and the site stays lexical.
  Cost cap 10 USD (the corpus is about 11M tokens). Deployment would send each query to Voyage: the About page would have to
  say so, and it is the user's decision.
- Round 131 amended before any dense result was seen (4 Nov, the user: voyage-3-large is the larger and newer model and did
  better in UNHRDB's benchmarks): voyage-law-2 left out, so systems (4) and (6) are not run; the gate's "best Voyage system" is
  among (3), (5) and (7).
- Round 131 results (4 Nov; eval/round131/results.json; eval/semantic_bench.py; voyage-3-large 10.2M tokens, rerank-2.5 15.6M,
  about 2.60 USD). 579 queries (Nowak 300, Saul 279; 1 dropped by the model, 4 left out because two Nowak pages shared a
  running head and so an id); pinpoint scored on 279 + 16 of them. Record Hit@10, pooled: the site's search 0.7% (it finds
  nothing for 538 of the 579, since every word must be in the segment), BM25 with OR 48.9%, voyage-3-large 81.0%, RRF of the two
  69.6%, RRF re-ranked by rerank-2.5 81.9% (Nowak 75.0%, Saul 89.2%). Hit@1 21.6 / 38.9 / 31.8 / 55.3%; MRR@10 0.29 / 0.52 /
  0.43 / 0.64; pinpoint Hit@10 24.8 / 53.2 / 44.1 / 59.7%. Re-ranked against BM25-OR: +33.0 points pooled (95% interval
  +28.8 to +37.0; 198 queries only it finds, 7 only BM25 finds; McNemar p < 0.001), +36.3 on Nowak, +29.4 on Saul: the gate is
  passed. The plain fusion is worse than the dense search alone (BM25's misses pull good dense hits down); the re-ranker
  recovers it and puts the right record first far more often. By kind of claim (Hit@10, BM25-OR -> re-ranked): positions 51 ->
  88%, drafting changes 39 -> 69%, votes and decisions 35 -> 70%, quoted words 73 -> 92%. Limits: the queries were written by
  a model from the commentaries, longer (median 20 words) than what people type into a search box, and a model's paraphrase may
  suit a model's embedding; the cited record is one place among several a claim can be checked, so every figure is a lower
  bound. Nothing is deployed: a semantic search on the site would send each query to Voyage, and that is the user's decision.
- Preregistered (4 Nov, the user: does semantic search still help with the short queries people type?): round 132. The 579
  claims of round 131, each restated as a short query of 2-5 words, as typed into a search box (a model, sonnet, from round
  131's query alone, not from the books; no quotes or operators; a country may be named). Same units, relevance and scores
  as round 131, plus (8) the site's search falling back to (2) when it finds nothing (the change proposed whatever comes of
  Voyage). Gate for proposing a "search by meaning" mode: (7) beats (8) on pooled record Hit@10 by at least 10 points with
  the 95% interval above 0. If it does not, the site gets only the fallback.
- Round 132 results (4 Nov; eval/round132/results.json): a negative for semantic search. The 579 short queries (median 4
  words, 2-7). Record Hit@10, pooled: the site's search 44.9% (finds nothing for 53), with the fallback to BM25-OR 46.6%,
  BM25-OR alone 22.5%, voyage-3-large 29.9%, RRF 28.3%, RRF re-ranked 25.9%. The re-ranked system is 20.7 points below the
  fallback (95% interval -25.2 to -16.2; Nowak -20.0, Saul -21.5): the gate fails, and the site gets only the fallback.
  Hit@1: the site 17.1%, re-ranked 9.8%. With a few keywords every word in the segment is the strongest signal; the
  dense search, given little meaning to work with, ranks segments on the same general subject as high as the cited one.
  Read with round 131: Voyage wins by 33 points when the query states the claim in a sentence and loses by 21 when it is
  a few keywords; the fallback helps both (+1.7 points here, +48 there over the site's search as it is).
- 4 Nov (the user: a new tab Ask, after HUDOC Researcher's Semantic Search; then a tour and usage counts as on HUDOC Researcher
  and UNHRDB): Ask (api/server.py ask(), POST /api/ask; site/ask.js) runs round 131's system (voyage-3-large over the 69,193
  segments, fused with BM25-OR, re-ranked by rerank-2.5), with six example questions, a hint toward Search for two to four words
  (round 132), identical texts shown once, at most 1,000 questions a day sent to Voyage; deployed on the VM (numpy in the image,
  the vectors in /mnt/data2/travaux/data/vectors, the key in the VM's .env, the container's memory 1 GB; smoke 22/22). A tour
  (site/assets/tour.js; five slides; opens once on a first plain visit, again from the footer's ✦ Tour). Usage counts
  (site/assets/analytics.js): GoatCounter without cookies or a script from another site, one count per view opened with the
  view's name only (/travaux/<view>) to the shared lszoszk site; Google Analytics only when a measurement ID is set and the reader
  allows it in a banner (none set yet); the anonymous "Who are you?" once; nothing under Do Not Track / GPC, for automated
  browsers or off the production host. The About page's privacy paragraph says all of it and shows the choice made.
- 4 Nov, later (the user: create the GA4 property; add Travaux's searches to the usage dashboard): GA4 property "Travaux"
  (562278529, account lszoszk; web stream "Travaux (AMU VM)", measurement ID G-06P7TEY291) with enhanced measurement switched off
  (it would send outbound link clicks, the UN documents a reader opens); only page_view with the view's name, after consent.
  The ID is in deploy/site_config.json (not in the repository) and on the VM. The dashboard's service account (ga-reader@...)
  reads it as a Viewer. On the VM, ~/traffic-stats (backups *.bak-20261104): search_stats.py counts Travaux's searches from the
  nginx log like UNHRDB's (searches, people, zero results, filters used, queries at least 3 people searched in a week, steps:
  opened a record, article page, Ask, export; Ask's question is a POST and never in the log), build_dashboard.py lists Travaux
  among the search apps, config.json has the GA4 property.
- UVA file check (4 Nov, the user: E/CN.4/SR.98/Corr.1 holds the text of A/C.3/SR.289; eval/uva_identity_check.json): the one document pipeline/uva_fetch.py fetched (30 Sep) took the file linked from its UVA item page, and UVA's own page /node/1779 (E/CN.4/SR.98/Corr.1, session 5th, '5 p.') links A-C_3-SR_289.pdf, while the file named E-CN_4-SR_98-Corr_1.pdf is linked from /node/1720 (E/CN.4/SR.153, '1 p.'): UVA's item-to-file links are shifted (of its 469 Covenant items with a symbol and a file, 12 link a file named after their own symbol), its file names are not; the ODS miss that sent the symbol to UVA is not in the log (uva_fetch.py replaced the entry). The other 21 UVA documents (25 Sep, fetched by file name) all match on page 1 (meeting number in words, date and weekday; E/CN.4/SR.249's blurred '1? May' is Friday 18 May). The record duplicates A/C.3/SR.289 under a wrong symbol, date (1950-10-19) and session (11 segments: 5 speeches and a chair's turn, one tagged ICCPR 18 that the ODS copy's speech does not carry). Proposed fix: download E-CN_4-SR_98-Corr_1.pdf from UVA (40,585 bytes, HEAD only so far; the user's yes needed) and keep it only if page 1 reads E/CN.4/SR.98/Corr.1, otherwise drop the record from uva_extra.json and list the symbol as missing (the About page's 22 UVA documents then become 21); uva_fetch.py to take a file by its name, never the node link, and to check page 1 before a file enters the database. Nothing in the data changed yet.
- E/CN.4/SR.98/Corr.1 replaced (4 Nov, the user: download it): UVA's E-CN_4-SR_98-Corr_1.pdf (40,585 bytes, 1 page) reads on page 1 'E/CN.4/SR 98/Corr.1, 15 June 1949', the Commission's corrigendum to the summary record of its 98th meeting (24 May 1949), a substitute text for page 8; OCR'd (layer, tess6, tess3, vision, vote), segmented (1 procedural segment, as Corr.2), harvest_uva_extra.json updated with a note. Entries keyed to the 11 old segment ids dropped, since their text (A/C.3/SR.289, held from ODS with the same topics) is not in the new file: the reader tag ICCPR 18 on Baroody's speech, one accepted topic, one round-70 topics gold item, 9 cached Jev answers, and 6 Ask vectors (ids renamed 'stale:', so they drop out of Ask until re-embedded). The rebuilt database differs from the previous one only in this record (documents row now 5th session (1949), 1949-05-24, 1 page, the new URL; 11 segments, 7 references and 4 topics out, 1 segment in; every other row of every table the same); 142 tests pass. pipeline/uva_fetch.py now fetches the file named after the symbol, never the node page's link. Not done: the VM still serves the old record until the next deploy; the new segment has no Ask vector; Baroody's speech in A/C.3/SR.289 has no article tag (the readers' ICCPR 18 was given to the duplicate only).
- Ask index after the replacement (4 Nov, the user: add it to Ask through Voyage): the new segment e_cn.4_sr.98_corr.1-0001 embedded with voyage-3-large as eval/semantic_embed.py does (325 tokens, logged in data/logs/voyage_usage.jsonl); the 6 vectors of the duplicate's old segments removed; data/cache/vectors/voyage-3-large now 69,188 rows (was 69,193), every id in the database. A local Ask for the corrigendum's words (a policeman firing on someone who throws a harmless substance into the water) ranks it 2nd, after the E/CN.4/SR.98 passage it corrects. The part files no longer add up to vectors.npy (eval/semantic_embed.py would ask for a fresh run). Not on the VM: its database and vectors are those of the last deploy.
- Deployed (4 Nov, the user: deploy): bundle built and checked (0 problems; against the VM only eval/what_went_wrong.md and site/config.js's time changed), the database (md5 31f441bc...) to /mnt/data2/travaux/data and the Ask vectors (69,188 rows) to its vectors/voyage-3-large, the old ones kept as travaux.sqlite3.bak-2026-11-04 and vectors/voyage-3-large.bak-2026-11-04; container rebuilt, healthy, smoke 22/22, the outside address 401. On the VM E/CN.4/SR.98/Corr.1 is the 1949 corrigendum (5th session, 24 May 1949, 1 page, UVA's file) and Ask ranks it 2nd for its own words.
- 4 Nov, the publication-readiness gaps against UNHRDB and HUDOC Researcher (the user: points 5-10, and E/CN.4/SR.98/Corr.1 to
  the VM): the corrected database (6699e7fd) and vectors (69,188) deployed. (5) Monitoring: ~/traffic-stats/health_probe.py asks
  Travaux's container directly every 5 minutes (health, a rotating search; through nginx once the password goes), and the
  dashboard's health panel lists it; Ask is not probed (each question is paid). (6) Backups: deploy/backup_vm_audit.sh on the VM
  (cron 03:40) keeps a dated copy of the publication audit's answers for 90 days; deploy/backup_to_vm.sh copies to the VM what
  exists only on the laptop (a git bundle of every branch, the untracked files, data/ without the page images, eval/private) and
  brings the audit copies back. (7) The page's metadata: og:image (deploy/social_card.py renders site/assets/social-card.png:
  the speeches of each year 1946-66), twitter large card, canonical, JSON-LD Dataset, and site/llms.txt, robots.txt, sitemap.xml,
  their address written by deploy/build_bundle.py. (8) "What is new" (#view=about&part=news), linked from About; a draft tool page
  for lszoszk.github.io (_tools/travaux.md, published: false, in that repository, not committed). (9) tests/test_e2e.py: six
  browser tests (Playwright, WebKit; search, record and Back, a record from another view and Back, Ask's examples and its message
  when off, the tour, About's privacy choice and What is new, no counting off the production host); they found that Ask's error
  showed in capitals (now plain text). Tests 149. (10) The API compresses text for browsers that accept gzip (facets 280 KB ->
  33 KB), /api/quality is memoised (650 -> 6 ms), and the server warms the facets, the quality page and Ask's vectors at start.
- 4 Nov, before publishing the code (the user: a public repository and a DOI): every blob of the 449 commits scanned. No secret
  (API keys, the panel's password), no path under private/, no .env or PDF ever committed. 12-word shingles shared with Nowak's
  and Saul/Kinley/Mowbray's commentaries: 9,598, of which 8,908 are in the database's UN text and the rest in older versions of
  covenants_final.json (the OCR of A/RES/2200's annex): treaty text both books quote, none of their prose. But the tracked files
  hold the full text of 6,507 of 24,354 speeches (27%: evaluation samples, gold sets). The user's decisions: a new public
  repository without history (code, tests, method documentation, aggregate results; the samples with record text, the gold sets
  and the internal documents stay in this repository, which stays private), and Zenodo gets the code only (the corpus stays
  behind the API and MCP). The article page's documents shown as a dated list (they ran together).
