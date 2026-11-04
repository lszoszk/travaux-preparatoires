# Research check: UDHR 26 and ICESCR 13 (the right to education)

**Date:** 29 September 2026. **Method:** as for articles 6, 11, 18 and 19, with a workflow of 67
agents, read-only on the database. There was no book note to check pinpoints against.

- **Ground truth:** 121 facts from UN reports:
  - E/CN.4/21, E/CN.4/95, E/600, E/800, E/CN.4/85 and A/777 for the UDHR, 1947-48;
  - E/1681, E/1992, E/CN.4/669, E/CN.4/689, E/CN.4/705, A/2929 and A/3764 for the ICESCR, 1950-57.
- **Research:** six researchers answered questions from the database alone:
  - the drafts of 1947-48 and who proposed free and compulsory education;
  - the parents' prior right to choose, in the Third Committee in 1948;
  - the aims of education;
  - the Commission's decisions of 1951-52 and the positions of the USSR, the United Kingdom, France
    and UNESCO;
  - the parents' liberty to choose schools (ICESCR 13(3));
  - the Third Committee in 1957.
- **Comparison and verification** as before: each discrepancy went to a verifier told to refute it.

## Result

**67 of 121 facts** could be found and were right (55%; article 19 had 73%, article 18 64%). Of 58
discrepancies, the verifiers confirmed 49. Most concern the 1947-52 records and the votes; the
Third Committee's debate of 1957 is the best covered. They fall into these groups.

1. **Votes (19 of the 49).**
   - OCR forms the parser did not read, of which some are now fixed: "11 votes with h abstentions" (h
     for 4), "votes 1 to 3", "throe", "with-1 abstention".
   - A vote that takes the figures of the next one in the same segment (SR.229: paragraph 3 given
     paragraph 4's 14-0-4), and segments that hold several votes with only one row.
   - Votes with no row at all (E/CN.4/SR.68-69, the Third Committee's SR.787-793).
   - Rows that conflict with the report's (A/3764: "27-25-25" for 27-23-25).
2. **The reports of 1951-52.** E/1992 para. 47 covers articles 28-30 in one paragraph and is mapped to
   "none", so all the 1951 education decisions carry no final article. Most 1951 speeches carry only
   the Chilean text's draft numbers (1-4) and no final article.
3. **Speakers.** A chair "speaking as the representative of the United States" carries no
   delegation, so Mrs. Roosevelt's proposals do not appear under the United States (AC.1/SR.14-15,
   AC.2/SR.8, SR.67). Speeches are merged (E/CN.4/SR.67-69, A/C.3/SR.147-148), and UNESCO's
   statements in E/CN.4/SR.226-229 sit inside other speakers' segments.
4. **Draft texts.**
   - W.2/Rev.1 (Cassin's first text) and the US suggestions (E/CN.4/AC.1/8/Rev.1) are not stages
     of the article's history.
   - The A/777 and E/CN.4/95 texts of the article are badly garbled by the OCR ("Zuezvyons nas the
     eight to education").
   - The A/2929 text of ICESCR 13 is cut in the middle of para. 2(c) and the E/1992 text has
     footnotes spliced in.
   - The Third Committee's text of 1957 (A/3764) is not a stage.
5. **Meetings and tags.**
   - E/CN.4/SR.230 (the plan and the final vote, 1951) is untagged, and SR.203-208 and SR.186-187
     are missing from the history.
   - The Third Committee's 1957 speeches (A/C.3/SR.780-788) and the amendment documents of 1948
     (A/C.3/257, 261, 273, 352-356, 397) are untagged.
   - E/CN.4/SR.69's procedure is tagged UDHR 23.
6. **Sponsors.** A/C.3/352, 273 and 397 have no proposer read, A/C.3/356 has one of its two sponsors,
   and E/CN.4/598-611 (1952) are missing from the list.
7. **Pinpoints.** The database's page is the PDF's, not the printed one, for E/1681, E/CN.4/689 and
   E/CN.4/705 (the printed number is 2-5 lower).

## Fixed in this step

- The vote figures in the OCR forms above: "with h abstentions", "votes 1 to 3", "votes | to 3 3", "throe", "with-1"
  (`pipeline/decisions.py`). Abstentions were found for 15 more decisions (3,488 to 3,503); a blind check of the
  16 that changed found the figures right in 14 (one is a digit the OCR garbled beyond a rule: "10 votes to 24
  sith ; 6").

## Suggested order of fixes

1. The reports' rows for the 1951-52 records (group 2) and the Third Committee's 1957 speeches
   (group 5): hand-read rows, and a Jev choice among the article's paragraphs.
2. A speaker for the chair "speaking as the representative of X" (group 3), by delegation.
3. The A/2929, E/1992 and A/777 texts of the article and two new stages, W.2/Rev.1 and A/3764
   (group 4).
4. The votes with no row (group 1): SR.68-69 and SR.787-793.
5. The printed page next to the PDF's in the reports (group 7).
