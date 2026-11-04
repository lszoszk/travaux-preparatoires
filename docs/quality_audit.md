# Article tags: overall audit (round 31, 24 September 2026)

The earlier hand checks each measured one kind of record, usually right after a change to it.
This audit measures the whole database as it stands: one fresh sample of tags from every kind
of record, and the first measure of coverage (how many speeches about an article get a tag).
Each item was judged by two independent readers against the full speech and its context.
They disagreed on 4 of 200 items, which were settled by hand. Figures:
`python3 eval/quality_audit.py`. Verdicts are in `data/gold/article_tags.jsonl` (round 31)
and `data/gold/coverage.jsonl`.

## Precision

110 tags, in proportion to each kind's share of the 7,231 tagged speeches:

| Records | Right | 95% interval | Tags |
|---|---|---|---|
| Third Committee 1954-61 | 24/26 | 76-98% | 2,110 |
| Commission 1949-54 | 23/24 | 80-99% | 1,883 |
| UDHR, Commission 1948 and Third Committee 1948 (E/800 numbering) | 13/16 | 57-93% | 1,234 |
| Third Committee 1962-66 | 8/12 | 39-86% | 701 |
| UDHR, Drafting Committee 1948 (E/CN.4/95) | 8/10 | 49-94% | 526 |
| UDHR 1947-48 (outline, Cassin, Drafting Committee I, Geneva draft) | 9/10 | 60-98% | 462 |
| ICCPR, Drafting Committee on the Geneva draft Covenant (May 1948) | 6/6 | 61-100% | 191 |
| Geneva plenary, December 1947 | 5/6 | 44-97% | 124 |

Weighted by each kind's share of the tags, **88% ± 6** (raw 96/110). The rounds that measured
one kind at a time found 95-100% (1952-53: 57/60; 1962-66: 38/40 and 30/30). The per-kind
figures here rest on 6-26 items each and have wide intervals. The Third Committee 1962-66 row
(8/12) is well below rounds 29-30 (68/70). Two of its four errors are the same issue: the debate
on the number of ratifications, under draft article 26 in 1966 (SR.1407-1410), which went into
article 27. Round 29 also found it once, so these tags need a rule of their own.

**The 14 errors**, by kind:
- **Stale context (5).** The article in force had changed without a heading or a chair line
  the rules read. Examples: A/C.3/SR.143, draft 21 kept during the debate on draft 22; the
  Geneva working group's SR.9, after article 13 was finished.
- **Procedure (4).** Suspending the meeting, the order of votes, the Chairman's discretion.
- **A paragraph that became another article (2).** The number of ratifications in draft
  article 26 (1966) became ICESCR 27, not 26.
- **A passing chair mention (2).** In A/C.3/SR.787 the chair mentioned article 15 during the
  debate on article 14.
- **Concordance (1).** E/CN.4/56 article 19: its second sentence is ICCPR 26 material, but the
  tag was ICCPR 2.

## Coverage

90 untagged speeches over 150 characters were judged for whether they are nonetheless mainly
about one specific article:
- 35 of 50 in records that have tags (70%);
- 6 of 40 in records with no tag at all (15%).

Taken with the correct tags, about **60%** of the speeches about an article are tagged, and
**72%** in the meetings that have tags. Precision was preferred throughout, and the rules leave
a speech untagged when unsure.

Why the 41 speeches were missed:
- **No article context (21).** Meetings on several articles at once with no heading between
  them; articles proposed without a number (1953, 1966); records whose headings the OCR lost.
- **Number not mapped (12).** Mostly the Commission's paragraph numbers ("article 9,
  paragraph 2" in 1950: 7 cases), which only the Third Committee stages read as their article.
  The rest are numbers of deleted or renumbered articles.
- **Dropped by Jev (8).** For example E/CN.4/SR.317 (the asylum proposals) and A/C.3/SR.1404
  (the natural-resources article).

## What would help most

1. Read the Commission's paragraph numbers as their article (as for 1962-66), under the
   meeting check. This is about a third of the misses in the sample.
2. Meeting lists for the Third Committee's 1954-61 sessions, whose reports are not in the
   collection (A/3077 ... A/5000). They would settle the stale context there.
3. Tag the 1966 debate on the number of ratifications (draft 26, SR.1407-1410) as ICESCR 27.
4. Keep a chair's passing mention of another article from setting the context (A/C.3/SR.787).

## After the audit: the first three fixes (round 32)

- **The Commission's paragraph numbers** ("paragraph 2 of article 9") now count as their
  article in every Commission stage, under the meeting check: +269 tags (mostly 1950 and
  1952; 5 in 1949, whose session has no meeting lists).
- **The 1966 debate on the number of ratifications** under draft article 26 is now ICESCR 27.
  This applies where a speech opens on the entry into force rather than on who may become a
  party, and dwells on it more: 8 speeches, including the audit's two errors.
- **The chair looking ahead** ("when considering article 15", "in connexion with article 20",
  "later") no longer sets the article in the Covenant records. The window stops at the
  sentence, so "(2) Article 40" after "until after the discussion on article 40." still does.
  A speech whose opening the OCR ran into a heading's tail ("A/C.3/L.625) (continued) 1.
  Mr. X") no longer sets the article. A/C.3/SR.787 (38 speeches) went from ICESCR 14 to 13.

Jev dropped 8 of the new tags; 7,382 tagged speeches. A hand check of the changed tags
alone (round 32, two judges): 30/30. The audit's figures above are as measured before these
fixes.

## The Third Committee's 1955-61 meeting lists (round 33)

The seven reports (A/3077 ... A/5000) were downloaded by hand in a browser and read, one reader
each. Each article's meetings were checked against the contents the printed records give on
their first page ("Article 14 of the draft Covenant on Economic, Social and Cultural Rights
(continued)"): 166 of 173 meetings agree. Where the contents name an article for meetings the
report leaves unassigned, they were added (SR.795, SR.862-865, SR.1028). 1955-61: 2,110 -> 2,369
tagged speeches. Hand check, round 33 (two judges, full agreement): 36/40 on a fresh sample of
the years' tags and 19/20 on the new tags alone. All 5 errors are procedural speeches (the order
of votes, a late oral amendment, the order of work), the error the audit found most often.

## Procedural speeches (round 34)

The commonest wrong tag left is a short speech about how the meeting proceeds. Jev's article
check gives these middling probabilities (median 0.67), which a higher threshold cannot separate
from the right tags: at 0.7 for speeches under 100 words it would drop 25 right tags to remove 11
wrong ones. So Jev was asked a second question about the 5,294 tagged speeches under 200 words:
is the speech mainly about the organisation of work? That covers taking up, deferring or
re-opening an article, the order of work, the basis of discussion, merging amendments,
suspending the meeting, and the rules. The vote on the article's text counts as the article's,
as in the hand checks. A first wording, which counted roll-calls and the order of votes as
procedure, dropped as many right tags as wrong ones and was set aside.

A hand check of 30 of the tags the second wording dropped at 0.7 found that band net harmful
between 0.7 and 0.8 (3 wrong, 6 right, 3 split). At 0.8 and above almost all were wrong (16
wrong, 0 right, 2 split). At 0.8 it drops 91 tags (7,550 left); on this evidence about 9 in 10
of them were wrong. `eval/jev_procedure_check.py`; answers cached in
`data/cache/jev_procedure_v2.json`.

## The audit repeated (round 35, after the fixes)

Same design as round 31, on the database as it now stands (7,550 tagged speeches): a fresh
sample of 110 tags in proportion to each kind of record, and 90 untagged speeches over 150
characters, none of them judged before. Two judges per item; they disagreed on 7 of 200, which
were settled by the rules the procedure check uses (the order of votes and separate votes are
the article's; re-opening a decision and the basis of discussion are not).

| Records | Round 31 | Round 35 |
|---|---|---|
| Third Committee 1954-61 | 24/26 | 29/30 |
| Commission 1949-54 | 23/24 | 23/26 |
| UDHR, E/800 numbering (1948) | 13/16 | 15/16 |
| Third Committee 1962-66 | 8/12 | 11/12 |
| UDHR, Drafting Committee 1948 | 8/10 | 9/10 |
| UDHR 1947-48 | 9/10 | 8/8 |
| ICCPR, May 1948 | 6/6 | 3/4 |
| Geneva plenary 1947 | 5/6 | 4/4 |
| **Weighted precision** | **88% +/- 6** | **93% +/- 5** |
| Untagged speeches about one article, records with tags | 35/50 | 32/50 |
| ... records without tags | 6/40 | 10/40 |
| **Coverage** (records with tags / overall) | 72% / 60% | 75% / 57% |

Precision rose from 88% to 93%. The intervals overlap, but the rise is what the fixes lead one
to expect: the Third Committee's meeting lists and the procedure check. The 8 errors left:
- stale context (3);
- procedure (2);
- the wrong one of two neighbouring articles (2): the Commission's 1950 final clauses, and
  the expulsion of aliens under E/600 article 12;
- a segment that ran two speeches together (1).

Coverage is about where it was. Within the meetings that have tags it rose from 72% to 75%,
which is what the paragraph numbers and meeting lists should give. The overall figure rests on
40 speeches from untagged records, which found 6 and then 10 about an article (intervals 7-29%
and 14-40%). Taken together, 16 of 80 (20%) gives an overall coverage of about 60%. Most of
those speeches sit in records with no article context at all: meetings on several articles at
once, articles proposed without a number, and sessions whose report was not read (1954,
1964-65).

## Coverage: Jev's choice among a meeting's articles, and the records the relevance filter had left out (round 36)

**Jev's choice.** Most of the untagged speeches about an article sit in meetings on several
articles, where the record gives no heading. Where the session's report lists the meeting's
articles, Jev now chooses among them for each untagged speech over 150 characters
(`eval/jev_article_choice.py`). The options are named as the record numbers the articles, with
the final article in brackets. A deleted draft, a proposal with no final article and "none"
are options too. A first labelling by final number took draft article 28 (deleted in 1966) for
the final article 28. On the 50 coverage-judged speeches, choices at 0.9 or more were 20 of 20
right, so the threshold is 0.9. Those tags then go through Jev's article and procedure checks.

**The relevance filter.** At harvest time `pipeline/ocr_all.py` kept only records whose ODS
text layer named the Covenants on their first two pages. The 1949-54 mimeographs' text layers
are often garbled, so 113 Commission records were left out. Among them were meetings the
session reports give to covenant articles (SR.303, 320, 323, 324, 330, 351, 353) and the 1952
debate on self-determination (SR.252-265). `pipeline/relevance_recheck.py` read their first
two pages with Apple Vision; 52 now pass. With them come 21 documents not on ODS, downloaded
with the user's approval from the University of Virginia's travaux collection (a public S3
copy): E/1681 (the 1950 report) and 20 of the Commission's 1951 records (SR.202-250).

1,761 records (was 1,695); 24,729 speeches (was 23,538); 8,830 tagged speeches (was 7,550), of
which 921 come from Jev's choice. Hand check, round 36 (two judges, two splits settled):
- the choice tags, 38/40. The errors: a clause of draft article 38 that became ICCPR 30(4),
  and a proposal numbered in its own way ("article 3 (formerly 4)");
- the rule tags in the newly added records, 18/20. The errors: a procedural remark, and E/1371
  article 14 tagged 14 rather than 15.

Coverage should now be well above the 60% measured before; it has not been measured again.

## Coverage measured again (round 37, after Jev's choice and the added records)

110 untagged speeches over 150 characters, none judged before: 50 from records with tags and
60 (was 40) from records without. Two judges each; 5 splits were settled by the usual rules.

| | Round 31 | Round 35 | Round 37 |
|---|---|---|---|
| Records with tags: untagged speeches about one article | 35/50 | 32/50 | 29/50 |
| Records without tags: the same | 6/40 | 10/40 | 7/60 |
| **Coverage within records with tags** | 72% | 75% | **78%** |
| **Coverage overall** | 60% | 57% | **69%** |

The precision used in the formula is round 35's (92%), weighted by today's tags. Round 36
measured the choice tags at 38 of 40, so the figure should still hold.

Within records with tags, coverage rose by three points. The pool there also grew, because the
52 records added are only partly tagged. The overall figure rests again on the untagged
records, and that sample remains the least certain part: 6/40, 10/40 and 7/60. Pooled (23 of
140, about 16%), overall coverage comes to about 66%.

What is still missed:
- no article context (24);
- speeches Jev dropped (7);
- numbers not mapped (5, down from 11 after the paragraph-number fix).

## The Third Committee's 1948 headings (round 38)

The Third Committee's printed records of 1948 (A/C.3/SR.88-179) print a footnote marker after
each new article heading. The footnote gives the article's number in A/777. The OCR reads the
marker as a last digit: "ARTICLE 71" is article 7 and "ARTICLE 201" is article 20. It sometimes
reads it as a sign instead ("ARTICLE 16}"). The records also run a heading into the end of the
passage before it ("... by the end of the month. ARTICLE 201"). There it was not read as a
heading at all, and the OCR misread some headings too ("Articte 3", "Axticte 3"). Whole
records were left without tags (SR.103, 105, 137, 149, 153). Some tags went to the next
article: SR.143's debate on draft article 22 was tagged 23, and SR.155's on draft article 28
was tagged 29.

`api/build_db.py` (`headings_1948`) now reads these headings in the order of the meetings. The
Committee took E/800's 28 articles in order. A three-digit number, or a two-digit number over
28, loses its last digit. For other two-digit numbers, the heading keeps its number when it
follows the last heading (e.g., "ARTICLE 25" after article 24). It loses its last digit when
only the first digit follows (e.g., "ARTICLE 21" after article 1). A run-in heading sets the
article from the next passage on. Nothing outside the 1948 records changed.

In the 1948 records, 1,362 speeches are now tagged (was 1,222). 702 untagged speeches over
150 characters are left (was 838), and 21 records have no tag (was 26). 16 tags moved to
another article. All the new and changed tags went through Jev's article and procedure checks.
Of the moved tags, 2 were dropped by Jev.

Hand check, round 38: 40 tags (36 new, 4 moved), two judges, who agreed on all 40. 39 of the
40 were right. The error was a speech on where to place the Mexican amendment (amparo,
later article 8) that was tagged with article 7.

The 21 records still without tags are mostly other business:
- the general debate (SR.88-94);
- Palestine refugees (SR.108, 117);
- the right of petition and minorities (SR.159-163);
- the additional articles and the preamble (SR.164-167);
- the vote on the whole declaration (SR.179).

**Jev's choice in the 1948 records (round 39).** A/777 gives the Committee's meetings on the
Declaration only as ranges. It lists meetings for no article. The choice
(`eval/jev_article_choice.py`) therefore takes its options from the articles the record's own
headings and chair give the meeting, numbered as E/800 numbers them. It adds an option for
another article (one not listed, a new article, the preamble). Where a meeting had more than
one article, a speech Jev judged not about its article is asked too.

Of 228 speeches asked, Jev chose an article for 62 and "none" for 153. 27 choices reached 0.9.
15 of them fall on speeches the rules treat as procedural: requests for a roll-call, with the
roll-call merged into the speech. Those stay untagged. 12 tags were added. Hand check, two
judges, who agreed on all 12: 11 were right. The error was a speech on the Lebanese amendment
to draft article 28, after article 27 had been adopted, which was tagged with article 27.

## The Commission's 1949-50 agendas (round 40, from the research check on ICCPR 6)

The research check on ICCPR article 6 (`docs/research_check_iccpr6.md`) found that
E/CN.4/SR.98 (1949) has no article tag. It holds the decisive votes on paragraph 1. Its record
prints no heading, and only the agenda on its first page names the article: "Article 5
(discussion continued)". For the Commission's 1949-50 stages, the article the agenda continues
now opens the meeting. That adds 96 tags in 10 records, and none is lost. The rule does not
apply from 1951: there the reports' meeting lists place such speeches, and the agenda's
article can be done with early in the meeting (SR.324).

Hand check, round 40: 30 of the new tags, two judges, who agreed on all 30. 29 were right. The
error was a motion to defer the vote on draft article 8.

## The reports tagged by section (round 41)

The reports of the Commission (1949-54) and of the Third Committee (1955-66) carried almost no
article tags. The Commission's reports held under their E/CN.4 symbols (E/CN.4/350 = E/1371,
E/CN.4/669 = E/2256, E/CN.4/689 = E/2447, E/CN.4/705 = E/2573) and the Third Committee's reports
of 1955-61, saved by hand, came from `covenants_alt.json`, which `api/build_db.py` loaded as
Declaration documents. The others had no stage, and their headings are often lost to the OCR.
Two reports were held twice (E/1992 and E/CN.4/640, E/1681 and E/CN.4/507).

Now:
- `covenants_alt.json` is read as Covenant documents, and a report held under both symbols is
  loaded once, under its E/ symbol. That leaves 1,759 records and reports, and 4,642 decisions
  instead of 4,763, 121 of which were counted twice.
- 16 reports have a table of sections (`data/concordance/report_sections.csv`, 388 rows): each
  run of numbered paragraphs about one article, with the final article it became. One reader per
  report wrote the table and a second checked every row against the text and the concordances.
  Sections about no one article (introduction, general debate, several articles, the
  implementation articles later deleted, other items, the Optional Protocol) are "none".
- A report paragraph takes the section of the last paragraph number that follows on. A heading
  ends a section: an article's heading opens the next section when that is the article's,
  since its first paragraph number may be misread. Any other heading leaves what follows
  untagged until the next paragraph number. The annexes are not tagged.

The reports' paragraphs now carry 3,062 tags. Their decisions carry 823 (was 186 of 1,504). In
A/6546, article 6 of the Optional Protocol is no longer tagged ICCPR 6. The body's articles
39-41, which the running heading had tagged 39, now carry 40 and 41. The annex texts lose
their heading-based tags.

Hand check, round 41: 39 report paragraphs, 20 at random and 19 at the edges of sections. Two
judges agreed on all 39. 19 of the 20 random paragraphs were right, and 16 of the 19 at the
edges. All four errors were headings, or a quotation under a heading whose paragraph number the
OCR misread ("52." for 32.). The heading rule above corrects all four; it was written after this
check, and no fresh sample has been drawn since.

## The reports' annexes: governments' amendments, proposals and comments (round 42)

The Commission's reports (1949-54) print the governments' and members' amendments, proposals
and comments in their annexes. The Third Committee's reports have no such annexes, and the
separate collections of comments (E/CN.4/353, A/2910) are not in the database.

The annexes of the six Commission reports (E/CN.4/350, E/1681, E/1992, E/CN.4/669, E/CN.4/689,
E/CN.4/705) now have a table of sections (`data/concordance/report_annex_sections.csv`, 569
rows). It has a new row wherever the article or the author changes. Each row gives:
- the page and the opening words of the segment where the section starts;
- the final article;
- the article as the annex numbers it;
- the author.

One reader per report wrote the table and a second checked every row. Annexes holding the
draft text itself are one "none" row each, since those texts are in the article histories
already. The author replaces the delegation the segmenter had read from a heading. For
instance, comments by several governments had all been credited to India or the Philippines.

