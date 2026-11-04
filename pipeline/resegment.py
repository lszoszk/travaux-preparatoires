#!/usr/bin/env python3
"""Segment again, keeping every hand check and every cached answer attached to its passage.

Segment ids are "symbol-seq": a change to the segmenter (a heading it now reads, two speeches it
now splits) shifts the seq of every segment after it, and with it the ids that the hand checks
(data/gold), Jev's cached answers (data/cache/jev_*.json), the tagger's accepted proposals, the
hand corrections of references and proposers, and the Geneva maps refer to. This runs the
pipeline's segmentation again (pipeline/build_all.py --no-db), aligns each changed record's old
segments with its new ones word by word, and moves
every id-keyed file to the new ids:

- an old segment goes to the new segment that holds most of its words (split: the largest part;
  merged: the one they joined);
- an old segment none of whose words survive is reported and its entries are left out of the
  id-keyed files (never silently re-pointed).

The map of every changed id is kept in data/id_maps/<date-time>.json (with how it moved), and the
database is rebuilt at the end.

  python3 pipeline/resegment.py [--dry-run]     # --dry-run: segment and align, report, change nothing
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEG = ROOT / "data" / "segments"
MAPS = ROOT / "data" / "id_maps"
ENGINE = "vote"
WORD_RE = re.compile(r"\w+")


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text or "")]


def align(old: list[dict], new: list[dict]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """{old id: new id} for the segments of one record, {old id: how} (same, moved, split, merged, lost), and for a split
    segment the new segment that holds its first words ({old id: new id}): a speech's opening, its speaker and turn."""
    ow, oseg, nw, nseg = [], [], [], []
    for k, s in enumerate(old):
        w = words(s["text"])
        ow += w
        oseg += [k] * len(w)
    for k, s in enumerate(new):
        w = words(s["text"])
        nw += w
        nseg += [k] * len(w)
    votes: dict[int, Counter] = defaultdict(Counter)
    first: dict[int, tuple[int, int]] = {}  # old segment -> (its first matched word, the new segment holding it)
    for a, b, size in difflib.SequenceMatcher(None, ow, nw, autojunk=False).get_matching_blocks():
        for i in range(size):
            votes[oseg[a + i]][nseg[b + i]] += 1
            if oseg[a + i] not in first or a + i < first[oseg[a + i]][0]:
                first[oseg[a + i]] = (a + i, nseg[b + i])
    mapping, how = {}, {}
    targets = Counter()
    for k, s in enumerate(old):
        if not votes.get(k):
            # no words (an empty or furniture segment): the new segment at the same place, if its text is the same
            same = [n for n in new if n["text"] == s["text"]]
            if same:
                mapping[s["id"]] = same[0]["id"]
                how[s["id"]] = "same" if same[0]["id"] == s["id"] else "moved"
            else:
                how[s["id"]] = "lost"
            continue
        best, n_best = votes[k].most_common(1)[0]
        mapping[s["id"]] = new[best]["id"]
        targets[best] += 1
        total = sum(votes[k].values())
        how[s["id"]] = "split" if len(votes[k]) > 1 and n_best < 0.9 * total else \
            "same" if new[best]["id"] == s["id"] and new[best]["text"] == s["text"] else "moved"
    for old_id, new_id in mapping.items():
        k = next(i for i, n in enumerate(new) if n["id"] == new_id)
        if targets[k] > 1 and how[old_id] in ("same", "moved"):
            how[old_id] = "merged"
    opening = {s["id"]: new[first[k][1]]["id"] for k, s in enumerate(old) if how.get(s["id"]) == "split" and k in first}
    return mapping, how, opening


# tables that judge a speech: for a split segment, its speaker and the rejections of its tag follow the part that keeps its
# opening, not the part with most of its words, which can be another speaker's turn the new text found inside it; the
# tables that give it an article go to both parts, each part's tag then checked by Jev on its own text (22 Oct 2026)
SPEECH_TABLES = {"tag_rejections.csv", "topic_rejections.csv", "topic_accepted.csv", "speaker_fixes.csv", "speaker_kept.csv", "speakers_audit.jsonl"}
ARTICLE_TABLES = {"reader_tags.csv", "speech_retags.csv", "accepted.csv", "possible_articles.csv", "schabas_candidates.csv"}


