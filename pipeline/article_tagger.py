#!/usr/bin/env python3
"""Propose article tags offline; never write to the source database.

Run: python3 pipeline/article_tagger.py --db /absolute/path/to/travaux.sqlite3
The frozen confidence models use dev judgments only, with records held out by hash.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path('/Users/lszoszk/Desktop/AI/travaux/data/travaux.sqlite3')
FIELDS = ['segment_id', 'instrument', 'final_article', 'score', 'evidence']
# Ordered features: lexical support, margin, vote share, draft similarity,
# same-record support, flanking agreement, amendment agreement, length,
# procedural language, multiple numbered articles, cross-record support,
# semantic adopted-article support and semantic margin.
# Dev-only, record-held-out logistic models; standardization folded into coefficients.
MODELS = [{'intercept': -7.869896053496892,
  'coef': [2.713743218461533,
           -2.20178545090741,
           4.093051727605152,
           0.9097452164251731,
           -9.783892178288655,
           4.03048670974833,
           0.8190270669103832,
           -1.4412451096112981,
           -1.162360668520607,
           1.195694308867762,
           4.617950349692783,
           5.074942964532965,
           18.61880106345004]},
 {'intercept': -11.382568106264388,
  'coef': [8.349550493551506,
           -5.072633491485391,
           3.5885707056394542,
           1.8729705248373418,
           -10.262283846260631,
           4.197298796115608,
           0.4858534719697222,
           -0.9035483452403121,
           -1.787646197570528,
           0.9175286317791448,
           0.6377925929872893,
           10.405274594234081,
           12.17795796964324]},
 {'intercept': -9.30295695456531,
  'coef': [1.7539432654560847,
           -6.67011041617334,
           2.0914981875917116,
           6.296689089247154,
           -11.076907441490475,
           4.830907628182763,
           1.8183222806231405,
           -0.38602172090020326,
           -2.0877373447198235,
           0.5759313760960763,
           9.09779219354971,
           7.331661036275621,
           17.6400562698948]},
 {'intercept': -10.916433395769175,
  'coef': [-1.4899031382651433,
           2.5268338446779586,
           2.86522490354433,
           3.0184657386365377,
           -5.979105521955246,
           3.9915849996221318,
           0.7936628026399772,
           -1.1900162760381576,
           -1.9068345958291415,
           1.5910302892976704,
           4.486885810373951,
           11.344784674105622,
           12.35615872635236]},
 {'intercept': -8.851582461426382,
  'coef': [-3.2520322613719577,
           3.5672765445215053,
           3.5291283004480767,
           1.5232642505199057,
           -6.3439814741822715,
           4.242985373744885,
           -1.992850290071895,
           -0.9204150103495982,
           -2.985515068528564,
           0.2429779076869858,
           5.349103499026808,
           8.301722041957957,
           19.404740034338896]}]
PROCEDURE = re.compile(
    r'\bpoint of order\b|\brules? of procedure\b|\badjourn|\blist of speakers\b|'
    r'\b(?:order|programme|plan) of (?:the |its )?(?:work|voting|discussion)\b|'
    r'\b(?:next|following) meeting\b|\bsummary records?\b|\bprocedural\b|'
    r'\b(?:set up|appoint|establish)\w* (?:a |the )?(?:sub-committee|working group)\b', re.I)


def canonical(instrument, article):
    """Only shared article 1 collapses the two covenant labels."""
    if not instrument or not str(article).isdigit():
        return None
    n = int(article)
    if n < 1 or instrument not in {'UDHR', 'ICCPR', 'ICESCR', 'ICCPR+ICESCR'}:
        return None
    if n == 1 and instrument != 'UDHR':
        instrument = 'ICCPR+ICESCR'
    return instrument, n



def same_article(first, second):
    """Match the official scorer, including existing explicitly joint tags."""
    if first is None or second is None:
        return False
    if first == second:
        return True
    return (first[1] == second[1] and first[0] != 'UDHR' and second[0] != 'UDHR'
            and (first[1] == 1 or '+' in first[0] or '+' in second[0]))


def fold(symbol):
    """Keep every speech in a record in the same calibration fold."""
    return int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % 5


def clean(text):
    """Remove speaker furniture and numbers that use unstable draft numbering."""
    text = re.sub(r'^\s*\d+[.\s]+', '', text)
    text = re.sub(r'^.{0,120}?\([^)]{1,80}\)\s*', '', text)
    text = re.sub(r'\b[A-Z]+(?:/[A-Z0-9.]+)+', ' ', text)
    return ' '.join(re.sub(r'[^a-z\s-]', ' ', text.lower()).split())


def is_candidate(segment):
    """Use the task's exact speech, null-tag, and character-length boundary."""
    return (segment['kind'] == 'speech' and segment['final_article'] is None
            and len(segment['text'] or '') > 150)


