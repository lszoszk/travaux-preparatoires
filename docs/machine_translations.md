# Machine translations of French-only documents

Eleven documents that the UN Digital Library holds only in French (corrigenda and revisions of 1947-48, and one
set of amendments of 1966) are in the database as machine translations. They are marked everywhere they appear and can be left out of any search.

| Document | Pages | What it is |
|---|---|---|
| E/CN.4/122/Rev.1 | 8 | American Declaration of the Rights and Duties of Man (French version; the original is Spanish) |
| A/C.3/309/Rev.1 | 1 | Amendment to draft article 6 (Mexico, Chile, Venezuela) |
| A/C.3/319/Rev.1 | 1 | Compromise text for draft article 10 (United Kingdom) |
| A/C.3/251/Corr.1, 278/Corr.1, 308/Corr.1 | 1 each | Corrigenda to Third Committee amendments |
| E/CN.4/1/Rev.1/Corr.1, 53/Corr.1, 97/Corr.1, SR.25/Corr.1 | 1-2 | Corrigenda of the Commission of 1947-48 |
| A/C.3/L.1355 | 2 | Netherlands: amendments to part IV of the draft Covenant on Civil and Political Rights, with a new article on petitions from individuals (17 October 1966; translated 21 October 2026, settled 5 of 7 points the check raised) |

## How they were made (29 September 2026)

1. Each page of the French PDF was rendered as an image (`data/raw/<symbol>-FR.pdf`).
2. **claude-fable-5-1** translated the document from the images, with the PDF's text layer as a help only
   (the text layer is full of OCR errors), into the English of a UN record, keeping headings, numbers and symbols.
   A word that could not be read was written `[illegible]`. Where the document says it is itself a translation
   ("ORIGINAL: SPANISH"), the French text as it stands was translated, not an English text of the original.
3. **claude-sonnet-5-5** compared the translation with the scans, without having made it, and listed every
   discrepancy (error or minor).
4. **claude-fable-5-1** settled each discrepancy from the scan. Two documents needed it: A/C.3/309/Rev.1
   ("granted" became "recognized", after the French *reconnus*) and E/CN.4/122/Rev.1 (a faint verb, read as
   *exaltent*, "exalt"). The other eight were judged faithful. Passages that stay doubtful are in each record's
   `uncertain` list.

The record of each translation, with the checker's findings, is `data/translations/<symbol>.json`;
`pipeline/translations.py` lays the pages out as the document's text and logs it as fetched (`via: machine_translation`).

## How they are marked

- `documents.machine_translated = 1`, with `source_language`, `translation_model`, `translation_check` and
  `translation_date`.
- **API:** every result carries those fields; the citation ends "[machine translation from French, claude-fable-5-1]";
  CSV and JSON exports have a `machine_translation` column. `translations=0` on `/api/search` leaves them out;
  `/api/facets` reports how many there are.
- **MCP:** results are marked "** Machine translation from French (...)"; `include_translations: false` leaves them out.
- **Site:** a badge and a line under each result, a banner over the record with a link to the French scan, and a
  checkbox "Include machine translations" (ticked by default; the state is in the URL as `translations=0`).

## Limits

- They are not UN texts. Quote the French scan, not the translation.
- They carry no article tags yet: none of the ten is tagged with an article of the Declaration.
- The translations are of the French version only; E/CN.4/122/Rev.1 is a translation of a Spanish original,
  so this is a translation of a translation.
