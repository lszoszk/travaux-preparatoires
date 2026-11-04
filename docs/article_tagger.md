# Offline article tagger

Implementation based on repository commit `8efaed6`, on `codex/article-tagger`.
The source database is read through `mode=ro` and `PRAGMA query_only=ON`.
No source segments, identifiers, concordances, or build code are changed.
Private files and `.env` are never read. It reads the **database's public segment table**,
not files in `data/segments`. Existing tags are allowed inputs, including tags that
were originally produced with Jev; the tagger does not import or call Jev.

## Run

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 pipeline/article_tagger.py \
  --db /Users/lszoszk/Desktop/AI/travaux/data/travaux.sqlite3
```

The output is `data/tagger/predictions.csv`, one row for every untagged speech
longer than 150 characters. An empty article and instrument mean abstention.
Scores below 0.5 are withheld; remaining proposals still require the selected
review/integration threshold. Scores on abstentions describe the rejected best
candidate, rather than the probability that abstention itself is correct.

Dependencies: the installed numpy, scikit-learn, torch, sentence-transformers,
and the already installed BGE snapshot
`a5beb1e3e68b9ab74eb54cfd186867f64f240e1a`. Missing model files are an error;
there is no download fallback. `--embedding-cache /tmp/tagger-embedding-cache`
optionally caches embeddings outside the repository, keyed by model revision,
preprocessing version, and the full ordered input text. No cache is required.

## Method and limits

1. Separate Declaration records from Covenant records using document metadata.
   Retrieve seven tagged speech/report examples by word and bigram TF-IDF,
   with sublinear term frequency, English stopwords, and an 80,000-feature cap.
   Select the final instrument/article by the sum of squared cosine similarities.
   Numbers, document symbols, and initial speaker furniture are removed before
   retrieval: draft article numbers are **not** treated as final numbers.
2. Measure strongest matching and competing example, vote share, similarity to
   historical draft texts, same-record and cross-record matches. Check agreement
   with the nearest tagged speeches on both sides, within 12 segment positions.
   A neighboring record never supplies a flank. Only article 1 is normalized
   across the two Covenants; all other instrument distinctions are preserved.
   Explicit joint tags already present in the database follow the scorer’s
   joint-tag matching convention.
3. Resolve cited amendments only if their existing tagged occurrences agree on
   one article. Generic document references and conflicting amendments do not
   provide amendment evidence. Add speech length, procedural vocabulary, and a
   flag for multiple distinct numbered article mentions.
4. BGE-base-en-v1.5 compares each candidate with adopted article texts. Its two
   features are similarity to the proposed article and the margin against the
   strongest other article in the same instrument family. This checks the lexical
   proposal; it does not replace its article. CPU inference uses four threads,
   batches of 32, normalized vectors, and at most 128 tokens per text. Long
   interventions can therefore lose their later substantive argument.
5. Five regularized logistic confidence models predict whether the proposal
   matches the dev coverage judgment. For each record, use the model trained
   **without** its SHA-256 modulo-five fold. Features are standardized using
   that training fold only; the means/scales are folded into the frozen raw-space
   coefficients. Frozen coefficients are in the Python
   file; ordinary inference never opens gold data. Both training and evaluation
   retain the natural imbalance of article/non-article speeches.

This is a retrieval experiment, not a stage-aware legal concordance engine.
There is no HMM, no mapping of explicit draft numbers, and no claim that topical
similarity proves a speech is chiefly about an article. Deleted proposals and
other agenda items are particularly difficult. Report paragraphs can mention
several amendments and articles; even a unique amendment association can be
wrong. Document-level instrument metadata can also hide early mixed
Declaration/Covenant debates. These limitations motivate abstention.

## Evaluation protocol

Use the existing committed `data/gold/tagger_eval.jsonl`. No gold regeneration was
needed: the candidate count is exactly 13,975, and the scorer confirms the
expected dev population of 303, including 74 about a final article.
Only dev coverage judgments train confidence; judged existing tags are not used
as additional training examples. The other evaluation split is untouched until
the one final scorer invocation.

To reproduce the five fitted models and their held-out predictions:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 pipeline/article_tagger.py \
  --calibrate-dev data/gold/tagger_eval.jsonl \
  --embedding-cache /tmp/tagger-embedding-cache --out /tmp/tagger-dev-refit.csv
python3 eval/tagger_score.py /tmp/tagger-dev-refit.csv --split dev
```

