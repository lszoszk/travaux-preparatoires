# The vision-reader pilot: plan (16 October 2026)

Status: approved, deferred to about 30 October 2026, when the API credits renew. Before that, the free local arm
(Chandra OCR 2 on Apple MLX) is benchmarked on the 60 Schabas pages of block B. No further rule rounds meanwhile.

Local arm, installed 16 October 2026: mlx-vlm 0.7.8, mlx 0.32.4, model `1qh/chandra-ocr-2-oq5-mlx` (community 5-bit MLX
build of Chandra OCR 2, ~3.7 GB, in the Hugging Face cache). Smoke test, E/CN.4/SR.1 p. 2 (`eval/vlm_local_bench.py`):
model loaded in 4 s, the page read in 69 s (550 tokens) on the M3 Pro; at that pace the 12,270 record pages would take
about ten days of continuous work. The reading is HTML with layout labels (`Page-Header`, `Text`; the catchword
"/to doubt" in a block of its own), paragraphs joined into one line each, and visibly cleaner than the vote on the same
page ("genocide to be" for "geuocive to ba", "resolution" for "rysolution"). Next: strip the HTML to text keeping the
labels, then CER on block B against Schabas.

Development set, 16 October 2026 (`eval/vlm_pilot/dev_set.json`, seed 7: 20 pages of seven documents with a Schabas
reference, excluded from the preregistered sample; `eval/vlm_local_dev_cer.py`, the method of `eval/ocr_bench.py` on
these pages only; result in `eval/vlm_pilot/dev_cer_chandra.json`):

| Group | Pages | Characters | vote | tess3 | Vision | layer | Chandra (local) |
|---|---|---|---|---|---|---|---|
| 1947–48 typed summary records | 13 | 20,577 | 2.51% | 3.96% | 6.90% | 4.23% | **0.41%** |
| 1948 printed, EN/FR columns | 3 | 7,930 | 2.74% | 1.83% | 3.90% | 16.19% | **0.93%** |
| 1947–48 typed documents | 4 | 1,139 | 2.11% | 0.88% | 23.88% | 4.39% | **0.70%** |
| All | 20 | 29,646 | 2.56% | 3.27% | 6.75% | 7.44% | **0.56%** |

About 85 s a page (59–116 s; the printed pages and long documents are the slowest): the 12,270 record pages would take
about 12 days of the laptop. On the bilingual printed pages the model reads both columns (the French with the English),
as the vote does before the segmenter drops French lines; the CER does not see the extra column, so the guard's length
test and an English-only step are needed before its text can be used. No check for invented text has been made yet.
These are development results, reported apart from the preregistered test.

**The readers of disputes, checked against the reference (development set 1).** `eval/vlm_disputes.py` aligns the local
model's reading with the OCR vote word by word: 386 disputes on the 20 pages, only one of them an insertion no OCR engine
has. 151 of them (up to 8 a page, seed 5) went blind, as A/B in random order, to readers of the page image
(`judge_dev1.json`, a Workflow). Where the reference decides the dispute (118 of 151), the readers agreed with it 104 times
(88%). Of the 14 disagreements about 9 are errors of the automatic match with the reference, not of the readers (Schabas
omits running heads, footnotes and the French column, where the readers were right), and about 4 are the readers' known
bias: a worn typewriter "e" that looks like "o" read literally ("Tho", "cf"). The readers' verdicts overall: the local model
right 136 times, the vote 8, neither 7. So the readers can stand in for a reference on pages without one, with that bias
noted (`disputes_dev1.json` keeps both verdicts per dispute).

**Development set 2: kinds of page without a reference** (`dev_set2.json`, seed 17, 62 pages excluded by page from the
preregistered sample; 61 read, one has no image). Disputes found by `vlm_disputes.py`, up to 6 a page judged blind on the
scan (282 in all: the local model right 219 times, the vote 42, neither 20); from the share of each verdict and the number of
disputes, the estimated words read wrong per 1,000 (`disputes_dev2.json`, field `estimate`):

