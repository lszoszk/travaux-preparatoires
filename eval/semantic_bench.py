"""Round 131: lexical search against Voyage semantic search on the meeting records two commentaries cite.

Queries: eval/private/semantic/queries.jsonl (eval/semantic_queries via the round's workflow: one per commentary note, kept
private with the notes in eval/private/semantic/*_raw.jsonl). Vectors: eval/semantic_embed.py. Systems and scores as the
devlog's preregistration of round 131 says. Query vectors and rerank answers are cached in eval/private/semantic/ (they are
keyed by the private queries); the scores, which hold no text, go to eval/round131/results.json.

  python3 eval/semantic_bench.py                      # every system whose vectors exist
"""
import json
import os
import random
import re
import sqlite3
import sys
from math import comb
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
import semantic_embed as se  # noqa: E402
from semantic_extract import cites  # noqa: E402
from server import fts_query  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRIV = ROOT / "eval" / "private" / "semantic"
OUT = ROOT / "eval" / "round131" / "results.json"
QUERIES = "queries.jsonl"
DENSE = ("voyage-3-large",)  # voyage-law-2 left out before any result (devlog, round 131 amended)
RERANK = "rerank-2.5"
K, DEPTH, RRF_K = 10, 100, 60
STOP = set("""a an the of in on at to for from by with and or not no is are was were be been being as that this these those
it its which who whom whose what when where why how than then there their they them he she his her we our you your i
into over under about between during after before against would could should may might can will shall do does did
had has have also only such any all each other more most some same very upon whether if but so""".split())


def load_queries():
    raw = {}
    for line in open(PRIV / "nowak_raw.jsonl"):
        pg = json.loads(line)
        for n in pg["notes"]:
            raw[f"nowak:{pg['page']}:{n['note']}"] = n["cites"]
    for line in open(PRIV / "saul_raw.jsonl"):
        it = json.loads(line)
        raw[f"saul:{it['page']}:{it['note']}"] = it["cites"]
    qs = [json.loads(l) for l in open(PRIV / QUERIES)]
    for q in qs:
        q["cites"] = raw[q["id"]]
        q["set"] = q["id"].split(":")[0]
    return qs


def relevance(con, q, held):
    """The cited records we hold, and the segments of those records that hold a cited pinpoint (None: no usable pinpoint)."""
    recs = {c["symbol"] for c in q["cites"] if c["symbol"] in held}
    pins, usable = set(), False
    for c in q["cites"]:
        p = c["pin"]
        if c["symbol"] not in held or not p:
            continue
        if p["type"] == "para":
            usable = True
            for sid, n, n_end in con.execute("SELECT id, n, n_end FROM segments WHERE symbol = ?", (c["symbol"],)):
                a = int(re.match(r"\d*", n or "").group(0) or 0)
                b = int(re.match(r"\d*", n_end or "").group(0) or 0) or a
                if a and a <= p["to"] and b >= p["from"]:
                    pins.add(sid)
        elif c["symbol"].startswith("E/CN.4/"):  # a typed record: its pages are the scan's, give or take one
            usable = True
            for (sid,) in con.execute("SELECT id FROM segments WHERE symbol = ? AND page_start <= ? AND page_end >= ?",
                                      (c["symbol"], p["to"] + 1, p["from"] - 1)):
                pins.add(sid)
    return recs, (pins if usable else None)


def site(con, q):
    try:
        return [r[0] for r in con.execute(
            "SELECT s.id FROM segments_fts f JOIN segments s ON s.id = f.id WHERE segments_fts MATCH ? "
            "AND s.kind IN ('speech', 'chair', 'vote') ORDER BY bm25(segments_fts, 1.0, 4.0, 2.0) LIMIT ?",
            (fts_query(q), DEPTH))]
    except sqlite3.OperationalError:
        return []


