"""Voyage embeddings of the database's segments, for the semantic-search benchmark (round 131).

Units: every segment of kind speech, chair, vote, procedural and paragraph, embedded as "symbol, speaker (delegation): text".
Vectors go to data/cache/vectors/<model>/ (gitignored) in parts of one request each, so a stopped run resumes where it was;
the token counts Voyage reports go to data/logs/voyage_usage.jsonl.

  VOYAGE_API_KEY=... python3 eval/semantic_embed.py --model voyage-3-large
  python3 eval/semantic_embed.py --model voyage-law-2 --dry     # count units and tokens only
"""
import argparse
import json
import os
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "travaux.sqlite3"
VEC = ROOT / "data" / "cache" / "vectors"
USAGE = ROOT / "data" / "logs" / "voyage_usage.jsonl"
KINDS = ("speech", "chair", "vote", "procedural", "paragraph")
ENDPOINT = "https://api.voyageai.com/v1/embeddings"
MAX_CHARS = 24000          # about 6k tokens; longer segments are cut (a handful of report paragraphs)
BATCH_TOKENS = 60000       # under the 120k per request, with room for Voyage's tokenizer counting more than chars / 4
BATCH_ITEMS = 128

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()


def units(db=DB) -> list[tuple[str, str]]:
    """(segment id, text to embed), in a fixed order (symbol, seq)."""
    con = sqlite3.connect(db)
    out = []
    for sid, symbol, speaker, deleg, text in con.execute(
            f"SELECT id, symbol, speaker, delegation, text FROM segments WHERE kind IN ({','.join('?' * len(KINDS))}) "
            "AND length(trim(text)) >= 20 ORDER BY symbol, seq", KINDS):
        who = f", {speaker}" + (f" ({deleg})" if deleg else "") if speaker else (f", {deleg}" if deleg else "")
        out.append((sid, f"{symbol}{who}: {' '.join(text.split())}"[:MAX_CHARS]))
    return out


def embed(texts: list[str], model: str, input_type: str) -> tuple[list[list[float]], int]:
    body = json.dumps({"input": texts, "model": model, "input_type": input_type, "truncation": True}).encode()
    for attempt in range(8):
        try:
            req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {os.environ['VOYAGE_API_KEY']}"})
            with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
                data = json.loads(r.read())
            vecs = [e["embedding"] for e in sorted(data["data"], key=lambda e: e["index"])]
            return vecs, data["usage"]["total_tokens"]
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="ignore")[:200]
            if e.code not in (429, 500, 502, 503, 504):
                raise SystemExit(f"Voyage HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(min(60, 2 ** attempt))
    raise SystemExit("Voyage: no answer after 8 tries")


def batches(items):
    cur, toks = [], 0
    for it in items:
        t = len(it[1]) // 4 + 1
        if cur and (toks + t > BATCH_TOKENS or len(cur) >= BATCH_ITEMS):
            yield cur
            cur, toks = [], 0
        cur.append(it)
        toks += t
    if cur:
        yield cur


def log_usage(model, task, tokens):
    USAGE.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE, "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "task": task, "tokens": tokens}) + "\n")


def load(model: str) -> tuple[list[str], np.ndarray]:
    """The ids and unit-normalised vectors of a finished run."""
    d = VEC / model
    ids = json.loads((d / "ids.json").read_text())
    m = np.load(d / "vectors.npy").astype(np.float32)
    return ids, m / np.linalg.norm(m, axis=1, keepdims=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    items = units()
    bs = list(batches(items))
    print(f"{len(items)} units, about {sum(len(t) for _, t in items) // 4:,} tokens, {len(bs)} requests")
    if a.dry:
        return
    out = VEC / a.model
    out.mkdir(parents=True, exist_ok=True)
    total = 0
    for i, b in enumerate(bs):
        part = out / f"part-{i:05d}.npy"
        if part.exists():
            continue
        vecs, tokens = embed([t for _, t in b], a.model, "document")
        np.save(part, np.asarray(vecs, dtype=np.float16))
        (out / f"part-{i:05d}.ids.json").write_text(json.dumps([sid for sid, _ in b]))
        log_usage(a.model, "document", tokens)
        total += tokens
        if i % 20 == 0:
            print(f"  {i + 1}/{len(bs)} requests, {total:,} tokens this run", flush=True)
    ids = [sid for i in range(len(bs)) for sid in json.loads((out / f"part-{i:05d}.ids.json").read_text())]
    assert ids == [sid for sid, _ in items], "the parts do not match the database: delete the model's folder and rerun"
    np.save(out / "vectors.npy", np.concatenate([np.load(out / f"part-{i:05d}.npy") for i in range(len(bs))]))
    (out / "ids.json").write_text(json.dumps(ids))
    print(f"done: {len(ids)} vectors in {out}; {total:,} tokens this run")


if __name__ == "__main__":
    sys.exit(main())
