# The GPU build against the laptop's: development set 1 (18 Oct 2026)

Before readings from Kaggle (the original `datalab-to/chandra-ocr-2`, fp16, vLLM 0.31.0, two T4s, eager mode) replace or join
the laptop's (MLX 5-bit `1qh/chandra-ocr-2-oq5-mlx`), both builds read the 20 pages of development set 1 with the same prompt and
the same text conversion (`eval/vlm_local_bench.py` PROMPT, `to_text`). Kaggle notebook `pipeline/hpc/kaggle_chandra_devset.ipynb`
(4 pages in flight, 20 pages in 0.23 h, no timeout, no runaway); GPU readings in `data/ocr/<doc>/chandra-gpu/`, run log
`data/logs/kaggle_chandra_devset1_run.jsonl`.

**Word agreement** (`eval/vlm_gpu_vs_mlx.py`, `gpu_vs_mlx_dev1.json`): 7,231 of 7,233 words the same and in the same order
(99.97%); 18 of 20 pages identical word for word; the two differences are one letter each, both in garbled or abbreviated tokens:
E/CN.4/AC.2/SR.7 p2 `f.` (MLX) / `e.` (GPU); E/CN.4/SR.61 p2 `(ihtu)` / `(ifctu)`.

**CER against the retyped reference** (`eval/vlm_local_dev_cer.py`, `dev_cer_gpu.json`, method of `eval/ocr_bench.py`):

| Group | Pages | Chars | vote | MLX 5-bit | GPU fp16 |
|---|---:|---:|---:|---:|---:|
| 1947-48 typed documents/reports | 4 | 1,139 | 2.11% | 0.70% | 0.70% |
| 1947-48 typed summary records | 13 | 20,577 | 2.51% | 0.41% | 0.41% |
| 1948 printed (GAOR, EN/FR columns) | 3 | 7,930 | 2.74% | 0.93% | 0.93% |
| All | 20 | 29,646 | 2.56% | 0.56% | 0.56% |

The only page-level difference in CER is E/CN.4/AC.2/SR.7 (0.85% MLX, 0.87% GPU: the `f.`/`e.` token). Decision: the two builds
are treated as one reader; the Kaggle readings go into `data/ocr/<doc>/chandra/` with the laptop's, and every result measured
with the laptop build (development sets, blocks B and C) holds for them. Limits: 20 pages, 1947-48 only; batch size differed
(4 in flight here, 16 in the corpus run), which in vLLM can change a token at most where two continuations are near-tied.
