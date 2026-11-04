# Stage-to-stage comparison: held-out result (20 Oct 2026)

Preregistered in docs/devlog.md (20 Oct): eval/stage_changes.py, developed on articles 1, 4, 18, 24, frozen, run on held-out
articles 3, 12, 17, 20. Texts: the vision reader's reading of the passage for 34 of the 36 stage texts (73 pages of the stage
documents read locally for this; no error, no runaway), the adopted text from un.org. Judgments: judgments_heldout.json.

| article | changes | real | noise | artifact |
|---|---:|---:|---:|---:|
| 3 | 12 | 9 | 3 | 0 |
| 12 | 35 | 24 | 6 | 5 |
| 17 | 26 | 19 | 7 | 0 |
| 20 | 23 | 13 | 4 | 6 |
| all | 96 | **65 (68%)** | 20 | 11 |

Gate (at least 80% real): **not passed.** Counting the 4 real changes that carry a stray number or catchword as real: 72%.

Against the one-graph collation (25% real), the artifacts fall from 66 of 117 to 11 of 96, and the OCR's misreadings are
gone with the vision reader's text. What is left:
- **noise (20)**, almost all systematic: article numbers left at the edge of a text ("9 every one", "13 no one": 12 changes),
  catchwords repeated at a page break ("placed placed", "/The State The State": 3), the cut of a text a few words off in the
  database (E/CN.4/21's art. 17 loses "Every" and repeats "are susceptible": 4), and the Secretariat outline's article in
  French (1);
- **artifacts (11)**: where a stage rewrites a sentence, word alignment reports a moved word as replaced ("reputation" > "his
  privacy" in E/800's art. 12) or pairs unrelated words ("association for" > "a").

Real and worth having, among others: A/777 prints "the security of person" and the plenary drops "the" (art. 3); E/800
"unreasonable" > A/777 "arbitrary" interference, and the clause on honour and reputation added in A/777 (art. 12); E/CN.4/95's
"such property as meets the essential needs of decent living" and its reversal in E/800 (art. 17); "peaceful" dropped in E/800
and restored in A/777, with "no one may be compelled to belong to an association" (art. 20).

Not preregistered, so only an estimate: stripping article numbers and catchwords from the texts would remove 12 noise changes
and turn 3 contaminated ones into real ones, about 68 of 84 (81%); that needs a new run on new held-out articles to count.

# Second held-out run: articles 6, 9, 13, 22 (20 Oct 2026)

Preregistered in docs/devlog.md before the run; the noise of the first run removed in development (article numbers and
headings at a text's edges, catchwords, the reader's passage widened, the corrected concordance: E/CN.4/95's notes,
E/CN.4/AC.1/3's English pages, damaged capital headings), then frozen. Judgments: judgments_heldout2.json.

| article | changes | real | noise | artifact |
|---|---:|---:|---:|---:|
| 6 | 21 | 12 | 0 | 9 |
| 9 | 12 | 10 | 0 | 2 |
| 13 | 26 | 23 | 0 | 3 |
| 22 | 33 | 31 | 0 | 2 |
| all | 92 | **76 (82.6%)** | 0 | 16 |

Gate (at least 80% real): **passed, narrowly.** No noise is left; the 16 artifacts are all of one kind, a word or clause that
only moved, or a rewritten sentence whose leftover pieces are paired across unrelated places (art. 6: "everywhere" moved
in E/CN.4/95 and E/800; "arrest, detention or exile" in A/777 shown as "detention" added). Six calls are borderline (a
substitution in the same place of the sentence counted as real); counted against, 76.1%, below the gate. The judge is the
one who built the method: a second reader's judgment of these 92 changes would settle it.

Real and worth having, among others: "everywhere in the world" in E/CN.4/57 shortened to "everywhere" in E/CN.4/95 (art. 6);
E/800 "no one shall be subjected to arbitrary arrest or detention" replacing the due-process text, and "exile" added in
A/777 (art. 9); the right to leave "any country, including his own" in E/CN.4/95 and "to return to his country" in A/777
(art. 13); E/800's rewrite of social security as the gateway to "economic, social and cultural rights", and A/777's
"indispensable for his dignity and the free development of his personality" (art. 22).