def read_database(path):
    """Read just the public corpus tables through an enforced read-only connection."""
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as con:
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA query_only=ON')
        segments = [dict(r) for r in con.execute(
            'SELECT id, symbol, seq, kind, text, final_article, article_instrument FROM segments ORDER BY symbol, seq, id')]
        documents = {r['symbol']: dict(r) for r in con.execute(
            'SELECT symbol, instrument, body, meeting_date, session FROM documents')}
        drafts = [dict(r) for r in con.execute(
            'SELECT instrument, final_article, text FROM draft_texts ORDER BY instrument, final_article, stage, draft_article')]
        refs = [dict(r) for r in con.execute(
            'SELECT segment_id, ref_symbol, amendment FROM refs ORDER BY segment_id, ref_symbol')]
    return segments, documents, drafts, refs


def amendment_index(segments, refs):
    """Accept cited amendments only when all tagged occurrences agree."""
    tags = {s['id']: canonical(s['article_instrument'], s['final_article']) for s in segments}
    labels = defaultdict(set)
    by_segment = defaultdict(set)
    for r in refs:
        if r['amendment']:
            by_segment[r['segment_id']].add(r['ref_symbol'])
            if tags.get(r['segment_id']):
                labels[r['ref_symbol']].add(tags[r['segment_id']])
    return {r: next(iter(v)) for r, v in labels.items() if len(v) == 1}, by_segment


def neighbors(segments):
    """Find nearest tagged speeches, stopping at record boundaries."""
    result = defaultdict(dict)
    for direction, ordered in [('before', segments), ('after', reversed(segments))]:
        previous = None
        symbol = None
        for s in ordered:
            if symbol != s['symbol']:
                previous = None
                symbol = s['symbol']
            if previous is not None:
                result[s['id']][direction] = previous
            if s['kind'] == 'speech' and canonical(s['article_instrument'], s['final_article']):
                previous = s
    return result


