# Preregistration: a vision-language page reader against OCR and rules on the UN human rights travaux préparatoires (1946–1966)

Draft for the OSF Secondary Data Preregistration template, 16 October 2026. To be registered on OSF Registries by the
author, with an embargo until the database is public (the UN Library has not yet approved republication of the records).

**Timestamp.** The state of this preregistration, the sample and the plan at commit `1cad764` was fixed on 16 October 2026,
21:08 CEST, with OpenTimestamps: `eval/vlm_pilot/timestamp/preregistration_2026-10-16.txt` lists the commit, its tree and
the SHA-256 of the three files, and the `.ots` file beside it proves, once anchored in the Bitcoin blockchain, that this
list existed at that time (`ots verify`). Only the hash left the author's computer.

**Author.** Łukasz Szoszkiewicz, Adam Mickiewicz University, Poznań (ORCID 0000-0001-6671-2893).

## 1. Study information

### 1.1 Description
The study compares three ways of turning scanned UN meeting records of 1946–1966 (the drafting of the Universal
Declaration of Human Rights and of the two International Covenants) into a database of speeches: (a) the present pipeline,
in which four OCR engines vote word by word and about 175 hand-written rules divide the text into turns of speech; (b) a
vision-language model that reads the page image and returns the transcription and the turns at once; (c) an open model
run locally that returns the transcription only. The study asks whether (b) or (c) improves the text and the division
into turns, and whether it does so without inventing text, in particular names, which character error rates hide.

### 1.2 Background
The records are typewritten (1946–1954) and printed in two columns (1948–1966). The present pipeline was refined over about
100 iterations of rule-writing; its quality on random pages stopped improving after iteration 76 (pages without a
segmentation error in five audits of 120 random pages: 53, 65, 71, 78, 67), while audits limited to the pages each rule
targeted kept improving. Vision-language models outperform conventional OCR on historical print, but their characteristic
error is fluent invention or normalization of text, most harmful in named entities. Typewritten archival pages are the
weakest category of the specialized OCR models benchmarked so far, and the models tested here have not been evaluated on
such material.

### 1.3 Hypotheses
Confirmatory, each with a decision threshold fixed in advance (section 4.3):

- **H1 (text).** On typewritten summary records with a reference text, the vision-language reader (b) has a lower
  character error rate than the OCR vote (a).
- **H2 (segmentation).** The turns returned by (b) recover more of the turns found by independent annotators than the
  present rules, without a loss of precision.
- **H3 (fabrication).** Reader (b) does not insert text absent from the page, and does not change a speaker's or a
  delegation's name into another plausible name, more often than the thresholds in 4.3.
- **H4 (local model).** The local model (c) has a lower character error rate than the OCR vote (a) on the same reference
  pages.

Exploratory (no threshold): a cheaper model of the same family against (b); the image resolution sent to (b) (2,576 against
1,568 pixels on the long edge); cost and time per page; the agreement of (b) with the annotators on pages without a
reference text.

## 2. Data

### 2.1 Name and source
UN meeting records and documents of the Commission on Human Rights, its Drafting Committee, the Third Committee of the
General Assembly, the General Assembly plenary and the Economic and Social Council, 1946–1966, scanned PDFs from the UN
Official Document System and the UN Digital Library: 2,157 documents, 18,514 page images (300 dpi), 12,270 of them pages of
the 1,291 meeting records.

### 2.2 Reference texts
For 626 documents of 1947–1948 a retyped edition of the records (W. A. Schabas, *The Universal Declaration of Human Rights:
The Travaux Préparatoires*, Cambridge University Press, 2013) serves as the reference for the character error rate. It is
copyrighted and used privately for measurement only; no text from it is published.

### 2.3 Prior knowledge of the data
The author and earlier automated work have examined the data extensively:
- the OCR vote has been measured against the reference on all 626 documents (character error rate 1.4%; typewritten
  records 1.5%, typewritten documents 1.9%, printed pages 0.9%);
- 40 random pages (seed 100) were annotated for turns by three model annotators and, for 6 of them, by the author; the
  present pipeline scores start precision 0.964 and recall 0.878 against them;
- on 16 October 2026, before this registration, model (c) was run on one page (E/CN.4/SR.1, page 2) to test the
  installation, and then on a development set of 19 more pages with a reference text (seed 7: E/CN.4/SR.61, E/CN.4/SR.80
  and E/CN.4/AC.2/SR.7, pages 2–5; E/CN.4/AC.1/9 and A/C.3/214, pages 1–2; A/C.3/SR.110, pages 2–4; listed in
  `eval/vlm_pilot/dev_set.json`), to fix the conversion of its output to text and to measure its speed; these seven
  documents are excluded from the sample, and the results on them are reported separately, as development results;
- on the same day, model (c) was run on a second development set of 62 pages without a reference text, drawn with seed 17
  from the kinds of page the first set does not cover (14 typewritten pages of the Commission on Human Rights 1949–54, half
  of them from the lowest third of the OCR agreement score; 8 printed two-column pages of the Third Committee 1950–61 and 8
  of 1962–66; 6 pages of A/2929; 8 pages of the L-series; 8 pages of the 1946–48 plenary; 10 single-column pages with an
  agreement score below 0.3; listed in `eval/vlm_pilot/dev_set2.json`), to measure its speed and its reading order on these
  kinds of page and to try the comparison of readings on the image that 3.2 uses; these 62 pages are excluded from the
  sample, and the results on them are reported separately, as development results;