| Kind of page | Pages | Words | Disputes | Vote wrong / 1,000 words | Local model wrong / 1,000 words |
|---|---|---|---|---|---|
| CHR typescripts 1949–54 (half from the lowest third of OCR agreement) | 14 | 4,552 | 200 | 39.9 | **6.7** |
| pages with the lowest OCR agreement (< 0.3) | 10 | 1,952 | 239 | 120.3 | **21.9** |
| plenary pages (E/PV.84 of 1948; A/PV.1496 of 1966) | 8 | 7,038 | 150 | 20.0 | **1.8** |
| A/2929 (1955, tables and letter-spaced type) | 6 | 1,506 | 97 | 52.3 | **18.1** |
| L-series | 8 | 1,480 | 63 | 35.6 | **9.9** |
| Third Committee printed 1950–61 | 8 | 6,232 | 25 | **1.7** | 2.3 |
| Third Committee printed 1962–66 | 8 | 7,957 | 13 | 0.9 | 0.8 |

So the gain is where the typescripts are: about six times fewer wrong words on the CHR records of 1949–54, five to ten times
on the plenary and the worst pages, three to four times on A/2929 and the L-series. On the clean printed Third Committee
records of 1950–66 the present OCR is already as good (1–2 wrong words per 1,000) and the local model brings nothing.
The model read the two English columns of every printed page whole and in order (`in_order` ≥ 0.96 on all 16).

Faults found: (1) a page cut short at the token limit (A/C.3/SR.904 p. 3, a back cover listing sales agents in three
columns): the reader now detects it and reads the page again with twice the room; (2) descriptions of pictures the model
writes in ("The emblem of the United Nations featuring a world map...", label `Image`, 10 blocks): now dropped with the
running heads; (3) 30 insertions no OCR engine has, most of them real text the engines missed (table cells of A/2929,
footnotes, French lines of the plenary) and the two picture descriptions; no invented sentence was found by the coverage
check of the six pages whose reading length departed most from the vote. One page drawn as "worst" is in Chinese
(A/C.3/L.1221, the Chinese version): read correctly; the corpus has a few such pages. Speed by kind of page: 67 s (L-series)
to 124 s (the dense plenary pages) a page.

## The pilot and the decision

## Context: the verdict on the current approach

The user asked whether the round-by-round rule work is a dead end and whether a vision model (Opus 5.5) could not simply
read the scans. The measured answer, from the project's own files:

- **The random-sample quality has been flat since round 76.** Fresh audits of 120 random pages (rounds 76/80/84/92/99):
  pages without error 53/65/71/78/67; missed turns 25/31/29/22/28; speeches inside another 4.8–7.0%, never under the 2%
  aim. The paired audits always looked good (653→441 errors over 12 rounds) because they score the pages each rule was
  written for; round 99 found 69 of its 77 located errors on segments no rule since round 93 touched.
- **pipeline/segment.py grew from 219 to 1,468 lines (~175 regexes, a 28-branch loop)** with no new unit test since round
  80. The speaker evals that pass at 1.000 are 206 speeches from 13 records of 1946–50 and cannot fail on the code added since.
- **Rounds 85–99 took one day, ~11,000 model turns and ~830M cache-read tokens**, which is roughly the price of a
  vision pass over every meeting-record page in the corpus.
- **OCR quality is measured only for 1947–48** (vote CER 1.4% against Schabas; typed records 1.5%, printed 0.9%);
  1949–66 (two thirds of the pages) was never measured and no per-page quality flag exists. On a later batch of typed
  documents the four-engine vote (4.1%) gained nothing over Tesseract alone (4.0%). The remaining segmentation errors are
  OCR garbling of the structural cues themselves ("Me. PICKFOR)", "CPAJRM{N", "Mo, MALIK", paragraph numbers read as
  words, specks and catchwords read as text), which is why more regexes rarely reach a random page.