def features(path):
    """Retrieve topical examples and extract confidence evidence without gold data."""
    segments, documents, drafts, refs = read_database(path)
    candidates = [s for s in segments if is_candidate(s)]
    exemplars = [s for s in segments if s['kind'] in {'speech', 'paragraph'}
                 and canonical(s['article_instrument'], s['final_article']) and len(s['text'] or '') > 150]
    drafts = [d for d in drafts if canonical(d['instrument'], d['final_article']) and d['text']]
    amends, cited = amendment_index(segments, refs)
    nearby = neighbors(segments)
    result = []
    for family in ['UDHR', 'Covenants']:
        targets = [s for s in candidates if documents.get(s['symbol'], {}).get('instrument') == family]
        if not targets:
            continue
        train = [s for s in exemplars if (s['article_instrument'] == 'UDHR') == (family == 'UDHR')]
        if not train:
            result.extend((s, None, [0.] * 11, 'no tagged examples for instrument') for s in targets)
            continue
        texts = [d for d in drafts if (d['instrument'] == 'UDHR') == (family == 'UDHR')]
        vectorizer = TfidfVectorizer(preprocessor=clean, stop_words='english', ngram_range=(1, 2),
                                     min_df=2, max_df=0.85, sublinear_tf=True, max_features=80000, dtype=np.float32)
        matrix = vectorizer.fit_transform([s['text'] for s in train] + [d['text'] for d in texts])
        query = vectorizer.transform([s['text'] for s in targets])
        labels = [canonical(s['article_instrument'], s['final_article']) for s in train]
        draft_labels = [canonical(d['instrument'], d['final_article']) for d in texts]
        for start in range(0, len(targets), 128):
            similarities = (query[start:start + 128] @ matrix.T).toarray()
            for s, sim in zip(targets[start:start + 128], similarities):
                # Stable tie handling, including zero similarities.
                top = np.argsort(-sim[:len(train)], kind='stable')[:7].tolist()
                votes = Counter()
                for j in top:
                    votes[labels[j]] += float(sim[j]) ** 2
                if not votes or not sum(votes.values()):
                    result.append((s, None, [0.] * 11, 'no lexical evidence'))
                    continue
                tag = max(sorted(votes), key=votes.get)
                support = max(float(sim[j]) for j in top if labels[j] == tag)
                other = max((float(sim[j]) for j in top if labels[j] != tag), default=0.)
                share = votes[tag] / sum(votes.values())
                same_record = max((float(sim[j]) for j in top if labels[j] == tag and train[j]['symbol'] == s['symbol']), default=0.)
                cross_record = max((float(sim[j]) for j in top if labels[j] == tag and train[j]['symbol'] != s['symbol']), default=0.)
                draft_sim = max((float(sim[len(train) + j]) for j, t in enumerate(draft_labels) if t == tag), default=0.)
                sides = nearby[s['id']]
                flanks = len(sides) == 2 and all(
                    canonical(v['article_instrument'], v['final_article']) == tag and abs(v['seq'] - s['seq']) <= 12
                    for v in sides.values())
                amend_labels = {amends[r] for r in cited[s['id']] if r in amends}
                agree = amend_labels == {tag}
                procedure = bool(PROCEDURE.search(s['text']))
                multiple = len(set(re.findall(r'\barticle\s+(\d+)\b', s['text'], re.I))) > 1
                x = [support, support - other, share, draft_sim, same_record, float(flanks), float(agree),
                     min(len(s['text']) / 2000, 3), float(procedure), float(multiple), cross_record]
                exemplar = next(train[j]['id'] for j in top if labels[j] == tag)
                evidence = f'lexical match {exemplar} ({support:.3f}); vote share {share:.3f}; draft overlap {draft_sim:.3f}'
                if flanks:
                    evidence += '; nearby flanking speeches agree'
                if agree:
                    evidence += '; cited amendment agrees: ' + ', '.join(sorted(r for r in cited[s['id']] if amends.get(r) == tag))
                if procedure:
                    evidence += '; procedural language'
                if multiple:
                    evidence += '; multiple draft articles mentioned'
                result.append((s, tag, x, evidence))
    covered = {s['id'] for s, _, _, _ in result}
    result.extend((s, None, [0.] * 11, 'unknown document instrument') for s in candidates if s['id'] not in covered)
    return sorted(result, key=lambda r: (r[0]['symbol'], r[0]['seq'], r[0]['id']))


def semantic_support(tag, similarities, labels):
    """Compare the proposed article only with articles in its instrument family."""
    if tag is None:
        return 0., 0.
    own = [float(s) for s, label in zip(similarities, labels) if same_article(label, tag)]
    others = [float(s) for s, label in zip(similarities, labels)
              if not same_article(label, tag) and (label[0] == 'UDHR') == (tag[0] == 'UDHR')]
    support = max(own, default=0.)
    return support, support - max(others, default=0.)


