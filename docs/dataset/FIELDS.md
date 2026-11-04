# Fields

Every file is JSON Lines (one JSON object per line, UTF-8). A field with no value is `null`. Dates are ISO 8601
(`1948-11-30`). An `id` of `segments.jsonl` is stable across versions unless the segment itself is divided or merged.

## documents.jsonl

One UN document.

| Field | Type | Meaning |
|---|---|---|
| `symbol` | string | the UN document symbol, for instance `E/CN.4/SR.60` or `A/C.3/L.88/Rev.1` |
| `instrument_corpus` | string | `UDHR` (the drafting of the Declaration, 1946–48) or `Covenants` (the Covenants, 1949–66) |
| `body` | string | the organ: `Commission on Human Rights`, `General Assembly Third Committee`, `CHR Drafting Committee` ... |
| `session` | string | the organ's session, for instance `3rd session (1948)` |
| `meeting_date` | string | the date of the meeting, or of the document |
| `doc_type` | string | the type given by the UN Library's research guide for the Declaration's documents (`summary_record`, `verbatim_record`, `resolution`, `working_paper`, `document`); every other document is `document`, so tell the meeting records by the symbol (`/SR.` for summary records, `/PV.` for verbatim records) |
| `pages` | integer | pages of the scan |
| `un_link` | string | the document's permanent UN link (`https://undocs.org/<symbol>`) |
| `pdf_url` | string | where the scan was downloaded: the UN's document server, or the University of Virginia's collection; `null` for the scans saved by hand |
| `source_language` | string | `fr` for a document held only in French, else `null` |
| `machine_translated` | boolean | `true` when the text is a machine translation from the French (not UN text: do not quote it as such) |
| `translation_model` | string | the model that made the translation |

## segments.jsonl

