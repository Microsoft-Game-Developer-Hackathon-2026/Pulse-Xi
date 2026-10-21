import csv
import io

from fastapi.testclient import TestClient
import pytest

from app.main import app, get_match
from app.exports import AnalysisExport, analysis_export, safe_cell

client = TestClient(app)
BASE = '/api/matches/comeback-1107/analysis-export'


def test_export_matches_real_source_and_cutoff():
    source = client.get('/api/matches/comeback-1107/events?limit=1000').json()
    result = client.get(BASE, params={'at_second': 1000}).json()
    AnalysisExport.model_validate(result)
    assert result['data'] == [e for e in source if e['match_second'] <= 1000]
    assert result['provenance']['engine_manifest'] is None
    assert result['provenance']['source_event_ids'] == [e['event_id'] for e in result['data']]
    assert [e['sequence'] for e in result['data']] == sorted(e['sequence'] for e in result['data'])
    assert client.get(BASE, params={'at_second': 1000}).json()['data'] == result['data']


def test_filtered_csv_and_pass_factors_equal_backend():
    match, events = get_match('comeback-1107')
    event = next(e for e in events if e.event_type == 'pass')
    params = {'at_second': event.match_second, 'team_id': event.team_id, 'event_type': 'pass', 'format': 'csv'}
    response = client.get(BASE, params=params)
    rows = list(csv.DictReader(io.StringIO(response.text.lstrip('\ufeff'))))
    assert rows and all(row['team_id'] == event.team_id and row['type'] == 'pass' for row in rows)
    assert all(int(row['match_second']) <= event.match_second for row in rows)
    from app.pass_difficulty import score_pass
    expected = score_pass(match, event, event.match_second).model_dump(mode='json')
    exported = client.get(BASE, params={'category': 'pass', 'at_second': event.match_second, 'event_id': event.event_id}).json()
    assert exported['data'] == [expected]
    csv_response = client.get(BASE, params={'category': 'pass', 'format': 'csv', 'at_second': event.match_second, 'event_id': event.event_id})
    csv_packet = list(csv.DictReader(io.StringIO(csv_response.text.lstrip('\ufeff'))))[0]
    import json
    assert json.loads(csv_packet['factors']) == expected['factors']
    assert exported['data'][0]['factors'][0]['raw_value'] == pytest.approx(((event.end.x-event.start.x)**2+(event.end.y-event.start.y)**2)**.5)
    assert client.get(BASE, params={'category': 'pass', 'at_second': event.match_second-1, 'event_id': event.event_id}).status_code == 404


def test_metrics_and_validation():
    expected = client.get('/api/matches/comeback-1107/metrics?at_second=2000').json()
    result = client.get(BASE, params={'category': 'metrics', 'at_second': 2000}).json()
    for row, side in zip(result['data'], ['home','away']):
        for name, value in expected[side].items(): assert row[name] == value
    for params in [{'at_second': -1}, {'at_second': 99999}, {'at_second': 0, 'event_type': 'fake'}, {'at_second': 0, 'team_id': 'foreign'}, {'at_second': 0, 'format': 'exe'}]:
        assert client.get(BASE, params=params).status_code == 422
    assert client.get('/api/matches/unknown/analysis-export?at_second=0').status_code == 404


@pytest.mark.parametrize('value', ['=SUM(1,2)', '+cmd', '-formula', '@macro', ' \t=1', '\ntext', '\ufeff=1'])
def test_formula_injection(value):
    assert safe_cell(value).startswith("'")
    assert safe_cell(-2) == -2
    assert safe_cell(None) == ''
    assert safe_cell(0) == 0


def test_empty_one_event_unordered_large_and_special_cells():
    match, events = get_match('comeback-1107')
    assert b'"data": []' in analysis_export(match, [], 0, 'events', 'json', None, None, None).body
    event = events[0].model_copy(update={'outcome': '=1+1,"Hi"\nHindi: नमस्ते'})
    response = analysis_export(match, [event], event.match_second, 'events', 'csv', None, None, None)
    rows = list(csv.DictReader(io.StringIO(response.body.decode('utf-8-sig'))))
    assert rows[0]['outcome'].startswith("'=1+1") and 'नमस्ते' in rows[0]['outcome']
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error: analysis_export(match, [event]*5001, 5400, 'events', 'json', None, None, None)
    assert error.value.status_code == 413
    oversized = event.model_copy(update={'qualifiers': {'adversarial_text': 'x' * 8_000_001}})
    with pytest.raises(HTTPException) as byte_error:
        analysis_export(match, [oversized], 5400, 'events', 'json', None, None, None)
    assert byte_error.value.status_code == 413
    output = analysis_export(match, list(reversed(events[:2])), 5400, 'events', 'json', None, None, None)
    import json
    assert [e['sequence'] for e in json.loads(output.body)['data']] == [e.sequence for e in events[:2]]


def test_missing_coordinates_stay_unavailable_and_filename_is_safe():
    match, events = get_match('comeback-1107')
    event = next(e for e in events if e.event_type == 'pass').model_copy(update={'start': None, 'end': None})
    import json
    output = analysis_export(match, [event], 5400, 'pass', 'json', None, None, event.event_id)
    row = json.loads(output.body)['data'][0]
    assert row['score'] is None and row['unavailable_reason']
    match = match.model_copy(update={'match_id': 'unsafe/filename\r\n"quoted'})
    output = analysis_export(match, [], 0, 'events', 'csv', None, None, None)
    assert '\r' not in output.headers['content-disposition'] and '\n' not in output.headers['content-disposition']
    assert 'unsafe_filename' in output.headers['content-disposition']


def test_export_recovers_imported_sqlite_events_without_mutating_them(tmp_path, monkeypatch):
    monkeypatch.setenv('PULSE_IMPORT_TOKEN', 'test-import-token-at-least-32-characters')
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'export.sqlite'))
    match, events = get_match('comeback-1107')
    match = match.model_copy(update={'match_id': 'analysis-imported'})
    event = next(e for e in events if e.event_type == 'pass').model_copy(update={
        'match_id': match.match_id, 'event_id': 'analysis-imported-e1', 'sequence': 1})
    payload = {'match': match.model_dump(mode='json'), 'events': [event.model_dump(mode='json', by_alias=True)]}
    assert client.post('/api/matches/ingest', headers={'Authorization': 'Bearer test-import-token-at-least-32-characters'}, json=payload).status_code == 200
    path = '/api/matches/analysis-imported/analysis-export'
    first = client.get(path, params={'at_second': 5400}).json()
    assert first['data'] == payload['events']
    from app.storage import imported_match
    assert imported_match(match.match_id)[1][0].model_dump(mode='json', by_alias=True) == payload['events'][0]
    assert client.get(path, params={'at_second': 5400}).json()['data'] == first['data']