805 annex segments and 108 annex decisions now carry their article. With the bodies, 3,867
report paragraphs are tagged.

The readers tagged some rows "ICCPR+ICESCR" with the ICESCR number for final clauses the two
covenants share: signature, the federal clause and amendments (ICESCR 26, 28, 29; ICCPR 48,
50, 51). Those 11 rows are now tagged ICESCR, and their notes give the ICCPR article. A segment
takes one number, and "both" holds only where the number is the same in both covenants.

Hand check, round 42: 30 annex segments, two judges, each judging the article and the author.
The article was right in 28 of 30:
- one error is the federal clause tagged ICCPR+ICESCR 28, fixed as above;
- the judges split on a footnote segment listing documents.

The author was right in 28 of 30:
- a proposal of the Commission on the Status of Women had no author, and now has one;
- a Yugoslav amendment as amended by China (E/CN.4/689, p. 72) stays with Yugoslavia.

## Sponsors of amendments, from the reports

The research check on ICCPR 6 found wrong or missing sponsors:
- L.654, the five-Power conception clause, had none;
- L.655, the Working Party's report, was credited to Japan;
- L.644 had Uruguay only.

The parser that reads sponsors from the records misses adjective lists ("the
Colombian-Uruguayan amendment"), sub-amendments and footnotes. The reports list the sponsors
plainly: "Amendments were submitted by Colombia and Uruguay (A/C.3/L.644), France (A/C.3/L.645)".

`pipeline/amendment_sponsors.py` reads those lists from the tagged reports, strictly. It takes a
sponsor only where the words before the symbol are state names and joining words, a
representative's proposal, an adjective, or a body ("In its report (A/C.3/L.655), the Working
Party"). Where the words tie a symbol to two parties ("the amendment of X to the Y amendment
(L.648)"), it reads nothing. It also reads a bare "(L.645)" in the series of the last full
symbol in the paragraph, and credits a corrigendum's sponsors to its document.

The result, `data/concordance/amendment_sponsors.csv`, covers 504 amendments:
- For 329 of them the sponsors agreed with those read from the records.
- The other 204 were checked by hand (with 20 of those that agreed):
  - 185 were right;
  - 10 were symbols the OCR had cut short or misread (e.g., "L.65" for L.654), each moved to
    its true symbol;
  - 5 lacked co-sponsors;
  - 4 were wrong. One of them, A/C.3/L.460, is the compilation of amendments, not Brazil's.

The corrections are in `amendment_sponsors_checked.csv`, which the script applies every time it
is run. The article histories, the amendment list and the MCP server take the reports' sponsors
first. A decision on a single amendment the reports list takes its sponsors: 129 decisions
changed, 102 of which had no sponsor.

Of the 1,565 L-series documents cited, 647 still have no sponsor (was 774). Most are ones the
reports do not list: the Commission's amendments of 1949-54 cited only in its records, and the
1948 series.

## The audit repeated (round 43, 26 September)

The audit was drawn again on the current database, after:
- the 1948 headings;
- Jev's choice in 1948;
- the 1949-50 agendas;
- the reports and their annexes;
- the vote parser's OCR tolerance.

The samples:
- 126 fresh tagged speeches, drawn in proportion to each kind's tags;
- 30 fresh report paragraphs, measured on their own and not weighted into the speeches'
  figure;
- 110 untagged speeches never judged before: R1, 50 from records with tags; R2, 60 from records
  without.

Two judges judged each item, and a third settled the 6 on which they split.

| | Round 31 | Round 35 | Round 43 |
|---|---|---|---|
| Precision, weighted by tags | 88% ± 6 | 92.8% ± 4.8 | **94.8% ± 3.8** (119/126) |
| Report paragraphs | | | 29/30 |
| Records with tags: untagged speeches about one article | 35/50 | 32/50 (r. 37: 29/50) | 28/50 |
| Records without tags: the same | 6/40 | 10/40 (r. 37: 7/60) | 12/60 |
| **Coverage within records with tags** | 72% | 75% (r. 37: 78%) | **80%** |
| **Coverage overall** | 60% | 57% (r. 37: 69%) | **67%** |

Precision by kind:
- Commission 1949-54: 37/40.
- Third Committee 1954-61: 32/34.
- Third Committee 1948 (UDHR): 19/19.
- Third Committee 1962-66: 11/11.
- Commission 1948 (UDHR): 7/8.
- The 1947-48 drafting and the Geneva plenary: 13/14.

The seven wrong speech tags:
- five are short procedural speeches: a promise to speak later, reserving rights on comments,
  "no procedural problem", asking for a vote and closure, "the matter should be referred
  back";
- one is a neighbouring implementation article: draft article 48, on convening the Committee,
  tagged 39 rather than 37;
- one is equal pay tagged with non-discrimination (Geneva, 1947).

The wrong report paragraph is the line that introduces a government's comments in an annex,
just before its first article.

Coverage overall stays near two thirds. The records without tags vary most from sample to
sample: 6/40, 10/40, 7/60, 12/60, which pooled is 35 of 200 (17.5%). Of the 40 untagged
speeches judged to be about an article, 32 have no article context, mostly in the Commission's
records of 1949-54 and in the Third Committee's of 1955-66. The other 8 had their tags dropped
by Jev.

## The offline tagger's proposals (round 44)

An offline tagger was written by an outside model (Codex) from the brief
`docs/codex_task_article_tagger.md`, and its report is in `docs/article_tagger.md`. On the dev
split it reached 0.78 precision at 0.9 (recall 0.09). The test split gave it no proposals at its
review threshold. Its 100 proposals at 0.95 were judged blind by two judges, with a third on
splits: **93/100 right** (86-97%). The Commission's records did best (1946-48 17/18, 1949-54
45/46), and the Third Committee's did worse (31/36). The 93 were added by hand
(`data/tagger/accepted.csv`), which brings the tagged speeches to 9,185.

## Jev's choice extended to every meeting record without a report list (round 45)

Jev's choice among a meeting's articles had used the reports' meeting lists (1951-66) and, in
1948, the record's own headings. It now also covers every other meeting record that no report
list covers:
- the Commission and its Drafting Committee and working groups (1947-54);
- the Third Committee's records outside the lists.

The options are the articles the record's own headings, chair and context give the meeting
(Declaration or Covenant articles, as tagged), with "another article" and "none". The
question and options are in `eval/jev_article_choice.py` (`candidates_records`,
`options_record`). A speech Jev had judged not about its context article is asked only where
the meeting had other articles.

1,210 speeches were asked, and 137 tags were added at a choice of 0.9 or more, after Jev's
article and procedure checks:
- the Commission: 69;
- the Drafting Committee: 45;
- the working groups: 20;
- the Third Committee: 3.

No tag was lost. Hand check, round 45: 40 of the new tags, blind, two judges, who agreed on all
40. 38 were right. Both errors were neighbouring articles: a Geneva assembly article tagged
with association, and an amendment on medical experimentation tagged with the right to life.
Tagged speeches: 9,322.

## Coverage measured again (round 46, after the tagger's and the extended choice's tags)

110 untagged speeches over 150 characters, none judged before: 50 from records with tags (R1)
and 60 from records without (R2). Two judges each, and a third on the 4 splits.

| | Round 37 | Round 43 | Round 46 | Pooled 37-46 |
|---|---|---|---|---|
| R1: untagged speeches about one article | 29/50 | 28/50 | 32/50 | 89/150 |
| R2: the same | 7/60 | 12/60 | 16/60 | 35/180 |
| Coverage within records with tags | 78% | 80% | 79% | **80%** |
| Coverage overall | 69% | 67% | 63% | **67%** |

The 230 tags added since round 43 (93 from the offline tagger, 137 from the extended choice) are
about 2.5% of the tags. On samples of this size that is less than the noise: R2 alone went from
12/60 to 16/60. `eval/quality_audit.py` now also gives the estimate pooled over the last three
measures, and the About page shows it next to the latest.

Of the 48 untagged speeches judged to be about an article:
- 41 have no article context: 18 in the Commission's records of 1949-54, 12 in the Third
  Committee's, and the rest in the 1947-48 records;
- 7 had their tag dropped by Jev.

**The tagger's proposals at 0.90-0.95 (round 47).** 48 of 57 right (84%, 73-91%), the judges
agreeing on all. Only the 48 hand-checked tags were added. Tagged speeches: 9,370.

## Segmenting again, with the ids kept (round 48)

Seven segmentation fixes from the two research checks (ICCPR 6, ICESCR 11) had waited because they
shift segment ids, and the hand checks, Jev's caches and the tagger's accepted list all refer to
those ids:
- Covenant headings in small capitals ("ARTICLE 13 oF THE DRAFT CovENANT", A/C.3/SR.743);
- "Kr." for "Mr.";
- curly quotes and bullets before a paragraph number or "The CHAIRMAN";
- delegations up to 100 characters ("Director-General of the Food and Agriculture Organization",
  A/C.3/SR.1232);
- "Article 5 (discussion continued)";
- report paragraph numbers the OCR garbled ("12h." for 124), taken only as the next number;
- French detected only from lower-case words, so that "Mr. AUJAY DE LA DURE (France)" is not
  dropped as French (A/C.3/SR.1267).

`pipeline/resegment.py` segments everything again (`build_all.py --no-db`). It then aligns each
changed record's old and new segments word by word and moves every id-keyed file to the new ids:
- the gold;
- Jev's caches;
- the tagger's lists;
- the amendment sponsors;
- the Geneva maps.

The map is kept in `data/id_maps/2026-09-28.json`. A first run with no change reproduced every
segment. This run changed 406 records:
- 17,546 segments stayed as they were;
- 14,909 moved;
- 293 were split;
- 25 were merged;
- 5 were lost (segments without words, to which nothing referred).

Speeches rose from 24,729 to 24,899, and speaker evaluation stayed at 1.000 on all three sets.
One report annex anchor had to allow a heading joined to its first line.

After Jev's checks on the new and changed tags, the tagged speeches went from 9,370 to 9,418.
Among the lost tags, four were at E/CN.4/SR.129, which had been tagged with the federal clause
(draft article 24 -> ICCPR 50). The re-split chair's segment shows that the Commission deferred
article 24 and went on to article 25, the colonial clause, which has no final article. Two
earlier hand judgments had passed those tags. Hand check of 30 of the new tags, blind: 29 right.
The error was a speech about the order of work.

## Round 49: the 1947-48 segmentation fixes (28 September 2026)

The fixes the article 18 research check asked for (`docs/research_check_article18.md`, group 1):
- "Ma," "M:" and "Lr." for "Mr.";
- a curly or square bracket before the delegation;
- a title after the name ("AZMI Bey");
- garbled chair lines ("The CHAIPMAN");
- joint headings ("Articles 17 and 18").

`pipeline/resegment.py` ran a second time. It changed 285 records: 10,104 segments moved, 311
were split, 3 were merged and none were lost. The map is `data/id_maps/2026-09-28-2.json` (map
names now carry the time, so a second run on the same day keeps the first map). Speeches rose
from 24,899 to 25,135, and speaker evaluation stayed at 1.000 on all three sets.

Two regressions followed:
- At E/CN.4/SR.182 a new chair segment ("whether the atrocities contemplated under article 7
  were ... covered by article 5") moved the context to article 5, untagging 14 speeches on
  ICCPR 7. In Covenant records "covered by / dealt with in / provided for in article N" now
  names where something else belongs, as it already did for the Declaration. This also fixed
  E/CN.4/SR.107, where a gold judgment of round 11 had found article 9 wrongly winning over
  the heading's article 13 (ICCPR 14).
- At E/CN.4/SR.268 the joint heading "Articles 20, 21 and 22" set article 20 (ICESCR 6), and
  Jev's check then dropped the speeches on article 21. Jev's choice for a record now offers
  the other articles of its joint headings too.

After Jev's checks and choice on the new candidates (292 asked), the tagged speeches went from
9,418 to 9,618. Blind checks, two judges each, who agreed on every item:
- 30 new speech segments: 26 split right, 29 speakers right, 6 of 6 tags right. The wrong
  splits are further speakers garbled beyond the new patterns ("SEMI Bey (Ezrpt)", "Mire NISOT")
  and a chair's ruling left inside a speech.
- 20 of the 96 tags Jev's choice added: 19 right. The error, at E/CN.4/SR.348, is on the
  election of the Committee's members (ICCPR 30), tagged 31. The judges also noted draft numbers
  that do not match the record's (the choice records the draft number most used for that final
  article in the meeting).

## Round 50: the reports' annexes article by article (28 September 2026)

Item 2 of the article 18 check's list. Readers, one per document or group of annexes, each
checked by a second (12 agents), split these texts into rows of
`data/concordance/report_annex_sections.csv`, one row per article or alternative text, each
with its final article:
- the draft covenant texts of E/CN.4/350, E/1992, E/CN.4/669 and E/CN.4/689 (formerly one
  untagged row each);
