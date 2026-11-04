"""Offline article proposals, abstention, and record-held-out calibration."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
import article_tagger as tagger


def segment(id='a-1', symbol='a', seq=1, instrument=None, article=None):
    return dict(id=id, symbol=symbol, seq=seq, article_instrument=instrument,
                final_article=article, kind='speech', text='A speech ' * 30)


def test_canonical_preserves_instrument_and_deleted_articles():
    assert tagger.canonical('ICCPR', 1) == tagger.canonical('ICESCR', '1')
    assert tagger.canonical('ICCPR', 2) != tagger.canonical('ICESCR', 2)
    assert tagger.canonical('UDHR', 1) != tagger.canonical('ICCPR', 1)
    assert tagger.canonical('ICCPR', 'former-2') is None
    assert tagger.canonical(None, 2) is None
    assert tagger.canonical('UDHR', 0) is None


def test_neighbors_never_cross_records_or_include_self():
    a = segment(instrument='ICCPR', article=6)
    b = segment('a-2', seq=2)
    c = segment('a-3', seq=3, instrument='ICCPR', article=7)
    d = segment('b-1', symbol='b')
    neighbors = tagger.neighbors([a, b, c, d])
    assert neighbors[b['id']] == {'before': a, 'after': c}
    assert 'before' not in neighbors[a['id']]
    assert 'after' not in neighbors[c['id']]
    assert not neighbors[d['id']]


def test_ambiguous_amendments_and_generic_references_are_not_evidence():
    segments = [segment('a', instrument='ICCPR', article=6),
                segment('b', instrument='ICCPR', article=7)]
    refs = [dict(segment_id='a', ref_symbol='X', amendment=1),
            dict(segment_id='b', ref_symbol='X', amendment=1),
            dict(segment_id='a', ref_symbol='Y', amendment=0),
            dict(segment_id='a', ref_symbol='Z', amendment=1)]
    mapping, cited = tagger.amendment_index(segments, refs)
    assert mapping == {'Z': ('ICCPR', 6)}
    assert 'Y' not in cited['a']


def test_clean_ignores_draft_numbers_and_speaker():
    assert tagger.clean('12. Mr. SMITH (Canada) Article 17 protects liberty.') == tagger.clean(
        'Mr. JONES (France) Article 6 protects liberty.')


def test_procedure_does_not_reject_substantive_roll_call_vote():
    assert tagger.PROCEDURE.search('He moved the adjournment of the meeting.')
    assert not tagger.PROCEDURE.search('He requested a roll-call vote on the words freedom of religion.')


def test_output_covers_abstentions_without_changing_ids(tmp_path):
    rows = [(segment('original-0001'), ('ICCPR', 6), [0.] * 11, 'weak'),
            (segment('original-0002'), None, [0.] * 11, 'no evidence')]
    out = tmp_path / 'predictions.csv'
    tagger.write_predictions(rows, out, [{'intercept': -1., 'coef': [0.] * 11}] * 5)
    result = list(csv.DictReader(out.open()))
    assert [r['segment_id'] for r in result] == ['original-0001', 'original-0002']
    assert all(not r['final_article'] and not r['instrument'] for r in result)


def test_confidence_uses_only_held_out_record_model():
    models = [{'intercept': float(i), 'coef': [0.] * 11} for i in range(5)]
    symbol = 'E/CN.4/SR.98'
    expected = 1 / (1 + tagger.np.exp(-tagger.fold(symbol)))
    assert tagger.confidence([0.] * 11, symbol, models) == expected


def test_calibration_ignores_test_labels_and_holds_out_records(tmp_path, capsys):
    rows, gold = [], []
    for i in range(100):
        s = segment(str(i), symbol=f'record-{i // 2}')
        rows.append((s, ('ICCPR', 6), [i % 3 / 3.] * 11, 'evidence'))
        gold.append(dict(id=s['id'], symbol=s['symbol'], label='ICCPR 6' if i % 2 else 'NONE',
                         split='dev', source='coverage', current_tag=None))
    gold.append(dict(id='private-test-label', split='test'))  # No other test fields may be consulted.
    path = tmp_path / 'gold.jsonl'
    path.write_text('\n'.join(map(json.dumps, gold)))
    first = tagger.calibrate(rows, path)
    held_out = tagger.fold(rows[0][0]['symbol'])
    for g in gold[:-1]:
        if tagger.fold(g['symbol']) == held_out:
            g['label'] = 'ICCPR 6'
    path.write_text('\n'.join(map(json.dumps, gold)))
    second = tagger.calibrate(rows, path)
    assert first[held_out] == second[held_out]
    assert any(first[i] != second[i] for i in range(5) if i != held_out)


def test_read_database_is_read_only_and_missing_db_is_not_created(tmp_path, monkeypatch):
    path = tmp_path / 'test.sqlite3'
    with sqlite3.connect(path) as con:
        con.executescript('''
            CREATE TABLE segments(id, symbol, seq, kind, text, final_article, article_instrument);
            CREATE TABLE documents(symbol, instrument, body, meeting_date, session);
            CREATE TABLE draft_texts(instrument, final_article, text, stage, draft_article);
            CREATE TABLE refs(segment_id, ref_symbol, amendment);
        ''')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    real_connect = sqlite3.connect
    def connect(database, **kwargs):
        assert database.endswith('?mode=ro') and kwargs['uri']
        con = real_connect(database, **kwargs)
        with pytest.raises(sqlite3.OperationalError):
            con.execute('CREATE TABLE forbidden(x)')
        return con
    monkeypatch.setattr(tagger.sqlite3, 'connect', connect)
    assert tagger.read_database(path) == ([], {}, [], [])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with pytest.raises(sqlite3.OperationalError):
        tagger.read_database(tmp_path / 'missing.sqlite3')
    assert not (tmp_path / 'missing.sqlite3').exists()


def test_candidate_boundary_is_exact():
    s = segment()
    s['text'] = 'x' * 150
    assert not tagger.is_candidate(s)
    s['text'] += 'x'
    assert tagger.is_candidate(s)
    s['final_article'] = 6
    assert not tagger.is_candidate(s)
    s['final_article'], s['kind'] = None, 'chair'
    assert not tagger.is_candidate(s)


def test_semantic_margin_ignores_other_family_but_not_other_covenant():
    labels = [('UDHR', 6), ('ICCPR', 6), ('ICESCR', 6)]
    support, margin = tagger.semantic_support(('ICCPR', 6), [.99, .7, .6], labels)
    assert support == .7 and margin == pytest.approx(.1)
    assert tagger.semantic_support(None, [.99, .7, .6], labels) == (0., 0.)


def test_output_is_deterministic_and_keeps_positive_proposal(tmp_path):
    models = [{'intercept': 3., 'coef': [0.] * 11}] * 5
    rows = [(segment(), ('ICCPR', 6), [0.] * 11, 'evidence')]
    first, second = tmp_path / 'first.csv', tmp_path / 'second.csv'
    tagger.write_predictions(rows, first, models)
    tagger.write_predictions(rows, second, models)
    assert first.read_bytes() == second.read_bytes()
    p = list(csv.DictReader(first.open()))[0]
    assert p['instrument'] == 'ICCPR' and p['final_article'] == '6'
    assert float(p['score']) > .95


def test_wrong_feature_count_cannot_silently_change_confidence():
    with pytest.raises(ValueError):
        tagger.confidence([0.] * 10, 'a', [{'intercept': 0., 'coef': [0.] * 11}] * 5)


def test_existing_explicit_joint_tags_follow_official_scorer():
    assert tagger.same_article(('ICCPR+ICESCR', 3), ('ICESCR', 3))
    assert not tagger.same_article(('ICCPR', 3), ('ICESCR', 3))
    assert not tagger.same_article(('UDHR', 3), ('ICCPR+ICESCR', 3))
    assert not tagger.same_article(None, None)