`--calibrate-dev` filters on `split == dev` before consulting labels. It prints
coefficients and applies the excluded-fold model to each record, rather than
reporting fitted training probabilities. Thus the shipped CSV's dev scores are
also grouped out-of-fold scores. Feature design was explored on dev; these are
not a nested-CV estimate of the entire model-development process. The independent
test result and the maintainers' planned fresh blind sample remain necessary.

The initial lexical-only calibrated model produced 6 correct proposals out of 8
at 0.5 (precision 0.75, recall 0.08); none at 0.9. Exploratory regularization
checks at C=10 and C=100 did not establish 0.90 precision. Adding BGE without scaling gave 6/9 at 0.5 and no predictions at 0.9.
The final model uses fold-local feature standardization with C=1 and the two
semantic features. A diagnostic check of BGE nearest-final-article retrieval
alone matched only 17/303 dev judgments, versus 32/303 for lexical candidate
generation, so it was not used to replace the lexical candidates. No threshold
is chosen using test.

## Results and recommendation

**Use 0.95 for blind human review only. Do not integrate automatically.**
The final dev point estimate satisfies the numeric target (4/4 = 1.00), but
recall is only 4/74 = 0.054. Even a nominal 95% Wilson precision interval is
approximately 0.51–1.00, before allowing for threshold selection on dev.
At 0.90 the final result is only 7/9 = 0.778. This experiment has not established
90% precision in deployment. There is no validated automatic integration threshold.

Final dev, using grouped out-of-fold confidence:

```text
split dev: 303 untagged judged speeches, 74 about a final article
threshold |   n | right | precision | recall
   0.50   |  20 |    12 |      0.60 |   0.16
   0.60   |  18 |    11 |      0.61 |   0.15
   0.70   |  17 |    11 |      0.65 |   0.15
   0.80   |  15 |    10 |      0.67 |   0.14
   0.90   |   9 |     7 |      0.78 |   0.09
   0.95   |   4 |     4 |      1.00 |   0.05
judged tags: reproduces 8/1158 right tags, repeats 2/148 wrong ones (any score)
```

The single test invocation, after freezing the method, coefficients, CSV and
review threshold, was:

```sh
python3 eval/tagger_score.py data/tagger/predictions.csv --split test
```

```text
split test: 67 untagged judged speeches, 20 about a final article
threshold |   n | right | precision | recall
   0.50   |   4 |     0 |      0.00 |   0.00
   0.60   |   4 |     0 |      0.00 |   0.00
   0.70   |   2 |     0 |      0.00 |   0.00
   0.80   |   0 |     0 |      0.00 |   0.00
   0.90   |   0 |     0 |      0.00 |   0.00
   0.95   |   0 |     0 |      0.00 |   0.00
judged tags: reproduces 0/326 right tags, repeats 0/37 wrong ones (any score)
```

At 0.95 the test has **no proposals**: precision is undefined, although the
provided scorer prints 0.00 for an empty set. Recall is zero. At 0.5 all four
test proposals are wrong. The model and threshold were not changed after this
result. The test offers no positive validation of the high-score tail.
The secondary judged-tag counts are not a masked-tag recovery benchmark:
this pipeline only predicts currently untagged speeches.

Confidence calibration is imperfect. The grouped out-of-fold Brier score for
raw candidate correctness is 0.0690. Reliability by score band, before abstention:

| Score band | Dev count | Mean score | Observed correctness |
|---|---:|---:|---:|
| [0, 0.1) | 239 | 0.019 | 0.025 |
| [0.1, 0.3) | 31 | 0.165 | 0.290 |
| [0.3, 0.5) | 13 | 0.418 | 0.385 |
| [0.5, 0.8) | 5 | 0.654 | 0.400 |
| [0.8, 0.95) | 11 | 0.886 | 0.545 |
| [0.95, 1] | 4 | 0.989 | 1.000 |