- the 1947 Drafting Committee report E/CN.4/21 (the Secretariat outline, the UK draft bill,
  the US suggestions, Cassin's articles in English and French, the Committee's revised
  articles, the articles for a convention, the Secretariat's memorandum).

Hand-set rows also cover E/CN.4/113 and A/4625's annex.

The anchors are now taken from the segments themselves and matched on their full 40
characters, not the first 30. In E/CN.4/669 two paragraphs open "1. Everyone shall have the
right to", so the row for the opinion article had landed on the religion article
(`tests/test_parsers.py::test_annex_anchor_full_length`). All anchors are found.
`build_db` now applies report rows to the Declaration's documents too.

1,114 report passages gained a tag, and none outside these documents changed. Tagged
decisions went from 2,594 to 2,600. The UK draft (annex B) and the articles for a convention
(annex G) became two Covenant draft stages (24 texts, anchored by one reader and checked by
a second).

Blind check, two judges who agreed on every item: 28 of 30 right. The errors: in Cassin's
art. 7, the sentence on torture (UDHR 5) was tagged with the article's first sentence (UDHR 3),
and a stray heading at the foot of a page was tagged with the article before it. Both are
fixed, the torture sentence in the English and French texts alike.

## Round 51: decisions in other wordings (28 September 2026)

Item 3 of the article 18 check's list. Of the passages that give vote figures, 551 had given no
decision. They showed these forms, which `pipeline/decisions.py` now reads:
- active sentences ("The Commission rejected the Polish proposal by 7 votes to 3");
- figures first ("By 19 votes to 12, the Committee decided to meet on that date");
- results in brackets ("(Adopted by 8 votes to 1)");
- "votes for ... against" in words;
- the OCR's forms of "was" and of the verbs, and stray marks around the figures.

"Rejected by 7 votes to 3" still counts 3 in favour, but "by one vote in favour to seven
against" is taken as written. The clause "if he so desires", when those are the words put to
the vote in the sentence before, no longer makes the vote look conditional (the check now
stays within the vote's own sentence). An anaphoric subject ("It was then rejected") takes in
only the subject of a vote in the sentence before, not its figures. Roll-call lists keep
names that contain "and". The proposers of an item exclude those who "seconded",
"supported" or only suggested a change ("amended at the suggestion of").

Decisions went from 5,002 to 5,304 and tagged decisions from 2,600 to 2,761. Decisions with
figures went from 3,729 to 4,017, and complete roll-calls from 86 to 156. No segment lost its
decisions. The sponsor evaluation is unchanged (exact precision 0.925, recall 0.745).

Blind check of 40 of the new decisions, two judges (`data/gold/decisions.jsonl`, a new file):
- 40 of 40 are decisions taken there, with the right outcome;
- figures: 33 right, 6 wrong, 1 split. Three of the wrong ones had lost their abstentions and
  are now read ("to.3.with", "epstentions", ". With"); the others are digits the OCR garbled
  ("1 votes to 2" for 14 to 2);
- subjects: 33 clear, 4 too short (e.g. "the Committee"), 3 split;
- the article, where given: 22 of 23 right (1 split);
- proposers: 36 right. The wrong ones:
  - suggesters counted as proposers (now fixed);
  - the United States named for a procedural decision on its amendment.

## A/777's numbering (28 September 2026)

The article 18 check found A/777 staged as "final". A/777 has 31 articles, and the plenary
deleted its article 3, so from article 4 on its numbers are one higher than the final
text's. Every vote at the plenary of 10 December 1948 (A/PV.183) was therefore tagged one
article too high: "Article 19" (religion) as UDHR 19, and so on.

What changed:
- A/777, the 1948 plenary records and the amendments to A/777 now use stage `a777`, mapped
  in `overrides.csv`. A/RES/217(III) keeps the final numbering.
- A/777's text was read article by article (30 rows, 31 draft texts, a reader and a checker),
  so it is a stage in each article's history.
- In the Declaration's records, votes on the preamble, a resolution, the whole Declaration or
  a group of articles carry no article. These were 15 decisions, among them the plenary's
  vote on the Declaration (48-0-8), which had been tagged article 2.
- "Article 12, paragraph 2, of the Charter" is now read as the Charter's article
  (`OTHER_TEXT_RE`). In the Covenant records this keeps chair lines that cite the Charter,
  the ICJ Statute or the Declaration with a paragraph number from moving the context. In
  E/CN.4/SR.120, SR.348 and SR.358, 17 speeches gained a tag; Jev's checks ran on them.

Tagged decisions went from 2,761 to 2,746 and draft texts from 719 to 750.

## Round 52: sponsors and references (28 September 2026)

These are the sponsor findings of the article 18 check (group 7), fixed as classes where that
was possible:
- document symbols the OCR spaced out ("A/C.3/ 247"), read with an l or 1 for L, or glued to a
  committee number ("A/C.38");
- a table for one passage's misread symbol (`ref_fixes.csv`: L.145 for L.143 at SR.319);
- a table of hand-checked proposers of a decision (`decision_proposers_checked.csv`: "or to
  adopt", the United Kingdom's);
- the mover of a procedural motion;
- hyphenated names;
- "his amendment" only when no other delegation's representative is named before it;
- 15 sponsors added by hand;
- a compilation kept with no sponsor.

`pipeline/resegment.py` moves both new tables with their segments. The number after a series
may no longer run into letters or more digits ("A/C.3/ 1027th meeting" is not a document), and
a new series may not start inside a symbol ("E/CN.4/ E/CN.4/631").

References went from 19,091 to 20,672, and those with a proposer from 5,643 to 6,321. The
sponsor evaluation rose from exact precision 0.925 and recall 0.745 to 0.941 and 0.764.

Blind check of 30 references that are new or whose proposers changed, two judges who agreed
on all (`data/gold/refs.jsonl`, a new file):
- symbols: 30 right;
- proposers: 27 right. The errors:
  - a bare "his amendment" credited to the speaker, which led to the rule above;
  - "Belgian and joint Chilean-Indian amendments (L.244 and L.252)", where each adjective
    belongs to one symbol;
  - co-sponsors the record leaves out, where the report's table takes precedence anyway.

## Round 53: the audit repeated (28 September 2026)

This round repeats round 43's design after the fixes since then:
- the 1947-48 segmentation;
- the reports' annexes and E/CN.4/21;
- A/777's numbering;
- decisions and sponsors.

The sample was 126 speech tags not judged before, drawn in proportion to the tags in each kind
of record, with 30 tagged report paragraphs and 110 untagged speeches over 150 characters
(R1 50 from records with tags, R2 60 from records without). Two judges read each item, and a
third settled the 9 they split on.

| | Round 43 | Round 53 |
|---|---|---|
| Precision, weighted by tags | 94.8% ± 3.8 (119/126) | **93.8% ± 3.8** (118/126) |
| Report paragraphs | 29/30 | 29/30 |
| R1: untagged speeches about one article | 28/50 | 32/50 |
| R2: the same | 12/60 | 7/60 |
| Coverage within records with tags | 80% | 78% |
| Coverage overall | 67% | 71% |
| Pooled over the last three measures | 80% / 67% | **79% / 67%** |

Precision by kind:
- Commission 1949-54: 42/44.
- Third Committee 1954-61: 32/33.
- Third Committee 1948: 18/18.
- Third Committee 1962-66: 11/11.
- Commission 1948: 7/8.
- The 1947-48 drafting and the Geneva plenary: 8/12.

The small early strata weigh the estimate down. With 12 items between them, their share of the
tags (9%) is judged on too few items to move the estimate reliably.

The eight wrong speech tags:
- two are procedural: a motion on the order of voting, and a one-line reservation;
- three are drafts that combine articles in 1947-48: arrest with trial, and the article after
  one just approved;
- one places a new article (on advocacy of hatred) and is tagged by the context;
- two are later references that the rules took as the article under discussion.

The last two are fixed. At E/CN.4/SR.197 the chair's "amendment ... submitted to article 26
... in accordance with those used in article 23" had moved the context to article 23; the
article that an amendment is submitted to now wins over a later mention (`AMENDMENT_TO_RE`). At
E/CN.4/SR.66, "covered by the provision against discrimination in Article 3" had tagged a
debate on equal pay UDHR 2; a reference may now have up to five words between "covered by"
and the number. Together these changed 62 passages, among them A/C.3/SR.139 (trade unions,
now UDHR 23) and E/CN.4/SR.361 (amendments to article 52). Jev's checks ran on the new tags.

The wrong report paragraph was annex G's heading in E/CN.4/21, which had been joined to its
first article. It now has a row of its own.

Of the 39 untagged speeches judged to be about an article:
- 30 have no article context;
- 9 had their tag dropped by Jev.

Tagged speeches: 9,628.

## Six Commission records added (28 September 2026)

When the harvest took in the Commission's records, a relevance filter read the first two pages
of each: the ODS text layer, then Apple Vision in `pipeline/relevance_recheck.py`. It left out
records that do not name the Covenant there. Eight of those are cited for the Covenants by
documents in the collection. Read by hand, six are about the Covenants:
- E/CN.4/SR.135 (1949): the USSR statement on the draft Covenant;
- E/CN.4/SR.191 (1950), SR.203, 239 and 247 (1951): A/2929 and E/1992 cite them for articles
  of the draft, SR.203 for the inclusion of economic, social and cultural rights;
- E/CN.4/SR.448 (1954): the Chile-Uruguay draft resolution on reservations.

The two left out are SR.339 (the opening of the ninth session) and SR.381 (a closed meeting
on communications).

The six were already on disk. They were read by OCR, marked relevant with their evidence in
`data/manifest/relevance_covenants_*.json`, and segmented with `pipeline/resegment.py`, which
changed no existing segment. Together they add 211 speeches. SR.135's 15 tagged speeches are
Pavlov's statement article by article. The others are general debate (the economic and social
rights, the measures of implementation, reservations) with no one article.

A meeting's date now follows "held ... on", even with the weekday garbled, rather than the date
of issue printed first (`segment.masthead_date`). SR.203 is 16 April 1951, not 2 April. SR.16
of the first session is 5 February 1947.

Totals: 1,765 records, 25,346 speeches, 9,643 tagged, 5,365 decisions.

## Round 54: the reports read by article for the article 19 list (28 September 2026)

E/600, E/CN.4/57, E/CN.4/95, E/CN.4/85 and E/800 were read in full, and E/CN.4/705's annex I
article by article: 16 agents, a reader and a checker per part. Their rows (699) replace the
Declaration documents' heading-based tags. The one exception was E/CN.4/705's two whole-text
rows. A/5000's annex rows were set by hand.

A/4625 and A/5000 are now Covenant draft stages (`a4625`, `a5000`), anchored from the printed
text and checked with `cut()`. That adds 12 draft texts, 762 in all.

1,286 passages changed:
- 679 gained a tag;
- 536 changed tag;
- 71 lost one (headings and procedure the heading tags had carried).

Tagged decisions went from 2,759 to 2,765. Blind check of 30 changed tags, two judges: 30
right. A judge noted a wrong author in E/CN.4/95's list of limitations to the right to life, now
split by author.

## Round 55: the freedom of information bodies (28 September 2026)

The Sub-Commission's records (five meetings), its documents and report, and the Conference's Final Act
were read by article, 12 agents (a reader and a checker per part). 194 passages changed their tag
(the speeches of the Sub-Commission are 24-26 of E/CN.4/SUB.1/SR.25, 27, 28 and 45); tagged
speeches rose from 9,643 to 9,722, tagged decisions from 2,765 to 2,772.

Blind check of 30 new tags, two judges who agreed on all: 25 right. The five errors were rows
that were too wide:
- E/CN.4/84's heading covering both instruments, and the introduction of SUB.1/36 to the two
  texts;
- paragraphs 12-14 of the draft report "adopted without discussion" (SR.45);
- an exchange on whether the report was ready (SR.45);
- a speech on the press and peace in E/CN.4/80.

They are corrected, and E/CN.4/84's text of the merged article, which the heading had swallowed,
has its own row. A row read by hand keeps its tag against Jev's check: it was settled by two
readers.

## Round 56-57: meetings and decisions for the article 19 list (28 September 2026)

Round 56 (blind, 30 of the 82 passages newly tagged by the second-reading, heading, continued-agenda
and meeting-list fixes): 30 of 30 right. Round 57: the procedural rule, ignoring the framing "on a
point of order", gave 27 new tags, of which 18 were right, so it was narrowed to withdrawals and
separate votes on words (7 new tags, 6 right); `data/gold/article_tags.jsonl` holds them under
`procedural-rule/check`.

Segment ids moved for 10 records (`data/id_maps/2026-09-28-2248.json`): a heading the OCR had
garbled started a new paragraph. Tagged speeches went from 9,722 to 9,767, tagged decisions from 2,772 to
2,806, decisions from 5,365 to 5,406 and decisions with figures from 4,044 to 4,085.

## Round 58: sponsors and speakers for the article 19 list (28 September 2026)

References went from 20,710 to 21,112 and those with a proposer from 6,326 to 6,773. The list of
amendments to ICCPR 19 now names India, Egypt and the United Kingdom for the Commission's 1950
amendments (E/CN.4/424, 434, 440) and India and Indonesia for L.923/Rev.2. The sponsors'
evaluation went from exact precision 0.941 and recall 0.764 to 0.945 and 0.764.

Blind check of 30 changed references, two judges who agreed on all: proposers 30 of 30, symbols
29 of 30. A speech's bare opening can no longer take another delegation's speaker (speaker
evaluation 1.000 on all three sets).

## Rounds 59-62: the reading order of two-column pages (29 September 2026)

The article 19 check found speeches that the OCR of two-column pages joined under one speaker or in the
wrong order, and the earlier checks found lost lines (E/CN.4/SR.222, E/CN.4/669). The front page of a
1954-66 record sets a contents column beside the text, and Tesseract's automatic layout (tess3), which
`pipeline/ocr_select.py` took on every two-column page without a check, read a line across both.

`tess3_across` now tests each two-column page and chooses the text layer or Vision instead where tess3:
- agrees with neither of them (under 70) while they agree with each other (85 or more);
- has more than a quarter of its lines longer than 90 characters; or
- lacks more than 15% of the words both of the others read.

Of 5,833 two-column pages, 34 in 33 documents are affected: A/C.3/SR.1076 and SR.1078 (page 1), E/CN.4/669
(page 19: paragraphs 126-133 are in order again), E/CN.4/AC.1/20 (pages 3-4, nearly empty in tess3) and
others. The vote leaves tess3 out on them. The documents were re-segmented with ids kept
(`data/id_maps/2026-09-28-2320.json`). Round 59, blind, 30 speeches with new text: splits 27 right,
speakers 29, tags 13 of 13.

`segment.PARA_NO` took any short run of letters before a speaker's name as the OCR's damage to a
paragraph number, "to" in "in reply to Mr. SAPOZHNIKOV (USSR)" among them, when that line wrapped. A line
that starts with to, by, of, in, on, at, and, for or the is no longer a new speech, which merged 72
false splits (map `2026-09-28-2326.json`, corrected by `-2329.json`). A first list also held he, it, is,
so and be, and merged real speeches with a garbled number ("he Mr. MENDEZ (Philippines)"): round 60 found
them, and they were taken out. Round 61 (25 of the merged segments): 16 clean; the others were older
splits in the middle of a list of speakers.

**Tried and dropped:** a speaker's line without a paragraph number after a fragment that ends in a
comma is not a new speech (lists such as "Mrs. KHOKHOL, Mr. SCHMELZ, Mrs. NOVIKOVA and ..." are one
sentence). Without a condition it merged 2,948 segments in a dry run. With the condition that the
fragment has no speaking verb yet it merged 93, but round 62 found that most joined separate speakers (a
list of verbs is never complete: "accepted") and that the group sentences ("X, Y and Z associated
themselves") still name one speaker. It was taken out (`2026-09-29-0902.json` and its reverse
`-0906.json` document the move). The list of speakers in a group sentence needs a segment kind of its own
("group"), not a merge.

Segments: 69,377; speeches 25,302; tagged speeches 9,773.


## Round 63 (29 September 2026): records that the relevance filter had left out

The Covenants' meeting series was filtered by a look at the first two pages of each record's text layer
(`pipeline/ocr_all.py`): 640 of 1,570 records were left out as not about the Covenants. Read in full, 90 of
them mention the Covenant or the draft International Covenant three times or more, or have no text layer.
The verdicts of these 90 were first changed to "relevant" and the PDFs, already on disk, OCR'd (899 pages).

The agenda on each record's first page then showed that most of the Third Committee's records among them are
about other items (refugees, the racial discrimination convention, freedom of information, the asylum
declaration, reports of the Council) and mention the Covenants in passing. They were put back (53 records;
`build_all.py` now leaves out every record the relevance files judge not relevant, and deletes a stale
segmentation of it). **37 records stay**: 35 of the Commission (the drafting sessions of 1949-54) and two of the
Third Committee on self-determination (A/C.3/SR.459, 464), with 975 speeches, 965 of them with a speaker.

**Articles.** Twelve agents (one per session to assign, one to check it independently) read the 35
Commission meetings and the session reports' lists of meetings per article. 31 belong to no numbered article
of the rights and are rightly untagged: the order of work and closing of sessions, the Sub-Commission's
programme, measures of implementation (a general debate, not an article), the resolutions on self-determination
(they are recommendations, not an article). Three meetings were on an article: E/CN.4/SR.157 (fair trial, ICCPR
14), SR.232 (the general clause of the ICESCR, article 2) and SR.253 (self-determination, ICESCR 1); they were
added to `covenant_drafts_chr.csv`. A list of meetings on the fair-trial row, empty until then, made the build refuse
tags of other meetings, so the row lists every meeting that already used it (149, 153, 158, 159, 167) with 156 and
157. Jev's check and choice were then run on the new segments.

Result: 60 new tags (SR.116 9, SR.156 16, SR.157 19, SR.232 11, SR.253 4, SR.218 1); 8 tags of SR.155 (Part II,
added by hand earlier, never checked by Jev) fell below Jev's threshold.

Blind checks of the 60 new tags: 57 right, 3 partly (procedural remarks inside a meeting on the article); none
wrong. A check of 30 random speakers in the records first brought in: 30 of 30 right (9 of them in the 37 that
stay).

Segments: 72,535; speeches 26,727; tagged speeches 9,848. Records in the database: 1,826.

## Round 64 (30 September 2026): the article of each draft and amendment of the L series

The 265 drafts and amendments of the L series that the UN's server holds (A/C.3/L.n, E/CN.4/L.n; 215 base documents,
with their revisions) had no article: an amendment rarely names its own. Each was read by two independent agents
(the text, the passages of the debates that cite it, and the article catalogue; the second, an Opus, saw nothing of the
first's answer): they agreed on 206 of 215 documents, 117 with an article and 89 with none (procedure, another item of the
agenda, several articles). Where they differed, the pipeline's tags on the speeches that cite the document decided (4 cases).

Blind check by two further readers (a Sonnet and an Opus) of a sample: of 40 documents given an article, both agreed with
it in 35, one in three more and neither in two (a Chairman's note on the order of voting, which is procedure); of 15 given
none, both agreed in all 15. The other 81 documents with an article were then read by the same two blind readers, and an
article is kept only where at least three of the four readers give it: five more were left out (four notes on the order of
voting and one on two articles). Article 1 is one text in both Covenants and is labelled "ICCPR+ICESCR".

Result: 116 base documents (157 documents with their versions) have an article, 685 of their 2,397 paragraphs; 17 of them
are now listed in the history of ICESCR 13. No tag of a speech changed. Recorded in `data/concordance/l_series_readers.json`,
made into `l_series_articles.csv` by `pipeline/l_series_articles.py` and applied by `api/build_db.py`.

## Round 65 (3 October 2026): the audit repeated after the additions

Since round 53 the database grew from 1,765 to 2,157 records and documents: the 37 Commission and Third Committee
records the relevance filter had left out, 21 more found through the UVA collection, 265 L-series drafts and amendments
(with their articles, round 64), 47 documents of the UVA list and 10 machine translations. The audit was drawn again with
the same design (`eval/audit_sample.py`, seed 65): 144 tagged speeches in proportion to each kind of record's tags (at
least two per kind), 30 report paragraphs, 10 L-series paragraphs (apart from the audit), and 110 untagged speeches over
150 characters (50 in records with a tag, 60 in records with none). Two blind judges per item, a third on the 8 they split
on (`eval/audit_record.py` writes the verdicts to `data/gold/`).

| | Round 53 | Round 65 |
|---|---|---|
| Precision, weighted by tags | 93.5% ± 3.9 | **96.0% ± 3.3** (129 of 134 speeches) |
| Report paragraphs | 29 of 30 | 28 of 30 |
| Coverage within records with tags | 78% | **81%** |
| Coverage overall | 70% | **67%** |
| L-series paragraphs (not in the audit) | | 10 of 10 |

The five wrong speech tags: a point of order on the closure, an offer to withdraw an amendment, a delegation's general
policy with a passing mention of an article (procedure the rules did not catch), the Commission's article on convening
the Committee tagged as the article on its officers (two articles debated together), and the 1966 debate on the number of
ratifications tagged ICESCR 26 instead of 27. Of the report paragraphs, one was a page header ("English Page 31") and one
the Chairman grouping the right to health with social security (UDHR 25, not 23).

Coverage overall fell because the added records are mostly untagged: of 60 untagged speeches in records with no tag, 12
are about one article (round 53: 13 of 60), and those records now hold 11,499 untagged speeches. The untagged speeches
about an article are untagged because nothing in the record names it (36 of 39) more than because Jev dropped the tag (3).

## Round 66 (3 October 2026): the audit after the reader tags, the resegmentation and the dates

Between rounds 65 and 66 the database received 975 article tags from readers of whole meeting records (two readers, opus
and sonnet, each reading a record in order; a tag needs both to give the same article, one of them sure of it, and Jev
to confirm it at 0.7 or more; weaker suggestions are kept apart as `possible_article` and used by no filter or count), a
segmentation that no longer merges a turn into the speech before it (727 more speeches), running heads and printers'
footers removed from the text, the names of the chairs, and 453 dates read from first pages. The audit was drawn again
with the same design (`eval/audit_sample.py`, seed 66): 131 tagged speeches in proportion to each kind of record's tags,
30 report paragraphs, 10 L-series paragraphs (apart from the audit), and 110 untagged speeches over 150 characters (50
in records with a tag, 60 in records with none). Two blind judges per item (one opus, one sonnet), a third on the 8 they
split on.

| | Round 65 | Round 66 |
|---|---|---|
| Precision, weighted by tags | 96.0% ± 3.3 (129 of 134) | **94.7% ± 3.8** (124 of 131) |
| Report paragraphs | 28 of 30 | 27 of 30 |
| L-series paragraphs (not in the audit) | 10 of 10 | 8 of 10 |
| Coverage within records with tags | 81% | **88%** |
| Coverage overall | 67% | **81%** |
| Coverage overall, pooled over rounds 53, 65 and 66 | | 74% |

The two precision figures do not differ by more than their intervals. The 13 reader tags that fell into the sample were
all right (together with the 150 checked in samples while they were made, 163 of 163).

All seven wrong speech tags were given by the older rules. Four are procedure the rules did not catch: the order of
voting on a regrouping (ICESCR 14), a delegation reserving its right to speak (ICCPR 14), a member saying that ideas
should be discussed before a committee drafts (UDHR 19), and a point of order on merging articles 2 and 6 (UDHR 7).
Three are about another article, namely the right to life tagged as the fair trial article (ICCPR 14 for 6, a speech on
"competent" and "intentional" in the Lebanese amendment, which cites article 13 only for comparison), the expulsion of
aliens tagged as freedom of movement (ICCPR 12 for 13), and the proposed article on reservations tagged ICCPR 2 although
the Chairman had said it was not part of article 2.

Of the three report paragraphs, two were the bare headings "PART III" and "PART VI", tagged with the article of the
section before them; the third was paragraph 3 of draft article 30 of the Commission's report (the quorum for electing
the Committee), tagged ICCPR 31 where the final text puts it in 30(4). Both L-series paragraphs were from E/CN.4/L.93, a
compilation of 26 pages with amendments to several articles, to which the single article of its first amendment had been
given: its paragraphs on education were tagged as the right to work.

Two classes of error were corrected after the audit. A bare part heading ("PART III") no longer takes an article (8
paragraphs), and an L-series document longer than 40 segments is not given one article for all its paragraphs
(E/CN.4/L.93, 143 segments, now untagged); the L-series paragraphs tagged went from 574 to 431. The procedure and
passing-mention errors in the speeches remain (4 of 131).

Coverage rose because the readers tagged what the records' own structure had left untagged. Of 50 untagged speeches in
records with a tag, 17 are about one article (round 65: 27 of 50); of 60 in records with none, 5 (round 65: 12 of 60).
The records with no tag at all now hold 10,829 untagged speeches (11,499 in round 65), and the untagged speeches that
are about an article are untagged mostly because nothing in the record names the article (17 of 22) and less because Jev
dropped the tag (5). The samples are small (50 and 60), so the overall figure moves by several points from one round to
the next; the pooled figure of 74% is the steadier estimate. The readers have so far covered the Commission's records of
1947-54, the Drafting Committee's and the Third Committee's of 1948, 1955-56 and 1966; the Third Committee's debates of
1950-54 and 1957-65 and the General Assembly's of 1951 are not yet read.