def semantic_features(rows, cache=None):
    """Compare to article texts using the installed BGE model, with downloads disabled."""
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from sentence_transformers import SentenceTransformer
    import torch
    path = Path.home() / '.cache/huggingface/hub/models--BAAI--bge-base-en-v1.5/snapshots'
    revision = 'a5beb1e3e68b9ab74eb54cfd186867f64f240e1a'
    snapshot = path / revision
    if not snapshot.is_dir():
        raise FileNotFoundError(f'No installed BGE model at {snapshot}; downloads are disabled')
    text_map = json.loads((ROOT / 'data/concordance/udhr_final.json').read_text())['articles']
    articles = [(('UDHR', int(k)), v) for k, v in text_map.items() if k.isdigit()]
    covenants = json.loads((ROOT / 'data/concordance/covenants_final.json').read_text())['instruments']
    for inst in ('ICCPR', 'ICESCR'):
        articles.extend((canonical(inst, k), v) for k, v in covenants[inst].items() if k.isdigit())
    inputs = [clean(s['text']) for s, _, _, _ in rows] + [clean(text) for _, text in articles]
    digest = hashlib.sha256(('bge-128-v1' + revision + '\0'.join(inputs)).encode()).hexdigest()
    cached = cache / (digest + '.npy') if cache else None
    if cached and cached.exists():
        embeddings = np.load(cached, allow_pickle=False)
    else:
        torch.set_num_threads(4)
        model = SentenceTransformer(str(snapshot), local_files_only=True, device='cpu')
        model.max_seq_length = 128
        embeddings = model.encode(inputs, batch_size=32, normalize_embeddings=True, show_progress_bar=True)
        if cached:
            cached.parent.mkdir(parents=True, exist_ok=True)
            np.save(cached, embeddings, allow_pickle=False)
    for i, (s, tag, x, evidence) in enumerate(rows):
        sims = embeddings[len(rows):] @ embeddings[i]
        support, margin = semantic_support(tag, sims, [label for label, _ in articles])
        rows[i] = (s, tag, x + [support, margin], evidence + f'; semantic support {support:.3f}, margin {margin:.3f}')
    return rows


def confidence(x, symbol, models=MODELS):
    """Apply the model that excluded this record's dev fold."""
    if len(models) != 5:
        raise ValueError('Five frozen confidence models are required')
    model = models[fold(symbol)]
    if len(x) != len(model['coef']):
        raise ValueError('Confidence feature count does not match the frozen model')
    z = model['intercept'] + sum(a * b for a, b in zip(x, model['coef']))
    return float(1 / (1 + np.exp(-np.clip(z, -40, 40))))


def write_predictions(rows, output, models=MODELS):
    """Keep every candidate; weak evidence is an explicit abstention."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        for s, tag, x, evidence in rows:
            score = confidence(x, s['symbol'], models) if tag else 0.
            if score < 0.5:
                tag = None
                evidence = 'abstain: ' + evidence
            writer.writerow(dict(segment_id=s['id'], instrument=tag[0] if tag else '',
                                 final_article=tag[1] if tag else '', score=f'{score:.6f}', evidence=evidence))


def calibrate(rows, gold):
    """Fit five confidence models on dev only, holding out entire records."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    judged = {r['id']: r for line in gold.read_text().splitlines()
              if (r := json.loads(line))['split'] == 'dev' and r['source'] == 'coverage' and r['current_tag'] is None}
    samples = [(s, tag, x) for s, tag, x, _ in rows if s['id'] in judged and tag]
    x = np.array([r[2] for r in samples])
    y = np.array([same_article(canonical(*judged[s['id']]['label'].rsplit(' ', 1)), tag)
                  if ' ' in judged[s['id']]['label'] else False for s, tag, _ in samples])
    folds = np.array([fold(s['symbol']) for s, _, _ in samples])
    models = []
    for i in range(5):
        training = folds != i
        scaler = StandardScaler().fit(x[training])
        model = LogisticRegression(C=1., max_iter=2000, random_state=0).fit(
            scaler.transform(x[training]), y[training])
        coef = model.coef_[0] / scaler.scale_
        models.append(dict(intercept=float(model.intercept_[0] - coef @ scaler.mean_), coef=coef.tolist()))
    print('MODELS = ' + repr(models))
    return models


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db', type=Path, default=DEFAULT_DB)
    ap.add_argument('--out', type=Path, default=ROOT / 'data/tagger/predictions.csv')
    ap.add_argument('--embedding-cache', type=Path, help='optional local cache directory (no downloads)')
    ap.add_argument('--calibrate-dev', type=Path, help='development only: fit dev confidence models; print frozen coefficients')
    args = ap.parse_args()
    if args.out.resolve() == args.db.resolve():
        ap.error('Prediction output must not overwrite the source database')
    rows = semantic_features(features(args.db), args.embedding_cache)
    models = calibrate(rows, args.calibrate_dev) if args.calibrate_dev else MODELS
    write_predictions(rows, args.out, models)
    print(f'{len(rows)} candidates -> {args.out}')


if __name__ == '__main__':
    main()