- no output of reader (b) has been seen on any page of these records;
- the readings of model (c) on the 60 pages of block B were produced on 16 October 2026, before registration, so that the
  computer's time could be used; no measure was computed on them, and they were not looked at, before registration (the
  files' times and the commit history show it).

## 3. Sampling and the sample

### 3.1 Sample
300 page images, drawn with the seed fixed here (2026) by `eval/vlm_pilot_sample.py` (written and run on 16 October 2026,
before registration; the sample is a deterministic function of the seed and the rules below):

| Block | Pages | Drawn from |
|---|---|---|
| A | 40 | the 40 annotated pages of 2.3 |
| B | 60 | pages with a reference text: 20 typewritten summary records, 20 typewritten documents, 20 printed two-column pages (1948); 15 of the 60 from the lowest decile of the OCR engines' agreement score |
| C | 170 | pages of 1949–1966 without a reference: three series (Commission on Human Rights 1949–54; Third Committee 1950–61; 1962–66) by tercile of the agreement score for single-column pages (9 cells of about 14), and 45 two-column pages; the printed Third Committee records have few single-column pages (44 of 3,348), so their cells hold 25 pages and the rest (57) is drawn at random from the pages of the three series |
| D | 30 | single-column pages with an agreement score below 0.5, any year, not already drawn |

### 3.2 Ground truth
- Text (H1, H4, H3): the reference text, aligned to the page as in the existing OCR benchmark (`eval/ocr_bench.py`:
  segments of the reference of at least 40 characters located in the reading by approximate matching; a segment counts only
  if some reading matches it with a score of at least 88; case-insensitive, running heads removed).
- Turns (H2): for blocks C and D, three model annotators per page reading the image (the same instructions as for block A),
  merged by majority; pages on which they disagree are decided by the author on the image. Block A keeps its existing
  annotation. The annotators are a different procedure from reader (b): they mark turns on the existing OCR lines and do not
  see the output of (b).
- Names (H3): every speaker and delegation that (b) returns on blocks C and D and that no OCR engine supports is checked by
  the author against the image, with 150 disputed words drawn at random from the guard's flags (4.2).

### 3.3 Stopping rule
Every page of the sample is read once by each arm. A page refused by the model or cut by the output limit is read again
once; a page still refused is reported and counted as a failure of that arm.

## 4. Variables and analysis

### 4.1 Arms
(a) the OCR vote of four engines (UN PDF text layer, Tesseract 5 in two layout modes, Apple Vision) and the rule-based
segmenter, as of commit `f0fd62a`; (b) Claude Opus 5.5 through the Anthropic API, one request per page, the image scaled to
2,576 pixels on the long edge, structured output (units of text with kind, speaker, delegation and paragraph number), a
diplomatic-transcription instruction (no correction, no completion of names, unreadable characters marked); exploratory
variants: Claude Sonnet 5.5, and Opus at 1,568 pixels on blocks A and B; (c) Chandra OCR 2 in a community 5-bit MLX build
(`1qh/chandra-ocr-2-oq5-mlx`), run on the author's computer, text only, on block B.

### 4.2 Measured variables
- **Character error rate** per page and pooled by characters, on block B, separately for typewritten records,
  typewritten documents and printed pages.
- **Turn starts**: precision and recall of the starts against the ground truth (a start matches on the same line, within
  15 characters); accuracy of kind, speaker and delegation on matched starts.
- **Guard measures** for (b): the reading aligned word by word with the four OCR readings; insertions of words no engine
  has within five words (runs of four or more words counted separately); names with no fuzzy match of at least 80 among the
  capitalized tokens of all engines on the page; reading length outside 0.85–1.15 of the OCR vote. On block B each flagged
  span is looked up in the reference: present means a true correction, absent an error.
- **Cost and time** per page from the API usage records and the local log.

### 4.3 Decision thresholds
| Hypothesis | Measure | Supported if |
|---|---|---|
| H1 | CER, typewritten records, block B | (b) ≤ 1.0%, or at least one third below (a) on the same pages |
| H1 (printed) | CER, printed pages, block B | (b) ≤ 0.9% |
| H2 | start recall / precision against the ground truth | ≥ 0.95 / ≥ 0.96 |
| H2 (attributes) | kind / speaker / delegation | ≥ 0.99 / 0.98 / 0.98 |
| H3 | runs of inserted text absent from the reference | ≤ 1 per 100 pages of block B |
| H3 | names changed into another plausible name | 0 on block B; ≤ 0.5% of the names checked on C and D |
| H4 | CER of (c), typewritten pages, block B | lower than (a) on the same pages |

For each measure, 95% intervals are computed by bootstrap over pages (10,000 resamples) for CER differences and for recall and precision; a
threshold is met when the point estimate meets it, and the interval is reported beside it.

### 4.4 Use of the result
If H1–H3 are supported, the reader replaces the OCR vote and the rules for the corpus, with the guard's flag kept per page
(the pages it marks as suspect keep the OCR vote). If H2 is supported but H1 is not, the reader's turns are used with the
OCR text. If H3 fails, the reader is not used, whatever H1 and H2 show. A cheaper model replaces (b) if it is within 0.2
percentage points of CER and 1 point of start recall.

### 4.5 Deviations
Any change to the arms, the sample or the thresholds after registration is reported with its date and reason. Results are
reported for every hypothesis, whether supported or not.