- **No vision model has ever been tried as a reader here**; yet three Opus annotators reading the 40 gold scans agreed on
  37/40 pages and found more than the rules (DB against them: start recall 0.878, precision 0.964).

The 2026 literature agrees on the direction and on the risk: vision models beat Tesseract by 3–10× in CER on degraded
historical print (Gemini 3.5 Flash 2.2% vs Tesseract 20.9% on early-modern print, "Reading the Archive by Machine", 2026),
but their characteristic failure is fluent fabrication and normalization that CER hides, worst on named entities (arXiv
2607.24077). Typewritten archival scans are the weakest category of every specialized OCR model (olmOCR-Bench "old
scans": best 50/100). Opus is untested on exactly this material. So: a pilot with a hallucination guard and a hard gate,
not a leap.

Decisions taken by the user: pilot first (200–300 pages), decide after with numbers; goal is **text and segmentation at
once** (the model returns the transcription and the turn structure), the existing OCR kept as a hallucination guard; the
pilot runs through the API with the user's Console key (in `travaux/.env`, gitignored, loaded like `pipeline/jev.py`
loads `TYPESAFE_API_KEY`; never printed, never committed).

Hard constraints: M3 Pro, 18 GB RAM, **22 GB free disk** (no local 7B model, no new images on disk: JSON only); all
processing local except the API calls; no publication; commits local only, explicit `git add` paths.

Verified interfaces to reuse: `pipeline/segment.py` `load_lines(symbol, engine)` and `segment_record(symbol, engine)`
take an engine directory name; `pipeline/vote.py` `vote_page(texts: {engine: text}, pivot)`; `pipeline/resegment.py`
`ENGINE = "vote"`; `eval/ocr_bench.py` `norm`, `ref_segments`, `locate`, reference files
`eval/private/reference/<sym>.json` with `pdf_pages` and `pages`; `eval/segment_audit_sample.py` `stratum()`;
`eval/gold_pages_build.py` `starts_on_page()` and the page-item format; `eval/gold_pages_merge.py` (3-reader majority);
`eval/segment_gold_eval.py` (metrics). API facts verified today: `claude-opus-5-5` $4/$20 per MTok, `claude-sonnet-5-5`
$2/$10, Batches 50% off; images on Opus 5.5 up to 2576 px long edge / 4,784 visual tokens (tokens = ⌈w/28⌉×⌈h/28⌉; a
page pre-shrunk to 1568 px costs ~1,560); structured outputs via `output_config.format`; thinking always on (use
`output_config.effort = "low"`); `fallbacks: "default"` for refusals on live calls only.

## Pilot design

### 1. `eval/vlm_pilot_sample.py` → `eval/vlm_pilot/sample.json`
300 pages, item shape as `eval/gold_pages/pages.json` (`id, stratum, symbol, page, image, lines, starts`) plus `block`,
`cell`, `score` (chosen engine's score from `selection.json`), `two_column`, `reference` (Schabas original page via
`pdf_pages`, when one exists). Fixed `--seed 2026`.

| Block | n | Purpose |
|---|---|---|
| A gold | 40 | the existing gold pages: segmentation metrics against the 3-reader majority + the 6 hand pages |
| B reference 1947–48 | 60 | per-page CER vs Schabas: 20 typed records, 20 typed documents, 20 printed EN/FR two-column (A/C.3/SR 1948); 15 of the 60 from the lowest score decile |
| C 1949–66 | 170 | no reference: CHR 1949–54, TC 1950–61, TC 1962–66 × score tercile for single-column pages (9 cells × ~14) + 45 two-column pages (score meaningless there) |
| D worst | 30 | single-column pages with score < 0.5, any year, not already drawn |

Ground truth for C+D segmentation: the existing 3-reader annotation Workflow (image + vote lines, same prompt as the gold
set), merged by `gold_pages_merge.py` with two new flags `--pages` / `--out`; disputed pages (~8% expected) decided by
hand in `eval/annotate_pages.py` (gets `--pages FILE`). These 200 pages then join the gold set permanently.

