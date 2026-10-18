import copy
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_match
from app.storage import imported_match

TOKEN = "test-import-token-at-least-32-characters"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
client = TestClient(app)


@pytest.fixture
def package(tmp_path, monkeypatch):
    from app.simulator import generate
    monkeypatch.setenv("PULSE_DB_PATH", str(tmp_path / "hub.sqlite"))
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", TOKEN)
    match, events = generate("comeback")
    match = match.model_copy(update={"match_id": "research-match"})
    # Noncontiguous sequences and tied timestamps are preserved, never reassigned.
    events = [e.model_copy(update={"match_id": match.match_id, "sequence": i * 2 + 1}) for i, e in enumerate(events[:10])]
    return {"schema_version": "pulse-xi-match-package/1", "match": match.model_dump(mode="json"),
            "events": [e.model_dump(mode="json", by_alias=True) for e in events]}


def test_preview_no_database_write_and_roundtrip(package, tmp_path):
    response = client.post('/api/data-hub/preview', json=package, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json()['quality']['event_count'] == 10
    assert not (tmp_path / 'hub.sqlite').exists()
    result = client.post('/api/data-hub/import', json=package, headers=HEADERS)
    assert result.status_code == 200, result.text
    assert result.json()['inserted'] == 10
    assert client.post('/api/data-hub/import', json=package, headers=HEADERS).json()['inserted'] == 0
    source = client.get('/api/matches/research-match/events').json()
    assert source == package['events']
    exported = client.get('/api/matches/research-match/package')
    assert exported.status_code == 200
    assert exported.json()['events'] == source
    assert client.post('/api/data-hub/preview', content=exported.content, headers={**HEADERS, 'Content-Type': 'application/json'}).json()['status'] == 'identical'
    # Fresh connection and app instance recover persisted data, not process memory.
    assert imported_match('research-match')[0].match_id == 'research-match'
    assert TestClient(app).get('/api/matches/research-match/events').json() == source
    recovered = subprocess.run([sys.executable, '-c', "import json; from app.storage import imported_match; print(json.dumps([e.model_dump(mode='json', by_alias=True) for e in imported_match('research-match')[1]]))"],
                               capture_output=True, text=True, check=True, env=os.environ.copy())
    assert json.loads(recovered.stdout) == source
    quality = next(e for e in client.get('/api/data-hub').json()['matches'] if e['match']['match_id'] == 'research-match')
    assert quality['origin'] == 'imported' and quality['quality']['event_count'] == len(source)


@pytest.mark.parametrize('change', ['match', 'player', 'duplicate', 'sequence', 'time', 'type', 'coordinates', 'metadata', 'extra', 'analysis', 'period', 'fulltime'])
def test_invalid_packages_are_atomic(package, change):
    broken = copy.deepcopy(package)
    event = broken['events'][1]
    if change == 'match': event['match_id'] = 'wrong'
    if change == 'player': event['actor_id'] = 'wrong'
    if change == 'duplicate': broken['events'].append(event)
    if change == 'sequence': event['sequence'] = broken['events'][0]['sequence']
    if change == 'time': event['match_second'] = 5401
    if change == 'type': event['type'] = 'invented'
    if change == 'coordinates': event['start'] = {'x': -1, 'y': 0}
    if change == 'metadata': broken['match']['home']['color'] = 'url(https://example.test)'
    if change == 'extra': event['tracking_positions'] = []
    if change == 'analysis': broken['schema_version'] = 'analysis-export/1'
    if change == 'period': event['period'] = 2
    if change == 'fulltime': broken['events'][0]['type'] = 'fulltime'
    for endpoint in ('preview', 'import'):
        response = client.post(f'/api/data-hub/{endpoint}', json=broken, headers=HEADERS)
        assert response.status_code == 422, response.text
    assert imported_match('research-match') is None


def test_conflicts_and_concurrent_imports(package):
    def post(_):
        return client.post('/api/data-hub/import', json=package, headers=HEADERS)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(post, range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert sum(r.json()['inserted'] for r in responses) == 10
    before = imported_match('research-match')
    for key in ('metadata', 'event', 'subset'):
        broken = copy.deepcopy(package)
        if key == 'metadata': broken['match']['title'] = 'conflict'
        if key == 'event': broken['events'][1]['outcome'] = 'changed'
        if key == 'subset': broken['events'].pop()
        assert client.post('/api/data-hub/preview', json=broken, headers=HEADERS).status_code == 409
        assert client.post('/api/data-hub/import', json=broken, headers=HEADERS).status_code == 409
        assert imported_match('research-match') == before


def test_authorization_and_limits(package, monkeypatch):
    for path in ('/api/data-hub/preview', '/api/data-hub/import', '/api/matches/ingest'):
        data = package if 'data-hub' in path else {k: package[k] for k in ('match', 'events')}
        assert client.post(path, json=data).status_code == 403
        # A forged local Host or Origin never grants permission.
        assert client.post(path, json=data, headers={'Host': 'localhost', 'Origin': 'http://localhost:5173'}).status_code == 403
        monkeypatch.delenv('PULSE_IMPORT_TOKEN')
        assert client.post(path, json=data, headers=HEADERS).status_code == 503
        monkeypatch.setenv('PULSE_IMPORT_TOKEN', TOKEN)
    assert client.post('/api/data-hub/import', content=b' ' * 2_000_001, headers=HEADERS).status_code == 413
    assert client.post('/api/data-hub/import', content=b'{', headers={**HEADERS, 'Content-Type': 'application/json'}).status_code == 422
    package['events'] *= 101
    assert client.post('/api/data-hub/preview', json=package, headers=HEADERS).status_code == 422


def test_empty_package_unavailable_data_and_unknown_match(package):
    package['events'] = []
    assert client.post('/api/data-hub/import', json=package, headers=HEADERS).status_code == 200
    exported = client.get('/api/matches/research-match/package').json()
    assert exported['events'] == []
    assert client.get('/api/matches/missing/package').status_code == 404
    assert client.post('/api/data-hub/import', json=exported, headers=HEADERS).json()['total'] == 0


def test_injected_write_failure_rolls_back(package, monkeypatch):
    from app import storage
    original = storage.MatchEvent.model_dump_json
    calls = 0
    def interrupted(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('interrupted transaction')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(storage.MatchEvent, 'model_dump_json', interrupted)
    with pytest.raises(RuntimeError, match='interrupted'):
        client.post('/api/data-hub/import', json=package, headers=HEADERS)
    assert imported_match('research-match') is None


@pytest.mark.parametrize('raw', ['{"match":{},"match":{}}', '{"events":[NaN]}', '{"events":[1e999]}', '[' * 1100 + '0' + ']' * 1100], ids=['duplicate-key','nan','infinity','deep-nesting'])
def test_ambiguous_nonfinite_or_nested_json_rejected(package, raw):
    assert client.post('/api/data-hub/import', content=raw, headers={**HEADERS,'Content-Type':'application/json'}).status_code == 400
    assert imported_match('research-match') is None


def test_provenance_and_package_immutability(package):
    package['provenance'] = {'source': 'Author supplied research fixture', 'application_revision': None}
    assert client.post('/api/data-hub/import', json=package, headers=HEADERS).status_code == 200
    exported = client.get('/api/matches/research-match/package').json()
    assert exported['provenance']['source'] == package['provenance']['source']
    assert exported['provenance']['application_revision'] is None
    assert exported['provenance']['exported_at']
    assert client.post('/api/matches/ingest', json={k:package[k] for k in ('match','events')}, headers=HEADERS).status_code == 409
    assert client.get('/api/matches/research-match/events').json() == package['events']


def test_missing_coordinates_and_optional_player_fields(package):
    for e in package['events']:
        e['start'] = e['end'] = e['recipient_id'] = None
    assert client.post('/api/data-hub/import', json=package, headers=HEADERS).status_code == 200
    event = next(e for e in package['events'] if e['type'] == 'pass')
    result = client.get(f"/api/matches/research-match/passes/{event['event_id']}/difficulty", params={'at_second':event['match_second']})
    assert result.status_code == 200 and result.json()['score'] is None
    assert result.json()['unavailable_reason']


def test_library_capacity_and_reserved_identity(package):
    from app.storage import connect
    with connect() as db:
        for i in range(100):
            match = {**package['match'], 'match_id': f'capacity-{i}'}
            db.execute('INSERT INTO matches VALUES (?,?)',(match['match_id'],json.dumps(match)))
    assert client.post('/api/data-hub/import', json=package, headers=HEADERS).status_code == 409
    assert imported_match('research-match') is None
    package['match']['match_id'] = 'custom-1'
    for e in package['events']: e['match_id'] = 'custom-1'
    assert client.post('/api/data-hub/preview', json=package, headers=HEADERS).status_code == 409


def test_legacy_import_can_be_adopted_without_rewriting_events(package):
    legacy = {k:package[k] for k in ('match','events')}
    assert client.post('/api/matches/ingest', json=legacy, headers=HEADERS).status_code == 200
    portable = client.get('/api/matches/research-match/package').json()
    before = client.get('/api/matches/research-match/events').json()
    assert client.post('/api/data-hub/import', json=portable, headers=HEADERS).json()['inserted'] == 0
    assert client.get('/api/matches/research-match/events').json() == before
    assert client.post('/api/matches/ingest', json=legacy, headers=HEADERS).status_code == 409
