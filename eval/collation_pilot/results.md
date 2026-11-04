# Collation pilot: UDHR articles 1, 4, 18, 24 across eight stages (20 Oct 2026)

Preregistered in docs/devlog.md (20 Oct). eval/collation_pilot.py (CollateX 2.3, segmentation on, no near-matching or
transposition detection); per article art-NN.json (witnesses, sources, branches), art-NN.txt (alignment table),
art-NN.tei.xml; judgments.json (branch by branch, with the rule). None of the 31 stage texts came from the vision reader:
it has not read these pages yet, so all are the OCR's.

| article | branches | real | OCR or extraction noise | alignment artifact |
|---|---:|---:|---:|---:|
| 1 | 21 | 8 (38%) | 10 | 3 |
| 4 | 34 | 6 (18%) | 0 | 28 |
| 18 | 43 | 9 (21%) | 2 | 32 |
| 24 | 19 | 6 (32%) | 10 | 3 |
| all | 117 | **29 (25%)** | 22 | 66 |

Gate (at least 80% real): **not passed**.

What fails:
- **Alignment, more than OCR (66 of 117).** Where a stage rewrites the article rather than amends it (art. 4: the Secretariat's
  "slavery and compulsory labour" against E/800's "no one shall be held in slavery", with the torture clause still inside;
  art. 18 from "freedom of conscience and belief" to "freedom of thought, conscience and religion"), word-level alignment
  pairs unrelated words: a coincidental "the", "of", "and", "to" makes stages share a reading they do not have, and a word
  that only moved in the sentence shows as dropped and added. Multi-witness word collation fits close versions of one text
  (editions, copies); the drafts are rewritings.
- **Noise (22).** OCR in the short articles (A/777's art. 24 "bveryoug 3 the wight to real and leisure ... pork hours ant"),
  paragraph markers ("Para 1."), and an extraction error in the database: E/CN.4/95's text of art. 1 carries the editorial
  note "The Drafting Committee did not have the time to consider this Article" twice and the limitations clause of the next
  article ("in the exercise of his rights everyone is limited by the rights of others...").

What works: where consecutive stages are close, the branches are real and citable: "men" becomes "human beings" and "like
brothers" "in a spirit of brotherhood" in E/800; "by nature" is dropped in A/777; "a fair share of" is dropped in E/CN.4/57;
"vacations" becomes "holidays" in A/777.

As preregistered, the texts are to be cleaned first; but cleaning alone would remove at most the 22 noise branches, not the 66
artifacts. Next step proposed: (1) the vision reader on the ~70 pages of the eight stage documents, and a fix of the extraction
error in E/CN.4/95; (2) instead of one graph over all stages, the change from each stage to the next (pairwise, clause by
clause), which is the question asked of a drafting history ("what changed at this stage, and who proposed it"); judged again
by the same rule.
