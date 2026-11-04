# Research check: ICCPR article 6 (right to life)

**Date:** 25 September 2026. **Method:** a workflow of 55 agents
(`research-check-iccpr6`), read-only on the database.

1. **Ground truth.** Two readers took the facts on article 6 from UN documents in the
   collection, not from the private compilations:
   - the Third Committee's 1957 report (A/3764, paras. 84-120);
   - the Secretary-General's annotations (A/2929) and the Commission's reports (E/1371,
     E/1681, E/1992, E/2256, E/2573).

   Each fact is an amendment, its sponsors, a vote with its figures, a meeting or a text change,
   with the report's page and paragraph. That gave 108 facts: 47 for the Third Committee in 1957,
   the rest for the Commission (1947-54) and the Working Party of 1957.
2. **Research from the database alone.** Six researchers answered typical questions with the
   research API only (the local MCP server's functions):
   - how the text changed, and who proposed "arbitrarily";
   - "from the moment of conception";
   - the genocide clauses;
   - persons under eighteen and pregnant women;
   - the Commission's decisions of 1950 and 1952;
   - the United Kingdom's position over the years.

   Each answer had to give its citations and what the database got wrong.
3. **Comparison and verification.** One agent checked each fact against the database. Each
   discrepancy then went to a verifier told to refute it from the rows and the scan text, and to
   find its cause in the pipeline.

## Result

**67 of 108 facts** could be found and were right: the meeting is in the article's history, the
vote has the report's figures, the amendment has its sponsors, and the speeches are tagged.
Of 46 discrepancies, the verifiers confirmed 43 and refuted 3.

The researchers could answer every question with pinpoints, and most answers held up against the
reports:
- the Belgian, Salvadorian and Mexican origin of the conception clause (SR.810-813);
- the Yugoslav origin of the genocide wording (1952, SR.309);
- Japan's amendment on minors (L.650, SR.815);
- the United Kingdom's case for listing exceptions, from 1947 to 1957.

The gaps sat in four places: votes, sponsors, meetings without a heading, and the report
documents, which carry no article tags.

## Fixed in this step

- **Final texts cut at 1,200 characters.** 16 long articles (e.g., ICCPR 2, 6, 9, 14, 41;
  ICESCR 8, 11, 13) stopped mid-paragraph. ICCPR 6 lost paragraph 6. The last article of each
  instrument ran on into the next one's preamble. They are now whole, read again from
  A/RES/2200(XXI) (`pipeline/build_concordance.article_runs` takes `cap=None`), with two page
  headers taken out.
- **Vote figures lost to the OCR.** "rejected by 31 votesto 20", "adopted hy 12 votes", "wes
  rejected" and "‘with 2 abstentlons" are now read (`pipeline/decisions.DECISION_RE`). 41 more
  decisions and 42 more with figures, among them the conception clause (20-31-17) and several
  1949-52 Commission votes.
- **Amendments that are not amendments.** The article's list showed reports and notes (E/1992,
  E/2573, A/2910), symbols cut short by the OCR ("E/CN.4/1", "A/C.3/1") and garbled series
  ("E/ON.4/L.140" for E/CN.4/L.140). `api/server.amendments` leaves them out and
  `build_db.fix_symbol` reads the garbled series. The MCP server listed only the first 40.
  ICCPR 6 now lists 37 amendments, not 49.
- **1949-50 meetings with no heading.** The Commission's typed records often give the article
  only in the agenda on the first page: "Article 5 (discussion continued)". E/CN.4/SR.98, with
  the decisive 1949 votes on paragraph 1, had no tag. For the 1949-50 stages the agenda's
  continued article now opens the meeting. That adds 96 tags in 10 records, and none is lost.
  From 1951 the reports' meeting lists already place such speeches. There the agenda's article
  is often finished early in the meeting (SR.324), so the rule does not apply. Hand check, round 40:
  30 of the new tags, two judges, who agreed on all 30. 29 were right. The error was a motion
  to defer a vote.
- **The MCP server's stage table** did not know E/1681 (added in the previous step): the running
  server imported `api/server.py` before the change. Reconnecting the server fixes it.

## Still open (confirmed, not fixed)

In order of how much they would add.

