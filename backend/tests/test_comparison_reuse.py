"""A successful independent audit must not trigger another full history replay."""
from app.sandbox import control, experiments
from app.sandbox.engine import digest
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
