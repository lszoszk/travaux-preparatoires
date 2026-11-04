# Research check: UDHR 19 and ICCPR 19 (opinion, expression, information)

**Date:** 28 September 2026. **Method:** as for articles 6, 11 and 18, with a workflow of 65
agents, read-only on the database. There was no book note to check pinpoints against.

- **Ground truth:** 103 facts from the UN reports:
  - E/CN.4/21, E/CN.4/95, E/600, E/800 and A/777 for the UDHR, 1947-48;
  - E/CN.4/350, E/1681, E/1992, E/CN.4/669, E/CN.4/705, A/2929 and A/5000 for the ICCPR,
    1949-61.
- **Research:** six researchers answered questions from the database alone:
  - how the articles on opinion and expression and on information became one;
  - the Conference on Freedom of Information of 1948;
  - the Soviet proposals on fascist and war propaganda;
  - a general limitation clause or a list;
  - the right to hold opinions;
  - the Third Committee in 1961.
- **Comparison and verification** as before: each discrepancy went to a verifier told to
  refute it.

## Result

**75 of 103 facts** could be found and were right (73%; article 18 had 63 of 98). Of 56
discrepancies, the verifiers confirmed 52. They fall into these groups.

1. **Reports and their annexes not yet read by article.** The earlier checks found the same
   gap in other reports:
   - E/600 (Geneva, December 1947) has no tag on any segment, and the Geneva working group's
     report E/CN.4/57 has none either;
   - E/CN.4/95 (1948) and the government comments E/CN.4/85 carry tags from the wrong
     numbering (UDHR 15, 18 or 19 for the articles on information, expression and assembly);
   - in E/800, annex B's covenant article 17 and its list of 25 limitations are untagged;
   - E/CN.4/705's annex I B and A/5000's annex (the text adopted in 1961) are untagged, and
     A/5000 is not a stage in the ICCPR 19 history;
   - a few rows of E/CN.4/21 and A/777 put two articles in one segment.
2. **The freedom of information bodies.** The Sub-Commission on Freedom of Information and of
   the Press (E/CN.4/SUB.1/SR.25-28, where the Mackenzie proposal merged the two articles), its
   report E/CN.4/80, and the Final Act of the 1948 Conference (E/CONF.6/79) are in the
   collection but carry no article tag. They are absent from both histories.
3. **Meetings untagged or tagged with a neighbouring article:**
   - the Geneva plenary (E/CN.4/SR.37) and the working group (E/CN.4/AC.2/SR.7);
   - the Drafting Committee's second session (AC.1/SR.40, SR.26);
   - the Commission in 1949-52 (SR.120, 162-165, 170-171, 200 and 322, where the 1952 votes on
     the limitations were taken);
   - the Third Committee in 1961 (A/C.3/SR.1073-1078);
   - in the plenary of December 1948, Vyshinsky's speeches and the USSR amendment in A/784.
4. **Decisions:**
   - figures lost or the article left off (SR.64, SR.322, E/CN.4/669);
   - a French OCR passage taken as a subject ("Par 25 voix contre 5");
   - two amendments in one row (E/1681);
   - subjects that mix in the vote before.
5. **Sponsors:**
   - A/C.3/294/Rev.1 has no proposer read;
   - E/CN.4/424 is credited to Egypt;
   - E/CN.4/434, 573, 626 and 628 have no sponsors;
   - Indonesia is given alone for the 1961 amendments (L.923/Rev.2, L.929).
6. **Speakers.** Several speeches in E/CN.4/SR.164-167 are joined under the chair or another
   delegate ("PIGUL (Belgium)"), and in E/CN.4/AC.1/SR.4 Cassin is credited to Chang.
7. **Draft texts and dates:**
   - the e1681 and e1992 texts of the article begin with footnote debris and are cut short;
   - reports are listed among the meetings of an article's history;
   - A/RES/217(III) is dated 8 December 1948 instead of 10 December.

## Fixed: the reports read by article (group 1)

These reports are now split into rows of `report_annex_sections.csv`, one row per article, per
government comment or per alternative text:
- E/600, E/CN.4/57, E/CN.4/95, E/CN.4/85 and E/800 in full: their bodies, the drafts, the
  comments of governments and the lists of limitations;
- E/CN.4/705's annex I A and B, which had been one untagged row each;
- A/5000's annex.

As before, one agent read each document and a second checked it (16 in all). The work gave 699
rows, and every anchor lands on its segment. A/4625 (articles 15-18, 1960) and A/5000 (articles
19-25, 1961) are now stages of the Covenant drafts, so ICCPR 19's history runs from the UK draft
of 1947 through A/5000 to the final text. UDHR 19's history now includes E/600 and E/800.

1,286 passages changed, all in these documents. In a blind check of 30 (round 54), all 30 tags
were right. One author was corrected: in E/CN.4/95 the right-to-life limitations 5-12 are the
United States', not South Africa's.

## Fixed: the freedom of information bodies (group 2)

The records of the Sub-Commission on Freedom of Information and of the Press (E/CN.4/SUB.1/SR.24,
25, 27, 28 and 45, and its documents SUB.1/36, 43, 45, 48, 56 and 60), its report E/CN.4/80,
E/CN.4/84 and E/CN.4/117, and the Final Act of the 1948 Conference (E/CONF.6/79) are read by
article: each speech, or run of speeches on one point, has its own row (12 agents, a reader and
a checker per part). The passages on the Declaration's articles 17-18 are UDHR 19, and those on
the Covenant's article 17 are ICCPR 19. The rest (procedure, the draft conventions on news
gathering and correction, the resolutions) is left without an article, and so is the
Sub-Commission's draft article on the press and peace (the ICCPR 20 that did not yet exist).
E/CN.4/80's passages on limitations against hatred and war propaganda go to ICCPR 20.