### 2. `pipeline/vlm_read.py` — the reader
One call per page; image loaded with PIL, downscaled in memory to `--long-edge` (2576 default; 1568 arm), PNG base64.
Arms are engine directories so every downstream tool sees them as engines with no change:

- `vlm` = Opus 5.5 @ 2576 (all 300 pages), `vlm-sonnet` = Sonnet 5.5 @ 2576 (all 300), `vlm-1568` = Opus @ 1568 (blocks A+B only).
- Output `data/ocr/<safe_symbol>/<arm>/page-NNN.json` (the structured answer) and `page-NNN.txt` (unit lines joined, furniture excluded, so `load_lines`, `segment_record`, `ocr_bench` work on it). `data/ocr/` is already gitignored.

Request: `max_tokens 8000`, `output_config={"effort": "low", "format": <json_schema>}`, system prompt as one text block
with `cache_control` (verify `usage.cache_read_input_tokens` on the second page; if the ~1.5k-token prompt is under the
minimum cacheable prefix, drop the breakpoint, it costs < $0.01/page). Live calls add
`betas=["server-side-fallback-2026-07-01"], fallbacks="default"`; Batches reject it. On `stop_reason == "max_tokens"`
retry once with 16000; on `refusal` log `stop_details.category`, write `page-NNN.refused.json`, re-run live later.
Modes: `--live` for the first 10 pages (prompt and schema debugging), then `--batch submit|poll|fetch` for every arm
(`custom_id = arm|symbol|page`; results keyed by id, never by position). Every response appends to
`data/vlm_usage.jsonl` (arm, page, input/cached/output tokens, stop_reason, latency, dollars). Expected: ~6.3k input
(4.8k image) + ~3.5k output per page → Opus ~$0.10 live / ~$0.05 batch, Sonnet half; **the whole pilot (700 calls) is
under $60**. Output dominates, so the 1568 arm saves only ~$0.013/page and exists to test whether resolution matters.

Schema (structured output):
```json
{"page": {"columns": 1, "languages": ["en"], "printed_number": "21", "furniture": ["E/CN.4/SR.153", "page 2", "/15. She thought"]},
 "units": [
  {"kind": "continuation", "para": null, "speaker": null, "delegation": null, "lines": ["..."]},
  {"kind": "speech", "para": "1", "speaker": "Mrs. CASTILLO LEDON", "delegation": "Commission on the Status of Women",
   "lines": ["1. Mrs. CASTILLO LEDON (Commission on the Status of Women) explained the", "..."]},
  {"kind": "vote", "para": null, "speaker": null, "delegation": null, "lines": ["The amendment was adopted by 9 votes to 4, with 2 abstentions."]}
 ],
 "illegible_count": 3}
```
`kind` ∈ speech, chair, vote, procedural, heading, closing, continuation (text at the top of a page belonging to a turn
begun earlier: not a start, as in the gold convention). Lines kept as printed so starts can be placed on line indices.
Prompt rules: diplomatic transcription; spelling, capitalisation, punctuation and the paragraph numbers as printed; no
expansion of abbreviations, no correction of the original's errors; **no guessing**: an unreadable character is `⟨?⟩`, an
unreadable word `⟨illegible⟩`; a speaker's name copied letter by letter from the page, never completed from memory;
**two-column pages: if both columns are English (the 1950–66 printed Third Committee records), left column then right
column; if one column is French (the 1948 Official Records), the English column only**; a typed bilingual page: English
passages only, French noted in `languages`; running heads, page numbers, catchwords, stamps, specks go to `furniture`.

