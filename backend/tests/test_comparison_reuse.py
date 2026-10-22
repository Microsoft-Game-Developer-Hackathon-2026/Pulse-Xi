"""A successful independent audit must not trigger another full history replay."""
import pytest

from app.sandbox import control, experiments, storage
from app.sandbox.engine import EngineError, digest
from app.sandbox.models import Command, ExperimentManifest
from test_runtime_integration import database, checkpoint, experiment_request, finish_experiment


def test_comparison_returns_the_same_verified_snapshot_without_post_audit_replay(database, monkeypatch):
    root = checkpoint()
    job = finish_experiment(control.create_experiment('alice', experiment_request(root)))
    expected = experiments.bundle('alice', job.experiment_id).comparison_hash
    verify = experiments.verify_bundle
    audits = []

    def audited(bundle):
        result = verify(bundle)
        assert result.verified
        audits.append(bundle.comparison_hash)

        def redundant_replay(*args):
            raise AssertionError('Verified comparison must not reconstruct histories a fourth time')

        monkeypatch.setattr(experiments, 'apply_command', redundant_replay)
        return result

    monkeypatch.setattr(experiments, 'verify_bundle', audited)
    actual = experiments.comparison('alice', job.experiment_id)
    assert audits == [expected]
    assert digest(actual) == expected


def test_calculation_reuses_checkpoint_but_full_verifier_still_rejects_bad_prefix(database, monkeypatch):
    root = checkpoint()
    job = finish_experiment(control.create_experiment('alice', experiment_request(root)))
    original = experiments.bundle('alice', job.experiment_id)
    apply = experiments.apply_command

    def suffix_only(state, command):
        assert command.expected_revision >= root.revision, 'Calculation must not replay the shared checkpoint prefix'
        return apply(state, command)

    monkeypatch.setattr(experiments, 'apply_command', suffix_only)
    assert digest(experiments.comparison('alice', job.experiment_id)) == original.comparison_hash
    # The independent manifest verifier retains its own complete kickoff replay.
    forged = original.model_dump(mode='json')
    forged['branches'][0]['operations'][0]['state_hash'] = '0' * 64
    rejected = experiments.verify_bundle(experiments.ExperimentBundle.model_validate(forged))
    assert not rejected.verified
    assert rejected.component == 'branches[0].operation.state_hash'


def test_current_trials_avoid_history_reconstruction_but_extended_branches_keep_original_boundary(database, monkeypatch):
    root = checkpoint()
    job = finish_experiment(control.create_experiment('alice', experiment_request(root)))
    historical = storage.manifest_at
    reads = []

    def counted(owner, session_id, revision):
        reads.append(session_id)
        return historical(owner, session_id, revision)

    monkeypatch.setattr(storage, 'manifest_at', counted)
    expected = experiments.comparison('alice', job.experiment_id)
    assert reads == []
    branch = storage.get_runtime('alice', job.branches[0])
    storage.mutate('alice', branch.session_id, Command(operation_id='after-trial',
        expected_revision=branch.revision, kind='step', ticks=1))
    actual = experiments.comparison('alice', job.experiment_id)
    assert actual == expected
    assert reads == [branch.session_id]


def test_current_manifest_fast_path_does_not_bypass_corrupt_prefix_rejection(database, monkeypatch):
    root = checkpoint()
    job = finish_experiment(control.create_experiment('alice', experiment_request(root)))
    original = storage.manifest

    def corrupted(owner, session_id):
        value = original(owner, session_id).model_dump(mode='json')
        if session_id == job.branches[0]:
            value['operations'][0]['state_hash'] = '0' * 64
        return ExperimentManifest.model_validate(value)

    monkeypatch.setattr(storage, 'manifest', corrupted)
    with pytest.raises(EngineError, match='experiment_diverged'):
        experiments.comparison('alice', job.experiment_id)
