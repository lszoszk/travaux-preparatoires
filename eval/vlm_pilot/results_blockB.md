# Block B, the local model (H4): results (16 October 2026)

Scored on 16 October 2026 after the preregistration state was timestamped (`timestamp/`, 21:08 CEST); the readings were made
before the timestamp and not looked at until then. Method as preregistered (`eval/vlm_pilot_cer.py`; per page, pooled by
characters, 95% bootstrap intervals over pages, 10,000 resamples, seed 2026). 59 of the 60 pages scored (one page has no
located reference segment). Data: `cer_blockB.json`.

## As preregistered (no exclusions)

| Group | Pages | OCR vote | Local model (c) | Difference [95% interval] |
|---|---|---|---|---|
| Typewritten records | 19 | 1.48% | 1.72% | +0.24 pp [−1.77, +4.05] |
| Typewritten documents | 20 | 13.77% | 12.41% | −1.36 pp [−2.82, −0.60] |
| Printed pages (1948, EN/FR) | 20 | 1.42% | 1.21% | −0.21 pp [−0.28, −0.14] |
| **Typewritten, records and documents (H4)** | 39 | 8.67% | 7.98% | **−0.69 pp [−1.85, +0.89]** |
| All | 59 | 5.95% | 5.44% | −0.51 pp [−1.23, +0.46] |

**H4 is supported by the preregistered rule (the point estimate is lower), but the interval includes zero: not conclusive.**

## What lies behind it
- **One failure of the model.** On E/CN.4/SR.8, page 1, the model ran away: its answer hit the token limit twice (8,000
  tokens, 60,090 characters of HTML repeating itself) and the text recovered from it holds only the masthead and three names
  (length 0.31 of the vote's). It alone turns the typewritten records from a gain into a loss. The length test of the
  preregistered guard (0.85–1.15 of the vote) trips on this page and on one other (E/CN.4/SUB.2/29 p. 1, 1.31, where the
  model reads more than the vote).
- **One page that measures nothing.** On E/CN.4/AC.1/3/Add.1, page 257, every engine scores 50.7%: the long document repeats
  its wording, and segments of the reference from other pages match this page at 88 or more. It inflates the level of
  every engine on the typewritten documents, not the differences.

## Secondary analyses (not preregistered for (c); the guard's rule is the one preregistered for (b))

| Group | Vote | Model | Model with the guard (vote where the length test trips) | Difference with the guard |
|---|---|---|---|---|
| Typewritten records | 1.48% | 1.72% | **0.35%** | −1.13 pp [−2.02, −0.51] |
| Typewritten, without the artefact page | 2.18% | 1.38% | **0.80%** | −1.38 pp [−2.14, −0.80] |
| All, without the artefact page | 1.87% | 1.31% | **0.97%** | −0.90 pp [−1.39, −0.53] |

## Lessons for the pilot
1. The guard is not optional: one page in 60 failed silently and badly. A reading that hits the token limit is to be
   treated as failed, not re-read once and kept.
2. Per-page CER needs a check that a located segment belongs to the page (long repetitive documents).
3. Where the model works, it reads typewritten records about four times better than the vote (0.35% against 1.48% with
   the guard), as on the development sets.