In particular, 0.8–0.95 scores substantially overstate observed correctness.
The scores are fitted estimates, not verified probabilities. Four examples
cannot establish calibration above 0.95.

## Candidate counts by period and body

Exactly **100** of 13,975 candidates (0.72%) reach the review threshold, compared
with 725 emitted proposals at 0.5 and 13,250 abstentions. These are counts of
proposals, not an estimate of confirmed correct additions. Period uses the
document date, falling back to the session year; missing years remain unknown.

| Period | Body | Candidates | Proposals ≥0.5 | Review ≥0.95 |
|---|---|---:|---:|---:|
| 1946–48 | CHR Drafting Committee | 600 | 41 | 5 |
| 1946–48 | CHR Working Group on the Declaration | 100 | 20 | 6 |
| 1946–48 | Commission on Human Rights | 1000 | 23 | 7 |
| 1946–48 | Commission on the Status of Women | 82 | 3 | 0 |
| 1946–48 | Economic and Social Council | 465 | 0 | 0 |
| 1946–48 | General Assembly Third Committee | 750 | 11 | 0 |
| 1946–48 | General Assembly plenary | 85 | 0 | 0 |
| 1946–48 | Sub-Commission on Freedom of Information and of the Press | 115 | 8 | 0 |
| 1946–48 | Sub-Commission on Prevention of Discrimination and Protection of Minorities | 162 | 6 | 0 |
| 1949–54 | Commission on Human Rights | 3547 | 277 | 46 |
| 1949–54 | General Assembly Third Committee | 2716 | 81 | 0 |
| 1955–66 | General Assembly Third Committee | 4289 | 254 | 36 |
| 1955–66 | General Assembly plenary | 45 | 0 | 0 |
| unknown | General Assembly Third Committee | 8 | 1 | 0 |
| unknown | General Assembly plenary | 11 | 0 | 0 |
| **Total** | | 13975 | 725 | 100 |

## Reproducibility and source drift

The source database was being corrected concurrently: three candidate texts
changed during development (a delegation spelling and two historical country
spellings). IDs and candidate count stayed unchanged. Those text changes also
alter TF-IDF frequencies, so the final calibration was repeated on a read-only
validation snapshot before the single test run. The final 0.90 table above
supersedes the earlier exploratory 8/10 result; the chosen 0.95 threshold stayed
unchanged at 4/4.

The local snapshot is `/tmp/article-tagger-validation.sqlite3`; it is not committed.
Its SHA-256 is
`9819fea53f902f42d197b1a8e439f4dc18a50f39757fe4b5be9176b2cf5bd138`.
The source segment ID/text digest (ordered by ID, each field followed by NUL) is
`114a35506c640302f85e2406cb0d944f3f07d829c016d26f35eeb8f9ae39ed82`.
To reproduce this exact local output, pass that snapshot with `--db` to the
normal or dev-refit command. Future source edits can legitimately change output.

A second ordinary CLI run against the snapshot reproduced the committed CSV
**byte for byte**, with SHA-256
`f8331e9f8514bc5c384cfc08dd346919b79a3a1c6875e802bd42bed78ab5a48c`.
The snapshot hash was unchanged after verification. The candidate ID set matched
the database query exactly: 13,975 distinct IDs, no omissions or extra rows,
all scores within [0, 1]. The CSV is 2,294,195 bytes.

Observed stages on this laptop: TF-IDF about 13–31 seconds; a cold BGE pass
318–327 seconds on CPU. Total execution is about six minutes, comfortably below
30 minutes. An embedding cache avoids the BGE pass on repeated identical inputs.


## Error analysis: 34 dev candidate errors

The table examines the 32 strongest lexical **wrong raw proposals** plus two
other emitted errors at 0.5, before
confidence-based abstention. This deliberately includes rejected proposals:
there are eight emitted dev errors at 0.5 and none at 0.95. All IDs and
labels are from dev coverage judgments. These are diagnostics of candidate
generation, not 34 accepted high-confidence tags. The gold labels are retained
as supplied, including debatable procedure/substance boundaries.

