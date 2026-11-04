# Block C, the local model: results (17 October 2026, exploratory)

Not a preregistered test for the local model (its hypothesis H4 is on block B); block C is the preregistered ground of
the API reader (b), and the local model's readings of it are reported here as exploratory. Method as for the second
development set: disputes between the local model and the OCR vote (`eval/vlm_disputes.py`, 1,477 on 170 pages), 4 a
page judged blind on the scan (552; seed 11), words read wrong per 1,000 estimated from the verdicts and the number of
disputes. Data: `disputes_blockC.json`; readers checked against the reference on development set 1 (88% agreement,
about 95% after the reference match's own errors).

| Pages of block C | Pages | Words | Disputes | Vote wrong / 1,000 | Local model wrong / 1,000 |
|---|---|---|---|---|---|
| CHR 1949–54, typewritten (score terciles) | 43 | 13,879 | 537 | 33.7 | **7.3** |
| CHR typewritten (the random filling) | 42 | 13,594 | 568 | 39.7 | **4.7** |
| Third Committee printed, two-column | 45 | 36,463 | 233 | 3.8 | **2.8** |
| Third Committee printed (the random filling) | 15 | 13,159 | 49 | 2.6 | **1.6** |
| Third Committee 1950–61, single-column pages | 15 | 1,216 | 58 | 33.1 | **17.5** |
| Third Committee 1962–66, single-column pages | 10 | 1,323 | 32 | **9.7** | 15.5 |

Verdicts overall: the local model right 399 times, the vote 120, neither 33. The length guard tripped on 3 pages of 170
(A/C.3/SR.906 p. 3, E/CN.4/SR.379 p. 15, E/CN.4/SR.378 p. 2); the coverage check found nothing missing on two of them and,
on the third (an attendance list set as a table), one line left out and one added. No runaway reading on block C.

What it says: on the typewritten records of the Commission (1949–54) the model reads 5 to 8 times fewer words wrong than
the vote, as on the development sets; on the printed Third Committee records it gains a little (about a quarter to a third
fewer errors, from a low level). The few single-column pages of the Third Committee (covers, attendance lists, short
pages; 25 in all) are mixed, and on those of 1962–66 the model is worse: too few pages to read much into, but a reason to
keep the vote there unless the guard and a check agree.