Both histories now list these bodies. Blind check of 30 new tags (round 55): 25 right. The five
wrong were in rows the readers had made too wide (the introduction to a text for both
instruments, paragraphs of a report adopted without discussion, a procedural exchange, a
speech on the press and peace); they are corrected.

The Final Act is dated 22 April 1948 (its last page), and resolution 217 (III) 10 December 1948
(`data/concordance/date_overrides.csv`). The MCP tool lists an article's reports with its
meetings as "Meetings and documents".

## Fixed: meetings and decisions (groups 3 and 4)

Fixes of classes, each measured and then checked blind:
- **The Commission's second reading (E/CN.4/SR.200, 1950)** is read through its headings "Article 14
  (former article 17)". The OCR misreads the digits ("Article 6 (fomany article 2)"), so a heading is
  taken only if the second reading's article and the first reading's go to the same final
  article. SR.200's votes and speeches are now ICCPR 19, 21, 22 and 26.
- **The OCR of a heading** ("Artigle 18 | So | Be", "Articlo 9") is read; SR.120's debate on assembly
  is ICCPR 21, not 19.
- **"Article 14 (continued)" in a later session** gives a meeting its article where the session's
  report lists it for that article alone (SR.322, 1952: the roll-calls on the USSR amendment; SR.329).
- **Meetings 170-171** (the joint resolution on freedom of information) belong to article 17.
- **Votes:** "adonted", "in its entirety", "on a roll-call by 11 votes to 5", and a passage break
  that ended a condition.
- **"Priority"** is procedural only in voting ("give the Convention any priority over the draft
  Covenant" is not). A delegate offering to withdraw part of an amendment or asking for a separate
  vote on words, "on a point of order", is speaking about the article.

A blind check of 82 speeches newly tagged by the first fixes: all 30 sampled right (round 56).
The procedural rule as first tried gave 27 new tags, of which 18 were right; the nine wrong were points
of order on the order of voting, so the rule now ignores the framing only for withdrawals and separate
votes on words (7 new tags, 6 right).

Tried and dropped: reading a chair "speaking as the representative of" as a delegate. Her mentions
of another article are asides at SR.162, but the same rule removed 24 correct tags (SR.147, SR.174).

**Not done:** the hand entries for seq 33 at SR.322 (the outcome word lost in every OCR engine); the
two-column pages of A/C.3/SR.1076 and SR.1078; A/784's amendments (the margin notes give them the
wrong article); the speakers of E/CN.4/SR.164-167; the Jev veto on speeches that name the article.

## Fixed: sponsors and speakers (groups 5 and 6)

- **References.** The OCR's punctuation inside document symbols is repaired ("A/C,3/L,929 and Add,1",
  "A/C.3/L»923/Rev.2", "E/CN.V117", "#/CN.4/434", "A/C.L/1373"). A document that recapitulates the
  amendments (A/C.3/294/Rev.1 and eight like it) is no longer an amendment. A sentence's whole
  wording before the symbol tells that it is one, and a list ("amendments submitted ... by the
  representatives of India (E/CN.4/563/Rev.1), of Yugoslavia (...), of Egypt (...)") keeps each
  sponsor with its own symbol.
- **Decisions.** "The India-Indonesia amendment" gives both states; a roll-call announced by
  "a vote was taken by roll-call on ..." takes its document and sponsors from that sentence.
- **Sponsors by hand:** E/CN.4/424 (India), 434 (Egypt), 438/Rev.1 (France), 440 (United
  Kingdom), from the Chairman's list at E/CN.4/SR.167; E/CN.4/102 (China) and E/CN.4/117 (USSR)
  from SR.63 and SR.64. A compilation such as A/C.3/L.460 no longer appears among an article's
  amendments.
- **Speakers.** A speech with only a bare opening ("Prof. CASSIN (France).") no longer takes the
  reading of another delegation's opening on the page: E/CN.4/AC.1/SR.4's Cassin was Chang.

Blind check of 30 references that changed (round 58): 30 of 30 proposers right, and 29 symbols
(the thirtieth, "A/C.L/1373", is now read). The exact-precision measure of the sponsors rose from 0.941 to 0.945.

**Not done:** the speeches that the two-column OCR joins under one speaker (E/CN.4/SR.164-165,
SR.167's "PIGUL"), the article of a document that an amendment amends ("the Brazilian amendment
(L.930/Rev.1) to that article", which is ICCPR 20's), and the reading order of the two-column pages.

## Suggested order of fixes

1. Hand-read rows for the reports and annexes of group 1 (E/600, E/CN.4/57, E/CN.4/95,
   E/CN.4/85, E/800 annex B, E/CN.4/705 annex I B, A/5000 annex), and A/5000 as a stage. This is
   data only.
2. Tags for the freedom of information bodies (group 2): the Sub-Commission's records and
   report, and the Conference's Final Act, as UDHR 19 and ICCPR 19 where they are about the
   article.
3. The meetings of group 3, record by record, and the decisions of group 4 at E/CN.4/SR.322 and
   E/CN.4/669.
4. The speakers of group 6, and the sponsors of group 5.
