---
name: travaux-research
description: Research the drafting history (travaux préparatoires) of the Universal Declaration of Human Rights (UDHR, 1946–48), the International Covenant on Civil and Political Rights (ICCPR, 1949–66) and the International Covenant on Economic, Social and Cultural Rights (ICESCR, 1949–66) with the UN Travaux Préparatoires database tools — trace article drafts stage by stage, search delegate speeches, inspect amendments and roll-call votes, and cite UN records with accurate page or paragraph pinpoints (UN standard, Bluebook, or OSCOLA). Use whenever the user asks about the drafting history or legislative history of the UDHR, ICCPR, or ICESCR, VCLT Article 32 interpretation of a treaty provision, what a delegation or delegate (e.g. Cassin, Malik, Roosevelt, Santa Cruz, Mehta, Baroody) argued, or wants citations to UN drafting records verified. Requires the UN Travaux Préparatoires MCP connector (tools named *_travaux).
---

# UN Travaux Préparatoires research (`UDHR`, `ICCPR`, `ICESCR`)

The UN Travaux Préparatoires database holds 2,160 UN drafting documents (836 on the UDHR, 1946–48;
1,324 on the ICCPR and ICESCR, 1949–66), segmented into 29,694 speeches (each with its speaker and delegation),
chair turns, 6,768 decisions (302 roll-call votes) and 2,716 indexed amendments, with each session's
draft article numbers mapped to the final adopted articles. Its MCP connector gives you six tools:

| Tool | Use it to |
|---|---|
| `search_travaux` | search speeches, chair statements, votes and document paragraphs by words, `"exact phrases"`, Boolean `AND`/`OR`/`NOT`, prefix `wildcards*`, and filters (`instrument`, `article`, `delegation`, `speaker`, `symbol`, `session`, `kind`, `topic`) |
| `lookup_travaux` | read one passage in full by `id` (with how its article tag was set, the heading/chair line before it, and the UN scan page) or read an entire document's outline by `symbol` |
| `article_history_travaux` | retrieve the complete drafting dossier of one final article (`UDHR` 1–30, `ICCPR` 1–53, `ICESCR` 1–31): final text, draft texts stage by stage, meetings that debated it, votes taken, and amendments submitted |
| `delegation_travaux` | inspect a delegation's (or individual delegate's) record: speakers, sessions, speeches by article, sponsored amendments, proposals put to the vote, and roll-call votes |
| `decisions_travaux` | search and filter the 6,768 recorded votes and decisions (including 302 roll-call votes) by instrument, article, outcome (`adopted`/`rejected`), delegation, or text |
| `amendments_travaux` | search the 2,716 documents cited as amendments or proposals (L-series and working papers) by instrument, article, sponsoring delegation, or symbol |

If these tools are not available, say so and point the user to the setup guide:
https://150.254.115.204/travaux/#view=about&part=mcp (remote MCP connector address:
`https://150.254.115.204/travaux-api/mcp`). Never invent UN document symbols, page or paragraph
pinpoints, vote tallies, or delegate statements from memory.

## Ground rules

1. **Summary records (`SR`) paraphrase; plenary records (`PV`) and draft texts are verbatim.**
   - Meeting records with `/SR.` in their symbol (`E/CN.4/SR.*`, `E/CN.4/AC.1/SR.*`, `A/C.3/SR.*`,
     `E/AC.7/SR.*`) are **Summary Records** written by the UN Secretariat in the third person
     (*"Mr. Cassin (France) said that…"*). Never present a summary record as a first-person verbatim
     transcript of the speaker; either attribute it in the third person (*"According to the summary
     record, Cassin (France) argued that…"*), or quote the third-person summary record explicitly as
     such.
   - General Assembly plenary records (`A/PV.*`) and draft/amendment texts (`E/600`, `E/800`,
     `E/2573`, `A/C.3/L.*`, `E/CN.4/L.*`) may be quoted directly.
2. **Cite the exact UN symbol and pinpoint the tools give.**
   - Early typescript records (1946–49) carry **page pinpoints** (`p. 10` or `pp. 2–3`).
   - Printed GAOR and later Commission summary records carry **numbered paragraph pinpoints**
     (`para. 14` or `paras. 7–15`).
   - Never guess a page or paragraph number, and never cite an internal segment ID (`a_c.3_sr.127-0005`)
     as a UN pinpoint.
3. **Always distinguish draft article numbers from final article numbers.**
   - Each drafting stage renumbered the articles (for example, final **UDHR Article 18** was Article 14
     in the Secretariat outline of 1947, Article 20 in the Drafting Committee's draft of June 1947
     (`E/CN.4/21`) and Article 16 in the Geneva draft of December 1947 (`E/600`) and the Lake Success
     draft of 1948 (`E/800`); final **ICCPR Article 19** was Article 17 in `E/600` and in the 1949 draft
     (`E/1371`), Article 14 in the 1951 draft (`E/1992`) and Article 19 in the 1954 report `E/2573`).
   - The tools tag passages with the **final** article (`UDHR art. 18 (draft 16)`). When a speech or
     amendment text mentions the draft number in use at that meeting, state the final article alongside
     it so the reader is not misled (`draft Article 16 [final Article 18 UDHR]`).
4. **Know what you are citing (VCLT Article 32 discipline).**
   - A single delegate's statement shows that delegation's position, not the collective intent of the
     drafters. Look at how other delegations responded and how the committee voted (`decisions_travaux`).
   - A **rejected amendment** (`outcome: "rejected"`) is strong evidence of what the drafters considered
     and chose *not* to adopt. Always check the vote outcome before relying on an amendment.
   - Remember UN voting phrasing: *"rejected by 28 votes to 17, with 8 abstentions"* means **17 in
     favour (`yes: 17`), 28 against (`no: 28`), 8 abstentions** — `decisions_travaux` normalises this
     into `yes`, `no`, `abstentions`.
5. **Flag machine-translated French-only documents.**
   - Eleven documents in the corpus exist only in French in the UN's document system (`E/CN.4/122/Rev.1`,
     `A/C.3/309/Rev.1`, `A/C.3/319/Rev.1`, `A/C.3/L.1355`, and the corrigenda `A/C.3/251/Corr.1`,
     `A/C.3/278/Corr.1`, `A/C.3/308/Corr.1`, `E/CN.4/1/Rev.1/Corr.1`, `E/CN.4/53/Corr.1`, `E/CN.4/97/Corr.1`,
     `E/CN.4/SR.25/Corr.1`).
   - The tools mark them `** Machine translation from French` and append
     `[machine translation from French, ...]` to the citation. Never quote their English text as
     official UN English text; state that it is an unofficial machine translation from the French
     original and direct the user to the French scan (`https://undocs.org/fr/<SYMBOL>`).