def bm25_or(con, q, pool):
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", q) if w.lower() not in STOP]
    if not words:
        return []
    match = " OR ".join(f'"{w}"' for w in dict.fromkeys(words))
    return [r[0] for r in con.execute(
        f"SELECT s.id FROM segments_fts f JOIN segments s ON s.id = f.id WHERE segments_fts MATCH ? "
        f"AND s.kind IN ({','.join('?' * len(se.KINDS))}) ORDER BY bm25(segments_fts, 1.0, 4.0, 2.0) LIMIT ?",
        (match, *se.KINDS, 2 * DEPTH)) if r[0] in pool][:DEPTH]


def rrf(*lists):
    score = {}
    for lst in lists:
        for r, sid in enumerate(lst):
            score[sid] = score.get(sid, 0) + 1 / (RRF_K + r + 1)
    return sorted(score, key=lambda s: -score[s])[:DEPTH]


def cached(name):
    p = PRIV / f"cache_{name}.json"
    return p, (json.loads(p.read_text()) if p.exists() else {})


def query_vectors(model, texts):
    p, c = cached(model)
    todo = [t for t in dict.fromkeys(texts) if t not in c]
    for i in range(0, len(todo), 128):
        vecs, tokens = se.embed(todo[i:i + 128], model, "query")
        se.log_usage(model, "query", tokens)
        c.update(zip(todo[i:i + 128], vecs))
        p.write_text(json.dumps(c))
    m = np.asarray([c[t] for t in texts], dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def rerank(q, ids, text_of):
    import time
    import urllib.error
    import urllib.request
    p, c = cached(RERANK)
    key = q + "\x00" + "|".join(ids)
    if key not in c:
        body = json.dumps({"query": q, "documents": [text_of[s] for s in ids], "model": RERANK, "truncation": True}).encode()
        req = urllib.request.Request("https://api.voyageai.com/v1/rerank", data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {os.environ['VOYAGE_API_KEY']}"})
        for attempt in range(8):
            try:
                with urllib.request.urlopen(req, timeout=120, context=se.CTX) as r:
                    data = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 7:
                    raise
                time.sleep(min(60, 2 ** attempt * 2))  # the rerank limit is tokens per minute
        se.log_usage(RERANK, "rerank", data["usage"]["total_tokens"])
        c[key] = [ids[d["index"]] for d in sorted(data["data"], key=lambda d: -d["relevance_score"])]
        p.write_text(json.dumps(c))
    return c[key]


def scores(ranked, rel, sym_of):
    recs, pins = rel
    top = ranked[:K]
    first = next((i for i, s in enumerate(top) if sym_of.get(s) in recs), None)
    return {"hit10": int(first is not None), "hit1": int(first == 0), "mrr10": 1 / (first + 1) if first is not None else 0.0,
            "pin10": None if pins is None else int(any(s in pins for s in top))}


def paired(a, b, seed=131, n=10000):
    """Mean difference b - a, its bootstrap 95% interval, and the exact McNemar p on the discordant pairs."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), (n, len(a)))
    d = (b[idx] - a[idx]).mean(axis=1)
    up, down = int(((b == 1) & (a == 0)).sum()), int(((a == 1) & (b == 0)).sum())
    m = up + down
    p = min(1.0, 2 * sum(comb(m, k) for k in range(min(up, down) + 1)) / 2 ** m) if m else 1.0
    return {"diff": round(float((b - a).mean()), 4), "ci95": [round(float(np.percentile(d, 2.5)), 4),
            round(float(np.percentile(d, 97.5)), 4)], "b_only": up, "a_only": down, "mcnemar_p": round(p, 4)}


def main():
    global OUT, QUERIES
    if "--round" in sys.argv:  # round 132: the short queries, eval/private/semantic/queries_short.jsonl
        r = sys.argv[sys.argv.index("--round") + 1]
        OUT, QUERIES = ROOT / "eval" / f"round{r}" / "results.json", f"queries_{sys.argv[sys.argv.index('--queries') + 1]}.jsonl"
    con = sqlite3.connect(se.DB)
    held = {r[0].upper() for r in con.execute("SELECT DISTINCT symbol FROM segments")}
    sym_of = dict(con.execute("SELECT id, symbol FROM segments"))
    qs = [q for q in load_queries() if not q["drop"] and q["query"].strip()]
    rels = {q["id"]: relevance(con, q, held) for q in qs}
    qs = [q for q in qs if rels[q["id"]][0]]
    texts = [q["query"] for q in qs]
    text_of = dict(se.units())  # the units the dense systems see (under 20 characters left out): BM25 gets the same pool
    runs = {"site": [site(con, t) for t in texts], "bm25_or": [bm25_or(con, t, text_of) for t in texts]}
    # the site's search falling back to BM25-OR when every word cannot be found together (round 132)
    runs["site_or_fallback"] = [a or b for a, b in zip(runs["site"], runs["bm25_or"])]
    for model in DENSE:
        if not (se.VEC / model / "vectors.npy").exists():
            print(f"{model}: no vectors yet, left out")
            continue
        ids, m = se.load(model)
        qv = query_vectors(model, texts)
        sims = qv @ m.T
        top = np.argsort(-sims, axis=1)[:, :DEPTH]
        runs[model] = [[ids[j] for j in row] for row in top]
        runs[f"rrf_{model}"] = [rrf(a, b) for a, b in zip(runs["bm25_or"], runs[model])]
    if "rrf_voyage-3-large" in runs:
        runs[f"rrf_voyage-3-large+{RERANK}"] = [rerank(t, r, text_of) for t, r in zip(texts, runs["rrf_voyage-3-large"])]
    per = {name: [scores(r, rels[q["id"]], sym_of) for r, q in zip(rs, qs)] for name, rs in runs.items()}
    res = {"queries": {s: sum(q["set"] == s for q in qs) for s in ("nowak", "saul")},
           "with_pinpoint": {s: sum(q["set"] == s and rels[q["id"]][1] is not None for q in qs) for s in ("nowak", "saul")},
           "dropped_by_model": sum(1 for q in load_queries() if q["drop"]), "systems": {}, "vs_bm25_or": {}, "vs_site": {}, "vs_site_or_fallback": {}}
    for name, sc in per.items():
        res["systems"][name] = {}
        for s in ("nowak", "saul", "pooled"):
            sub = [x for x, q in zip(sc, qs) if s == "pooled" or q["set"] == s]
            pin = [x["pin10"] for x in sub if x["pin10"] is not None]
            res["systems"][name][s] = {m: round(sum(x[m] for x in sub) / len(sub), 4) for m in ("hit10", "hit1", "mrr10")}
            res["systems"][name][s]["pin10"] = round(sum(pin) / len(pin), 4) if pin else None
        for base in ("bm25_or", "site", "site_or_fallback"):
            if name != base:
                res[f"vs_{base}"][name] = {s: paired([x["hit10"] for x, q in zip(per[base], qs) if s == "pooled" or q["set"] == s],
                                                     [x["hit10"] for x, q in zip(sc, qs) if s == "pooled" or q["set"] == s])
                                           for s in ("nowak", "saul", "pooled")}
    kinds = sorted({q["kind"] for q in qs})
    res["by_kind_hit10"] = {k: {name: round(np.mean([x["hit10"] for x, q in zip(sc, qs) if q["kind"] == k]), 4)
                                for name, sc in per.items()} | {"n": sum(q["kind"] == k for q in qs)} for k in kinds}
    res["site_empty"] = sum(1 for r in runs["site"] if not r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print(f"{len(qs)} queries ({res['queries']}); the site's search found nothing for {res['site_empty']}")
    print(f"{'system':38} " + "  ".join(f"{s:>22}" for s in ("nowak hit10/pin10", "saul hit10/pin10", "pooled hit10 mrr")))
    for name, v in res["systems"].items():
        f = lambda d, m2: f"{d['hit10']:.3f}/{d[m2]:.3f}" if d[m2] is not None else f"{d['hit10']:.3f}/-"
        print(f"{name:38} {f(v['nowak'], 'pin10'):>22}  {f(v['saul'], 'pin10'):>22}  {f(v['pooled'], 'mrr10'):>22}")
    for name, v in res["vs_bm25_or"].items():
        print(f"vs bm25_or {name:30} pooled {v['pooled']}")


if __name__ == "__main__":
    sys.exit(main())