## Round 67 (3 October 2026): speaker attribution and segmentation, checked on the page images

The article tags were audited against the text (rounds 43 to 66). Two things the tags depend on were not yet checked
against the scans outside the 13 records of the reference sets (`eval/speaker_eval.py`): who the speaker of each speech
is, and where each speech starts and ends. Both were checked on page images, by readers who did not see the database's
answer.

**Speakers.** 150 speeches were drawn (`eval/speaker_audit.py`, seed 67), 30 from each kind of record. Two readers (opus
and sonnet) read the speaker and the delegation from the scan, and a speech counts as right when both agree with the
database. The 10 speeches on which the readers and the database differed were settled from the readers' unanimous
answers (without a third judge): five were the same state or body under another name (Philippines and the Philippine
Republic, the Secretariat and an Assistant Secretary-General, the ILO and the ILO office).

| Kind of record | Right |
|---|---|
| Commission on Human Rights 1949-54 | 30 of 30 |
| Third Committee 1950-61 | 30 of 30 |
| Third Committee 1962-66 | 30 of 30 |
| UDHR drafting 1946-48 | 29 of 30 |
| Plenary records (A/PV, E/PV) | 25 of 30 |
| All | **144 of 150 (96.0%)** |

The six errors were three surnames the OCR had misread in a record whose roster has no entry for them (Smoliar, Kiselev,
Pérez Perozo), two speeches of the Soviet delegate in an ECOSOC plenary whose delegation had been lost to the bilingual
columns ("Union des Républiques socia…"), and one plenary speech with no speaker. The summary records of the Commission
and of the Third Committee were right on 90 of 90. After the audit the delegation is read from the country as printed
when the columns garble it (39 speeches), and the three surnames are corrected in `data/gazetteer/speaker_fixes.csv`.

**Segmentation.** Pages were drawn at random from five kinds of record (12 each, 60 per sample,
`eval/segment_audit_sample.py`), and a reader compared the segments listed for the page with the scan: a turn that
begins on the page and is inside the speech before it, a running head or footer left in the text, a heading left in a
speech, a wrong speaker, a wrong kind.

| Sample | Pages with no error | Turns merged into the speech before | Running heads and footers in the text | All errors |
|---|---|---|---|---|
| 1 (before any fix) | 20 of 60 | 29 of 181 (16%) | 19 | 80 |
| 2 (new pages, after the first fixes) | 27 of 60 | 13 of 203 (6.4%) | 13 | 63 |
| 3 (new pages, after the second fixes) | 20 of 60 | 15 of 226 (6.6%) | 28 | 91 |
| 3 again (the same pages, after the third fixes) | 23 of 60 | 14 of 224 (6.3%) | 14 | 80 |

The share of merged turns fell from 16% to about 6.5% with the first fixes (a turn run into the end of a line, a garbled
title such as "Mz. DEHOUSSE", and a turn opened by a phrase such as "In reply to Mr. X, Mr. Y") and has stayed there.
The samples differ in difficulty and the readers do not judge identically from one run to the next, so only the last two
rows, the same pages, say what a fix did: the running heads and footers in the text halved (28 to 14) and the errors
fell from 91 to 80. Between the samples the following were also added: an italic vote result closes the speech before
it, also when it wraps onto a second line (about 200 segments), "Mr. X, Vice-Chairman, took the Chair" is a note and not
a speech (69), and the running heads and printers' lines of the meeting records of the Third Committee and the
Commission (`pipeline/normalize.py`).

Two first tries were wrong and are recorded here. Making a bare "ANNEX IV" line a heading broke 190 hand-read annex
anchors, which join the heading to the line after it. Taking page numbers and printers' lines out of the documents
(reports, compilations) as well as the meeting records joined paragraphs that those lines had separated, and 678 anchors
no longer matched. The rules for page numbers and printers' lines now apply to meeting records only.

Still open, in the order of how often the readers named them: headings (the agenda item, "ARTICLE 17, PARAGRAPH 1",
"Paragraphs 22 to 26") and underlined decisions ("It was so agreed.") that sit inside the speech or the chair's turn
before them; the attendance list of a record whose list runs onto page 2, read as a speech by the Chairman and the
Rapporteur; the chair's turn after a speaker, in the records that print no paragraph numbers, left inside the speech;
footnotes and catchwords at the foot of a page spliced into a sentence. A merged turn puts another delegate's words
under the speaker before; the other classes put a few words of another passage into a quotation. This is why the scan is
the text to check before quoting, as the application says.

## Round 68 (6 October 2026): the open segmentation classes, checked on the page images

Round 67 left four classes open: headings and decisions inside the turns, the attendance list read as a speech, the chair's
turns and other turns left inside the speech before them, and footnotes and catchwords spliced into a sentence. The
segmenter (`pipeline/segment.py`, `pipeline/normalize.py`) now:
- reads openings the OCR damaged or the printer wrapped (a quote or three dots after the paragraph number, initials with a
  comma, a quote or a brace around the delegation, an opening that ends at a bracket and has its verb on the next line, a chair's
  turn opened by a phrase in a numbered paragraph);
- keeps a joint statement ("Mr. X (Country), supported by / Mr. Y (Country), asked") and a list of speakers in one turn;
- looks for the end of the masthead up to page 8, so that the attendance table of the Commission's records of 1951-53 is no
  longer a speech (records without a masthead: 148 to 6);
- closes a turn at "It was so agreed.", at results that open in the plural ("Paragraphs 22 to 26 were adopted") and, in the
  verbatim plenary records, at stage directions and "Decision:" lines;
- gives headings between the turns ("Paragraphs 22 to 26", an agenda item in capitals) a segment of their own, marked as agenda
  headings, which set no article;
- takes footnotes out of the speeches and keeps each as a segment of kind `footnote` (844), with the documents it cites.

The first article in the contents list of a masthead counts for a Covenant meeting when the session report lists that article
at the meeting (`api/build_db.py`): the old segmenter had read the contents as a passage and given its article to the speeches.

**Segmentation, paired.** 120 pages (two samples, seeds 68 and 69, 12 pages from each kind of record) were read by a reader on
the image, once with the old division and once with the new (`eval/segment_audit_sample.py --db`, `eval/segment_audit_round68.json`):

| | Old | New |
|---|---|---|
| Pages with no error | 31 | 39 |
| All errors | 182 | 147 |
| Turns inside another segment | 22 | 17 |
| Wrong kind (heading, decision, attendance list inside a turn) | 57 | 45 |
| Text in no segment | 45 | 33 |
| Running head, catchword or footnote in the text | 33 | 29 |

The reader was asked for more than in round 67 (headings and footnotes as segments of their own), so the figures compare old
and new only. Two small fixes came after the audit (speaker lists, the printer's line at the end of a line).

**Tags.** 250 speeches whose tag changed were judged blind (two judges, a third on splits; `eval/tag_change_check_2026-10-06.json`).
Of 120 new tags 93 were right; the 27 wrong ones are refused (`data/concordance/tag_rejections.csv`). Of 130 tags the
resegmentation lost, 116 had been right; the 99 that Jev also confirms are given back (`data/concordance/reader_tags.csv`).
The speaker reference sets are unchanged (128/128, 49/49, 29/29).

## Round 69 (13 October 2026): the audit after the resegmentation of 6-7 October

The audit was drawn again with the same design (`eval/audit_sample.py`, seed 69): 133 tagged speeches in proportion to each
kind of record's tags, 30 report paragraphs, 10 L-series paragraphs (apart from the audit), and 110 untagged speeches over
150 characters (50 in records with a tag, 60 in records with none). Two blind judges per item (one opus, one sonnet), a
third on the 6 they split on. One report paragraph has the verdict of one judge only and is left out.

| | Round 66 | Round 69 |
|---|---|---|
| Precision, weighted by tags | 94.7% ± 3.8 (124 of 131) | **95.4% ± 3.5** (127 of 133) |
| Report paragraphs | 27 of 30 | 27 of 29 |
| L-series paragraphs (not in the audit) | 8 of 10 | 10 of 10 |
| Coverage within records with tags | 88% | **83%** |
| Coverage overall | 81% | **76%** |
| Coverage, pooled over the last three rounds | 74% (53, 65, 66) | 75% (65, 66, 69); 85% within records with tags |

The six wrong speech tags: two are procedure, namely whether the Lebanese-Pakistani amendment to article 1 could be put to the
vote (A/C.3/SR.671) and a motion for closure and the order of voting on the amendments to the torture article (A/C.3/SR.854);
one is about how article 1 would be implemented, tagged as the inter-State communications article (ICCPR 41, E/CN.4/SR.360);
one supports France's proposal to put the Declaration's equality before the law into the covenant, tagged ICCPR 2 instead of
26 (E/CN.4/SR.35); and two are about the next article of the debate. In E/CN.4/SR.155 the Commission's report (E/1681) lists
the meeting only for article 12 of E/1371 (the expulsion of aliens, ICCPR 13), and the context carried that article through
the whole record, although from paragraph 17 the Commission debated article 13 (the fair and public hearing, ICCPR 14). In
A/C.3/SR.1397, a debate on part IV of the economic covenant, three speeches on the United Kingdom's amendments to draft
article 21 (ICESCR 20) had the article the Chairman opened with (draft 17, ICESCR 16). Of the report paragraphs, one is a
decision of the Working Group on the Declaration ("Article 11 was adopted on the understanding that it covered traffic in
women, servitude and forced labour") tagged UDHR 11 instead of 4, and one a procedural question of the Chairman tagged UDHR 29.

The errors were corrected after the audit, and every correction was judged blind (two judges, who agreed on all 19). In
E/CN.4/SR.155, 10 speeches and 2 votes move to ICCPR 14 (Jev 0.80-0.97), and 3 speeches that Jev does not confirm for 14 and
4 lines of the Chairman lose ICCPR 13; in A/C.3/SR.1397, 3 speeches move to ICESCR 20 (Jev 0.91-0.96)
(`data/concordance/speech_retags.csv`). The six other wrong tags are refused (`data/concordance/tag_rejections.csv`). The
speeches with a tag went from 11,195 to 11,188. The precision above is the database's before these corrections.

Coverage: of 50 untagged speeches in records with a tag, 25 are about one article (round 66: 17 of 50); of 60 in records with
none, 7 (round 66: 5). Of these 32, nothing in the record names the article in 22, and Jev dropped the tag in 10 (round 66: 5
of 22). Three of the seven in records with no tag are on the federal clause, in the Third Committee's general debates of 1950
and 1953 (A/C.3/SR.308, 519, 520), when it had no number in the draft. The samples are small, so the pooled figure is the
steadier estimate.

## Round 70 (13 October 2026): questions of general debate for the untagged speeches

Most untagged speeches sit in general debates: the Third Committee's of 1950-54 on the covenants (the 5th, 6th and 9th
sessions had 98-100% of their speeches untagged), the Commission's on measures of implementation, and the 1947 debates on
the form of the bill. They are about questions that run across the articles, and an article tag would be wrong for most
of them. A second layer now holds those questions (`data/concordance/topics.csv`): self-determination, one covenant or two
(with the place of economic, social and cultural rights), measures of implementation, petitions, the federal clause, the
territorial clause, reservations, the form of the International Bill, and "general" (the instrument as a whole, or several
questions at once). For each of the 14,932 untagged speeches over 150 characters, Jev chose one of them or "none"
(`pipeline/topics.py`, with the record and the passage before the speech); 3,497 got a question.

The blind check drew 22 picks per question in three bands of Jev's probability (10 at 0.9 or more, 6 at 0.8-0.9, 6 at
0.6-0.8), and 30 speeches Jev answered "none" for. Two judges per item (opus and sonnet), a third on the 22 they split on
(`data/gold/topics.jsonl`).

| Jev's probability | Right |
|---|---|
| 0.9 or more | **87 of 90** (97%; 91-99%) |
| 0.8 to 0.9 | 40 of 54 (74%) |
| 0.6 to 0.8 | 30 of 54 (56%) |
| "none" (about a question nonetheless) | 0 of 30 |

At 0.9 or more each question was right in 9 or 10 of its 10 picks. The threshold is therefore 0.9: 1,567 speeches carry
a question, less the three the check found wrong (`data/concordance/topic_rejections.csv`: a correction to a report's
paragraph on the self-determination article, an Economic and Social Council directive on the timetable, and a point on the
wording of a report). Below 0.9 the wrong picks were mostly procedure or a vote on a resolution about the question, one
article debated in the light of the question (education in the colonies), and passing mentions.

The questions are kept apart from the article tags: a speech carries one only when no article tag fits, and no article count
uses them. The search filters by them ("General debate"), and an article page links to the question it settled
(self-determination at article 1 of both covenants, the federal clause at ICCPR 50 and ICESCR 28, measures of
implementation at parts IV). The Third Committee's 6th session (1951-52) now has 50 speeches on self-determination and 64
on one covenant or two; before, it had 11 speeches tagged with article 1.

## Round 71 (13 October 2026): tags the context carried past the debate

Round 69 found a record (E/CN.4/SR.155) in which the article the session report lists for the meeting was carried through
the whole record, although the debate had moved on to the next article. To see how often that happens, every speech whose
tag came from the context (the chair, the agenda or the report's list of the meeting's articles) and which names another
draft article, not its own, was drawn where at least two such speeches in a record name the same other article: 275
speeches in 88 records. Two blind judges per speech (opus and sonnet), a third on the 10 they split on.

Of the 275, **18 were wrong** (6.5%, about the rate of the audit itself): the rest are speeches on their article that
compare it with another. The pattern is not systematic: the 18 sit in 10 records, and two of them were cases like
E/CN.4/SR.155:
- E/CN.4/SR.55 (1948): the Chairman's remark on article 2 (the general limitations, UDHR 29) gave that article to the
  debate on draft article 10 (freedom of movement, UDHR 13); judged blind, all nine speeches of that debate are about
  article 10;
- A/C.3/SR.794 (1957): a meeting on reopening and regrouping draft articles 14 and 15 of the economic covenant; 12 of its
  13 speeches tagged ICESCR 14 are procedure.

Corrections, each judged blind: 8 speeches move to the article they are about where Jev confirms it at 0.7 or more
(A/C.3/SR.100: three to UDHR 2; E/CN.4/SR.55: five to UDHR 13) and the two votes on the texts of draft article 10 in
E/CN.4/SR.55 with them (`data/concordance/speech_retags.csv`); 25 speeches lose their tag (procedure, a new article
without a number, or an article Jev does not confirm; `data/concordance/tag_rejections.csv`). The speeches with a tag
went from 11,188 to 11,163. The Chairman's lines in E/CN.4/SR.55 that read the drafts of article 10 still carry UDHR 29:
the Chairman's lines count in no figure, and these were not judged.

## Round 72 (13 October 2026): roll-calls, results and notes set apart from the turns

The largest class of segmentation errors in round 68 (45 of 147, "wrong kind") was the record's own matter left inside a
speech or the chair's turn: the roll-call block ("A vote was taken by roll-call ... In favour: ... Against: ..."), the
result the chair announced, a decision by a count of votes ("It was agreed by a vote of three to one", "The Committee
decided by six votes to none"), "The meeting was suspended ... and resumed" and "Mr. X (Country), Vice-Chairman, took the
Chair". Most of them were run by the OCR into the line of the turn before. The segmenter (`pipeline/segment.py`) now:
- cuts a line before a roll-call block wherever it starts (no speaker words a sentence "A vote was taken by roll-call"),
  and before the meeting suspended or resumed, a member taking the chair and a decision by a count, after the end of a
  sentence;
- cuts the chair's line before the result it announced (also when its verb is on the next line); a result inside a
  delegate's speech is left alone, as the speaker may be recalling an earlier vote;
- reads a result whose count comes after a few words ("were retained in paragraph 1 by 55 votes"), as "was not adopted, 17
  votes being cast", through an OCR period ("was .adopted") and over three lines, if it is one sentence;
- reads "took the Chair" on the line after the member's name (29 notes had been speeches).

On the whole corpus, before it was written: 264 records changed, about 290 new segments (roll-calls, results, decisions,
notes), no speech lost but the 29 notes. The speaker reference sets are unchanged (128/128, 49/49, 29/29).

One rule of the build had to follow: a vote that adopts an article as a whole ends its debate in the Commission's typed
records, and "The third amendment to article 28 ... was adopted", now a vote of its own, read as such and took the article
from the speeches after it. An adoption of an amendment no longer counts (`api/build_db.py`, `adopts_article`).

**Segmentation, paired.** 40 pages where the division changed (drawn by the kind of change: roll-calls, results, decisions,
notes), each read on the image by one reader against the old division and by another against the new
(`eval/segment_audit_round72.json`):

| | Old | New |
|---|---|---|
| Pages with no error | 0 | 7 |
| All errors | 102 | 66 |
| Wrong kind (roll-call, result, decision, note inside a turn) | 61 | 22 |
| Other classes | 41 | 44 |

Two forms the readers found left ("It was decided, by 20 votes", "The vote was taken / A vote was then taken by roll-call")
were added after the audit. What remains of the class: results at the top of a page before the next turn begins, a result
at the end of a delegate's speech, and headings run into a vote segment.

**Tags.** The resegmentation gave 42 speeches a tag they did not have (a roll-call request now a speech of its own, the
debates after an amendment's adoption): Jev dropped 9, and of the 33 it kept a blind check (two judges) found 31 right; the
2 wrong ones (procedure on the article on trust territories, A/C.3/SR.176) are refused. Speeches with a tag: 11,150
(11,163 before: the 29 notes that had been speeches, and the tags Jev and the judges refused).

## Round 73 (13 October 2026): headings between the turns

The second class of segmentation errors in round 68 was the headings: the printed records' agenda item ("AGENDA ITEM 35" /
"Draft Convention on Freedom of Information (A/AC.42/7 ...)"), the typed records' underlined headings in ordinary letters
("Draft resolution B (continued)", "Paragraph 3 of the Philippine amendment in document E/CN.4/253", "Article 15 (E/CN.4/365,
E/CN.4/353/Add.10)"), the plenary's numbered items ("116. Draft universal declaration of human rights: report of the Third
Committee (A/777)") and article headings broken over two lines. Most were left at the end of the turn before them. The
segmenter now:
- takes an agenda item to the next turn, also where the OCR ran it into the line before after the end of a sentence;
- takes a heading in ordinary letters between two turns when it is opened by a heading's word (Draft, Article, Paragraph,
  Item, Programme, Organization, Report, Election, Statement ...), is short, has no verb, no semicolon and no verb in -ed
  outside its brackets, and is followed by a turn (a numbered paragraph is not enough: it can be the rest of the speech a
  garbled running head cut);