6. **The UN document is the authoritative text.**
   - The text is read by machine from the scans (a vision model and several OCR engines); where it was
     measured against a retyped edition (1947–48), under 1% of characters are wrong, and worn typescript
     is worse.
     Always provide the `https://undocs.org/<SYMBOL>` link and remind the user to verify the UN scan
     before publishing a quotation.

## Citation styles

Follow the user's preferred style (defaulting to **UN standard**):

- **UN standard**:
  - Paragraph pinpoint: `A/C.3/SR.290, paras. 7–15 (Hoffmeister, Czechoslovakia)`
  - Page pinpoint: `E/CN.4/SR.60, p. 10 (Malik, Lebanon)`
- **Bluebook (21st ed. r. 21.7)**:
  - `U.N. Doc. A/C.3/SR.290, ¶¶ 7–15 (1950) (Hoffmeister, Czechoslovakia)`
  - `U.N. Doc. E/CN.4/SR.60, at 10 (1948) (Malik, Lebanon)`
- **OSCOLA (4th ed.)**:
  - `UN Doc A/C.3/SR.290 (1950) paras 7–15 (Hoffmeister, Czechoslovakia)`
  - `UN Doc E/CN.4/SR.60 (1948) 10 (Malik, Lebanon)`

## Workflows

### 1. "Trace the drafting history of Article X (VCLT Art. 32)"
1. Call `article_history_travaux(instrument, article)` first. This gives you the adopted text, every
   draft stage in chronological order (from the 1947 Secretariat outline `E/CN.4/AC.1/3` through
   `E/600`, `E/800`, `E/2573`, Third Committee drafts, to GA adoption), the list of meetings, the
   recorded votes, and the amendments.
2. Identify the stage where the wording at issue entered or changed in the draft text.
3. Call `search_travaux(instrument=..., article=..., query="...")` to find the debates on the key
   phrase, or call `decisions_travaux(instrument=..., article=...)` and
   `amendments_travaux(instrument=..., article=...)` to inspect the proposals and votes at that stage.
4. Call `lookup_travaux(id=...)` on the 3–6 pivotal speeches and chair rulings so you read the full
   text and see what heading or chair announcement set the article context.
5. Present the drafting evolution chronologically:
   - Early draft text and numbering;
   - Key amendments proposed (`L.` symbols and sponsors) and the arguments for and against;
   - The vote tally and outcome (`adopted` or `rejected`, with roll-call alignments where relevant);
   - The resulting text and its significance for interpreting the final provision.

### 2. "What did Delegation Y or Delegate Z argue on X?"
1. Call `delegation_travaux(delegation=..., speaker=...)` to see the delegation's speakers, active
   sessions, top articles spoken on, sponsored amendments, and roll-call votes.
2. Call `search_travaux(delegation=..., speaker=..., article=..., query=...)` to retrieve the specific
   interventions.
3. Read the most important speeches in full with `lookup_travaux(id=...)`.
4. Synthesise the delegation's position across sessions (Commission, Drafting Committee, ECOSOC, Third
   Committee, Plenary), noting which of its amendments were adopted or rejected.

### 3. "Cross-cutting debates not tied to a single article"
When a question concerns a general structural debate (e.g., whether to have one covenant or two, the
federal state clause, the colonial/territorial application clause, reservations, the right of
individual petition, or measures of implementation), call `search_travaux` with the `topic` filter:
`self_determination`, `two_covenants`, `implementation`, `petitions`, `federal_clause`,
`territorial_clause`, `reservations`, `form_of_bill`, or `general`.

### 4. "Check the UN travaux citations in my draft"
For each UN document citation in the user's text:
1. Call `lookup_travaux(symbol=...)` or `search_travaux(symbol=..., speaker=...)` to locate the passage.
2. Verify:
   - The UN document symbol, body, session, and meeting date;
   - The page (`p.`/`pp.`) or paragraph (`para.`/`paras.`) pinpoint;
   - The speaker's name and delegation;
   - The draft-to-final article mapping;
   - Any vote tally (ensuring *"rejected by X to Y"* was not inverted into X in favour);
   - Whether the text accurately reflects the summary record without misquoting a third-person
     paraphrase as verbatim speech.
3. Report each citation as verified / needs correction (with the exact corrected citation and link to
   `https://undocs.org/<SYMBOL>`).
