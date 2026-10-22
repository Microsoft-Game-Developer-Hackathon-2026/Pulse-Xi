"""Idle observers must retain live authorization without rebuilding large snapshots."""
import time
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.sandbox import storage
from app.sandbox.engine import EngineError
from app.sandbox.models import Command
from test_runtime_integration import database, runtime, command, TOKEN


def test_idle_observer_reuses_unchanged_boundary_and_delivers_next_revision(database, monkeypatch):
    root = runtime(duration=120)
    real = storage.get_runtime
    reads = []

    def counted(owner, session_id):
        reads.append(session_id)
        return real(owner, session_id)

    monkeypatch.setattr(storage, 'get_runtime', counted)
    with TestClient(app).websocket_connect(f'/api/sandbox/sessions/{root.session_id}/observe') as socket:
        socket.send_json({'token': TOKEN})
        assert socket.receive_json()['kind'] == 'snapshot'
        for _ in range(3):
            socket.send_text('ping')
        time.sleep(.6)
        assert reads == [root.session_id]
        command(root, ticks=10)
        message = socket.receive_json()
        assert message['kind'] == 'delta'
        assert message['view']['tick'] == 10
        assert len(reads) == 2


def test_owned_revision_covers_inherited_branch_and_idempotent_receipt(database):
    root = runtime(duration=120)
    assert storage.runtime_revision('alice', root.session_id) == 0
    advanced = command(root, ticks=10)
    saved = command(advanced, 'checkpoint')
    child = storage.create_session('alice', 'restore-boundary', checkpoint_id=saved.checkpoint_id,
                                   expected_revision=saved.revision)
    assert storage.runtime_revision('alice', child.session_id) == saved.revision
    request = Command(operation_id='same-step', expected_revision=child.revision, kind='step', ticks=1)
    first = storage.mutate('alice', child.session_id, request)
    assert storage.mutate('alice', child.session_id, request) == first
    assert storage.runtime_revision('alice', child.session_id) == child.revision + 1
    assert storage.runtime_revision('alice', root.session_id) == saved.revision
    with pytest.raises(EngineError, match='not_found'):
        storage.runtime_revision('bob', child.session_id)
    with pytest.raises(EngineError, match='not_found'):
        storage.runtime_revision('alice', 'missing')