- lets such a heading set the article when it names one article ("5. Discussion of Article 8, Paragraph 3", "Article 2
  Paragraph (a) (Document E/CN.4/AC.1/26)", "Article 15 (E/CN.4/365 ..."), and ends the article at a heading on the preamble;
- joins an article heading whose second line is its bracket of documents, its "(continued)" or the rest of its title;
- reads a tilde as a hyphen in a surname ("Mr. MASSOUD~ANSARI (Iran)"): 26 speeches had been procedural segments.

The masthead of the printed records keeps the agenda item printed above paragraph 1 (the audit's readers did not see the
masthead and counted it as missing; the reader shows it under "Masthead and attendance"): moving it would take the meeting's
contents from the rule that reads them.

**Segmentation, paired.** 39 pages where a heading was added (drawn by the kind of heading), each read on the image against the
old division and the new (`eval/segment_audit_round73.json`):

| | Old | New |
|---|---|---|
| Pages with no error | 1 | 5 |
| All errors | 112 | 83 |
| Errors of headings | 67 | 37 |

The two-line article headings the readers found split were joined after the audit. What remains: headings over several lines
in the typed records whose lines the OCR garbled, italic headings in the printed records above paragraph 1 ("Tribute to the
memory of ..."), and agenda headings run into a decision.

**Tags.** Every tag the change gave or changed was judged blind (two judges, a third on splits), after Jev's check: of 33, 20
were right; the 13 wrong ones were the debate on the preamble after "Article 32" in E/CN.4/SR.308 (since ended by the preamble
heading), five speeches on draft article 19 after the heading "Discussion of Article 18" in E/CN.4/AC.1/SR.31 whose own heading
the OCR lost (moved to ICCPR 22, Jev 0.93-0.97), one on draft article 64 (moved to ICESCR 20) and one procedural (refused).
The 11 tags of the restored speeches were judged in the same way: 10 right, one on the order of work refused. Speeches: 28,087
(the 26 restored, and the 29 notes of round 72 out); with a tag: 11,172.

## Round 74 (13 October 2026): running heads, catchwords and printers' lines

The third class of segmentation errors in round 68 (29) was page furniture left in the text: the typed records' running head
as the OCR garbles it ("E/CN,4/SR.391", "E/CN.1|/3R.67", "Hen AS 135" for "E/CN.4/SR 135", "~ 70 Page 11", "Tare 1"),
the catchword at the foot of a page when the OCR lost its slash ("6 ° The CHAIRMAN", "[subjective") or ran it into the last
sentence ("would withdraw it. /The CRATRMAN"), the typist's date mark ("10/6 a.m."), and in the printed records the running
head run into a line ("the 276 General Assembly — Twenty-first Session — Third Committee", "worthy of 909 182nd plenary
meeting", "1124 11 December 1946", "23 septembre 1948") and the printer's line ("Printed in France"). For meeting records only
(`pipeline/normalize.py`, `record=True`; the OCR's own tools use the old rules), the furniture rules now also take:
- at the top of a page, a symbol with a comma or a bar, a page line after a handwritten folio, a short line with the
  meeting's own number;
- at the foot, the typist's date mark and a catchword in lower case;
- anywhere in a line, the printed records' running heads, the bilingual plenary's French date, "Printed in ...";
- a running head broken over two lines, the meeting and its date ("1259th meeting -" / "11 November 1963"; a date alone is
  text: "the period from 17 January 1946 to" / "15 July 1946."), and a page number next to a running head.
A last line of a page is a catchword when the tail of its letters (after at most a few letters of debris) matches the head of
the next page (`pipeline/segment.py`, `drop_catchwords`).

On the whole corpus, before it was written: about 5,600 words in 659 records, all furniture on review of the 1,947 pieces
taken out (one piece of text the catchword rule took at first, "the words "criminal law", /60. With regard", was the reason
to limit the debris; dates alone were the reason for the pair rule). A heading in ordinary letters could take a speaker's
opening as its continuation when the verb is on the next line ("Sir Mohammed ZAFRULLAH KHAN (Pakistan)" / "recalling ..."):
no longer. A/PV.181 no longer holds the start of the 182nd meeting (its running head had hidden the end of the 181st).

**Segmentation, paired.** 40 pages where the text changed (18 typed, 12 printed Third Committee, 10 plenary), each read on the
image against the old and the new division (`eval/segment_audit_round74.json`):

| | Old | New |
|---|---|---|
| Pages with no error | 15 | 20 |
| All errors | 39 | 33 |
| Running head, catchword or footer in the text | 16 | 8 |

What remains: the plenary's date alone in a line ("9 December 1948"), a page number alone mid-sentence ("para- 187 graph"),
a catchword after the "Digitized by Dag Hammarskjöld Library" stamp. Speakers unchanged (128/128, 49/49, 29/29); the 5 tags
that changed (E/CN.4/AC.1/SR.25, the expulsion of aliens, ICCPR 12 to 13) were judged blind and are right.

## Round 75 (13 October 2026): turns hidden in the turn before, and the last of the furniture

The fourth class of segmentation errors in round 68 (17) was the turn left inside the speech before it. The audits of rounds
68-74 named 35 such turns; most fell into three kinds, which the segmenter (`pipeline/segment.py`) now reads:
- a title or paragraph number the OCR garbled: "Mir.", "Mya", "i'r.", "Migs", "Mr‘.", "50;" with a semicolon, debris before
  the title ("19. ° « My, WHITLAM"), "The. CHAIRMAN", a leftover "Page 70" before "The CHAIRMAN", "The Marquis DE
  VALDEIGLESIAS (Spain)", a quote before the name;
- an opening broken over two lines, before its delegation ("... the Secretariat Draft. Mr. WILSON" / "(United Kingdom)
  opposed") or before its verb ("... the French paper. Professor KORETSKY (Union of Soviet Socialist Republics)" /
  "reserved"): the opening goes to its line (after the end of a sentence, never after a paragraph number's full stop);
- a turn opened by a phrase, numbered or not, whose subject comes a few lines later: "After a further exchange of views, in
  which Mr. INGLES (Philippines) ... took part, the CHAIRMAN proposed", "In reply to Mr. HOARE (United Kingdom), the CHAIRMAN
  said", "On behalf of the Committee, the CHAIRMAN thanked", "After an exchange of views in which ... took part, Mr. BAROODY
  (Saudi Arabia) proposed" (the speaker's name a line later does not open the turn again).
Of the furniture of round 74: a plenary running head that is only the date (a date alone in a line on three pages or more, also
where the OCR put it inside a sentence), a page number between the halves of a hyphenated word ("para-" / "187" / "graph"),
and the scanning library's stamp, which hid the catchword after it.

On the whole corpus: 146 speeches and 150 turns of the chair more (28,228 speeches; 145 of the new ones attributed to a
speaker), no speech lost; a first version cut a paragraph number from its turn ("1." / "Mr. PAVLOV") and was corrected before
anything was written. Speakers unchanged (128/128, 49/49, 29/29).

**Segmentation, paired.** 40 pages with a new turn (chair and speaker turns, typed and printed records), each read on the image
against the old and the new division (`eval/segment_audit_round75.json`):

| | Old | New |
|---|---|---|
| Pages with no error | 2 | 13 |
| All errors | 91 | 59 |
| Turns inside another segment | 54 | 16 |
| False splits | 1 | 3 |

Two of the false splits were a phrase-opened turn cut again where its speaker is named; corrected after the audit. **Tags.** The
75 tags the change gave or changed were judged blind (two judges per batch, a third on splits): 68 right; the 7 wrong ones are
refused. Speeches with a tag: 11,223. Jev's questions of general debate were asked for the speeches that lost or have no tag:
1,571 speeches carry one.

## Round 76 (13 October 2026): a fresh audit on random pages

Rounds 72-75 each measured their own change on pages where the change had acted. That shows the gain of a rule, not the
state of the database, so the audit of round 68 was repeated on random pages: two samples (seeds 76 and 77, 12 pages from each
of the five kinds of record; four pages are in both), 120 page images, each read by one reader with the same instructions
as in rounds 68-75 (`eval/segment_audit_sample.py`, `eval/segment_audit_round76.json`). To separate the change from the
samples, the same 120 pages were read again against the segments of the database after round 68 (the database of 6 October,
before rounds 69-75: `eval/segment_audit_round76_old.json`).

| Same 120 pages | After round 68 | Today |
|---|---|---|
| Pages with no error | 49 (41%) | **53 (44%)** |
| All errors | 127 | **117** |
| Wrong kind (heading, decision, vote inside a turn) | 32 | 22 |
| Running head, catchword, footnote in the text | 27 | 23 |
| Turns inside another segment | 27 | 25 |
| Text in no segment | 26 | 27 |
| Wrong speaker or delegation | 8 | 9 |
| Other (false split, other column) | 7 | 11 |

17 pages got better, 8 worse, 95 stayed as they were (sign test p = 0.11): **a small gain, not significant on 120 pages**. The
audit of round 68 itself (other pages, the same state of the database) gave 39 pages without error (32%); the same state on
these pages gives 49 (41%). The two samples differ by nine points for one and the same database, so a comparison with round 68
on different pages would have claimed a gain of twelve points that is mostly the pages. By kind of record (pages without error,
after round 68 -> today): CHR 1949-54 10 -> 10, Third Committee 1950-61 7 -> 7, Third Committee 1962-66 12 -> 13, UDHR
1946-48 11 -> 12, the plenary 9 -> 11.

Why the gain on random pages is smaller than on the pages of rounds 72-75: those pages were drawn where a rule had acted, and
the rules (roll-calls, headings, running heads, turns) act on a minority of the corpus; the errors of a random page are
mostly elsewhere. What is left, by class (117 errors):
- **footnotes, 21:** 11 left in the text of a speech and 10 with no segment of their own, most in the printed Third Committee
  records ("1/ See Official Records of the General Assembly ...", "* Resumed from the 1453rd meeting.");
- **headings, 21:** 11 left inside a turn or a vote and 10 in no segment (the printed records' italic headings above
  paragraph 1, the agenda item in the masthead);
- **turns inside another segment, 25:** 15 speakers' and 10 of the chair's, mostly in the typed records of 1948-54, where the
  paragraphs have no numbers and the opening is broken; three pages account for 11 (E/CN.4/SR.195, A/C.3/SR.109,
  E/AC.7/SR.39);
- **running heads, catchwords and printers' lines, 23**, and **votes and decisions inside a turn, 9**.

The aims of the handover (60% of pages without error; fewer than 2% of the speeches inside another) are not reached: 44% and
5.6% (25 of 445 speeches on the images; 6.1% after round 68). The next step with the largest return is the footnotes of the
printed records, then the typed records' turns.

## Round 77 (13 October 2026): footnotes

The largest class left by the audit of round 76 was the footnotes of the printed records (21 of 117 errors): left in the text
of a speech, or in no segment. The furniture rules (`pipeline/normalize.py`, meeting records only) now know:
- the markers the OCR makes of a footnote's number: "*", "+", an apostrophe, "J/" for "1/", a digit with no space after it
  ("1The omission was rectified in document A/C.3/L.337/" / "Corr.2.");
- the openers that have no "See": "Resumed from", "Subsequently circulated", "Decision taken at", "Official Records", "Ibid.",
  "This document reads", "Document A/... was submitted", "United Nations publication", and the 1948 "Article 24 of the draft
  universal declaration of human rights (A/777)", which the bilingual page sets in the middle of the English column with no marker;
- a footnote of up to four lines, with a line that goes on after a slash or a hyphen (and, for the unmarked 1948 footnote, the
  short line that ends its sentence);
- the footer symbol with a comma ("A/C.3/SR,1028").
A first version took the opening of a numbered paragraph for a footnote ("9. The omission of a reference ..."): found on the
whole corpus before it was written (187 records, 218 pieces, 2,048 words; no piece that opens like a numbered paragraph is left),
and the opener narrowed. 222 more footnote segments (1,066 in all); speakers unchanged (128/128, 49/49, 29/29); one tag changed
(A/C.3/SR.1098), judged right.

**Segmentation, paired.** 27 pages with a new footnote segment (16 printed Third Committee, 10 other, 1 typed; fewer than 30
because the new footnotes are almost all of the printed records), read against the old and the new division
(`eval/segment_audit_round77.json`):

| | Old | New |
|---|---|---|
| Pages with no error | 2 | 2 |
| All errors | 52 | 42 |
| Errors of footnotes | 27 | 18 |

A gain on the pages where the rules act, as in rounds 72-75 and not to be read as the state of the database. What is left of the
footnotes: the second and third line of a footnote that the rules do not take (a short lower-case line: "page 10.", "in A/2808 and
Corr.1, para. 41)."), the second footnote of a page that has no marker the OCR kept, and a document symbol and date line under an
annex heading taken for a footnote. A short line that ends with a period after a footnote cannot be told from a speech that
goes on (the line "para. 12 of the draft." after a footnote is body text in a test of round 68), so this class needs the page
layout, not the text.

## Round 78 (13 October 2026): votes and decisions, read on the page images

**The audit.** 68 decisions drawn from the meeting records (`eval/vote_audit_sample.py`, seed 78, with 8 roll-calls), each read
against its page image (`eval/vote_audit_round78.json`): the outcome right in 63 of 64 found, the figures in 51, the clause voted
on in 51, the roll-call lists in 5 of 8, the article filed under in 21 of 21; the proposers missing in 18. The errors were
systematic: figures in forms the parser did not read ("a vote of four to none", "45 vote. to 6", "61.votes", "ik" for 14,
"with no abstentions", "approved 1 by 11 votes"); a clause that named what was voted on only by reference ("The amendment",
"The second paragraph") taken with the sentence before it, which was often a roll-call list, a speech or the result of the vote
before (the OCR reads a full stop as a comma: "with 11 abstentions, The second paragraph was adopted"); decisions without a vote
read as votes ("Is there any objection?", "accepted without comment", "I take it that ... approved", a ruling under rule 128);
the proposers named only in the chair's sentence before the result.

**The fixes** (`pipeline/decisions.py`, `api/build_db.py`):
- the figures in those forms; "25 votes with 10 abstentions", with no "to", as none against. Checked first on 15 such votes on
  the page images: none prints a figure against, and the French column of the bilingual records gives "contre zéro";
- an anaphoric clause takes the sentence that put it to the vote ("The CHAIRMAN put to the vote the Lebanese amendment
  (A/C.3/L.86) ..."), looking back past roll-call lists, requests for a roll-call, remarks and the results of the parts voted on
  before, but not past the result of another vote or a proposal made in between; a clause that names its proposer ("The Lebanese
  proposal") takes that sentence only when it names the same delegation; the result of the vote before is cut off the clause,
  except in a vote by parts, where the part keeps the sentence's start ("The United Kingdom amendment ... the word 'solely'");
- decisions without a vote after the chair's formulas; the mover of an adjournment or closure from the turns before; "proposed by
  the French representative", "the United Kingdom representative's amendment"; not the authors of the text an amendment is to
  ("the Egyptian amendment to the United States text"), nor proposers for a base text ("as a whole", "as amended", "the original
  text") unless the clause names them; a proposal to suspend consideration is procedural; "a new article after article 30" is on
  no article;
- in the build, the passages before a decision (up to 3,000 characters, so the chair's turn and a roll-call set apart in round 72
  are both there); a decision whose clause cites one document takes the proposers the record's own words give that document; "Mr.
  Pavlov's amendment" takes the delegation of that speaker in the record.

**On the whole corpus**, before and after: decisions 5,781 -> 5,797; with figures 4,326 -> 4,373 (against known 4,177 -> 4,292);
with proposers 1,701 -> 2,043; without a vote 50 -> 152; filed under an article 2,845 -> 2,839 (18 procedural votes, on closure,
adjournment or postponement, no longer filed under the article debated; one moved from ICCPR 30 to 32). Speakers unchanged
(128/128, 49/49, 29/29).

**Blind check on the page images** of 138 changes (`eval/vote_change_check_round78.json`; the old and new value shown in random
order, one reader (Sonnet), a second (Opus) wherever either value was judged wrong), re-scored against the final build:

| Change | New value right | Old value right |
|---|---|---|
| Proposers (75: 35 added, 25 changed, 15 removed) | 61 | 7 |
| Without a vote (20 added) | 20 | 0 |
| Figures (20 added) | 16 | 0 |
| Decisions found (16 added) | 15 | – |
| Articles (7 changed or removed) | 6 | 1 |

What is left: proposers where the sentence before names a second proposal (a sub-amendment and its amendment: "the USSR
amendment (E/CN.4/L.121) to the United Kingdom amendment" still gives both), a possessive base text ("the Afghan amendment to
India's text"), proposers named only under an OCR-garbled name ("Uruae", "Nétherlands", "Greck"), and a few right proposers lost
with the previous sentence (5 of the 75); figures the OCR dropped ("with 4 abstentions" printed, "with abstentions" read); the
roll-call lists of the plenary's 1946 form ("Voted in favour: ...") and lists attached to the wrong vote of a pair (2 of 8).

## Round 79 (13 October 2026): what round 78 left of the votes

- **Proposers.** A symbol's full stops ("the USSR amendment (E/CN.4/L.121) to the United Kingdom amendment") no longer hide
  the text amended; the object of another's proposal ("the United Kingdom proposal to add the Belgian amendment"), a text
  amended "in point 2 of the Indian amendment", and a proposal "with the exception of" or "without" another are not its
  proposers; a clause that names its proposers is read alone ("The amendment proposed by the representative of Yugoslavia");
  "The proposal, as amended," and "the amendment as a whole" keep their proposers (a base text is an article, a paragraph, a
  draft resolution); "sub-amendment" is a proposal of its own ("The Syrian sub-amendment"); accents the OCR added are dropped
  ("Nétherlands"), and a misread adjective just before "amendment" or "proposal" is matched at a similarity of 85 or more
  ("Teyptian", "Beleian"; not "Greck" or "Uruae").
- **Roll-calls.** A list with two or more names more than a vote's figures is not that vote's (the OCR loses names, it does not
  add them): of 12 such lists, 9 belonged to the vote before or after on the page images. They now go to the neighbour whose
  figures fit, or stand alone.
- **The plenary of 1946** (A/PV.7, the only record in this form): "Voted in favour: ... Voted against: ... Abstained: ...
  Absent: ..." and "The result of the voting is as follows: ... The amendment is not carried" read as a rejection by 12 votes
  to 27, with 10 abstentions, the lists complete ("Philippine Commonwealth" added to the gazetteer, which also gives two
  speeches of A/PV.7 their delegation).

On the whole corpus against round 78: proposers 2,043 -> 2,075 decisions (34 added, 23 changed, 2 removed); 12 lists moved off
a vote they did not fit, 9 attached elsewhere. Blind check on the page images of every proposer change and the plenary vote
(`eval/vote_change_check_round79.json`, same protocol as round 78): proposers right in 52 of 59 (6 wrong, 1 the reader could not tell; the old value right in 4), the plenary
vote 2 of 2. The errors left: a joint proposal under an OCR-garbled name (one of two sponsors found), a chair's procedural
proposal read as the amendments it lists, two clauses whose figures belong to the neighbouring vote.

## Round 80 (14 October 2026): a second fresh audit on random pages, and the typed records' hidden turns

**The audit.** Two new random samples (seeds 80 and 81, 12 pages of each kind of record, 120 page images; 4 pages are also in
round 76's sample), read with the instructions of rounds 68-77 (`eval/segment_audit_round80.json`), against the database after
round 79:

| | Round 76 sample (13 Oct) | Round 80 sample (14 Oct) |
|---|---|---|
| Pages with no error | 53 of 120 (44%) | **65 of 120 (54%, 95% interval 45-63%)** |
| All errors | 117 | 81 |
| Speeches inside another segment | 25 of 445 (5.6%) | 31 of 441 (7.0%) |

The database changed little between the two (round 77's footnotes; rounds 78-79 did not touch the segments), so the ten points
are mostly the pages: round 76 showed that two samples of one database can differ by nine. Pooled, 118 of 240 pages (49%) have
no error. By kind of record (pages with no error): CHR 1949-54 7 of 24, Third Committee 1950-61 15, 1962-66 16, UDHR 1946-48 13,
the plenary 14. The largest class was the turns inside another segment (31): 15 in the Commission's typed records, 9 in the
plenary of 1946-48. Then running heads and printers' lines in the text (20), headings in no segment (13, the printed records'
agenda item above paragraph 1).

**The fix** (`pipeline/segment.py`): a turn is now recognised at the start of a line and inside one with a title of more than
four letters ("Major DUKES (United Kingdom) recalled", "64, Ato Haddis ALEMAYEHOU (Ethiopia) wondered"; Major, Ato, Tengku and
others added to the titles), with a full stop after the name or the delegation ("JEVREMOVIC. (Yugoslavia). supported"), an adverb
before the verb ("formally proposed"), more OCR debris before it ("2300- » Mrs. MEHTA (India)"; a number of four digits is no
longer kept as the paragraph number), when it opens with a phrase and no paragraph number ("In reply to a question by the
CHAIRMAN, Mr. JUVIGNY (France)" / "formally proposed"); the typed records' "Tho CHAIRMAN said" with no paragraph number, and the
plenary's "The PRESIDENT (Translation from the French):" and "Mr. Pérez Cisneros (Cuba) (Translation from the French):". 92
records changed, 128 segments more (28,273 speeches; 7,279 turns of the chair); speakers unchanged (128/128, 49/49, 29/29).

**Paired audit** on 30 of the 119 pages with a new segment, read against the old and the new division
(`eval/segment_audit_round80_changed.json`): pages with no error 0 -> 6, errors 78 -> 55, speeches inside another 41 -> 11;
23 pages better, 1 worse, 6 the same.

**Tags.** The first build changed 52 article tags and a blind check (two judges, a third on splits) found the old tag right in
40: a chair's turn split off from a speech now moved the article. Two causes, two fixes in `api/build_db.py`:
- the chair speaking as a delegate ("Tho CHAIRMAN, speaking as the representative of France, stressed the fundamental importance
  of article 3 ...") had the article set by the last one the long speech named; it is now the first (E/CN.4/SR.310, 19 speeches
  on the right to life). Two other rules were tried and measured first: ignoring such a turn, or letting it move the debate only
  when it takes an article up, each lost more right tags than it saved;
- a speech the context filed under one article and two readers of the record (Jev confirming) under another now takes the
  readers' article, as it is read from the speech itself (13 speeches; the case was E/CN.4/AC.1/SR.36, where the chair's turn
  carried article 10 of the Geneva draft into the debate on asylum). A hand re-read still comes first.

After them, 34 tags differ from the database before the round, all judged blind
(`eval/tag_change_check_round80.json`): 16 added right, 2 changed right, 2 removed rightly; 10 right tags lost (and one removal
not judged), and 6 wrong new tags, which are rejected (`data/concordance/tag_rejections.csv`). Tagged speeches 11,224 -> 11,240.
The chair speaking as a delegate remains a weak point: the first article such a speech names is right more often than the last,
but not always (E/CN.4/AC.1/SR.23, 26).

Also found: the chair of E/CN.4/AC.1/SR.11 is named CHANG in all 19 of its turns, where the record shows Dr. CHANG speaking as
the delegate of China; the presiding officer of that meeting needs checking (pipeline/chairs.py).

## Round 81 (14 October 2026): the agenda item above the first turn, and the page's furniture in the middle of a column

Two classes of round 80's audit on random pages (13 and 20 of its 81 errors):

- **The agenda item printed above paragraph 1** ("AGENDA ITEM 48 / Draft International Covenants on Human Rights (A/2907 ...)
  (continued)", "Draft international covenant on human rights and measures of implementation ... [Item 29]* / GENERAL DEBATE
  (continued)", the plenary's "117. Continuation of the discussion on the draft universal declaration of human rights") was the
  last part of the masthead, which the audit does not show, so the readers found it in no segment. It is now a heading of its own
  (`pipeline/segment.py`, masthead_agenda): the block after the line that names who presided ("Chairman: Mr. Humberto DIAZ
  CASANUEVA (Chile).", "... Vice-Chairman, presided.", "... took the Chair.", "President: ..."), or in the typed records the
  first heading in capitals after the list of the Secretariat; at most 25 lines, reading as an agenda item, never an attendance
  list. 834 records have one. `api/build_db.py` still reads it with the masthead for the meeting's instrument and article, so no
  tag moved; it is stored as a heading and found by the search. Where the masthead had swallowed the first turn, the turn now
  stands alone (A/C.3/SR.796, Mrs. Leflerova's speech on draft article 16, now ICESCR 15).
- **The page's furniture in the middle of a column** (`pipeline/normalize.py`, meeting records): the printed page number alone on
  a line ("drafted in a" / "878" / "liberal and generous spirit"; 3-4 digits, not a year, the printed records only), the record's
  own symbol ("A/C,3/SR,1268"), "Litho m U.N.", the printer's job line ("77301~November 1958=-2,075"), the typed records' "Page
  13" as the OCR read it ("Bago 13", "Page iO", "page BT", "Page' 13'", "Page k"); after "The meeting rose at 12.40 p.m." the
  debris of the page is dropped and a footnote there is set apart. Found on the whole corpus before writing: 882 pieces, 1,484
  words, all of them furniture but one footnote's first lines without a marker (A/C.3/SR.959); the 49 numbers whose neighbours
  could make them figures ("by" / "106" / "votes") were read and all are page numbers.

Speeches 28,273 -> 28,274 (the one freed from a masthead), tags otherwise unchanged (11,241), speakers unchanged (128/128, 49/49, 29/29). **Paired audit** on 30 pages where
the division changed (15 with a new agenda heading, 15 with furniture taken out; 25 of them changed), read against the old and
the new segments (`eval/segment_audit_round81.json`): pages with no error 5 -> 15, errors 47 -> 30, text in no segment 23 -> 9;
16 pages better, none worse.

## Round 82 (14 October 2026): the chair of two 1947 meetings, and the documents' titles and printers' numbers

- **The chair.** E/CN.4/AC.1/SR.11 named Dr. Chang in the chair in all its turns: the OCR read "Chaixman: Mrs. Eleanor Roosevelt",
  and the pattern for the presiding officer took the next line, "Vice-Chairman: Dr. P. C. Chang (China)". `pipeline/chairs.py` no
  longer reads a Vice-Chairman as the chair and knows "Chaixman" and "Chatrman"; a name with the OCR's bars ("Mrs. Roosevelt | |
  (United States)") is read past them. 21 turns changed (20 in AC.1/SR.11, 1 in E/CN.4/SR.16), all to Roosevelt; no other
  record changed.
- **Titles over two lines** in the documents ("Brazil: amendments to articles 19 and 26 of the draft" / "Covenant on Civil and
  Political Rights 1/", "... amendment to article IV" / "submitted by Czechoslovakia (A/C.3/L.1220, para. 2)"): the title takes up
  to two more lines when it ends on a preposition or the next line starts in lower case, not a numbered or lettered line nor an
  article heading (`pipeline/segment.py`). 451 titles are longer; `api/build_db.py` still reads the instrument and the article
  from the title's first line (its second line, "section D, Measures of Implementation", first moved the context of E/CN.4/L.227
  and cost its tags: found on the comparison of the tags and fixed before keeping it). No tag of a speech or paragraph changed.
- **The printer's job number** at the foot of a page ("65-25443", "61-23698", the OCR's "65-25hh5", "52-1878", "5928355"): taken
  off the last lines of a page, alone or at the end of the last line (`pipeline/normalize.py`); 137 removed, all read first.

Paired check on 12 document pages with a longer title (`eval/segment_audit_round82_documents.json`): errors 28 -> 26, 8 pages
better, 2 worse. A small gain: the documents' pages have other errors the rules do not touch (footnotes inside paragraphs, the
two-column lists of documents in the session reports' annexes, where each title is split over a heading and a paragraph, the
archive's stamps), and one title's middle line is missing in the OCR itself (A/C.3/L.818).

## Round 83 (14 October 2026): the documents' footnotes, lists of documents and archive stamps

Three classes the audits of rounds 81-82 found in the documents (not the meeting records):

- **Footnotes inside paragraphs.** A document's footnote is now a segment of its own, where it stood (`pipeline/normalize.py`,
  `_drop_doc_footnotes`; `pipeline/segment.py`): a marked note in the last lines of the page ("1/ Official Records of the
  Economic and Social Council, eighteenth session, Supplement No. 7, annex I (E/2573)", up to four lines), and the reports' notes
  of sources, which close a column ("22 E/CN.4/618, E/CN.4/SR.236 and 237, E/CN.4/L.10/Add.6."); not a numbered paragraph. A
  footnote takes no article. **Not in the 39 reports whose sections were read by hand** (`report_sections.csv`,
  `report_annex_sections.csv`): their rows' anchors name lines of such notes, and the first build, which set the notes apart there
  too, moved 1,500 tags (E/1992, E/CN.4/689) until the section rows were found out of step; the notes stay in their text. On the
  bilingual pages each footnote is kept or dropped by its own words (the French column's notes are dropped, as in the records).
- **Lists of documents** in the reports' annexes (two columns read one after the other: a run of symbols, then the titles): on
  a page with eight symbols or more alone on a line, each title ("Yugoslavia : amendment to the Lebanese proposal on equality of
  rights of men and women", "Ditto") is one paragraph, not a heading and a paragraph, and names no author for what follows; where
  the symbols and the titles are as many, each title takes its symbol in order ("E/CN.4/607 — Yugoslavia : amendment to the
  Chilean proposal on the right to education"), else the symbols stay one paragraph.
- **The archive's stamps** ("RECEIVED" / "MAY 14 1948" / "UNITED NATIONS" / "ARCHIVES", or run onto a line: "... racial
  discrimination. RECEIVED 2:3 OCT 1947"): the short line with RECEIVED or ARCHIVES alone and, around it, the date, the stamp's
  own words and debris of a few letters (not "HAVING RECEIVED the report", "COMMUNICATION RECEIVED FROM CANADA", nor a heading in
  capitals: a first rule took "ERRATUM" and "AND" from a masthead, the second an anchor's word; both found and narrowed).

Words lost on the whole corpus, read before writing: the stamps, the French copies of three footnotes on a bilingual page
(A/125) and one hyphenated word joined. Speeches unchanged; of 65,242 segments that can be matched by their text, none changed
its tag; speakers unchanged (128/128, 49/49, 29/29). **Paired audit** on 20 document pages (8 with new footnotes, 6 lists, 6
stamps; `eval/segment_audit_round83_documents.json`): errors 62 -> 54 (footnote pages 34 -> 29, lists 24 -> 21, stamps 4 -> 4),
10 pages better, 4 worse. Of the 4, two were the stamp rule taking a heading and a footnote cut after its first line (both fixed
after the audit), two keep old errors the rules do not touch (a list of documents without a symbol column, E/CN.4/669 p. 67; a
catchword, E/CN.4/82/Add.9). The documents' pages keep other errors: headings inside paragraphs ("Article 47 42/", "PART VI"),
running heads ("English", "A/C.3/L.1414 English Page 39"), the governments' comments not split by government (E/CN.4/365).

## Round 84 (14 October 2026): a third fresh audit on random pages

Two new random samples of the meeting records (seeds 84 and 85, 12 pages of each kind of record, 120 page images; 9 of them in
an earlier sample), read with the same instructions as rounds 76 and 80, against the database after round 83
(`eval/segment_audit_round84.json`):

| Sample (database after) | Pages with no error | Errors | Speeches inside another |
|---|---|---|---|
| Round 76 (round 75) | 53 of 120 (44%) | 117 | 25 of 445 (5.6%) |
| Round 80 (round 79) | 65 of 120 (54%) | 81 | 31 of 441 (7.0%) |
| **Round 84 (round 83)** | **71 of 120 (59%, 95% interval 50-68%)** | **85** | **29 of 461 (6.3%)** |

Each sample is a random draw from the same records, so they measure the state of the database at three points: the gain from
round 76 to now is significant (z = 2.3, p ≈ 0.02); the one from round 80 to now is not (z = 0.8). Pooled over the three
samples, 189 of 360 pages (53%) have no error. By kind of record (pages with no error, of 24): CHR 1949-54 10, Third Committee
1950-61 16, 1962-66 18, UDHR 1946-48 10, the plenary 17. The handover's aims (60% of pages without error; fewer than 2% of
the speeches inside another) are reached for the first only at the upper end of the interval, and not for the second.

What is left, by class (85 errors):
- **turns inside another segment, 29**, almost all in the typed records of 1947-54 (the Commission, its Drafting Committee and
  Sub-Commissions) and the plenary of 1946 (A/PV.7 alone has 4): a turn that starts in the middle of a paragraph ("Mr. MALIK
  (Lebanon) had little to add", "The CHAIRMAN pointed out that ...", "In reply to a question by Mr. PAVLOV (USSR) the
  representative of the UNITED KINGDOM said"), or after a page break;
- **decisions and headings inside a turn, 26** (the underlined results of the typed records, "The motion was adopted by 10 votes
  to none", "Document E/CN.4/L.366/Add.12 was adopted"; a heading at the top of a page joined to the segment before; the
  paragraph number of the next turn left at the end of a segment, "88. In reply to a question from the CHAIRMAN,");
- **running heads and catchwords, 13**, mostly the typed records' symbol and page as the OCR garbled them ("E/C:..4/9R.251",
  "eee B/CN.4/5R. 308", "page 1%", "page & Se");
- **speakers, 7**: names the roster does not resolve (Khomussko, Quarles van Ufford), and three wrong surnames (Cortina for
  Braña, Fernandez for Santa Cruz, van Roijen for van Kleffens).

## Round 85 (15 October 2026): the typed records of 1947-54, turns inside a paragraph and underlined decisions

The two largest classes round 84 left, both in the typed records of the Commission, its Drafting Committee and
Sub-Commissions (`pipeline/segment.py`):

- **Turns without a delegation in brackets.** The typed records often name a delegate a second time without the country
  ("Mr. WILSON suggested deleting the last sentence", "Professor CASSIN replied that it was correctly placed"). A new turn now
  starts at a title (Mr., Mrs., Miss, Mme, Prof., Professor, Dr., Sir, Colonel, General, Major, Begum), a surname in capitals of
  four letters or more and a verb of saying right after it, but only where the text before has ended a sentence (not "could",
  "would", "did", "was", "had" after the name). The openings also take the OCR's punctuation inside the title and before the
  bracket ("Mr.:NISOT (Belgium)", "Mr,-JUVIGNY (France)", "TEPLIAKOV•(Union ..."), and the chair after "After further
  discussion" or "views".
- **Underlined results.** "The Commission adopted the Chinese proposal by ten votes to one", a short line ending a sentence
  with a result ("Paragraph 23 was adopted unchanged."), "Document E/CN.4/L.366/Add.1 was adopted, subject to those
  amendments" are now results of their own, not the end of the speech before (not "had been adopted").
- **The delegation of a speaker named without one** (`pipeline/entities.py`): the delegation of the delegate on the meeting's
  list whose name matches at 80 or more, as for an unreadable country (58 speeches: Wilson, United Kingdom; Koretsky, USSR;
  Humphrey, the Secretariat).

128 records changed: speeches 28,274 -> 28,367, results 2,509 -> 2,576, procedural 868 -> 902; no word lost on the corpus;
speakers unchanged (128/128, 49/49, 29/29).

**Tags.** The first build changed 31 article tags; the blind judges (two, a third on splits) preferred the old tag in 21.
Two causes: a chair's turn or a result split off a tagged speech lost the speech's tag (13, among them the votes on the
fair-trial article in E/CN.4/SR.110 and SR.157 and on social security in SR.221), and a piece split off an untagged speech
took the tag of the debate's context where it was procedure (8: adjournments, closures, the Drafting Committee's first
meetings filed under article 1 of the Secretariat's outline). The 13 old tags are restored (`reader_tags.csv`, "restored"
rows, which now apply to a chair's turn or a vote too) and the 8 rejected (`tag_rejections.csv`); after them 10 changes,
all judged right (`eval/tag_change_check_round85.json`).

**Decisions.** 22 new decisions, read on the page images: 20 right; the closure of SR.183 lacks its figures (9 to 2, the OCR
lost the 9) and a vote of SR.62 was filed under article 1, not 16 (corrected, `speech_retags.csv`). Of 4 changed fields, 3
right; the fourth gives a joint draft resolution "as amended" (A/C.3/SR.655) the sponsors the session report lists, which is
the database's convention for a named proposal and not the judge's rule (no proposer for a text "as amended").

**Paired audit** on 30 changed pages (`eval/segment_audit_round85_typed.json`): pages with no error 3 -> 6, errors 83 -> 57
(decisions inside a turn 48 -> 29, turns inside another 20 -> 16), 21 pages better, 1 worse (one error more, a result line
the OCR cut). What is left there: results inside a chair's turn that runs on ("The CHAIRMAN put to the vote the second
sentence ... The second sentence ... was rejected"), turns opened by "In reply to a question by ...", turns after a page
break, and the typed records' running heads.

## Round 86 (15 October 2026): results inside the chair's turn, "In reply to ..." turns, running heads, four surnames

What rounds 84-85 left (`pipeline/segment.py`, `pipeline/normalize.py`, `pipeline/entities.py`, `pipeline/decisions.py`):

- **Results inside a turn.** The typed records label the decision ("DECISION: This proposal was rejected by 5 votes to 3",
  "Decision;", the OCR's "Recision:") and the OCR misreads the verb ("wes rejected", "vas accepted", "wag adopted",
  "reJectod"): both now open a result, also after a speech whose last full stop the OCR read as a comma. A decision that
  stops on "submitted by" goes on with the name ("Mr. Amado (Panama) by 2 votes to 1"), not a new turn.
- **Turns opened by a phrase.** "49. In reply to a question by Mr. PAZHWAK (Afghanistan),-Mr. URQUIA (El Salvador) said",
  "88. In reply to a question from the CHAIRMAN," / "Mr. LOPEZ VILLAMIL (Honduras), speaking for", "In reply to the CHAIRMAN,
  Mrs. ROSSEL (Sweden) reaffirmed": the speaker after the phrase's comma, with any verb (not "and", "or", "the": "After an
  exchange of views between Mr. CASSIN (France), Mr. HOARE (United Kingdom) and the RAPPORTEUR, article 44 was adopted" is
  a decision). The chair as the OCR spells it, "The CEAIRMAN", opens the chair's turn at the top of a page.
- **Running heads.** At the top of a typed page, the symbol and folio as the OCR garbled them ("B/CN.4/5R. 308" after "eee",
  "Ning deen 308", "E/CN.4/SR.4 ›c", "£/cn, ¥/sR. 61", "page 1%", "page & Se", "Feige 10", "Pages 11", "Page 12 q"). The
  first rule also took "persons.", "tegory A" and the heading "Article 10" of E/CN.4/AC.1/SR.10 (whose number is the meeting's);
  all three were read before writing and the rule narrowed. Words removed on the corpus: 1,585, all running heads and
  catchwords (the "/Mr. CASSIN" at the foot of a page that the next page repeats).
- **Speakers.** In the General Assembly's printed records a speaker is matched to a delegate the session knows only if the
  name fits too (two engines read "BRANA (Cuba)", and the delegation alone made it CORTINA); a name known only from another
  speech is the delegation's one delegate only if a reading is at least half like it ("Mr. Santa Cnuz (Chile)" was FERNANDEZ,
  "Mr. van KLEFFENS" VAN ROIJEN, "Mr. Dayres (United Kingdom)" BEVIN). 19 speeches change speaker, 18 to the name the page
  prints (Braña, Santa Cruz, van Kleffens, Davies, Delhaye five times, Lange, Zuloaga, Nosek, Morozov, Mendès-France...), one
  (Thorp, E/SR.215) to none. A first version also required the name to fit in the typed records, where the engines agree on
  garbage ("MEM'EA" for MEHTA): it changed 67 speakers, many for the worse, and was narrowed before the build.
- **Votes.** "amendment" as the OCR spells it ("emeniment", "anendment", "emenduent") names the proposer; an article adopted
  as a whole when the OCR runs its number on ("Article 4as amended was adopted"), and not a paragraph of it ("Paragraph 1 of
  the joint France-United States text of article 16 ... was adopted").

490 records changed: speeches 28,367 -> 28,422, results 2,576 -> 2,709, procedural 902 -> 1,013, decisions 5,825 -> 5,874
(with proposers 2,082 -> 2,107); speakers unchanged on the three evaluations (128/128, 49/49, 29/29).

**Tags.** The first build changed 93 article tags and the judges preferred the old tag in 63: the chair's turns now found
("The CEAIRMAN ruled that the USSR proposed text for article 21 should be put to the vote") move the debate's article as
the chair's turns do, and a vote on one paragraph closed the article (fixed). The old tags are restored (40) and the wrong
ones rejected (35); after them 26 changes remain, all judged right, and two tags both judges found wrong are gone
(`eval/tag_change_check_round86.json`). **Decisions** (72 read on the page images): 42 of 50 new decisions right, the other 8
real but with figures the OCR cut ("rejected None-3" for 1-3-4); 17 of 22 changed fields right, two proposers corrected by
hand (`decision_proposers_checked.csv`, which now takes an empty entry for "no proposer").

**Paired audit** on 30 changed pages (`eval/segment_audit_round86.json`): pages with no error 3 -> 10, errors 52 -> 34
(results inside a turn 19 -> 7, turns inside another 20 -> 15, running heads 8 -> 7), 18 pages better, 2 worse by one error.
What is left there: turns that start at the top of a page after a catchword ("/The CHAIRMAN"), the masthead of a corrigendum.

## Round 87 (15 October 2026): turns the OCR's marks hid

The turns rounds 85-86 still left inside another, from their audit (`pipeline/segment.py`): a paragraph number the OCR read
with a degree sign or a bar ("3°. | Mr. ORDONNEAU (France) noted"), a mark after the title ("Mrs.» MEHTA", "Mr» CASSIN",
"Mr'• CASSIN", "* Mie: ROOSEVELT"), a speaker's line that ends with the delegation, its verb on the next line ("* MI. BERNSTEIN
(Co-ordinating Board of Jewish Organizations)" / "appreciated"), a quotation mark before the verb ("he. PAVLOV (Union of Soviet
Socialist Republics) ‘stated"), and the printed records' small capitals inside a line ("; _ Mr: Morozov (Union of Soviet
Socialist Republics) wished"; not "Mr. Urquia (El Salvador) had been elected Chairman", a note).

33 records changed: speeches 28,422 -> 28,457; no word lost; speakers unchanged on the three evaluations; of the speeches that
kept their opening, 3 have a better speaker (Malik twice, Whitlam). Two article tags changed, both judged: one old tag restored,
one chair's tag removed (both versions wrong). Decisions unchanged. **Paired audit** on 30 changed pages
(`eval/segment_audit_round87.json`): pages with no error 1 -> 12, errors 58 -> 34 (turns inside another 39 -> 14), 23 pages
better, none worse.

## Round 88 (15 October 2026): results the OCR misspelled, decisions without a vote, and the documents' article headings

- **Results** (`pipeline/segment.py`): more of the typed records' misreadings open a result: the verb ("adonted", "adoptec",
  "resected", "rotected"), the opener ("Paragvoph 2", "Paragrae"), the label ("DEOISTON:", "Decision,;", and "Decision;" alone on
  its line above the result), "It was zo decided.", "It was so agreed, 2/" (with its footnote mark). The label must be
  capitalised and followed by a colon or semicolon: a first version took the word "decision, which ..." at the start of a line.
  A heading after a result whose full stop the OCR read as "•" ("paragraph 5•" / "Paragraphs 6 to 9") is a heading.
- **Figures** (`pipeline/decisions.py`): a rejection whose verb the OCR misspelled ("rejecte|", "reJccted", "resected") now has
  its majority against, as the others; before, its figures were the wrong way round (A/3764: 41 for, 12 against, for a UK
  amendment rejected by 41 to 12).
- **Decisions without a vote.** "It was so decided" set apart by the earlier rounds at the head of its own passage takes what
  was decided from the passage before (the chair's proposal), not a footnote: 339 decisions found, most of them on the work
  (time-limits, the order of votes, the list of speakers); such a decision takes no article (`api/build_db.py`,
  `ORDERS_WORK_RE`), only one that settles a text does.
- **The documents' article headings** ("Article 11 : ,", "Article 12 | .", "Article 5 (continued) : explanation of vote") are
  headings, and their paragraphs take the article by the draft's numbering (A/C.3/230 draft article 11 is UDHR 13, A/C.3/285/Rev.1
  draft article 12 UDHR 14, A/C.3/SC.4/20 draft article 8 UDHR 10).

Decisions 5,874 -> 6,220 (without a vote 154 -> 493, with proposers 2,107 -> 2,160); no word lost; speakers unchanged on the
three evaluations. **Checks on the page images:** 27 article tags changed (all in documents), 22 judged right, 5 both wrong
(paragraphs under a next draft article whose heading the OCR lost) and rejected; of the decisions, all 39 new ones with an
article and 40 drawn at random from the 300 others, 77 of 79 right, the two changed articles right, one proposer corrected by hand
(`eval/tag_change_check_round88.json`). **Paired audit** on 30 changed pages (`eval/segment_audit_round88.json`): pages with
no error 2 -> 8, errors 61 -> 41 (results and headings inside a passage 38 -> 21), 21 pages better, 1 worse (the label
"Decision,;", fixed after the audit).

## Round 89 (15 October 2026): catchwords, runs of results, the headings after them

- **Catchwords** (`pipeline/normalize.py`): the first words of the next page at the foot of a typed page, behind a little
  debris ("| _ 4 ~ “/Rise BOWIE |", "» /The CHAIRMAN") or run onto the page's last line ("... rejected by 4 votes to 3 /The
  CHAIRMAN", "or /with requests"); not a document's symbol ("(E/CN.4/SR.120 /Add.1)"). 477 words removed, all read: each is a
  catchword the next page repeats.
- **Runs of results** (`pipeline/segment.py`): a result after a result is the next vote ("Article 13 was adopted ..." / "Article
  14 was adopted ..."), "was unanimously adopted", "It was 50 agreed."; a heading after a result needs no full stop before it
  ("... subject to those amendments" / "Paragraphs 106 to 113"); "Examination of Article 9" (the OCR's "Bxu.aation of Article
  10") and "_ Article 1A" (14) are headings. A first version of the heading rule also took quotations of an article's text in the
  reports ('"Article 26 ...', "(Article 17)") and moved 1,239 tags, in A/6546 and E/600 among others; it was narrowed before the build.
- **The article of a result** (`api/build_db.py`): a result that names no article takes the one a later result of the same run
  names ("The first United Kingdom amendment was adopted ..." ... "Article 63, as amended, was adopted"), not the preamble's or
  a run of several articles'; a result set apart as procedural ("Article 2 as a whole as amended wes adopted") closes the
  article as a vote does (E/CN.4/SR.331: the debate on the preamble had taken article 2). Sentences of the vote parser also end
  before "the CHAIRMAN" the OCR wrote in lower case. Two hand corrections of proposers, attached to a segment the split moved,
  were moved with their decision.

Results 2,716 -> 3,296; speakers unchanged on the three evaluations. **Tags:** 85 changes judged, then the rule above, then
the 5 left: 53 right, 12 old tags restored, 12 rejected, and 10 passages left without a tag where both versions were wrong
(`eval/tag_change_check_round89.json`). **Decisions:** 23 changed fields read on the page images: proposers 6 of 8 right (two
corrected by hand), articles 2 of 15 right before the run rule, which then brought back the other 12. **Paired audit** on 30
changed pages (`eval/segment_audit_round89.json`): pages with no error 9 -> 11, errors 37 -> 31, 7 pages better, 4 worse by one
(a heading of the previous meeting's column, a stray "of", a garbled running head, two results still joined).

## Round 90 (15 October 2026): turns behind marks, the next column's headings, the figures the OCR garbled

- **Turns** (`pipeline/segment.py`): a semicolon or a "+" before the title ("; “Mrs. ROOSEVELT (United States of America)
  requested"), the title "Mp.", the typographic apostrophe inside a name ("Mr. D’SOUZA (India)": twelve of the thirty pages of
  the audit had a turn of his hidden; not "FOMIN’", a quotation mark), a comma before "The CHAIRMAN", and the chair after a
  numbered phrase inside a line ("38. After a procedural discussion in which Mr. X (Sierra Leone) took part, the CHAIRMAN
  suggested"). In a meeting record a heading behind a bar ("| ARTICLE 28") is the next column's, the previous meeting's, and no
  heading; in a document it is one.
- **Figures** (`pipeline/decisions.py`): "to_one", "to )" (one), "b; 8 votes to k", "J0" (10), "adopted .by 7", "adopted. by. 11"
  (the dot only before a lower-case "by": "was adopted. By 19 votes to 12, the Committee decided" keeps its own figures).

Speeches 28,458 -> 28,515; figures read in 4,385 -> 4,405 decisions; speakers unchanged on the three evaluations. **Tags:** 18
changes judged, 4 right; 14 old tags restored or the new ones rejected (`eval/tag_change_check_round90.json`). **Decisions:** 31
changes read on the page images: 25 right, 5 better but still short of a figure (an abstention the OCR lost), 1 wrong (a decision
in E/CN.4/SR.112 adopted unanimously that took another vote's figures). **Paired audit** on 30 changed pages
(`eval/segment_audit_round90.json`): pages with no error 5 -> 13, errors 50 -> 33 (turns inside another 29 -> 10), 19 pages
better, 2 worse by one (a heading behind a bar that was a heading, a turn after a catchword).

## Round 91 (15 October 2026): a rule for the chair's passing mentions, measured and dropped; three small fixes

- **Measured and not kept.** Rounds 85-90 each restored tags by hand where a chair's turn found by the segmenter had moved the
  debate's article by naming one in passing ("the true analogy was with the procedure adopted in connexion with article 23").
  A rule was tried that let a chair's turn move the article only when it acts on it (puts it to the vote, reads it, opens or
  closes its debate, asks for comments). It changed 608 tags; on a random sample of 60 judged blind, the old tag was preferred in
  35, the new in 21, neither in 4 (most of the losses: speeches that kept a right article through a chair's aside). The rule was
  removed; the hand restorations stay the way to handle such cases (`eval/tag_change_check_round91.json`).
- **Fixes** (`pipeline/segment.py`): "The CHATRMIN" opens the chair's turn; "ves adopted" is a result; a heading behind a bar in a
  meeting record is dropped only when it repeats the article under debate ("| ARTICLE 28" during article 28, the previous
  meeting's column, A/C.3/SR.178), not when it names the next one ("| Article 38" after article 37, E/CN.4/SR.240).

9 records changed, no word lost, speakers unchanged on the three evaluations; one tag changed, judged. Two decisions keep wrong
figures that no rule reaches (E/CN.4/SR.183: the OCR reads "6 votes tok" for 8 to 4; E/CN.4/SR.112: a result inside a speech
takes another vote's figures).

## Round 92 (15 October 2026): a fourth fresh audit on random pages

Two new random samples of the meeting records (seeds 92 and 93, 12 pages of each kind of record, 120 page images; 6 of them in
an earlier sample), read with the same instructions as rounds 76, 80 and 84, against the database after round 91
(`eval/segment_audit_round92.json`):

| Sample (database after) | Pages with no error | Errors | Speeches inside another |
|---|---|---|---|
| Round 76 (round 75) | 53 of 120 (44%) | 117 | 25 of 445 (5.6%) |
| Round 80 (round 79) | 65 of 120 (54%) | 81 | 31 of 441 (7.0%) |
| Round 84 (round 83) | 71 of 120 (59%) | 85 | 29 of 461 (6.3%) |
| **Round 92 (round 91)** | **78 of 120 (65%, 95% interval 56-74%)** | **69** | **22 of 460 (4.8%)** |

Against round 76 the gain is significant (z = 3.2); against round 80 it is not quite (z = 1.7), nor against round 84 (z = 0.9).
By kind of record (pages with no error, of 24): CHR 1949-54 13, Third Committee 1950-61 19, 1962-66 18, UDHR 1946-48 14, the
plenary 14. The handover's first aim (60% of pages without error) is reached; the second (fewer than 2% of the speeches inside
another) is not.

What is left (69 errors): turns inside another 22 (9 in the Commission's typed records, "AZMI Bey (Egypt)" twice, a title after
the name that the turn rules do not take; 6 in the plenary of 1946, the President's turns after a decision in A/PV.7); results
and headings inside a passage 22 (the plenary's item headings after a decision, "Paragraph 7" after a result); running heads 8;
missing headings or notes 8; speakers and delegations 6.

**Fixed after the audit:** "Mr. KOITE (Mali)" was filed under Malta in 8 speeches: one reading "KOITE (Mala)" / "(Malı)" had
gone to Malta by the closest name, and the session's entry then took every later "(Mali)". The OCR's dotless "ı" is now an "i"
(`pipeline/entities.py`) and "Mala" a variant of Mali (`data/gazetteer/states.csv`); the 8 speeches are Mali's, and no other
speaker changed. (A first fix, refusing the joint reading when the engines agree on another country, would also have undone the
right corrections of "CHANG (Chine)" to China and of "Mrs. AFNAN (Iran)" to Iraq; it was dropped.)

## Round 93 (15 October 2026): the plenary of 1946, and a title after the name inside a line

From the audit of round 92 (`pipeline/segment.py`): a turn whose title follows the name inside a line ('... a punishable
offence." AZMI Bay (Egypt) was unable to accede', with the OCR's "Bay" for Bey); in the verbatim plenary records, the President
however the OCR spells the role before "(Translation from the French)" ("THe she", "The Presiwent ."), a numbered item of the
agenda after a decision ("Decision: The agenda was adopted." / "102. Distribution of Agenda Items among" / "the Committees
(document A/163)."), and the masthead that now ends at the first translated speech (A/PV.7: the masthead ran to page 7 and took
two decisions and the President's turns). A result right after its own heading ("Paragraph 6" / "Paragraph 6 was accepted without
objection." / "Paragraph 7") is a result, so the next heading is one.

13 records changed; no word lost; no article tag or decision changed; speakers unchanged on the three evaluations (one better
spelling, Pérez Cisneros). **Paired audit** on 30 changed pages (`eval/segment_audit_round93.json`): pages with no error 4 -> 9,
errors 58 -> 35 (turns inside another 24 -> 6), 20 pages better, none worse. What is left there: the plenary's item headings that
carry no number or no document (A/PV.55), 18 results or headings inside a passage.

## Round 94 (15 October 2026): the plenary's agenda items, and headings after a result

- The plenary's item of the agenda after a decision or after the President's sentence ("152. Provisional Financial Regulations
  of" / ... / "(document A/218).", "160. Application of Article 27 of the Charter (postponement of the discussion)"), over up to six
  lines; with a number of two or three figures (not the list the President reads out, "1. The items on the provisional agenda
  (document A/66)", which a first version took for a heading).
- In the typed records, a heading after a result: "First new article", "Second new article", "Document E/CN.4/L.366/Add.3".
- "Article 52 was adopted_as amended." (the OCR's underscore) and "The amendment was withdrawn." are results.

5 records changed, no word lost, no decision changed; one result split off a speech took the speech's article back by hand.
**Paired audit** on the 12 changed pages (`eval/segment_audit_round94.json`): pages with no error 1 -> 5, errors 22 -> 10,
9 pages better, none worse.

## Round 95 (15 October 2026): results without figures, the Rapporteur, the Secretary-General

- A result on its own line after a speech that opens with "Both", "All" or "These" ("Both suggestions were adopted.",
  "All the amendments were rejected.") is a result, not the end of the speech: 3 more decisions.
- The Rapporteur's turns ("The RAPPORTEUR read the amended text ...") were filed as the chair's, without a name. They are now
  speeches, named from the masthead's "Rapporteur:" line with the delegation it gives (29 turns: MALIK, Lebanon, in
  E/CN.4/AC.1/SR.17-19, E/CN.4/SR.12 and E/CN.4/SR.81; WHITLAM, Australia, in E/CN.4/SR.408; KAECKENBEECK, Belgium, in
  E/CN.4/SR.410), each checked against its masthead.
- "the Secretary-General" inside a sentence no longer opens a chair's turn (chair's turns 7,367 -> 7,289 with the
  Rapporteur's); "The SECRETARY-GENERAL:" and "The SECRETARY-GENERAL (translated from ...)" still do (A/PV.1496).
- Two tags that the new turns exposed were judged wrong and rejected (E/CN.4/AC.1/SR.18, UDHR 19; E/CN.4/SR.348, ICCPR 30); no
  other tag changed.
- The French column in the 1946 plenary: one passage only (A/PV.55, p. 91), too few for a rule; left as known.

33 records changed, no word lost. **Paired audit** on 30 changed pages (`eval/segment_audit_round95.json`): pages with no error
3 -> 8, errors 79 -> 53, 21 pages better, 2 worse (A/C.3/SR.495, p. 4, a speaker left without a name; E/CN.4/SR.12, p. 3, the
Rapporteur's turn then still the chair's, now a speech). What is left: decisions and procedural paragraphs inside a Rapporteur's
turn (E/CN.4/SR.12).

## Round 96 (15 October 2026): the body's decisions inside a turn, the chair's names from the list of officers

- The record's own decision at the head of a line after a sentence that ended ("At the request of Dr. CHANG (China), the
  Commission decided to take" / "a vote by paragraphs.", "The Committee agreed to leave to the Drafting Sub-Committee ...") is a
  passage of its own, not the end of the speech or the chair's turn before it (17 records). A speaker's account of it would say
  "had decided".
- "IECISION:" is the label of a decision; "First Paragraph", "Fourth paragraph" (without a colon: with one it heads a list of
  amendments) a heading; "• Article 8" and "Article 3, paragraph 2" the article's heading, the latter with its paragraph, which
  the split drafts need (E/CN.4/95 art. 3, para. 2 is final art. 7).
- The OCR's "GHAIRMAN", "GHATRMAN" and "RAPPORITUR", "RAPPORTHOR" open the chair's or the Rapporteur's turn (the Rapporteur's
  variants only with the turn's words after them, not a masthead's "The RAPPORIEUR"); "The Chairman of the Inter-American
  Commission", "The President of the Council had himself ...", "The Secretary of the Committee shall enjoy ..." do not.
- The chair's name from the list of officers when a contents line read as a heading had cut it off the masthead, and up to the
  next officer when the lines run together ("Mrs. F. D. ROOSEVELT United States of America Members: ..."): 25 records, 261 turns
  more named (Roosevelt 1949-50, Malik 1951-52, Azmi 1953-54), each against its masthead; none when the OCR put another officer
  right after the label (E/CN.4/SR.99, "Chairman: Rapporteur: Mr. AZKOUL"). "MAHMOUD AZMI" and "MAHMOUL AZMI" are AZMI.
- A delegate's name with a particle in capitals is read as printed: ESTRADA DE LA HOZ (Guatemala, 7 speeches), AUJAY DE LA DURE
  (France, 2), COELHO LISBOA DE LARRAGOITI (Brazil).

No word lost. 21 tags changed with the new passages and headings; blind judges (two, a third on splits) kept 15, preferred the
old tag on 4 (restored: the asylum article in E/CN.4/AC.1/SR.37, the deferral of article 7 in E/CN.4/SR.142, E/CN.4/85) and no
tag on 3 (rejected). **Paired audit** on 30 changed records, one page each (`eval/segment_audit_round96.json`): pages with no
error 7 -> 14, errors 47 -> 31, 15 pages better, 1 worse (E/CN.4/AC.1/SR.27, p. 9, where the reader counted two lines of a
decision that the OCR lost, and the Rapporteur's turn "Mo, MALIK (Lebanon); Rapporteur," still inside the chair's). The fixes to
the Rapporteur's variants and to "The Chairman of the" came after the audit (11 records, checked by hand).

## Round 97 (15 October 2026): votes on the chair's ruling, and the chair as the OCR misreads him

- "Mo, MALIK (Lebanon); Rapporteur," opens a speech ("Mo," for "Mr."; with it "Mo, WHIPLAS (\uatrat ia)", WHITLAM of
  Australia, E/CN.4/SR.199), and "Second Pararrraph" is a heading (E/CN.4/SR.12).
- The body's note opens its passage also when the requester's title has its full stop ("At the request of Dr. CHANG (China), the
  Commission decided ..."), and a labelled decision after that note is a passage of its own ("IECISION: ...").
- A vote on the chair's ruling is a result ("The Chairman's ruling was upheld by 12 votes to 5, with 30 abstentions.", 15 in
  the records), as is the count alone ("There were 6 votes in favour, 6 against and 4 abstentions;") and "It was so decided, °°".
  Two blind judges took the vote on a ruling for procedure: such votes carry no article, in the decisions or the passages.
- The chair's role with a sign for a letter in the typed records: "Tho CHAIRM‘N, as representative of", "The CPAJRM{N.",
  "The CHAIRM/N suggested" (E/CN.4/SR.61, SR.153, SR.52, E/CN.4/AC.1/SR.4).
- The chair's article "in view of the provisions of article 2" is a reference, not the article taken up (a first version moved
  eight passages of E/CN.4/SR.61 from UDHR 17 to UDHR 29; the tag diff caught it).

No word lost. 9 tags changed; the judges kept 5, preferred the old tag on 1 (restored, E/CN.4/SR.153) and none on 3 (votes on
the chair's ruling, rejected with three more of the same). **Paired audit** on 27 changed records, one page each
(`eval/segment_audit_round97.json`): pages with no error 2 -> 9, errors 48 -> 33, 16 pages better, 1 worse (A/C.3/SR.385, where
the vote on the ruling was then a procedural passage, not a vote: since marked a vote).

## Round 98 (15 October 2026): OCR debris before a turn, and the phrase that opens a chair's turn

- A token of OCR debris before a speaker's turn, after a sentence that ended or a page's head ("Bie Mr. MALIK (Lebanon),
  Rapporteur, read article 3.", "viet) Mr, SCHWELB (Secretariat)", "Te Miss BOWIE", "Lye Mr. CHANG (China)", "Qe Mr. NISOT"):
  15 turns in 11 records of 1950. Never a word that joins the line to the sentence before ("and Mr. WILSON (United
  Kingdom) said", "by Mr. ENCINAS (Peru), proposed", "As Mr. ENTEZAM (Iran) was also dissatisfied"), and the turn must name a
  delegation.
- "On that understanding," opens a turn ("gh, On that understanding, Mr. HOARE (United Kingdom) withdrew the clause", "gh,"
  the OCR's "94.").
- After such a phrase the chair as the OCR misreads him ("the CHATRMAN", "the CHARMAN", "the CHAIFIN", ", . the CHATRMAN") opens
  the chair's turn: 8 turns. A number that ends a sentence before the next paragraph's number ("... the USSR text. 6, Mr.
  CHANG") stops the phrase, which had given the chair's words to the next speaker.

No word lost. A first version of that stop also took a line's own paragraph number ("56. In reply to ...") for the end of a
sentence and merged 63 records' turns; the next pass undid it, but the id-keyed caches had moved with it, and three unchanged
speeches changed their tag (kept at the tag before the round, not judged). 5 tags changed with the new turns: the judges kept 3
and preferred the old tag on 2 (restored). **Paired audit** on 22 changed records, one page each
(`eval/segment_audit_round98.json`): errors 58 -> 49, pages with no error 2 -> 2, 13 pages better, 2 worse (the readers listing
OCR specks before turns that both versions keep). What is left there: paragraph numbers misread as words ("26 "Mr, EYROU",
"Ds Mr, CRIRE") kept at the head of the turn.

## Round 99 (16 October 2026): a fifth fresh audit, paragraph numbers, the chair behind an opening phrase

**Fresh audit.** Two new random samples of the meeting records (seeds 98 and 99, 12 pages of each kind of record, 120 page
images, 2 in both), read with the same instructions as rounds 76-92, against the database after round 98
(`eval/segment_audit_round99.json`): pages with no error 67 of 120 (56%, 95% interval 47-65%), errors 86, speeches inside
another 28 of 514 (5.4%). Against round 92 (78 of 120, 69 errors) the difference is not significant (z = 1.4); by kind of record
(of 24): CHR 1949-54 13, Third Committee 1950-61 14, 1962-66 16, UDHR 1946-48 12, the plenary 1946-48 12. Of the 77 errors that name a
segment, 69 sit on segments as they were before round 93; on reading, the other 8 are no new errors either (the President's turn
that round 93 split off in A/PV.7 still holds two more turns, which before sat inside the Cuban speech; "The Secretary-Gencral is
directed to convene" in an annex of E/PV.84 read as the chair's turn, as "The Secretary-General therefore suggests" was before). The classes: turns inside another 28, page furniture in a text 14, text in no segment 13
(mostly headings), results or headings inside a turn 7, wrong speaker 6.

What changed in this round:
- **Paragraph numbers.** A paragraph number that breaks its record's sequence is read again from its neighbours when exactly one
  number of the gap is a digit off the reading ("355." between 54 and 60 is 55, "730" is 73, "34." between 53 and 55 is 54): 91
  numbers, the ¶ that citations give; never a number a neighbour also has, nor one whose own paragraphs would run into the next
  number. The text keeps the number as printed. A blind reading of 30 of them on the scans agreed with all 30
  (`eval/paragraph_numbers_round99.json`).
- **The chair behind an opening phrase is named** ("In reply to Mr. AZKOUL (Lebanon), the CHAIRMAN said ...", "At the request of
  Mr. BAROODY (Saudi Arabia), the CHAIRMAN called for ..."): 103 turns more, from the same masthead and "took the Chair" reading as
  the others.
- "49. After a further exchange of views in which" / "Mr. KASLIWAL (India), Lady TWEEDSMUIR (United Kingdom) and the CHAIRMAN took
  part, the CHAIRMAN said ..." is one chair's turn, not Kasliwal's (a line that stops on "which" or "whom" joins the next).
- An office printed for the delegation does not match a state's delegate: "Mr. DAS (Secretary of the Committee)" is the
  Secretariat's Das, not Daes of Greece (9 speeches); "Mr. BALDWIN (International League for the Rights of Man)" and "Mr.
  ABDELRAHMAN (International Labour Organisation)" likewise. A delegate holding an office ("Mr. NISOT (Rapporteur)") keeps his
  delegation.
- In the Covenants, an article of another treaty ("article 2 of the draft Convention on Freedom of Information") and "as had been
  done in articles 12 and 14" are references, not the article the chair takes up (A/C.3/SR.1077).
- The close of a meeting ("The meeting rose at 5.25 p.m.") carries no article: two blind judges, and 403 such lines had one.

No word lost. 8 tags changed besides the closings: the judges kept 4 and took 4 for procedure or the close (rejected).

## A gold set of 40 pages (16 October 2026): the auditors calibrated

40 random pages of the meeting records (8 of each kind, seed 100; `eval/gold_pages/pages.json`) were set aside for a full
annotation: every start of a segment on the page (line, kind, speaker, delegation) and the lines that are not the record's text.
The author annotated 6 of them by hand (`eval/annotate_pages.py`, `data/gold/segment_pages.json`); three model annotators read
each of the 40 scans independently, in the same format (`eval/gold_pages/model_annotators.json`, merged by majority in
`data/gold/segment_pages_models.json`).

- The three annotators agreed on everything on 37 of the 40 pages; on the other 3 they differed only in a name's spelling
  (Kayaly, Morozov) or one line of debris.
- On the author's 6 pages, every difference from the annotators' majority was a start or a line the hand annotation had left out
  (a turn whose name the OCR broke, "Me. PICKFOR)"; a result after an underscore; a catchword; a heading's kind; the speaker's
  name as on the scan); none the other way.
- The audits on page images used since round 66 (one reader per page, reporting errors) agree with the full annotation where they
  overlap: on these 40 pages the audit found 4 turns inside another, the annotation the same 4; pages without an error 22 of 40,
  against 25 of 40 with every start and kind right in the annotation. The annotation finds more results and headings left inside
  a passage (18), which the audits report under other kinds of error or not at all.

The database against the annotators' majority (`python3 eval/segment_gold_eval.py --gold data/gold/segment_pages_models.json`):
starts precision 0.964, recall 0.878 (22 missed: 4 turns, 18 results and headings; 6 too many); kind 0.994; speaker 0.981 of
103; delegation 0.981; 31 lines that are not the record's text (most of them specks and underlines the OCR read as text). This is
now the fixed check run each round, alongside the speaker evaluations.

## Round 109 (29 October 2026): the audit repeated after the Athena merge, with model judges only

Since round 69 the database changed a great deal: the vision reader's text on 10,348 pages (21 and 28 October), the French
columns taken out (round 105 and after), the rule for Covenant speeches without a drafting word (round 107), 827 tags from the
readers' possible articles (round 108) and 745 questions of general debate accepted below the threshold. The audit was drawn
again with the design of rounds 43-69 (`eval/audit_sample.py`, seed 109) and, as before, judged by two blind judges per item
(opus, sonnet) and a third on the splits; unlike round 69, each judge took about 25 items instead of 12, and nobody reviewed the
verdicts by hand this time (the publication audit with a human annotator stays the reference).

| | Round 69 | Round 109 |
|---|---|---|
| Precision, weighted by tags | 95.4% ± 3.5 (127 of 133) | **95.3% ± 3.5** (126 of 132) |
| Report paragraphs | 27 of 29 | 30 of 30 |
| L-series paragraphs (not in the audit) | 10 of 10 | 10 of 10 |
| Coverage within records with tags | 83% | **91%** (R1: 12 of 50 untagged speeches about one article) |
| Coverage overall | 76% | **85%** (R2: 5 of 60) |
| Coverage, pooled over the last three rounds | 75% (65, 66, 69); 85% within | 81% (66, 69, 109); 87% within |

The six wrong speech tags: a speech on freedom of association tagged with equality before the law (E/CN.4/SR.171, ICCPR 26
for 22); a procedural request on the summary record (E/CN.4/SR.251); the number of ratifications for entry into force tagged
with signature (A/C.3/SR.1407, ICESCR 26 for 27); an order-of-work point on taking an article's paragraphs separately
(A/C.3/SR.1085); a second to a motion to refer the work articles to a drafting committee (E/CN.4/SR.64); and the French addition
on the standard of living accepted into the text for articles 25-26, tagged with the work article (E/CN.4/SR.66). All six are
refused (`data/concordance/tag_rejections.csv`); the figure above is the database's before that. Of the 17 untagged speeches
about an article, 13 have no article context in their record and 4 were refused by Jev.

**Questions of general debate** (new stratum): 20 random speeches from each group, the topic judges' prompt.

| Group | Speeches | Right |
|---|---|---|
| Jev at 0.9 or more | 1,588 | 19 of 20 |
| accepted at 0.8-0.9 (two judges) | 434 | 19 of 20 |
| accepted at 0.7-0.8 (two judges and a third on 40) | 311 | 16 of 20 |
| weighted by the groups' sizes | 2,333 | **93%** |

The six wrong: the preamble's wording filed as general, a procedural exchange on the federal and colonial clauses, a scheme of
State reports outside the covenant, two order-of-work points (implementation; self-determination) and a one-sentence defence of
the Commission's report. They are refused (`data/concordance/topic_rejections.csv`). The 0.7-0.8 band is the weakest, as its
two judges' yield (66%) suggested.

**Fresh pages** (the design of rounds 76-99, `eval/segment_audit_round109.json`): two new random samples (seeds 108 and 109,
12 pages of each kind of record, 120 page images, 2 in both), one opus reader per 10 pages instead of one per page. Pages with
no error **77 of 120** (64%, 95% interval 55-72%), against round 99's 67 of 120 (z = 1.3, not significant); errors 64 (86); turns
inside another 7 of 412 turns on the pages (round 99: 28 of 514). By kind of record (of 24): UDHR 1946-48 17, Third Committee
1962-66 16, CHR 1949-54 15, the plenary 1946-48 15, Third Committee 1950-61 14. The classes: other 17 (mostly decisions, headings
or footnotes inside a turn), page furniture in a text 13, text in no segment 10 (mostly footnotes and headings), a heading or an
election line of the wrong kind 10, turns inside another 7, wrong speaker 5, wrong delegation 2. A reader with ten pages may look
less closely than one with one, so the fall in turns inside another is a direction, not a measured gain.

## Rounds 110–126 (30–31 October 2026): whole-record readers, context switches, non-speech tag hygiene, and metadata completion

- **Whole-record readers and possible articles (rounds 110 and 126).** All 274 remaining tagged meeting records (`R1`) with untagged
  speeches over 150 characters (`1,220` speeches) were read by two independent whole-record readers (opus, sonnet): 112 new tags passed
  the agreement and Jev (`p >= 0.7`) rule, and a blind check of 40 found **40 of 40 right** (`eval/readers110_check`). A 40-record
  pilot of the 554 untagged records (`R2`, 827 speeches) yielded 0 agreed tags (only other agenda items and general procedural work).
  In round 126, the 210 new `(speech, article)` pairs added to `possible_articles.csv` by round 110 after round 108's pass were judged
  by two blind judges (`eval/round126/`): both called 83 right (`79` speeches; `4` dual-article speeches excluded by rule, `75` added to
  `reader_tags.csv`, `73` new speech tags in the database).
- **Context switched by a passing mention and stranded non-speech tags (rounds 111d, 113, 121–122).** Every `A-B-A` context-switch
  run in the meeting records and every non-speech segment stranded when surrounding speeches were retagged (`13 + 763 + 114 = 890`
  tagged segments across 126 records) was judged by two blind judges with the surrounding record window (`eval/round113/`,
  `eval/round122/`): 38 speeches were retagged (`data/concordance/speech_retags.csv`) and 209 wrong context tags were refused
  (`data/concordance/tag_rejections.csv`), which leaves no unjudged case of the class as `eval/context_switch.py search --remaining` defines it (`0`).
- **Tag hygiene on non-speech segments (rounds 115, 119, 120, 125).** A stratified audit of tagged non-speech segments (round 115) found
  votes at 95% (`19/20`), the chair's turns at 83% (`25/30`), and procedural lines at 40% (`4/10`). Applying Jev's procedure check at
  `p >= 0.8` to short chair turns (round 120; `612` dropped, blind check `31/40` wrong), stripping tags from procedural lines on
  attendance, chair handovers, suspensions, order of work, elections and non-drafting decisions (rounds 119 and 125; `419` -> `216`
  tagged procedural lines, blind check `40/40` wrong), and clearing article tags from `masthead` segments after the masthead sets the
  opening context (round 125; `263` -> `0`) removed most of the wrong non-speech tags; their precision after these rounds has not
  been measured again.
- **Speaker, delegation, presiding-officer and document metadata completeness (rounds 123–125).** Every one of the `29,694` `speech`
  segments (`100.0%`) now carries a speaker and a delegation (`0` missing; `1,694` distinct speakers, `155` delegations; round 128's blind
  check of the changed attributions: 17 of 18 speeches right, and 29 chair's turns round 124 had left unnamed restored), `99.5%`
  of the chair's turns (`7,841 / 7,877` before speech-opening overrides; `7,764 / 7,877 = 98.6%` in `segments`) name the presiding
  officer, all `2,156` real documents (excluding the 4 ODS 404 placeholders) carry a `meeting_date`, `session`, and `doc_type` (36 dates
  read from the page images in round 124, not checked by a second reader),
  and all `266` `L`-series drafts and amendments are covered in `data/concordance/l_series_readers.json`.
- **Database totals after round 126:** `2,160` documents (`836` UDHR, `1,324` Covenants), `86,039` segments, `29,694` speeches,
  `12,935` speeches tagged with a final article (`43.6%`), and `2,302` untagged speeches tagged with a general-debate question.
  Weighted speech tag precision was **95.3% ± 3.5** (`126/132`, round 109's audit, before these rounds), coverage **91%** within records
  with tags and **86%** overall; round 129's audit, after them: 94.6% ± 3.7, 86% and 84%.
