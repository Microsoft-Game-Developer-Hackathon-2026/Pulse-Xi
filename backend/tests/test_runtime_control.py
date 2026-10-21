import pytest
from app.sandbox import storage
from app.analytics import control_chaos_at
from app.evidence import verify_control_turning_point
from test_native_analysis import database, create, advance, client, HEADERS
from app.sandbox.native_analysis import project
from app.sandbox.models import Command
from concurrent.futures import ThreadPoolExecutor


@pytest.mark.parametrize('duration', [60,120,300,600,900,1800,5400])
def test_runtime_control_source_windows_and_read_only(database, duration):
    view = advance(create(duration), duration)
    match, events = project(view)
    for cutoff in sorted({0, duration//2, duration}):
        for window in [300,600,900]:
            response = client.get(f'/api/sandbox/sessions/{view.session_id}/control-chaos',
                params={'at_second':cutoff,'window_seconds':window}, headers=HEADERS)
            assert response.status_code == 200, response.text
            assert response.headers['cache-control'] == 'no-store'
            result = response.json()
            assert result['session_id'] == result['branch_id'] == view.session_id
            assert result['state_hash'] == view.state_hash and result['event_hash'] == view.event_hash
            assert result['revision'] == view.revision and result['event_cursor'] == view.event_cursor
            assert result['current_window_complete'] == (cutoff >= window)
            assert result['comparison_available'] == (cutoff >= 2*window)
            visible = [e for e in events if e.tick <= cutoff]
            expected = control_chaos_at(match, visible, cutoff, window)
            assert result['analysis'] == expected.model_dump(mode='json')
            for team in [match.home.team_id, match.away.team_id]:
                count = sum(e.team_id==team and e.event_type.value=='pass' and max(0,cutoff-window)<e.tick<=cutoff for e in visible)
                assert result['analysis']['teams'][team]['retention']['pass_attempts']['value'] == count
            for claim in expected.interpretation.turning_points:
                assert verify_control_turning_point(claim,match,visible,cutoff,window)
                assert all(id.startswith(view.session_id+'-') for id in claim.current_event_ids)
    assert storage.get_runtime('alice',view.session_id).state_hash == view.state_hash


def test_runtime_control_authorization_and_invalid_bounds(database, monkeypatch):
    view = advance(create(120),120)
    path = f'/api/sandbox/sessions/{view.session_id}/control-chaos'
    assert client.get(path,params={'at_second':120}).status_code in [401,403]
    assert client.get(path,params={'at_second':120},headers={'Authorization':'Bearer other-owner-token-at-least-32-characters'}).status_code==404
    for params in [{'at_second':121},{'at_second':-1},{'at_second':120,'window_seconds':30}]:
        assert client.get(path,params=params,headers=HEADERS).status_code==422
    assert client.get('/api/sandbox/sessions/missing/control-chaos?at_second=0',headers=HEADERS).status_code==404
    monkeypatch.delenv('PULSE_RUNTIME_TOKENS')
    monkeypatch.delenv('PULSE_RUNTIME_TOKEN',raising=False)
    assert client.get(path,params={'at_second':120},headers=HEADERS).status_code==503


def test_runtime_control_keeps_captured_boundary_when_engine_advances(database,monkeypatch):
    captured = advance(create(120),60)
    real_read = storage.get_runtime
    def read_then_progress(owner,session_id):
        view = real_read(owner,session_id)
        advance(view,120)
        return view
    monkeypatch.setattr(storage,'get_runtime',read_then_progress)
    result = client.get(f'/api/sandbox/sessions/{captured.session_id}/control-chaos?at_second=60',headers=HEADERS).json()
    assert result['revision']==captured.revision and result['authoritative_tick']==60
    assert result['state_hash']==captured.state_hash and result['event_hash']==captured.event_hash
    assert real_read('alice',captured.session_id).tick==120
    match,events = project(captured)
    assert result['analysis']==control_chaos_at(match,events,60,300).model_dump(mode='json')


def test_runtime_control_branch_capture_and_tampered_evidence(database):
    parent = advance(create(1800),600)
    checkpoint = storage.mutate('alice',parent.session_id,Command(operation_id='control-save',expected_revision=parent.revision,kind='checkpoint'))
    child = storage.create_session('alice','control-restore',checkpoint_id=checkpoint.checkpoint_id,expected_revision=checkpoint.revision)
    child = storage.get_runtime('alice',child.session_id)
    storage.mutate('alice',child.session_id,Command(operation_id='control-tactics',expected_revision=child.revision,kind='intervene',team_id='home',field='pressing',value=90,requested_tick=child.tick))
    child = advance(storage.get_runtime('alice',child.session_id),1800)
    parent = advance(storage.get_runtime('alice',parent.session_id),1800)
    def inspect(view):
        return client.get(f'/api/sandbox/sessions/{view.session_id}/control-chaos?at_second=1800',headers=HEADERS).json()
    with ThreadPoolExecutor(max_workers=4) as pool:
        packets = list(pool.map(inspect,[parent,child,parent,child]))
    assert packets[0] == packets[2] and packets[1] == packets[3]
    assert packets[0]['branch_id'] != packets[1]['branch_id']
    match,events = project(parent)
    claims = [(cutoff,point) for cutoff in range(600,1801,300)
              for point in control_chaos_at(match,events,cutoff,300).interpretation.turning_points]
    assert claims, 'real engine workload must exercise evidence verification'
    cutoff,point = claims[0]
    assert verify_control_turning_point(point,match,events,cutoff,300)
    forged = point.model_copy(update={'current_event_ids':[f'{child.session_id}-1']})
    assert not verify_control_turning_point(forged,match,events,cutoff,300)