| Cause | Segment ID | Raw proposal | Gold | What went wrong |
|---|---|---|---|---|
| Procedure | a_c.3_sr.1437-0026 | ICCPR 2 | NONE | Withdrawal to facilitate committee work; amendment vocabulary is insufficient. |
| Procedure | a_c.3_sr.97-0007 | UDHR 1 | NONE | Closure and order of work mention article 1 only as context. |
| Other text | e_cn.4_sr.39-0019 | UDHR 29 | NONE | Addition to an Indian resolution, not the Declaration article. |
| Procedure | a_c.3_sr.793-0019 | ICESCR 14 | NONE | Priority and mechanics of voting; strong topical and flanking agreement still mislead. |
| Other text | a_c.3_sr.422-0002 | ICCPR 19 | NONE | Report and wider freedom-of-information work share the article's vocabulary. |
| Related article | a_c.3_sr.1258-0009 | ICCPR 26 | ICCPR 2 | Quotation about discrimination retrieves equality rather than the article under discussion. |
| Deleted proposal | e_cn.4_sr.387-0017 | ICCPR 39 | NO_FINAL | Proposed national representation on the committee resembles surviving implementation provisions. |
| Other text | a_c.3_sr.1195-0007 | ICCPR 13 | NONE | Separate asylum declaration resembles the expulsion article. |
| Insufficient context | a_c.3_sr.138-0041 | UDHR 21 | UDHR 22 | Generic vote on the chair's ruling gives no lexical article identity. |
| Insufficient context | e_cn.4_sr.306-0011 | ICCPR 23 | ICESCR 5 | OCR-damaged amendment citation and voting order, without substantive words. |
| General debate | e_cn.4_ac.1_sr.14-0048 | UDHR 25 | NONE | Referral of an entire section of economic and social rights. |
| Procedure | a_c.3_sr.1220-0002 | ICESCR 17 | NONE | Withdrawal and change of sponsorship resemble tagged amendment discussion. |
| Procedure | e_cn.4_sr.186-0027 | ICCPR+ICESCR 1 | NONE | Voting priority between draft resolutions. |
| Other text | e_cn.4_sr.266-0019 | ICCPR+ICESCR 1 | NONE | Resolution on self-determination, not the final covenant article. |
| Related article | e_cn.4_ac.1_sr.14-0037 | UDHR 24 | UDHR 23 | Work and rest vocabulary overlap; placement of the right to work loses the vote. |
| Related article | e_cn.4_sr.159-0009 | ICESCR 2 | ICCPR 14 | Compensation for wrongful conviction confused with generic obligations. |
| Related article | e_cn.4_sr.222-0006 | ICESCR 7 | ICESCR 10 | Equal-pay reference is an aside; lexical topic differs from gold context. |
| Procedure | a_c.3_sr.1232-0049 | ICCPR 6 | NONE | Opportunity to explain votes, rather than an explanation of a substantive vote. |
| Other text | a_c.3_sr.315-0055 | ICESCR 11 | NONE | Wording of an anniversary resolution. |
| Procedure | e_cn.4_sr.314-0044 | ICCPR 2 | NONE | Withdrawal of a reconsideration motion to expedite business. |
| Insufficient context | a_c.3_sr.1058-0028 | ICCPR+ICESCR 1 | NONE | Fragment consisting almost entirely of delegations and sponsors. |
| General debate | e_cn.4_sr.216-0007 | ICESCR 6 | NONE | Broad ILO contribution and drafting agenda mention the right to work. |
| Instrument ambiguity | e_cn.4_sr.328-0014 | ICCPR 5 | ICESCR 5 | Similar safeguard wording across both Covenants; cannot collapse article 5. |
| Deleted proposal | e_cn.4_ac.2_sr.9-0084 | UDHR 4 | NO_FINAL | Rejected minority proposal retrieves an unrelated surviving article. |
| Deleted proposal | e_cn.4_sr.442-0006 | ICESCR 24 | NO_FINAL | Reservations proposal has no final-article equivalent. |
| General debate | a_c.3_sr.95-0010 | UDHR 22 | NONE | Broad duties-of-the-individual proposal, not one adopted article. |
| Instrument ambiguity | e_cn.4_ac.1_sr.31-0029 | UDHR 15 | ICCPR 22 | Early mixed-instrument record; metadata restriction excludes the correct Covenant article. |
| Procedure | a_c.3_sr.708-0037 | ICCPR+ICESCR 1 | NONE | Scheduling the covenant debate and allocating meetings. |
| Procedure | a_c.3_sr.560-0006 | ICESCR 4 | NONE | Section-by-section versus part-by-part organization. |
| Other text | e_cn.4_sr.80-0042 | UDHR 30 | NONE | How to append drafts to the Commission's report. |
| Other text | e_cn.4_sr.170-0006 | ICCPR 19 | NONE | Institutional remit and separate freedom-of-information convention. |
| Procedure | e_cn.4_sr.133-0096 | ICCPR 14 | NONE | Protest against indefinite postponement of a vote. |
| Other text | a_c.3_sr.824-0002 | ICCPR+ICESCR 1 | NONE | General self-determination debate and a five-Power resolution, not article 1. |
| General debate | e_cn.4_sr.209-0016 | ICCPR 41 | NONE | Several implementation mechanisms and individual petitions, rather than one article. |

