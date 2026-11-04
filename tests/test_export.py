"""The dataset export (api/export_dataset.py): every field it writes is described in docs/dataset/FIELDS.md, the datasheet is
filled, and manifest.json matches the files."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
import export_dataset  # noqa: E402

pytestmark = pytest.mark.skipif(not export_dataset.DB.exists(), reason="no database")


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("export")
    assert export_dataset.main(["--out", str(d)]) == 0
    return d


def documented() -> dict[str, set[str]]:
    """{file: field names} from the first column of the first table under each file's heading in FIELDS.md (the tables of
    values after it are not fields)."""
    fields, current, in_table = {}, None, False
    for line in (ROOT / "docs" / "dataset" / "FIELDS.md").read_text().splitlines():
        m = re.match(r"## (\w+\.jsonl)", line)
        if m:
            current, in_table = fields.setdefault(m.group(1), set()), False
        elif current is not None and line.startswith("|"):
            in_table = True
            if line.startswith("| `"):
                current.update(re.findall(r"`(\w+)`", line.split("|")[1]))
        elif in_table:
            current = None
    return fields


def test_every_field_is_described(out):
    docs = documented()
    for name in ("documents.jsonl", "segments.jsonl", "decisions.jsonl", "amendments.jsonl"):
        keys = set()
        with (out / name).open(encoding="utf-8") as f:
            for line in f:
                keys |= json.loads(line).keys()
        assert keys <= docs[name], f"{name}: not in FIELDS.md: {sorted(keys - docs[name])}"
        assert docs[name] <= keys, f"{name}: described but not written: {sorted(docs[name] - keys)}"


def test_datasheet_and_manifest(out):
    sheet = (out / "DATASHEET.md").read_text()
    assert "$" not in sheet and "DOI not yet assigned" in sheet
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["rows"]["documents"] == sum(1 for _ in (out / "documents.jsonl").open())
    for rel, meta in manifest["files"].items():
        assert hashlib.sha256((out / rel).read_bytes()).hexdigest() == meta["sha256"], rel


def test_machine_translation_is_marked(out):
    translated = {d["symbol"] for d in map(json.loads, (out / "documents.jsonl").open()) if d["machine_translated"]}
    assert translated
    with (out / "segments.jsonl").open(encoding="utf-8") as f:
        cites = [s["citation"] for s in map(json.loads, f) if s["symbol"] in translated]
    assert cites and all("machine translation" in c for c in cites)
