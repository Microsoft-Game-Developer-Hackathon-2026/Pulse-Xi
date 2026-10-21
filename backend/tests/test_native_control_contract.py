"""Compatibility only: no public or private Control vs Chaos runtime route is added."""
import pytest

from app.analytics import control_chaos_at
from app.evidence import verify_control_turning_point
from app.sandbox import storage
from app.sandbox.analysis import source
from app.sandbox.engine import build_scenario
from app.sandbox.models import ScenarioConfig, Command


@pytest.mark.parametrize('duration', [60,600,1800])
def test_existing_control_calculations_accept_native_source_contract(tmp_path, monkeypatch, duration):
    monkeypatch.setenv('PULSE_DB_PATH',str(tmp_path/'matches.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH',str(tmp_path/'runtime.sqlite'))
    scenario=storage.save_scenario('alice',build_scenario(ScenarioConfig(seed=7,duration_seconds=duration)))
    view=storage.create_session('alice','native-control',scenario.scenario_id)
    while view.tick<duration:
        storage.mutate('alice',view.session_id,Command(operation_id=f'advance-{view.revision}',
            expected_revision=view.revision,kind='step',ticks=min(300,duration-view.tick)))
        view=storage.get_runtime('alice',view.session_id)
    cutoff=duration-1
    captured,match,events=source('alice',view.session_id,cutoff,'native')
    packet=control_chaos_at(match,events,cutoff,300)
    assert packet.match_id==view.session_id and packet.at_second==cutoff
    assert packet.window.start_second==max(0,cutoff-300)
    assert packet.window.end_second==cutoff
    if cutoff<600:
        assert packet.previous_window is None
    else:
        assert packet.previous_window is not None
    for team in (match.home,match.away):
        passes=packet.teams[team.team_id].retention['pass_attempts']
        expected=[e.event_id for e in events if e.team_id==team.team_id and e.event_type=='pass'
                  and packet.window.start_second<e.match_second<=cutoff]
        assert passes.value==len(expected)
        assert passes.supporting_event_ids==expected
        assert all(event_id.startswith(view.session_id+'-') for event_id in passes.supporting_event_ids)
    assert all(verify_control_turning_point(claim,match,events,cutoff,300)
               for claim in packet.interpretation.turning_points)
    assert captured.event_hash==storage.get_runtime('alice',view.session_id).event_hash
