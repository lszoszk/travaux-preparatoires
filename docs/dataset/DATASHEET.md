# UN Travaux Préparatoires: a speech-level database of the drafting records of the UDHR, ICCPR and ICESCR

**Datasheet** (after Gebru et al., "Datasheets for Datasets", *Communications of the ACM* 64(12), 2021)

| | |
|---|---|
| Version | $version, exported $date (database built $built, code $commit) |
| DOI | $doi |
| Author | Łukasz Szoszkiewicz, Adam Mickiewicz University, Poznań (ORCID 0000-0001-6671-2893) |
| Licence | our additions CC BY-NC-SA 4.0; the text of the UN documents under the UN's terms (see "Distribution") |
| Contact for corrections | l.szoszkiewicz@amu.edu.pl |

## Summary

The drafting records of the Universal Declaration of Human Rights (1946–48) and of the International Covenant on Civil and
Political Rights and the International Covenant on Economic, Social and Cultural Rights (1949–66), from $first_date to
$last_date, divided into speeches.
Each speech carries its speaker, delegation, date, the UN symbol of the record and the page or paragraph where it stands, and,
where the debate was about one article, the final article of the Declaration or of a Covenant.

| File | Rows | One row is |
|---|---:|---|
| `documents.jsonl` | $documents | a UN document: a meeting record, a report, a draft, an amendment, a letter |
| `segments.jsonl` | $segments | a speech, a turn of the chair, a vote, a heading, a footnote or a numbered paragraph of a document |
| `decisions.jsonl` | $decisions | a decision a record reports: what was voted on, the outcome, the figures and the roll-call |
| `amendments.jsonl` | $amendments | a document the records cite as an amendment or proposal, with its sponsors and fate |
| `concordance/` | | the tables mapping each session's draft numbering to the final articles, and the final texts |
| `FIELDS.md` | | every field of the files above |
| `CHANGELOG.md` | | what changed between versions |
| `manifest.json` | | version, date, row counts and a checksum of each file |

Of the $documents documents, $udhr_docs belong to the drafting of the Declaration and $cov_docs to the drafting of the
Covenants. There are $speeches speeches, $attributed of them attributed to a speaker and a delegation; $tagged speeches carry
the article under debate and $topics speeches of the general debates carry the question they are about instead (for
instance, self-determination or the federal clause).

## Motivation

The drafting records are a supplementary means of interpretation of a treaty (Article 32 of the Vienna Convention on the
Law of Treaties) and the usual source for the history of each provision. The UN holds them as scanned typescripts and
printed volumes, indexed by document only. Thus, to find what a delegation said on, for instance, Article 18 of the
ICCPR, a researcher has to know which session numbered it how, open each record and read it. This
dataset does that indexing once, for every meeting record the UN's own lists name, and keeps each speech tied to the page
of the UN record, so that the reader can always check the original.

It was built by the author as research of his own at the Faculty of Law and Administration, Adam Mickiewicz University,
without external funding. The computing for the reading of the scans by a vision model was provided by Kaggle (free GPU
time) and by the PLGrid infrastructure (grant PLG/2026/020181, ACK Cyfronet AGH).

## Composition

**What is in it.** The meeting records (summary records and verbatim records) of the bodies that drafted the three
instruments: the Commission on Human Rights (1946–54), its Drafting Committee and working groups (1947–48), the Economic and
Social Council (1946–48), the Sub-Commissions on Freedom of Information and on Prevention of Discrimination and Protection of
Minorities (1947–48), the Third Committee of the General Assembly (1946–66) and the Assembly's plenary, together with the
reports, drafts, amendments and comments of governments that the records and the finding aids name and that the UN's
document server holds.

