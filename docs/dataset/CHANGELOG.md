# Changelog

Versions follow the form `vMAJOR.MINOR`. A new major version changes the files or their fields (a field renamed, removed or
given another meaning); a new minor version changes the data (documents added, text re-read, tags and speakers corrected)
with the same fields. Each version on Zenodo has its own DOI, and the concept DOI always leads to the latest one. The code
repository keeps, for every rebuild that divides or merges segments, a map of the old `id`s to the new ones
(`data/id_maps/`).

## v1.0 (planned, early 2027)

- The vision model's reading of the rest of the corpus (about 12,900 pages, read on PLGrid), taken with the same checks.
- An audit of about 300 random speeches, checked on the scans for every field at once, and its error table in the
  datasheet.
- The first release on Zenodo, with a DOI.

## Since v0.9 (not yet deployed)

- The text of 5,282 pages of 588 records is the reading of a vision-language model (Chandra OCR 2) where it passed the
  checks; the speakers stay as the OCR engines resolve them (172 speeches kept so), the hand-anchored documents keep the
  OCR text. The cleaner text divides 1,024 more speeches (turns the OCR had run together), tags 391 more and reads 508 more
  decisions; five meeting dates corrected. A blind check of 40 new or changed tags found 37 right; the three wrong were
  removed.
- The Australian member of the Drafting Committee's second session is HEYWARD throughout (the typists also wrote HEYWOOD).

## v0.9 (21 October 2026): test edition

For the invited testers; not deposited.

- 2,157 documents (834 on the Declaration, 1,323 on the Covenants), 1946–66; 28,560 speeches, 99.6% attributed to a speaker
  and a delegation; 11,331 speeches tagged with the article under debate, 1,570 speeches of the general debates with the
  question they are about.
- Text: OCR by four engines with a word-by-word vote.
- New fields against the export of 23 September 2026: `source_language`, `machine_translated` and `translation_model` in
  `documents.jsonl`; `topic` and `topic_confidence` in `segments.jsonl`; the citation of a machine-translated segment says so.
