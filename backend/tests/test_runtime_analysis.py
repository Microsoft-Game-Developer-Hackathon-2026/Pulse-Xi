import csv
import io
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.sandbox import storage
from app.sandbox.engine import build_scenario, digest, match_record, match_events
from app.sandbox.models import ScenarioConfig, Command
from app.pass_difficulty import score_pass

TOKEN = 'runtime-analysis-owner-token-at-least-32-chars'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
client = TestClient(app)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'matches.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(tmp_path / 'runtime.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': TOKEN, 'bob': 'other-owner-token-at-least-32-characters'}))
    scenario = storage.save_scenario('alice', build_scenario(ScenarioConfig(seed=7)))
    current = storage.create_session('alice', 'new-analysis', scenario.scenario_id)
    storage.mutate('alice', current.session_id, Command(operation_id='step-analysis', expected_revision=current.revision, kind='step', ticks=300))
    return current.session_id


def get(sid, path, headers=HEADERS):
    return client.get(f'/api/sandbox/sessions/{sid}/{path}', headers=headers)


def test_source_parity_cutoff_and_no_mutation(runtime):
    before = storage.get_runtime('alice', runtime)
    response = get(runtime, 'analysis?at_second=100')
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    data = response.json()
    projected = match_events(before.state, runtime)
    assert data['events'] == [e.model_dump(mode='json', by_alias=True) for e in projected if e.match_second <= 100]
    assert data['metrics']['home']['passes'] == sum(e.event_type == 'pass' and e.team_id == 'home' and e.match_second <= 100 for e in projected)
    assert data['event_hash'] == before.event_hash
    from app.evidence import verify
    from app.models import Insight
    assert all(verify(Insight.model_validate(item), match_record(before.state, runtime), projected) for item in data['insights'])
    assert digest(storage.get_runtime('alice', runtime).state) == digest(before.state)
    assert get(runtime, 'analysis?at_second=301').status_code == 422
    assert get(runtime, 'analysis?at_second=-1').status_code == 422
    assert client.get(f'/api/matches/{runtime}').status_code == 404


@pytest.mark.parametrize('path', ['analysis?at_second=300', 'pass-difficulty?at_second=300', 'analysis-export?at_second=300'])
def test_owner_enforcement(runtime, path):
    assert get(runtime, path, {}).status_code == 403
    assert get(runtime, path, {'Authorization': 'Bearer other-owner-token-at-least-32-characters'}).status_code == 404


def test_pass_evidence_export_parity_and_invalid_ids(runtime):
    view = storage.get_runtime('alice', runtime)
    match = match_record(view.state, runtime)
    passes = [e for e in match_events(view.state, runtime) if e.event_type == 'pass']
    response = get(runtime, 'pass-difficulty?at_second=300&limit=1').json()
    first = passes[0]
    assert response['items'][0] == score_pass(match, first, 300).model_dump(mode='json')
    assert response['next_cursor'] == first.sequence
    evidence = get(runtime, f'passes/{first.event_id}/difficulty/evidence?at_second=300').json()
    assert evidence['verified'] is True
    assert evidence['source_events'] == [first.model_dump(mode='json', by_alias=True)]
    assert get(runtime, f'passes/{passes[-1].event_id}/difficulty/evidence?at_second=0').status_code == 404
    assert get(runtime, 'passes/fabricated/difficulty/evidence?at_second=300').status_code == 404
    assert get(runtime, f'passes/{first.event_id}/difficulty/evidence?at_second=300', {}).status_code == 403
    exported = get(runtime, f'analysis-export?at_second=300&category=pass&event_id={first.event_id}').json()
    assert exported['data'] == [evidence['claim']]
    assert exported['provenance']['fixture_seed'] is None
    assert exported['provenance']['runtime']['event_hash'] == view.event_hash
    assert TOKEN not in json.dumps(exported)


def test_csv_identity_provenance_cutoff(runtime):
    response = get(runtime, 'analysis-export?at_second=100&format=csv')
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert rows
    assert all(row['runtime_session_id'] == runtime and int(row['match_second']) <= 100 for row in rows)
    assert all(row['event_id'].startswith(runtime + '-') for row in rows)
    assert response.headers['cache-control'] == 'no-store'
    assert TOKEN not in response.text
    assert get(runtime, 'analysis-export?at_second=301').status_code == 422


def test_short_scenarios_are_explicitly_unsupported(runtime):
    scenario = storage.save_scenario('alice', build_scenario(ScenarioConfig(duration_seconds=300)))
    short = storage.create_session('alice', 'short-analysis', scenario.scenario_id)
    response = get(short.session_id, 'analysis?at_second=0')
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'v1_requires_90_minutes'
