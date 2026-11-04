# Documents to fetch by hand

Generated 2026-09-29 by `pipeline/missing_documents.py`. **65 documents** that documents.un.org does not serve as a PDF (8 meeting records). The same list is in `missing_documents.csv`.

## How

1. Open the Digital Library link, open the record and download the **English** PDF.
2. Save it under the name in the *Save as* column (the symbol with `/` replaced by `_`, then `-EN.pdf`).
3. When you have a batch, run `python3 pipeline/missing_documents.py --add`, then `python3 pipeline/ocr_all.py data/manifest/harvest_<corpus>.json` and `python3 pipeline/build_all.py data/manifest/harvest_*.json`.

The harvest will not fetch these itself: the Digital Library sits behind a bot check, which it does not get round.
Documents marked *alternate queued* are being fetched under their Commission symbol instead; skip them unless that fails.

10 more exist only in French and are left out (`data/raw/*-FR.pdf`, machine-translated, see pipeline/translations.py): A/C.3/251/Corr.1, A/C.3/278/Corr.1, A/C.3/308/Corr.1, A/C.3/309/Rev.1, A/C.3/319/Rev.1, E/CN.4/1/Rev.1/Corr.1, E/CN.4/122/Rev.1, E/CN.4/53/Corr.1, E/CN.4/97/Corr.1, E/CN.4/SR.25/Corr.1.