Counts: procedure 10; other text 8; related article 4; deleted proposal 3;
insufficient context 3; general debate 4; instrument ambiguity 2.

## Validation and next steps

**64 tests passed** (50 existing plus 14 new), including the existing API and
parsers. New unit tests cover
instrument distinctions, record boundaries, conflicting amendment evidence,
normalization, abstention, read-only SQLite, missing databases, and held-out
calibration. API tests use loopback only; no external network is needed.

Before integration, draw the planned fresh blind sample, stratified by body,
period and score, and distinguish alternative agenda texts from final-article
debate. The most promising next improvement is explicit identification of the
text being debated, including deleted proposals and early mixed-instrument
meetings, before any semantic article match. More general embeddings alone
cannot establish that distinction. No integration into the build is performed.

## Open questions

No access or implementation blocker. The numeric dev target is supported by
only four accepted examples, so an integration decision remains open pending
the planned independent blind review. The maintainers should resolve ambiguous
procedure/substance judgments under the existing rubric during the fresh blind
review; this implementation does not relabel them or alter gold.

## Blind check by the maintainers (round 44, 28 September 2026)

The branch was merged into `main` as a documented experiment. The 100 proposals at the
recommended threshold of 0.95 were then judged blind: two judges each, a third on the one split.
The judges saw the tag and the context, but not the tagger, its score or its evidence.

**93 of 100 were right** (Wilson 95% interval 0.86-0.97):
- Commission 1946-48: 17/18;
- Commission 1949-54: 45/46;
- Third Committee: 31/36.

The seven errors are speeches that use the article only as an argument or are about another
text:
- draft article 44 argued with article 27;
- article 3 rather than article 2;
- the other covenant's final clauses;
- a political reply;
- the Convention's rather than the Declaration's article;
- a CERD meeting that cites the draft ICCPR;
- a procedural point on self-determination.

The 93 accepted tags are listed in `data/tagger/accepted.csv`. `api/build_db.py` applies them
to speeches that the rules and Jev's checks left untagged ("the offline tagger's proposal (score
0.97), checked by hand (round 44)"). No classifier overrides them. The tagger is not otherwise
wired into the build, and there is still no validated threshold below 0.95.

## Second blind check: scores 0.90-0.95 (round 47)

57 proposals scored from 0.90 to 0.95 and still untagged were judged the same way. **48 of 57 were
right** (84%, Wilson 0.73-0.91), and the judges agreed on all. Of the nine errors:
- three are the 1956 debate on the Afghan resolution on permanent sovereignty, an ECOSOC-report
  item, not article 1;
- three are procedure (postponing an article);
- two are neighbouring articles;
- one is a digression.

The 48 were added to `data/tagger/accepted.csv`, which now holds 141 checked proposals. Below
0.9 the share of right proposals will be lower still. Each proposal can still be judged and
added, but no threshold alone is safe.
