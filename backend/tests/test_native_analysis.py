import csv
import io
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from math import floor, hypot

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models import MatchEvent
from app.sandbox import storage
from app.sandbox.engine import build_scenario, digest
from app.sandbox.models import Command, ScenarioConfig
from app.sandbox.native_analysis import NativeEvent

TOKEN = 'native-analysis-owner-token-at-least-32-characters'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
client = TestClient(app)


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'matches.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(tmp_path / 'runtime.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice':TOKEN,'bob':'other-owner-token-at-least-32-characters'}))


def create(duration):
    scenario = storage.save_scenario('alice', build_scenario(ScenarioConfig(seed=7, duration_seconds=duration)))
    return storage.create_session('alice', f'native-{duration}', scenario.scenario_id)


def advance(view, target):
    while view.tick < target:
        receipt = storage.mutate('alice', view.session_id, Command(operation_id=f'step-{view.revision}',
            expected_revision=view.revision, kind='step', ticks=min(300, target-view.tick)))
        view = storage.get_runtime('alice', receipt.session_id)
    return view


def read(sid, path, headers=HEADERS):
    separator = '&' if '?' in path else '?'
    return client.get(f'/api/sandbox/sessions/{sid}/{path}{separator}projection=native', headers=headers)


@pytest.mark.parametrize('duration', [60,120,300,600,1800,2700,5400])
def test_native_boundaries_identity_metrics_evidence_and_exports(database, duration):
    view = create(duration)
    sid, half = view.session_id, duration//2
    kickoff = read(sid, 'analysis?at_second=0').json()
    assert kickoff['schema_version'] == 'runtime-native-analysis/1'
    assert kickoff['match']['duration_seconds'] == duration
    assert kickoff['clock']['halftime_tick'] == half
    assert kickoff['events'][0]['period'] == 1
    assert kickoff['events'][0]['tick'] == 0
    assert read(sid, 'analysis?at_second=1').status_code == 422
    view = advance(view, half)
    at_half = read(sid, f'analysis?at_second={half}').json()
    halftime = next(e for e in at_half['events'] if e['type']=='halftime')
    assert halftime['tick'] == half and halftime['period'] == 1
    assert at_half['clock']['current_period'] == 2
    assert at_half['clock']['inspection_period'] == 2
    assert all(e['tick'] <= half for e in at_half['events'])
    view = advance(view, duration)
    before_hash = digest(view.state)
    response = read(sid, f'analysis?at_second={duration}')
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    result = response.json()
    events = result['events']
    assert result['revision'] == view.revision and result['event_cursor'] == view.event_cursor
    assert result['state_hash'] == view.state_hash and result['event_hash'] == view.event_hash
    assert result['branch_id'] == sid and result['scenario_id'] == view.scenario_id
    assert [(e['sequence'],e['tick'],e['period'],e['type']) for e in events] == [
        (e.sequence,e.tick,e.period,e.type) for e in view.state.events]
    assert len({e['event_id'] for e in events}) == len(events)
    assert all(e['event_id']==f'{sid}-{e["sequence"]}' and e['generated_at_utc'] is None for e in events)
    assert events[-1]['type']=='fulltime' and events[-1]['tick']==duration and events[-1]['period']==2
    for side in ['home','away']:
        counts = Counter(e['type'] for e in events if e['team_id']==result['match'][side]['team_id'])
        assert result['metrics'][side]['passes'] == counts['pass']
        assert result['metrics'][side]['shots'] == counts['shot']
        assert result['score'][side] == counts['goal']
        assert result['event_counts_by_team'][result['match'][side]['team_id']].get('carry',0) == counts['carry']
    earlier = read(sid, f'analysis?at_second={half-1}').json()
    assert earlier['events'] == [e for e in events if e['tick']<half]
    assert earlier['clock']['inspection_period']==1
    assert earlier['unavailable']['legacy_insight_templates']
    packet = read(sid, f'analysis-export?at_second={duration}').json()
    assert packet['data']==events
    assert packet['provenance']['runtime']['halftime_tick']==half
    csv_response = read(sid, f'analysis-export?at_second={half}&format=csv')
    rows = list(csv.DictReader(io.StringIO(csv_response.content.decode('utf-8-sig'))))
    assert [r['event_id'] for r in rows]==[e['event_id'] for e in events if e['tick']<=half]
    assert all(int(r['halftime_tick'])==half and int(r['tick'])<=half for r in rows)
    first_pass = next(e for e in events if e['type']=='pass')
    evidence = read(sid, f'passes/{first_pass["event_id"]}/difficulty/evidence?at_second={duration}').json()
    assert evidence['schema_version']=='runtime-pass-evidence/1' and evidence['verified']
    assert evidence['source_events']==[first_pass]
    dx = first_pass['end']['x']-first_pass['start']['x']
    dy = first_pass['end']['y']-first_pass['start']['y']
    expected = floor(100*((55/85)*min(hypot(dx,dy)/100,1)+(30/85)*min(max(dx,0)/60,1))+.5)
    assert evidence['claim']['score']==expected
    exported_pass = read(sid,f'analysis-export?category=pass&event_id={first_pass["event_id"]}&at_second={duration}').json()
    assert exported_pass['data']==[evidence['claim']]
    assert TOKEN not in json.dumps(packet)
    assert digest(storage.get_runtime('alice',sid).state)==before_hash
    assert read(sid, f'analysis?at_second={duration+1}').status_code==422


def test_native_validation_does_not_weaken_legacy_events(database):
    view = advance(create(120),120)
    events = read(view.session_id,'analysis?at_second=120').json()['events']
    second = next(e for e in events if e['period']==2 and e['tick']>60)
    NativeEvent.model_validate(second)
    with pytest.raises(ValidationError):
        NativeEvent.model_validate({**second,'period':1})
    first = events[0]
    with pytest.raises(ValidationError):
        NativeEvent.model_validate({**first,'period':2})
    with pytest.raises(ValidationError):
        NativeEvent.model_validate({**first,'halftime_tick':2700})
    with pytest.raises(ValidationError):
        MatchEvent.model_validate({**second,'schema_version':'1.0','source_type':'synthetic-generator','generated_at_utc':'2000-01-01T00:00:00Z'})
    assert client.get(f'/api/sandbox/sessions/{view.session_id}/analysis?at_second=120',headers=HEADERS).status_code==422


def test_private_cutoffs_concurrent_reads_and_stale_mutation(database):
    view = advance(create(120),120)
    sid = view.session_id
    for path in ['analysis?at_second=120','pass-difficulty?at_second=120','analysis-export?at_second=120']:
        assert read(sid,path,{}).status_code==403
        assert read(sid,path,{'Authorization':'Bearer other-owner-token-at-least-32-characters'}).status_code==404
    with ThreadPoolExecutor(max_workers=4) as pool:
        replies=list(pool.map(lambda tick:read(sid,f'analysis?at_second={tick}'),[0,59,60,120]))
    for cutoff, reply in zip([0,59,60,120],replies):
        assert reply.status_code==200
        assert reply.json()['at_second']==cutoff
        assert all(e['tick']<=cutoff for e in reply.json()['events'])
    assert read(sid,'passes/missing/difficulty?at_second=120').status_code==404
    assert read(sid,'analysis?at_second=-1').status_code==422
    assert client.get(f'/api/matches/{sid}').status_code==404
    stale=client.post(f'/api/sandbox/sessions/{sid}/commands',headers=HEADERS,json={
        'operation_id':'stale-native','kind':'step','ticks':1,'expected_revision':0})
    assert stale.status_code==409