### 3. `eval/vlm_guard.py` — the hallucination guard and the per-page flag
Per page: VLM words (NFKC, lower, punctuation stripped) aligned with `difflib.SequenceMatcher(autojunk=False)` to each of
`vote, layer, tess3, vision`; the engine with most matches is the anchor. Opcodes classified: `replace` with
`fuzz.ratio ≥ 60` or a pair from `spellfix`'s confusable table → `ocr_confusable` (benign, the corrections we want);
`replace` below 60 → `substitution`; `insert` of words no engine has within ±5 words → `insertion`, runs ≥ 4 words →
`insertion_run`; `delete` → `omission`; any capitalised VLM token and every `speaker`/`delegation` value with no fuzzy
match ≥ 80 among the capitalised tokens of all four engines on the page → `entity_unsupported`; VLM/vote length ratio
outside 0.85–1.15 → `length`. Per-page divergence = (substitution+insertion+omission)/VLM words. Suspected fabrication =
`insertion_run`, `entity_unsupported` or `length`. **Flag**: `clean` (divergence < 2%, no fabrication marks), `check`
(< 8% or one entity mark), `suspect` (otherwise, or refused, or `illegible_count` > 5% of words). Written to
`page-NNN.guard.json` beside the reading, summarised in `eval/vlm_pilot/guard_<arm>.json`.
`--validate` on block B: every flagged span looked up in the Schabas page with `ocr_bench.locate`; present = a true VLM
correction (false alarm), absent = a real error → guard precision; and recall = VLM words absent from the reference that
the guard did not flag. Accepted if it catches ≥ 90% of unsupported insertions and entity errors. Its `check/suspect`
spans on C+D supply the 150 disputed words for the hand check (`id, line, Opus, Sonnet, vote` triplets, judged on the scan).

### 4. `eval/vlm_pilot_eval.py` → `eval/vlm_pilot/report.json` and the gate table
- Text: per-page CER on block B for `vote`, each arm, and "arm with guard" (a `suspect` page falls back to vote), via
  `ocr_bench.ref_segments/locate/norm` restricted to the sampled pages. C+D: Opus/Sonnet word agreement, Opus/vote
  agreement, outcome of the 150 hand-checked disputes.
- Segmentation (`segment_gold_eval.py` gains `--pages FILE` and `--starts FILE`): (a) current DB, (b) `segment_record(sym,
  "vlm")` = the regex segmenter on VLM text, (c) the VLM's own units placed on vote line indices by word alignment of each
  unit's first line; each against gold-40 majority, the 6 hand pages, and the pilot majority.
- Per arm: cost/page, latency, refusal rate, max_tokens rate, thinking share of output tokens.
- `eval/vlm_pilot/decision.md`: the gate table and the verdict, committed locally (English, like the other docs).

## Metrics and the gate

