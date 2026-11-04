# A third OCR witness for the name guard: PP-OCR, docTR, PERO (20 Oct 2026)

Preregistered in docs/devlog.md (20 Oct) before any page was read. Pages: dev set 1 (20 pages with the retyped reference) and
the 40 gold pages (1946-66). Readers: eval/ocr_witness_read.py (each engine with its defaults, in its own environment);
names: eval/ocr_witness_names.py (witness_names.json); CER: eval/vlm_local_dev_cer.py (witness_cer_dev1.json).
Versions: paddleocr 3.7.0 / paddlepaddle 3.3.1 (its default English recognizer is now PP-OCRv6_medium_rec, not v5);
python-doctr 1.1.0 (db_resnet50 + crnn_vgg16_bn); pero-ocr 0.7.0 with pero_eu_cz_print_newspapers_2022-09-26 (CPU config).
Deviation: tess4 read only 5 of the 60 pages, so "Tesseract" is tess3 and tess6.

## Names at turn openings (60 pages, 133 true names; 30 read exact by no Tesseract engine)

| engine | exact | garbled | missed | plausible wrong | independence |
|---|---:|---:|---:|---:|---:|
| tess3 (best Tesseract) | 102 | 19 | 12 | 0 | - |
| tess6 | 71 | 16 | 46 | 0 | - |
| Apple Vision | 104 | 13 | 16 | 0 | 40% |
| text layer | 91 | 9 | 33 | 0 | 27% |
| OCR vote | 108 | 13 | 12 | 0 | 20% |
| Chandra (vision reader) | 129 | 4 | 0 | 0 | 93% |
| docTR (CRNN) | 110 | 4 | 19 | 0 | 57% |
| **PERO** | **116** | 6 | 11 | 0 | **57%** |
| PP-OCR (v6 recognizer) | 103 | 8 | 22 | 0 | 40% |

## CER on dev set 1

| group | vote | tess3 | Vision | Chandra | docTR | PERO | PP-OCR |
|---|---:|---:|---:|---:|---:|---:|---:|
| typed summary records (13 pp) | 2.51% | 3.96% | 6.90% | 0.41% | 3.91% | **1.82%** | 3.57% |
| typed documents (4 pp) | 2.11% | 0.88% | 23.9% | 0.70% | 3.07% | 0.35% | 2.81% |
| printed EN/FR (3 pp) | 2.74% | 1.83% | 3.90% | 0.93% | 44.3% | 1.21% | 32.9% |
| all (20 pp) | 2.56% | 3.27% | 6.75% | 0.56% | 14.7% | 1.60% | 11.4% |

(docTR's and PP-OCR's printed pages are read across the two columns: our reading order did not split those pages.)

## Speed on the M3 (CPU), seconds a page

docTR median 8.1 (mean 10.7); PERO median 10.7 (mean 11.4); PP-OCR median 65.5 (mean 75.7). PERO's GPU models are traced
for CUDA and do not run on the Mac's GPU (MPS: aten::cudnn_convolution_relu not implemented; the CPU-traced models fail the same way).

## The gate

| | CER typed records <= 2.0% | exact names >= 102 | independence >= 25% | plausible wrong <= 1 | <= 10 s a page |
|---|---|---|---|---|---|
| docTR | no (3.91%) | yes (110) | yes (57%) | yes (0) | yes (8.1) |
| PERO | yes (1.82%) | yes (116) | yes (57%) | yes (0) | **no (10.7)** |
| PP-OCR | no (3.57%) | yes (103) | yes (40%) | yes (0) | no (65.5) |

No engine passes all five: as preregistered, nothing changes. PERO fails only on speed, by 7% at the median (18,510 pages
would take ~59 h of laptop CPU instead of ~51 h); on quality it is the best non-generative engine we have, better than the OCR
vote on the typed records (1.82% against 2.51%) and on names (116 against 108). Any use of it now is a new decision, not this
gate's outcome.
