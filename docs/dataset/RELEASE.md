# Releasing a version of the dataset

A checklist, in order. Each step that changes a file ends with a local commit.

1. **Rebuild and check.** `python3 api/build_db.py`, the speaker evaluations and the tests (README, "Evaluation");
   `python3 eval/quality_audit.py` for the figures of the datasheet.
2. **Version.** Set `version` in `CITATION.cff` and in `deploy/site_config.json`; add the version's entry to
   `docs/dataset/CHANGELOG.md` (what changed, the counts, any field added or changed). A field added or changed means a new
   major version and a new entry in `docs/dataset/FIELDS.md`.
3. **Datasheet.** Read `docs/dataset/DATASHEET.md` against the version: the "Processing" section must describe the text as it
   is (OCR only, or the vision model's reading where it replaced the OCR), and the "Quality" section the audits behind it.
4. **Export.** `python3 api/export_dataset.py --version vX.Y` writes `data/export/`: the four JSON Lines files, `concordance/`,
   `DATASHEET.md` (with the counts and figures of this build), `FIELDS.md`, `CHANGELOG.md`, `DATA_LICENSE.md`,
   `CITATION.cff` and `manifest.json` (the checksums). `python3 -m pytest tests/test_export.py` checks that every field
   written is described in `FIELDS.md`.
5. **Archive.** `cd data && zip -r travaux-vX.Y.zip export` (the archive goes to Zenodo, not to git).
6. **Zenodo** (the author, at zenodo.org, logged in): New upload, the archive, and these fields:
   - Resource type: Dataset. Title: *UN Travaux Préparatoires: a speech-level database of the drafting records of the UDHR,
     ICCPR and ICESCR*. Version: `vX.Y`. Publication date: the day of release.
   - Creator: Szoszkiewicz, Łukasz; ORCID 0000-0001-6671-2893; Adam Mickiewicz University, Poznań.
   - Description: the datasheet's "Summary" and "What it is not".
   - Licence: Creative Commons Attribution Non Commercial 4.0 International; in Additional notes, the UN credit line
     ("© United Nations, 1946–1966, https://digitallibrary.un.org, downloaded in September 2026") and that the UN text stays
     under the UN Library's terms.
   - Keywords: travaux préparatoires; human rights; UDHR; ICCPR; ICESCR; United Nations; treaty interpretation.
   - Funding: none. Related works: the code repository ("is supplemented by"); for a new version, "New version" of the
     earlier record, so that the concept DOI is kept.
   Reserve the DOI before publishing, then re-export with `--doi 10.5281/zenodo.N` so that the datasheet carries it,
   re-zip and upload.
7. **Citation.** Put the DOI and the date in `CITATION.cff` (`doi:`, `date-released:`) and the version in the `label` of
   `deploy/site_config.json`; `python3 deploy/build_bundle.py --public` refuses to build while the placeholders remain.
8. **Tag.** `git tag dataset-vX.Y` on the commit the export was made from (`manifest.json` names it).