| Metric | Now | Go | Source |
|---|---|---|---|
| CER typed records, block B | 1.5% | ≤ 1.0%, or at least one third below vote on the same pages (Schabas's own corrections set a floor: the per-segment oracle is 1.0%) | ocr_bench on sample |
| CER printed two-column, block B | 0.9% | ≤ 0.9% | same |
| Unsupported insertion runs absent from the reference | — | ≤ 1 per 100 pages | guard × reference |
| Names (speaker/delegation) wrong but plausible | — | 0 on block B; ≤ 0.5% of names in the C+D hand check | guard, hand check |
| Starts recall (VLM units) | 0.878 | ≥ 0.95 | segment_gold_eval |
| Starts precision | 0.964 | ≥ 0.96 | same |
| Kind / speaker / delegation | 0.994 / 0.981 / 0.981 | ≥ 0.99 / 0.98 / 0.98 | same |
| Furniture lines left in text | 31 per 40 pages | ≤ 5 per 300 pages | same |
| Opus vs 3-reader majority disagreements, C+D, after hand check | — | ≤ 2 per 100 pages | majority.json |
| Cost per record page (batch) | — | ≤ $0.08 | usage log |
| Refusals after fallback | — | < 1% | usage log |

Decision rule: **GO-replace** (VLM text and units primary) if every row passes; **GO-augment** (VLM units for the
boundaries, text stays vote) if segmentation passes but CER does not improve; **NO-GO** if a fabrication row fails,
whatever the rest. Sonnet replaces Opus for the corpus if within 0.2 pp CER and 1 pp start recall. The 1568 arm is
adopted only if indistinguishable on block B. (If the budget question later needs a second provider, the harness is
model-agnostic: Gemini 3.5 Flash led the 2026 archive benchmark and would be the natural extra arm; not in this pilot.)

## Full-corpus phase, sketched (only after GO, a separate decision with the pilot's numbers)
1. **Engine**: `vlm` as a fifth engine directory. Not a voter (four OCR engines sharing the same confusions would outvote
   true corrections): the VLM text is the selected text wherever its flag is `clean` or `check`, `suspect` pages keep
   `vote`; `ocr_select.py` writes choice and flag into `selection.json`; `resegment.py ENGINE = "vlm"`.
2. **Segmenter**: `segment_record_vlm(symbol)` builds segments from units and reuses `finalize`, `mend_numbers`, the
   masthead/date reading; `segment_record` runs only for pages without a VLM reading. What leaves the main path (kept,
   frozen, as fallback): `classify`, `lead_turn`, `debris_turn`, the catchword and running-head rules in `normalize.py`,
   `split_turns`, and most of the ~175 patterns.
3. **Migration**: copy `data/cache` first (the round-98 lesson), `resegment.py --dry-run`, inspect `lost`, then the real
   run; `api/build_db.py` tagging unchanged; the hand files move with the ids as now.
4. **Quality flag**: table `page_quality(symbol, page, engine, flag, divergence)`; `segments.quality` = worst flag of its
   pages; API and site show it and the "check the scan" note on `check/suspect` (the first per-page OCR quality signal
   the project has had).
5. **Order and cost**: the 12,270 record pages first, Batches of ~2,000 (~$600 Opus or ~$300 Sonnet), then reports and
   the L-series (~$300). ~20 KB JSON per page, under 400 MB in all.
6. **What stops now, whatever the pilot says**: no further rule rounds; `segment_gold_eval.py` gets `--min-recall` and a
   pytest wrapper so the gold set guards every change; the gold set grows to 240 pages from the pilot's annotations.

## Risks
- Refusals on 1940s–60s political content: `fallbacks="default"` live, batch refusals re-run live, persistent ones listed, never silently dropped.
- Rate limits: Batches for volume, SDK retries, ≤ 4 worker threads live.
- Disk: no new images, resizing in memory, JSON only.
- Two-column pages: the English-only vs left-then-right rule validated on block B's 20 EN/FR pages and C's 45 two-column English pages; the guard's `length` test catches a column read across or dropped.
- Wholly French documents: transcribed as French and left to the existing machine-translation path.
- Fluent normalization CER hides: the entity and insertion rules, the no-guessing prompt, the hand check of disputes; names decide the gate.
- Thinking-token cost drift: effort low, max_tokens 8000, thinking share logged, alert above 30% of output.
- Correlated readers: segmentation ground truth comes from independent readers of the image with vote lines, not from the VLM arm; text ground truth for 1947–48 is Schabas; the hand check covers the rest.
- The key: read from `travaux/.env` only, never logged or echoed; the usage log holds token counts, not text.

## Verification
1. `vlm_pilot_sample.py --dry-run`: cell counts printed; every page has an image, vote lines and (block B) a reference page.
2. 10 live pages: schema validates, the lines cover the page, cache hits appear, cost per page within the estimate.
3. Batch submit/poll/fetch for each arm; refused and truncated pages listed and re-run.
4. `vlm_guard.py --arm vlm --validate`: guard precision and recall on block B printed.
5. Workflow annotation of C+D, merge, hand decision of disputes; the 150-word hand check.
6. `vlm_pilot_eval.py` prints the gate table per arm; `eval/vlm_pilot/decision.md` written; local commit with explicit paths (`eval/vlm_pilot_*.py`, `pipeline/vlm_read.py`, `eval/vlm_pilot/*.json`, `decision.md`, the gold additions); report to the user in Polish with the table.
