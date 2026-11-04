# The database with the vision reader's text: a preview (19 October 2026)

`pipeline/preview_mixed.py` built a copy of the project in which every page read by the vision reader (Chandra OCR 2; 540 pages on
the laptop, 4,012 on Kaggle, plus the 34 gold pages and 6 block-D pages read for this check) replaces the OCR vote, unless the
reading was a runaway (5), the page is two-column (141; the English column is cut by the vote's layout) or its length is outside
0.85-1.15 of the vote's (55). 4,391 pages were taken (`preview_manifest_2026-10-19.json`). In the copy, `pipeline/resegment.py`
segmented again, moved the hand checks and cached answers to the new ids and rebuilt the database. Nothing here or on the VM
changed.

**Database** (`eval/preview_compare.py`, `preview_compare_2026-10-19.json`): speeches 28,560 -> 29,558 (+998, all in the 597
records with vision-reader pages, +6.8% there); with a speaker +1,014; unresolved speakers 116 -> 100; with an article 11,332 ->
11,647 (+315); chair's turns +533; votes +606. Migration: 595 records changed, 32 old ids lost (no words survive), 1,744 splits,
341 merges. Meeting dates: 8 changed, all filled in or corrected (e.g. E/CN.4/SR.232: the vote read "4 Hay 1951", the model
"Tuesday, 8 May 1951"; 8 May 1951 was a Tuesday; E/CN.4/SR.104/Corr.1: 1946 -> 1949).

**Gold pages.** The automatic comparison with the annotation does not hold when the text changes: the annotation is anchored on the
vote's lines and its matcher places the database's starts by their first words; two fuzzy variants were tried and dropped (one
left the current figures unchanged but misplaced repeated chair's lines; the other moved the current figures from 0.878 to 0.773
recall). The 12 of the 40 gold pages with the model's text (the other 28 are mostly two-column printed pages, left at the vote)
were compared by hand, segment by segment:

| Page | Result | What |
|---|---|---|
| E/CN.4/SR.153 p2, SR.163 p5, SR.31 p9, SR.48 p3, AC.1/SR.13 p5 | same | same kinds and speakers |
| E/CN.4/SR.246 p9 | better | Mr. PICKFORD (ILO) found (the vote's "Me. PICKFOR)" had hidden his turn in the chair's); chair named |
| E/CN.4/SR.367 p11 | better | the vote "adopted by 11 votes to 1" split from the chair's turn; chair named (AZMI) |
| E/CN.4/SR.226 p6 | better | seven votes, one per paragraph, where the vote's text gave one |
| E/CN.4/SR.17 p9 | better | a chair's turn found |
| E/CN.4/SR.245 p7 | better | Miss TOMLINSON (Int. Federation of Business and Professional Women) found inside BIENENFELD's turn |
| E/CN.4/SR.338 p28 | probably better | 9 segments for 3: votes, annex headings, a turn of HOARE (to check on the scan) |
| E/CN.4/SR.42 p8 | worse | "It was adopted by 10 votes" joined to the chair's turn (the model reads the paragraph as one line) |

**The risk that shows: names.** 114 speaker names (182 speeches) in the preview are absent from the current database. Part are
people the vote had hidden (LABEYRIE, JOUHAUX, TOMLINSON, ELVIN, HOWELL, CHRISTENSEN), part are misreadings: by the model
(E/CN.4/SR.203 p13 "ADRI Bey (Egypt)" where the vote and Tesseract read "AZMI"; the chair of E/CN.4/SR.250 as "KALLK", 20 turns)
or by the vote on pages left at the vote whose turns the new split exposes (KOWALEHKO, SUREMSEM). Before the vision reader's text
goes into the database, a speaker's name outside the session's attendees should be checked against the vote's reading and the
roster (and the chair's against the session's officers).

## With the name guard (20 October 2026)

`pipeline/name_guard.py` checks every name at a turn's opening and in the officers' lines of the vision reader's text before
segmentation (in the copy): a name known for its delegation stays (known: given by an attendance list at least 4 times in the
current database, or checked on the scan, or in the gazetteer; compared without spaces, hyphens or accents); otherwise the OCR
engines' reading of the same opening, if known, replaces it; otherwise the one close known name of the session (ratio >= 75; for an
officer >= 60, and for "Chairman:" the session's one chair of that delegation). A first version took any name the database held as
known and "corrected" good readings to its garbles (CHRISTENSEN -> CERISTENSEN, INSFRAN -> INSRRAN, BADAWI -> BAGDADI, VAN EEGHEN ->
VAN HGHER); the rule above dropped them. Over the 4,391 pages: 629 names replaced (280 by the engines, 349 by the session), 506 left
unverified; all 303 kinds of replacement were read: almost all right (AZKOU -> AZKOUL, HOROSOV -> MOROSOV, GASSIN -> CASSIN, KALLK and
HALLA -> MALIK, ADRI -> AZMI), 5 doubtful (JØRGENSEN -> SORENSEN, ADRI -> AMI, NARAY -> MEHTA, AMIN -> AZMI, TU -> YU).

Second source of bad names: the speaker resolution (pipeline/entities.py) votes among the old OCR engines and the clean printed
name lost to their shared garble ("Mrs. MEHTA (India)" printed, HEETA voted). With TRAVAUX_TRUST_PRINTED_NAMES=1 (set in the copy
only; the pipeline as it stands is unchanged) a printed name known for the delegation is taken first, in the database's spelling
("Charles MALIK" -> MALIK, "SØRENSEN" -> SORENSEN).

Result (`preview_compare_2026-10-20_final.json`): speeches 29,558 (+998); with a speaker 29,462 (+1,018); with a delegation 29,489
(+1,027); unresolved 96 (-20). Names absent from the current database: 114 (182 turns) before the guard, 90 (130 turns) after; the
rest are partly real people the vote had hidden (TOMLINSON, LABEYRIE, ELVIN, JOUHAUX, HOWELL) and partly garbles left unverified
(GORPHARR as a chair, KOWALEHKO, BAY for Bey). Speakers through the id map (old id -> new id): 27,772 the same, 530 changed; of the 182
changes within the same delegation, checked against the name printed in the new segment's text: 101 now fit the print and did not
before, 48 fitted before and not now (about 25 of them MOROSOV/MOROZOV, the same man spelled both ways in the current database, and
13 HEYWOOD/HEYWARD of Australia, to check on the scan; real losses: WHITE -> WHITLAM, LAWSON -> LAWSOM, LOPES -> LOPEZ, SANTA CRUZ ->
CRUZ), 21 fit neither (garbled prints), 9 both, 3 without a printed name.

## The losses fixed (20 October 2026)

`eval/preview_speakers.py` (old id -> new id through the copy's id map; the new segment's printed name decides). Before: 101
better, 48 worse. Three causes, three changes (all behind TRAVAUX_TRUST_PRINTED_NAMES=1, so the pipeline as it stands is unchanged):
- a printed name two OCR engines read exactly at that opening is kept, known or not (name_guard and entities: "Mr. WHITE
  (Australia)", three engines WHITE, had been matched to WHITLAM);
- the database's spelling of a printed name is the longest known name ending in its last word ("SMIT SANTA-CRUZ", "GANEA CRUZ" ->
  SANTA CRUZ, not CRUZ);
- api/build_db.py unify_speakers merges close spellings within a delegation (WHITE, 2 speeches, into WHITLAM, 83); a name that two
  engines read exactly at every one of its speeches is now treated as printed, as the General Assembly's printed records already
  were.
After: speeches through the id map 27,665 the same speaker, 694 changed; within the same delegation 206 better, 32 worse, 48 both
fit, 37 neither, 1 without a printed name. Of the 32: about 25 MOROSOV -> MOROZOV (one man, two spellings in the current database,
now one), 5 CRUZ -> SANTA CRUZ where the print is garbled ("SANTI CRUZ"; right, though the check counts it worse), and 2 real
losses: LAWSON -> LAWSOM (UN Secretariat, E/CN.4/AC.1/SR.39 and E/CN.4/SR.86: one engine reads LAWSOM, the attendance list's garble
wins). `preview_speakers_2026-10-20.json`.

## With Kaggle Version 5 (20 Oct): 5,319 pages of the vision reader

5,524 pages read; 5,319 taken (left at the vote: two-column 141, length outside the guard 55, runaway 9). Name guard: 596
replaced (292 by the session roster, 304 by the engines), 422 left unverified. Same flags as above (name guard on,
TRAVAUX_TRUST_PRINTED_NAMES=1 in the copy). `preview_compare_2026-10-20_v5.json`, `preview_speakers_2026-10-20_v5.json`.

| | current | preview (4,391 pp) | preview (5,319 pp) |
|---|---:|---:|---:|
| speeches | 28,560 | 29,558 | 29,595 (+1,035) |
| with a speaker | 28,444 | 29,462 | 29,503 (+1,059) |
| with a delegation | 28,462 | 29,489 | 29,524 (+1,062) |
| unresolved | 116 | 96 | 92 |
| with an article | 11,332 | 11,647 | 11,637 (+305) |

Speakers through the id map, within the delegation: better 187, worse 32 (before: 206 and 32). The drop is a correction of the
measure, not a loss: 20 of the 21 "better" cases no longer counted were wrong (KORETSKY read KORBUSKY, WILSON read WIISON), and
were counted better because the measure takes the printed name from the new segment's own text, garbled there too; they are
now KORETSKY and WILSON again. The measure can therefore flatter the preview where the new text garbles a name the same way as
the new speaker; the blind review by hand (eval/preview_review) does not share this weakness.

## Blind review by hand (20 Oct): the user, 66 items on the scan

eval/preview_review (items drawn from the preview of 20 Oct before Kaggle V5; scored by eval/preview_review_score.py,
score.json). Consistency: the 6 repeated items (A and B swapped) got the same verdict all 6 times.

| | preview better | current better | both good | both wrong | unsure | preview's share of decided |
|---|---:|---:|---:|---:|---:|---:|
| pages (division into turns) | 28 | 1 | 4 | 2 | 0 | **97%** |
| speakers | 15 | 9 | 0 | 0 | 1 | **62%** |

The division of the pages is the preview's clear gain. The speakers are not yet: unblinded, the 24 decided speaker items are
- real gains of the preview: WARREN > WINANT, CRIDE > ORIBE, HEYWARD > HEYWOOD, MCROZOV > MOROZOV, a missing speaker filled
  (VAN DER MANDELE);
- first names added to a known person, judged better against the page but splitting the person in the database
  (CHARLES MALIK 4, HANSA MEHTA 2): the canonical spelling (MALIK, MEHTA) should win, and does not in the engine-confirmed
  path of entities.resolve;
- garbles that replace a right name (BAGDADI > BACPAPI, CORBET > CARDET, LOPEZ > LOFEZ, ARUTIUNIAN > ARURRUNTAN, HABIB >
  HASRE, HODGSON > HOPGSCN; BEGTRUP > BECRRUP seen beside them): still so in the V5 preview. Some come in as "printed_known"
  because two OCR engines read the same garble, and tess3 and tess6 are the same engine family; some as "text_name", where
  the vision reader's unverified name beats the engines' vote that had the right name;
- the typists' spellings (MOROSOV for MOROZOV 3, DOWIE for BOWIE, SOERENSEN), judged against the page: by the user's decision
  of 20 Oct the text keeps them and the speaker field takes the person's usual name.

## Blind review round 2 (20 Oct): the speaker fixes, 30 new items + 4 repeats

eval/preview_review2 (seed 2027, no record of the first round; the user's rule: the person's usual name). Repeats 4 of 4
consistent. Speakers: preview better 21, current better 7, both good 1, both wrong 1; **75% of the 28 decided. Gate (85%,
at most one garbled preview name judged worse): not passed** (five garbles judged worse: LURD and LOND for LORD, MURUSUV
for MOROZOV, CAZE for SANTA CRUZ, JEXXS for JENKS).

Gains now include WARREN > WINANT, MTBOT > NISOT, ROGAN > HOGAN, MALEK > MALIK, HOANS > HOARE, LAM and WITTA > WHITLAM,
PUXUZ CISNEROS > PÉREZ CISNEROS, TEPER > SENDER, BELTRAMINO > BLANCO, two speakers found where the current database has none
(ABDUR RAHMAN, COX), and RONALD MACDONALD > MACDONALD (the current pipeline's fuller name, from another record). The losses
have three causes:
- in typed records, damaged type makes every reader agree on a garble (LURD, LOND, MURUSUV read so by Tesseract and Apple
  Vision alike): the "two engine families confirm a printed name" rule, meant for "Mr. WHITE (Australia)", takes them;
  the current pipeline's roster match had LORD and MOROZOV;
- a one-family majority (JEXXS, tess3 and tess6) outvotes the vision reader's right reading (JENKS) in the organisations' path;
- where no engine finds the opening, the vision reader's own misreading (CAZE) becomes a name.
One item (E/CN.4/AC.1/SR.39) is not a speech but the list of members (a segmentation error in both).

## Blind review round 3 (20 Oct): the second set of speaker fixes, 30 new items + 4 repeats

eval/preview_review3 (seed 2028, no record of rounds 1-2). Repeats 4 of 4 consistent. Preview better 15, current better 11,
both wrong 3, unsure 1: **58% of 26 decided. Gate not passed**, and worse than round 2. The new losses sit in the records the
vision reader did not read (printed General Assembly records, ECOSOC): the rule "a one-family majority does not outvote the
vision reader's reading" took the segment's own text as that reading, and on a page the vision reader did not read that text
is the OCR vote's (Gancta-Sayan for GARCIA-SAYAN, RAARAR, MONEW); the garbles it made then entered the session's pool and the
roster match chose them elsewhere (LINPSTRÉM for LINDSTROM). Two right names were lost by the rule that leaves a speech without
a speaker when no engine finds its opening (EKSTRAND, SANTA CRUZ).

Three rounds, each fixing the last one's losses and making new ones: the speaker resolution should not be reworked further
case by case. Proposed instead: the current resolution unchanged everywhere, and the vision reader's name taken only where its
page was read by it and the name is a known person of the delegation (the canonical spelling, or one delegate of the session
close to it); nothing else.

## The minimal rule (20 Oct): development check on the 77 decided items of rounds 1-3

The current resolution everywhere; the vision reader's name only on its own pages (5,388 marked) and only when a known person
(10,538 speeches take it). Against the user's verdicts: 41 items as judged better; of the rest, the losses the wider rules made
are gone (BACPAPI, CARDET, LOFEZ, HOPGSCN, LURD, LOND, MURUSUV, JEXXS, the round-3 garbles); one remains (CAZE, a vision-reader
page, through the current pipeline's text-name path); 16 are the user's rule at work against round 1's print-based verdicts
(MALIK for "Charles MALIK", MEHTA, SORENSEN, BOWIE, LOUTFI, MOROZOV); and about 20 gains of the wider rules are given up, all
on pages the vision reader did not read (WINANT, CLEMENTIS, YAZICI, DUQUESNE, STEPANENKO...): improvements to the OCR-only
resolution, a separate question from the vision reader. Round 4 (eval/preview_review4, 30 + 4 repeats, seed 2029, no record
of rounds 1-3) is the test, same gate.