| Symbol | What | Body / session | In Schabas | Save as | Link |
|---|---|---|---|---|---|
| E/AC.7/SR.33 | summary_record | ECOSOC Social Committee | yes | `E_AC.7_SR.33-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FAC.7%2FSR.33&ln=en) |
| E/CONF.6/C.4/SR.10 | summary_record | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_SR.10-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2FSR.10&ln=en) |
| E/CONF.6/C.4/SR.24 | summary_record | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_SR.24-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2FSR.24&ln=en) |
| E/CONF.6/C.4/SR.4 | summary_record | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_SR.4-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2FSR.4&ln=en) |
| E/CONF.6/C.4/SR.5 | summary_record | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_SR.5-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2FSR.5&ln=en) |
| E/CONF.6/C.4/SR.6 | summary_record | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_SR.6-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2FSR.6&ln=en) |
| E/SR.29 | summary_record | Economic and Social Council | yes | `E_SR.29-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FSR.29&ln=en) |
| E/CN.4/SR.244 | summary_record | Commission on Human Rights |  | `E_CN.4_SR.244-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCN.4%2FSR.244&ln=en) |
| A/C.1/38 | document | General Assembly First Committee | yes | `A_C.1_38-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.1%2F38&ln=en) |
| A/C.3/126 | document | General Assembly Third Committee | yes | `A_C.3_126-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F126&ln=en) |
| A/C.3/135 | document | General Assembly Third Committee | yes | `A_C.3_135-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F135&ln=en) |
| A/C.3/166 | document | General Assembly Third Committee | yes | `A_C.3_166-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F166&ln=en) |
| A/C.3/167 | document | General Assembly Third Committee | yes | `A_C.3_167-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F167&ln=en) |
| A/C.3/170 | document | General Assembly Third Committee | yes | `A_C.3_170-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F170&ln=en) |
| A/C.3/171 | document | General Assembly Third Committee | yes | `A_C.3_171-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F171&ln=en) |
| A/C.3/172 | document | General Assembly Third Committee | yes | `A_C.3_172-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F172&ln=en) |
| A/C.3/175 | document | General Assembly Third Committee | yes | `A_C.3_175-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F175&ln=en) |
| A/C.3/176 | document | General Assembly Third Committee | yes | `A_C.3_176-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F176&ln=en) |
| A/C.3/177 | document | General Assembly Third Committee | yes | `A_C.3_177-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F177&ln=en) |
| A/C.3/181 | document | General Assembly Third Committee | yes | `A_C.3_181-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F181&ln=en) |
| A/C.3/183 | document | General Assembly Third Committee | yes | `A_C.3_183-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F183&ln=en) |
| A/C.3/184 | document | General Assembly Third Committee | yes | `A_C.3_184-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F184&ln=en) |
| A/C.3/184/Rev.1 | document | General Assembly Third Committee | yes | `A_C.3_184_Rev.1-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F184%2FRev.1&ln=en) |
| A/C.3/186 | document | General Assembly Third Committee | yes | `A_C.3_186-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F186&ln=en) |
| A/C.3/187 | document | General Assembly Third Committee | yes | `A_C.3_187-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F187&ln=en) |
| A/C.3/W.13 | working_paper | General Assembly Third Committee | yes | `A_C.3_W.13-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2FW.13&ln=en) |
| A/C.3/W.2 | working_paper | General Assembly Third Committee | yes | `A_C.3_W.2-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2FW.2&ln=en) |
| A/CN.4/W.18 | working_paper | General Assembly | yes | `A_CN.4_W.18-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FCN.4%2FW.18&ln=en) |
| E/1009 | document | Economic and Social Council | yes | `E_1009-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F1009&ln=en) |
| E/248 | document | Economic and Social Council | yes | `E_248-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F248&ln=en) |
| E/353 | document | Economic and Social Council | yes | `E_353-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F353&ln=en) |
| E/386 | document | Economic and Social Council | yes | `E_386-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F386&ln=en) |
| E/386/Add.1 | document | Economic and Social Council | yes | `E_386_Add.1-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F386%2FAdd.1&ln=en) |
| E/422 | document | Economic and Social Council | yes | `E_422-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F422&ln=en) |
| E/439 | document | Economic and Social Council | yes | `E_439-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F439&ln=en) |
| E/533 | document | Economic and Social Council | yes | `E_533-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F533&ln=en) |
| E/7 | document | Economic and Social Council | yes | `E_7-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F7&ln=en) |
| E/704 | document | Economic and Social Council | yes | `E_704-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F704&ln=en) |
| E/737 | document | Economic and Social Council | yes | `E_737-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F737&ln=en) |
| E/738 | document | Economic and Social Council | yes | `E_738-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F738&ln=en) |
| E/965 | document | Economic and Social Council | yes | `E_965-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F965&ln=en) |
| E/AC.7/13 | document | ECOSOC Social Committee | yes | `E_AC.7_13-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FAC.7%2F13&ln=en) |
| E/AC.7/18 | document | ECOSOC Social Committee | yes | `E_AC.7_18-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FAC.7%2F18&ln=en) |
| E/AC.7/19 | document | ECOSOC Social Committee | yes | `E_AC.7_19-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FAC.7%2F19&ln=en) |
| E/AC.7/20 | document | ECOSOC Social Committee | yes | `E_AC.7_20-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FAC.7%2F20&ln=en) |
| E/AC.7/8 | document | ECOSOC Social Committee | yes | `E_AC.7_8-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FAC.7%2F8&ln=en) |
| E/CONF.6/17 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_17-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2F17&ln=en) |
| E/CONF.6/65 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_65-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2F65&ln=en) |
| E/CONF.6/69 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_69-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2F69&ln=en) |
| E/CONF.6/74 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_74-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2F74&ln=en) |
| E/CONF.6/C.4/1 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_1-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2F1&ln=en) |
| E/CONF.6/C.4/1/Rev.1 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_1_Rev.1-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2F1%2FRev.1&ln=en) |
| E/CONF.6/C.4/10 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_10-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2F10&ln=en) |
| E/CONF.6/C.4/3 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_3-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2F3&ln=en) |
| E/CONF.6/C.4/71 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_71-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2F71&ln=en) |
| E/CONF.6/C.4/8 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_8-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2F8&ln=en) |
| E/CONF.6/C.4/9 | document | UN Conference on Freedom of Information (1948) | yes | `E_CONF.6_C.4_9-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FCONF.6%2FC.4%2F9&ln=en) |
| E/1371 | CHR 5th session report (1949) (alternate queued: E/CN.4/350) | Economic and Social Council |  | `E_1371-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F1371&ln=en) |
| E/2256 | CHR 8th session report (1952) (alternate queued: E/CN.4/669) | Economic and Social Council |  | `E_2256-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F2256&ln=en) |
| E/2447 | CHR 9th session report (1953) (alternate queued: E/CN.4/689) | Economic and Social Council |  | `E_2447-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F2447&ln=en) |
| E/2573 | CHR 10th session report (1954); the draft Covenants sent to the GA (alternate queued: E/CN.4/705) | Economic and Social Council |  | `E_2573-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2F2573&ln=en) |
| A/C.3/299/Rev.1/Corr.1 | document | General Assembly Third Committee / 3rd session (1948) |  | `A_C.3_299_Rev.1_Corr.1-EN.pdf` | [search](https://digitallibrary.un.org/search?p=A%2FC.3%2F299%2FRev.1%2FCorr.1&ln=en) |
| E/RES/116(VI)F | resolution | CHR Drafting Committee / 2nd session (1948) |  | `E_RES_116_VI_F-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FRES%2F116%28VI%29F&ln=en) |
| E/RES/118(VI)B | resolution | Economic and Social Council |  | `E_RES_118_VI_B-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FRES%2F118%28VI%29B&ln=en) |
| E/RES/120(VI)C | resolution | Economic and Social Council |  | `E_RES_120_VI_C-EN.pdf` | [search](https://digitallibrary.un.org/search?p=E%2FRES%2F120%28VI%29C&ln=en) |