def migrate(idmap: dict[str, str], lost: set[str], dry: bool, opening: dict[str, str] | None = None) -> Counter:
    """Move every id-keyed file to the new ids; entries of lost segments are dropped (and counted). The speech-level tables
    follow a split segment's opening (opening: {old id: new id}); Jev's answers about a split segment are dropped, so that
    each part is asked about its own text."""
    done = Counter()
    opening = opening or {}

    def new_id(i: str, table: str = "") -> str | None:
        if i in lost:
            return None
        return opening[i] if table in SPEECH_TABLES and i in opening else idmap.get(i, i)

    for name in ("article_tags.jsonl", "coverage.jsonl", "tagger_eval.jsonl", "speakers_audit.jsonl"):
        path = ROOT / "data" / "gold" / name
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        out = []
        for r in rows:
            n = new_id(r["id"], name)
            if n is None:
                done[f"{name}: dropped"] += 1
                continue
            done[f"{name}: moved"] += n != r["id"]
            out.append({**r, "id": n})
        if not dry:
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    for path in sorted((ROOT / "data" / "cache").glob("jev_*.json")):
        cache = json.loads(path.read_text())
        out = {}
        for key, val in cache.items():
            sid, sep, rest = key.partition("|")
            if sid in opening:
                done[f"{path.name}: dropped (split: asked again)"] += 1
                continue
            n = new_id(sid)
            if n is None:
                done[f"{path.name}: dropped"] += 1
                continue
            done[f"{path.name}: moved"] += n != sid
            out[n + sep + rest] = val
        if not dry:
            path.write_text(json.dumps(out))
    for path, col in ((ROOT / "data" / "tagger" / "accepted.csv", "segment_id"),
                      (ROOT / "data" / "tagger" / "predictions.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "amendment_sponsors.csv", "segment"),
                      (ROOT / "data" / "concordance" / "ref_fixes.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "decision_proposers_checked.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "reader_tags.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "speech_retags.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "tag_rejections.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "topic_rejections.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "topic_accepted.csv", "segment_id"),
                      (ROOT / "data" / "gazetteer" / "speaker_fixes.csv", "segment_id"),
                      (ROOT / "data" / "gazetteer" / "speaker_kept.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "possible_articles.csv", "segment_id"),
                      (ROOT / "data" / "concordance" / "schabas_candidates.csv", "segment_id")):
        if not path.exists():
            continue
        rows = list(csv.DictReader(path.open()))
        fields = list(rows[0].keys()) if rows else []
        out = []
        for r in rows:
            if r[col]:
                old_id = r[col]
                n = new_id(old_id, path.name)
                if n is None:
                    done[f"{path.name}: dropped"] += 1
                    continue
                done[f"{path.name}: moved"] += n != old_id
                r[col] = n
                if path.name in ARTICLE_TABLES and old_id in opening and opening[old_id] != n:
                    out.append({**r, col: opening[old_id]})
                    done[f"{path.name}: copied to the opening"] += 1
            out.append(r)
        if not dry and rows:
            with path.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                w.writeheader()
                w.writerows(out)
    # the Geneva maps give spans by seq: each end moves with its segment
    path = ROOT / "data" / "gold" / "geneva_plenary_maps.json"
    maps = json.loads(path.read_text())
    for m in maps["maps"]:
        prefix = m["symbol"].lower().replace("/", "_")
        for sp in m["spans"]:
            for key in ("from_seq", "to_seq", "evidence_seq"):
                if sp.get(key) is None:
                    continue
                old = f"{prefix}-{int(sp[key]):04d}"
                n = new_id(old)
                if n and n != old:
                    sp[key] = int(n.rsplit("-", 1)[1])
                    done["geneva_plenary_maps.json: moved"] += 1
    if not dry:
        path.write_text(json.dumps(maps, ensure_ascii=False, indent=1) + "\n")
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    before = Path(tempfile.mkdtemp(prefix="segments-before-"))
    shutil.copytree(SEG, before, dirs_exist_ok=True)
    manifests = sorted(str(p) for p in (ROOT / "data" / "manifest").glob("harvest_*.json"))
    subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_all.py"), *manifests, "--no-db"], check=True)
    idmap, hows, changed, opening = {}, {}, [], {}
    for p in sorted(before.glob(f"*.{ENGINE}.json")):
        q = SEG / p.name
        if not q.exists():
            continue
        old, new = json.loads(p.read_text()), json.loads(q.read_text())
        if [s["id"] for s in old] == [s["id"] for s in new] and [s["text"] for s in old] == [s["text"] for s in new]:
            continue
        changed.append(p.name.split(f".{ENGINE}.json")[0])
        m, h, o = align(old, new)
        idmap.update(m)
        hows.update(h)
        opening.update(o)
    lost = {i for i, h in hows.items() if h == "lost"}
    moved = {i: n for i, n in idmap.items() if n != i}
    print(f"records changed: {len(changed)}; segments: {Counter(hows.values())}", file=sys.stderr)
    done = migrate(moved, lost, args.dry_run, opening)
    for k, v in sorted(done.items()):
        print(f"  {k}: {v}", file=sys.stderr)
    if args.dry_run:
        shutil.rmtree(SEG)
        shutil.copytree(before, SEG)  # put the old segments back
        print("dry run: segments restored, nothing migrated", file=sys.stderr)
        return 0
    MAPS.mkdir(parents=True, exist_ok=True)
    out = MAPS / f"{dt.datetime.now().strftime('%Y-%m-%d-%H%M')}.json"  # one map per run
    out.write_text(json.dumps({"records": changed, "moved": moved, "how": {i: hows[i] for i in moved.keys() | lost},
                               "lost": sorted(lost), "opening": opening}, indent=1) + "\n")
    print(f"id map -> {out.relative_to(ROOT)}", file=sys.stderr)
    subprocess.run([sys.executable, str(ROOT / "api" / "build_db.py"), "--engine", ENGINE], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