**How complete it is.** In total, $records_pct% of the meeting records that the UN's lists name for the drafting are in the dataset
(the missing ones are not on the UN's document server). However, the documents the speeches cite are covered much less:
only $cited_pct% of the distinct documents cited (and $citations_pct% of the citations) are held, because most drafts and amendments
of the L series (for instance A/C.3/L.n) are not on the UN's document server. Their sponsors and votes come from the
records. The list of what is missing is in `docs/missing_documents.md` of the code repository.

**Languages.** English. $mt_docs documents exist only in French; they are machine-translated into English and marked as such
(`machine_translated` in `documents.jsonl`, a notice at the head of their text). They must not be quoted as UN English text.

**Kinds of segment.** A meeting record is divided into speeches, turns of the chair, votes, headings, footnotes and the
closing; a document into its numbered paragraphs. The running heads, page numbers and the record's masthead are left out of
the text. `FIELDS.md` lists the kinds.

**Personal data.** The names in the dataset are those of delegates, UN officials and representatives of organizations
speaking in their official capacity at public meetings, 1946–66, as the UN's public records give them, and no other personal
data.

**What it is not.** The text of a summary record is the Secretariat's paraphrase, not what the delegate said word for word;
only the plenary records of the General Assembly and of the Economic and Social Council (A/PV, E/PV) are verbatim. The dataset does not include the printed compilations of the
travaux (Schabas 2013, Bossuyt 1987, Saul 2016), which were used privately as finding aids and to measure the accuracy of the
text, and nothing of their text is included.

## Collection

The documents were downloaded by their UN symbol from the UN's document server (documents.un.org) between 22 and 30 September
2026, one request at a time and at least six seconds apart: $src_ods documents. A further $src_uva come from the University of
Virginia's public collection of the travaux (scans of the UN originals), and $src_hand were saved by hand in a browser. Which
documents to fetch was read from the UN Library's research guide to the drafting of the Declaration, the reports of each
session (which list the meetings and documents on each article) and the series of meeting records; for the Covenants, from
the series of meeting records 1949–66 and the reports, keeping only the meetings whose agenda concerned the Covenants.

## Processing

**Text.** The scans were read by four OCR engines (the text layer of the UN's PDF, Tesseract in two modes and Apple Vision).
For each page the best reading is kept and corrected word by word by the majority of the engines; misreadings that every
engine shares are then corrected from the word frequencies of the corpus. In the bilingual printed records of 1948 only the
English column is kept. On $vision_pages pages of $vision_records records (mostly the typescripts of 1947–54, where the OCR
errs most) the text is instead the reading of an open vision-language model (Chandra OCR 2), taken only where it passes three
checks: the model did not run away, the page is not set in two columns, and the reading's length is within 15% of the OCR's.
The names it prints at the openings of speeches are checked against the attendance lists and the OCR engines' readings, since
such a model can write a plausible name the page does not have. The documents whose text the hand-made tables anchor (the
reports' sections and annexes, the drafts the concordance is read from) keep the OCR text. Nevertheless, the pages are not
corrected by hand, so errors remain (see "Quality").

**Speeches and speakers.** The records are divided at the openings of the speeches ("Mr. MALIK (Lebanon) said ..."). The
speaker's name is read from the opening as the OCR engines read it (also where the text is the vision model's: four blind
reviews found its names less reliable than its text) and matched with the attendance lists of the session
(and with checked lists of delegates where they exist), so that a misread name takes the form the lists give. Where a typist
misspelt a name, the text keeps the spelling of the page and the `speaker` field gives the usual one.

**Articles.** Each session numbered the drafts differently. For instance, article 18 of the Declaration was article 14 of the
Secretariat's outline of 1947 (E/CN.4/AC.1/3) and article 16 of the Commission's draft of June 1948 (E/800), and the
Covenants' articles moved between 1949 and 1966. Each session's numbering is
mapped to the final articles by comparing the draft texts with the adopted ones (`concordance/`). A speech gets an article
from the record's headings, the chair's announcements and the reports' lists of the meetings on each article; each such tag is
then checked by a classifier (TypeSafe's Jev, asked whether the speech is about that article) and dropped when it is judged
unlikely. For this reason, weaker evidence is not used, and a speech is left without an article rather than given a
doubtful one.
`article_mapping` says, for each tag, where it came from, and `article_confidence` gives the classifier's probability.

**Questions of the general debates.** Speeches in the general debates that no article fits (self-determination, one
covenant or two, measures of implementation, petitions, the federal and territorial clauses, reservations, the form of the
International Bill, the instrument as a whole) carry the question they are about, chosen by the classifier with a
probability of 0.9 or more.

**Decisions.** The votes the records report are read with their outcome, figures, roll-calls and the proposers named.

Every step is in the code repository (`pipeline/`, `api/build_db.py`), with the decisions and their reasons in
`docs/devlog.md`.

## Quality

The tags, the questions and the speakers are measured on random samples, judged on the text (for the speakers, on the
page images) by two blind readers (the language models Claude Opus and Claude Sonnet, which did not see the database's
answer), with a third reading or the author on the items they disagreed on. The judgments are kept in `data/gold/` of the
code repository. The text of 1946–48 is measured against the records retypeset in Schabas (2013), used privately and not
included, and the text of 1949–66 by blind readers of the scan on the words where the OCR and a vision model disagree.

| What | Measure | Result |
|---|---|---|
| Article tags | share of tags that are right (weighted by kind of record), $tag_round | **$tag_precision** ($tag_correct of $tag_checked) |
| Article tags | share of the speeches about one article that carry it | $coverage_overall overall; $coverage_within in the meetings that have tags |
| Report paragraphs | share of tags that are right | $reports_correct of $reports_checked |
| Questions of the general debates | share right at a probability of 0.9 or more (blind check) | 87 of 90 (97%) |
| Speakers | speaker and delegation right, on the page images ($speaker_round) | **$speaker_correct of $speaker_checked** ($speaker_pct) |
| Text, 1946–48 | characters read wrong ($cer_chars characters of $cer_docs documents) | $cer_vote |
| Text, 1949–66 | words read wrong per 1,000 (170 pages, `eval/vlm_pilot/results_blockC_local.md`) | the Commission's typescripts of 1949–54: 34–40 by the OCR, 5–7 by the vision model (its reading is the text where it passed the checks); the printed Third Committee records: 3–4 and 2–3 |

However, these samples were drawn at different dates (see the rounds above), each after the change it measures; a single audit of
about 300 random speeches, checked on the scans for every field at once, is planned for version 1.0.

**Read with care.**
- Check the scan before quoting: each segment gives the page, and `documents.jsonl` the link to the UN copy.
- A speaker may range beyond the article tagged; a tag says what the debate was about, not that every sentence is.
- The text of the worn 1947–48 typescripts has more OCR errors than the printed records of 1948 and later.
- Counting speeches is not counting influence: summary records give some delegates a line and others a page.

## Uses

The dataset is meant for finding the debates on a provision, a delegation's positions and the votes, and for studies of the
drafting across the three instruments. However, it is not meant to replace the UN record: quote the UN document, by symbol and page
or paragraph, after checking the scan.

## Distribution

The dataset is released on Zenodo ($doi). From version 1.0 the database can also be searched at
https://lszoszk.github.io/travaux-preparatoires/.

What this dataset adds to the documents (the division into speeches, the speakers and delegations, the article tags and the
concordance of drafts, the decisions and votes, the machine translations) is released under the Creative Commons
Attribution-NonCommercial-ShareAlike 4.0 International licence (CC BY-NC-SA 4.0). The text of the UN documents is the United Nations' and is
used under the UN Library's terms for non-commercial use: © United Nations, 1946–1966, https://digitallibrary.un.org,
downloaded in September 2026. The code that built the dataset is released under the PolyForm Noncommercial License 1.0.0.

## Maintenance

The author maintains the dataset. Errors can be reported to l.szoszkiewicz@amu.edu.pl, with the segment's `id`. Corrections
go into the next version; `CHANGELOG.md` lists what changed, and each segment keeps its `id` across versions unless the
segment itself is divided or merged (the code repository keeps a map of the old identifiers to the new ones).

## How to cite

Cite the UN document for anything you quote, by symbol and pinpoint, for instance "E/CN.4/SR.60, p. 10 (Malik, Lebanon)" or
"A/C.3/SR.290, paras. 7–15 (Hoffmeister, Czechoslovakia)". Cite the dataset as:

Szoszkiewicz, Ł. ($year). *UN Travaux Préparatoires: a speech-level database of the drafting records of the UDHR, ICCPR and
ICESCR* (Version $version) [Data set]. Zenodo. $doi