One piece of a document, in reading order.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | the segment's identifier: the symbol in lower case with `/` and brackets as `_`, a hyphen and the position (`e_cn.4_sr.60-0012`) |
| `symbol` | string | the document (`documents.jsonl`) |
| `seq` | integer | position in the document, from 1 |
| `kind` | string | `speech` (a delegate or representative), `chair` (a turn of the chair), `vote` (a decision with its outcome), `heading` (a heading of the record, for instance "Article 18"), `procedural` (an agenda item or a decision without a vote count), `footnote`, `closing` (the meeting rose ...), `paragraph` (a numbered paragraph of a report or other document) |
| `page_start`, `page_end` | integer | the pages of the scan where the segment starts and ends |
| `para_start`, `para_end` | string | the paragraph numbers the document prints, where it numbers them (the Commission's records from 1949, the Third Committee's from 1950, the reports); `para_end` is `null` for a single paragraph |
| `pinpoint` | string | the pinpoint to cite: `p. 10`, `pp. 10-11`, `para. 7` or `paras. 7-15` |
| `citation` | string | the citation of the segment: symbol, pinpoint and speaker, for instance `E/CN.4/SR.60, p. 10 (Malik, Lebanon)`; a machine-translated document's segments say so in brackets |
| `speaker` | string | the speaker's surname, in the form of the session's attendance list (where a typist misspelt it, `text` keeps the misspelling) |
| `delegation` | string | the State or organization the speaker represented |
| `speaker_method` | string | how the speaker was found (below) |
| `article_instrument` | string | `UDHR`, `ICCPR` or `ICESCR`: the instrument of `article` |
| `article` | integer | the final article under debate (the number in the adopted text), or `null` |
| `draft_article` | string | the number the article had in the draft the meeting worked from |
| `article_mapping` | string | where the tag came from (the heading, the chair, the session's report, the concordance of drafts) and the classifier's check; for an untagged speech, why a tag was dropped (for instance "not tagged: Jev judged the speech not about the article (p = 0.38)") |
| `article_confidence` | number | the classifier's probability that the speech is about `article` (0 to 1) |
| `topic` | string | for a speech of a general debate that no article fits, the question it is about (below), else `null` |
| `topic_confidence` | number | the classifier's probability for `topic` (0.9 or more) |
| `vote` | object | for `kind` `vote`: `outcome` (adopted, rejected ...), `yes`, `no`, `abstentions` (integers or `null`) and `unanimous` (boolean) |
| `review` | string | a note for checking, for instance a speaker not in the session's list of delegates |
| `text` | string | the text of the segment, as read from the scan (OCR: check the scan before quoting) |

**`speaker_method`**

| Value | Meaning |
|---|---|
| `vote_joint` | the name and delegation as the OCR engines read them, matched together with one delegate of the session's list |
| `roster_match` | the name matched with a delegate of the session's list (within the delegation where it is known) |
| `roster_token` | as `roster_match`, on one part of a compound surname ("SANTA CRUZ" and "Cruz") |
| `sole_delegate` | the name is unreadable, but the list has one delegate for that delegation |
| `text_name` | a clean name the record prints that the list does not have (an alternate, for instance); taken as printed |
| `text_org` | a representative of an organization or an office (for instance the Secretary of the Committee), as printed |
| `rapporteur (masthead)` | the rapporteur named in the record's masthead |
| `checked on the page image` | set by hand from the scan |
| `unresolved` | no speaker found (`speaker` is `null`) |

**`topic`**: `self_determination` (self-determination of peoples), `two_covenants` (one covenant or two), `implementation`
(measures of implementation), `petitions` (petitions from individuals and groups), `federal_clause`, `territorial_clause`
(the territorial or colonial clause), `reservations`, `form_of_bill` (the form of the International Bill of Rights, 1947–48),
`general` (the instrument as a whole, or several of these questions at once).

## decisions.jsonl

One decision a record reports.

| Field | Type | Meaning |
|---|---|---|
| `segment_id` | string | the segment that reports it |
| `symbol` | string | the record |
| `meeting_date` | string | the date of the meeting |
| `subject` | string | what was decided on, as the record words it |
| `outcome` | string | `adopted`, `rejected`, `decided`, `approved`, `accepted`, `defeated`, `carried`, `retained`, `deleted` ... |
| `yes`, `no`, `abstentions` | integer | the figures of the vote, where the record gives them |
| `unanimous` | boolean | the record says the decision was unanimous |
| `proposers` | list of strings | the delegations the record names as proposing what was voted on |
| `documents_named` | list of strings | the UN symbols the decision names (an amendment, a draft) |
| `roll_call` | object | for a roll-call vote: `yes`, `no` and `abstentions`, lists of the delegations as the record prints them, and `complete` (whether the lists add up to the figures) |
| `article_instrument`, `article`, `draft_article` | | as in `segments.jsonl` |

## amendments.jsonl

One document the records cite as an amendment or proposal.

| Field | Type | Meaning |
|---|---|---|
| `symbol` | string | its UN symbol |
| `mentions` | integer | how many segments cite it |
| `records` | list of strings | the records that cite it |
| `articles` | list of [instrument, article] | the final articles of the debates in which it is cited |
| `proposers` | list of strings | its sponsors |
| `proposers_from` | string | where the sponsors come from: `report` (the session's report) or `records`; `null` when none is known |
| `first`, `last` | string | the dates of the first and the last record that cite it |
| `in_corpus` | boolean | whether the document itself is in `documents.jsonl` |
| `decisions` | list of objects | the decisions that name it (outcome and figures) |

## concordance/

| File | What it holds |
|---|---|
| `articles.csv` | the final articles of the three instruments, with their short titles |
| `udhr_final.json`, `covenants_final.json` | the adopted texts, article by article |
| `drafts.csv` | the Declaration's drafts of 1947–48: each draft article with the final article it became (by text similarity, checked) |
| `udhr_drafts_early.csv` | the same for the texts of 1947, matched by hand |
| `udhr_early_meetings.csv` | which text each meeting of 1947–48 worked from |
| `covenant_drafts.csv`, `covenant_drafts_chr.csv`, `covenant_drafts_tc.csv` | the Covenants' drafts: the numbering of each session of the Commission (1949–54) and of the Third Committee (1954–66), with the meetings the reports list for each article |
| `report_sections.csv`, `report_annex_sections.csv` | the paragraphs and annexes of the session reports, read by hand with the article they concern |
| `amendment_sponsors.csv` | the sponsors of amendments as the session reports list them |
| `overrides.csv` | corrections made by hand to the concordance, with the reason |
