"""ProofTrail comparison tests use isolated durable sessions and verified checkpoint branches."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sandbox import storage
from app.sandbox.engine import build_scenario
from app.sandbox.models import Command, ScenarioConfig
from app.sandbox.prooftrail import build_sandbox_insight


@pytest.fixture
def runtime_db(tmp_path, monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(tmp_path / 'runtime.sqlite'))
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'matches.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', '{"alice":"' + 'a' * 32 + '"}')


def create(owner='alice'):
    scenario = storage.save_scenario(owner, build_scenario(ScenarioConfig(seed=7, duration_seconds=120)))
    return storage.create_session(owner, 'root', scenario.scenario_id)


def mutate(view, kind='step', operation_id=None, **kwargs):
    return storage.mutate('alice', view.session_id, Command(
        operation_id=operation_id or f'op-{view.revision}', expected_revision=view.revision,
        kind=kind, **kwargs))


def divergent_pair():
    baseline = create()
    baseline = mutate(baseline, ticks=20)
    baseline = mutate(baseline, 'checkpoint')
    checkpoint = storage.get_checkpoint('alice', baseline.checkpoint_id)
    branch = storage.create_session('alice', 'branch', checkpoint_id=checkpoint.checkpoint_id,
                                    expected_revision=baseline.revision)
    branch = mutate(branch, 'intervene', operation_id='press-change', team_id='home',
                    field='pressing', value=100, requested_tick=20)
    baseline = mutate(baseline, ticks=100)
    branch = mutate(branch, ticks=100)
    return baseline, branch, checkpoint


def test_verified_comparison_recalculates_cited_same_window_metrics(runtime_db):
    baseline, branch, checkpoint = divergent_pair()
    result = build_sandbox_insight(
        storage.get_runtime('alice', branch.session_id),
        storage.get_runtime('alice', baseline.session_id),
        storage.manifest('alice', branch.session_id),
        storage.manifest('alice', baseline.session_id),
        'press-change', 120, checkpoint.tick,
    )
    assert result.verification_result == 'verified'
    assert result.checkpoint_id == checkpoint.checkpoint_id
    assert result.branch_window.start_tick == result.baseline_window.start_tick == 21
    assert result.branch_window.end_tick == result.baseline_window.end_tick == 120
    assert result.intervention.operation_id == 'press-change'
    assert result.branch_verification == result.baseline_verification == 'verified'
    assert result.uncertainty.startswith('one deterministic trajectory')
    assert 'not a real-world causal prediction' in result.interpretation
    branch_citations = set(result.branch_before_window.evidence_event_ids + result.branch_window.evidence_event_ids)
    baseline_citations = set(result.baseline_before_window.evidence_event_ids + result.baseline_window.evidence_event_ids)
    assert all(value.startswith(branch.session_id + '-') for value in branch_citations)
    assert all(value.startswith(baseline.session_id + '-') for value in baseline_citations)


def test_prooftrail_api_is_owner_scoped_and_rejects_unrelated_baseline(runtime_db):
    baseline, branch, _ = divergent_pair()
    with TestClient(app) as client:
        headers = {'Authorization': 'Bearer ' + 'a' * 32}
        response = client.get(
            f'/api/sandbox/sessions/{branch.session_id}/prooftrail',
            params={'baseline_session_id': baseline.session_id, 'intervention_id': 'press-change', 'at_tick': 120},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()['verification_result'] == 'verified'
        assert client.get(
            f'/api/sandbox/sessions/{branch.session_id}/prooftrail',
            params={'baseline_session_id': baseline.session_id, 'intervention_id': 'press-change', 'at_tick': 120},
        ).status_code == 403

        unrelated = create()
        rejected = client.get(
            f'/api/sandbox/sessions/{branch.session_id}/prooftrail',
            params={'baseline_session_id': unrelated.session_id, 'intervention_id': 'press-change', 'at_tick': 120},
            headers=headers,
        )
        assert rejected.status_code == 422
        assert rejected.json()['detail']['code'] == 'baseline_not_ancestor'


def test_prooftrail_rejects_future_or_invalid_windows(runtime_db):
    baseline, branch, checkpoint = divergent_pair()
    with pytest.raises(Exception, match='invalid_comparison_window'):
        build_sandbox_insight(
            storage.get_runtime('alice', branch.session_id),
            storage.get_runtime('alice', baseline.session_id),
            storage.manifest('alice', branch.session_id),
            storage.manifest('alice', baseline.session_id),
            'press-change', 121, checkpoint.tick,
        )