1. **Report documents have no article tags.** (Done on 26 September, for the reports' bodies and the Commission reports' annexes: see `docs/quality_audit.md`, rounds 41-42.) A/3764, E/CN.4/350 (E/1371), E/1681, E/1992,
   E/CN.4/669 (E/2256) and E/2573 are in the database. Their paragraphs on article 6, their
   decisions and the governments' comments in their annexes are untagged, and some carry a
   delegation read from a heading. The alternate manifest (`covenants_alt.json`) is not loaded
   as Covenant documents, and no rule gives a report's sections their articles. A table of
   report sections (symbol, pages, stage, instrument) would open about 1,300 untagged decisions (of 1,504 in reports) and the
   reports' summaries to article search.
2. **Sponsors of amendments.** (Done on 26 September for the amendments the reports list: see `docs/quality_audit.md`, sponsors.)
   - A/C.3/L.654 (the five-Power conception clause), L.649/Rev.1 and L.657 (the genocide
     paragraph) and L.658 have no sponsor. L.644 shows only Uruguay.
   - The Working Party's report L.655 is credited to Japan, and Costa Rica is credited as
     co-sponsor of the Netherlands' L.651.
   - In 1952 the USSR is credited with Yugoslavia's L.179.

   The causes are in `pipeline/decisions.proposers_of`:
   - sponsors named as adjectives ("the Colombian-Uruguayan amendment");
   - sub-amendments ("X's amendment to Y's");
   - sentences that run two votes together;
   - footnotes at the foot of the printed page, which carry the sponsors, cut into speeches.
3. **Votes still missing or joined.** (28 September: 'deleted', 'retained', 'upheld' and 'decided by N votes' are read with their figures, and 'It was so decided' as a decision without a vote; see below.)
   - In 1949-50 some decisions use other verbs ("deleted", "It was decided by 7 votes to
     6").
   - Roll-calls attached to the result segment lose their names.
   - One figure left out by the OCR ("12 votes . tch") needs the other engines' reading.
4. **Meetings not tagged.** (28 September: SR.90 and SR.139 keep their stage, since the agenda item's own title no longer counts as a meeting on implementation; 13 speeches tagged.)
   - E/CN.4/SR.90, 101, 139 and 199, the first because its heading reads "(discussion
     continued)".
   - The Commission records of 1950 whose agenda names the measures of implementation lose
     their stage on purpose.
   - The Drafting Committee's 1947 texts (E/CN.4/21, annex G) and the E/600 comments have no
     Covenant stage.
   - A/2929's documentation tables name more meetings (e.g., E/CN.4/SR.135, A/C.3/SR.288-291)
     than the tags reach.
5. **Wrong tags.**
   - In A/6546, article 6 of the Optional Protocol (1966) is tagged ICCPR 6: vote 53-0-32.
   - At A/C.3/SR.818 a procedural vote on the order of items is tagged ICCPR 6.
   - Two 1948-49 speeches have the neighbouring article.
6. **Search.** (28 September: done, see below.) The full-text index stems "conception" to "concept". An unstemmed index next to
   it would make phrase searches exact.
7. **Speakers.** (28 September: done for "The Chairman of the Working Party", see below.) "The Chairman of the Working Party said" opens a chair segment in 1957
   (SR.817). A few 1952 segments hold two speakers.

The full findings, with row ids and the verifiers' proposed fixes, are in the workflow result
(not kept in the repo). The list above is what they confirmed.

## Fixed on 28 September (the smaller open items)

- **Votes with other verbs.** "was deleted/retained/maintained/upheld/overruled by N votes" and
  "was not adopted" are read, only with their figures. "It was decided, by 7 votes to 6, to ..."
  and "The Commission decided by 9 votes to 3 that ..." are read too, with what follows as the
  subject. "It was so decided" is a decision without a vote on the sentence before. It carries
  the article only when that sentence settles the text: words, paragraphs, amendments,
  deleting, combining. The rest (when to meet, what to take up) orders the work. Decisions:
  4,619 -> 4,999, of which 348 are "decided" and 217 have no vote.
- **Meetings.** The rule that leaves a 1949-50 meeting on the measures of implementation without
  a stage read the agenda item's own title ("Draft international covenant on human rights and
  measures of implementation"). It now ignores that title: E/CN.4/SR.90 and SR.139 keep their
  stage, and 13 speeches are tagged.
- **Search.** A query entirely in quotes (`"conception"`, `"moment of conception"`) is matched
  word for word in a second, unstemmed index. For ICCPR 6, `"conception"` gives 25 hits
  against 50 before. A query without quotes still finds the other forms of a word.
- **"The Chairman of the Working Party said ..."** is no longer the chair speaking. It goes on
  from the speech before (A/C.3/SR.817, Small, New Zealand; A/C.3/SR.1119), or is procedural.
