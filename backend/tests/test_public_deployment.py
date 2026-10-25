import asyncio
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import deployment, main


@pytest.fixture
def public_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PULSE_DEPLOYMENT_MODE", "public-readonly")
    monkeypatch.setenv("PULSE_RUNTIME_DRIVER", "0")
    monkeypatch.setenv("PULSE_DB_PATH", str(tmp_path / "imported.sqlite"))
    monkeypatch.setenv("PULSE_RUNTIME_DB_PATH", str(tmp_path / "runtime.sqlite"))
    for name in ("PULSE_RUNTIME_TOKEN", "PULSE_RUNTIME_TOKENS", "PULSE_IMPORT_TOKEN",
                 "PULSE_FOUNDRY_ADMIN_TOKEN", "PULSE_STUDIO_PRODUCER_TOKEN",
                 "FOUNDRY_PROJECT_ENDPOINT", "FOUNDRY_MODEL",
                 "PULSE_ENABLE_LOCAL_DATA_ADMIN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PULSE_ENABLE_FOUNDRY", "false")
    return tmp_path


def test_local_mode_remains_default(monkeypatch):
    monkeypatch.delenv("PULSE_DEPLOYMENT_MODE", raising=False)
    deployment.validate_deployment_config()


@pytest.mark.parametrize("name,value", [
    ("PULSE_RUNTIME_TOKEN", "x" * 40), ("PULSE_RUNTIME_TOKENS", '{"operator":"' + "x" * 40 + '"}'),
    ("PULSE_IMPORT_TOKEN", "x" * 40), ("PULSE_FOUNDRY_ADMIN_TOKEN", "x" * 40),
    ("PULSE_STUDIO_PRODUCER_TOKEN", "x" * 40),
    ("FOUNDRY_PROJECT_ENDPOINT", "https://example.invalid"), ("FOUNDRY_MODEL", "model"),
])
def test_public_mode_rejects_privileged_or_provider_configuration(public_env, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match="cannot be configured"):
        deployment.validate_deployment_config()


def test_public_mode_requires_distinct_disposable_database_paths(public_env, monkeypatch):
    monkeypatch.setenv("PULSE_DB_PATH", str(Path(tempfile.gettempdir()).parent / "outside.sqlite"))
    with pytest.raises(RuntimeError, match="temporary directory"):
        deployment.validate_deployment_config()
    monkeypatch.setenv("PULSE_DB_PATH", str(public_env / "same.sqlite"))
    monkeypatch.setenv("PULSE_RUNTIME_DB_PATH", str(public_env / "same.sqlite"))
    with pytest.raises(RuntimeError, match="must be distinct"):
        deployment.validate_deployment_config()


@pytest.mark.parametrize("name,value,expected", [
    ("PULSE_ENABLE_FOUNDRY", "true", "requires PULSE_ENABLE_FOUNDRY to be false"),
    ("PULSE_RUNTIME_DRIVER", "1", "requires PULSE_RUNTIME_DRIVER=0"),
    ("PULSE_ENABLE_LOCAL_DATA_ADMIN", "1", "cannot enable local dataset administration"),
])
def test_public_mode_rejects_enabled_runtime_or_inference(public_env, monkeypatch, name, value, expected):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=expected):
        deployment.validate_deployment_config()


def test_public_demo_serves_seeded_reads_and_allows_bounded_generation(public_env, monkeypatch):
    dist = public_env / "frontend-dist"
    dist.mkdir()
    (dist / "assets").mkdir()
    (dist / "index.html").write_text("<html>test</html>", encoding="utf-8")
    monkeypatch.setattr(main, "DIST", dist)
    with TestClient(main.app) as client:
        fixtures = client.get("/api/matches")
        assert fixtures.status_code == 200
        assert {item["match_id"] for item in fixtures.json()} >= {"comeback-1107", "high-press-2209"}
        events = client.get("/api/matches/comeback-1107/events?limit=2")
        assert events.status_code == 200 and len(events.json()) == 2
        generated = client.post("/api/matches/generate", json={"seed": 123})
        assert generated.status_code == 200 and generated.json()["match_id"] == "custom-123"
        ambiguous = client.post("/api/matches/generate", content=b'{"seed":1,"seed":2}',
                                headers={"Content-Type": "application/json"})
        assert ambiguous.status_code == 400
        assert client.post("/api/matches/generate", json={"seed": 2_147_483_648}).status_code == 422
        recap = client.post("/api/matches/comeback-1107/recap?at_second=5400")
        assert recap.status_code == 200 and recap.json()["provider"] == "verified_rule_based_templates"
        assert client.post("/api/matches/generate", json={"seed": -1}).status_code == 422
        health = client.get("/health")
        assert health.status_code == 200 and health.json() == {
            "status": "ok", "simulation": "synthetic", "narrative_provider": "not_configured",
        }
        assert client.get("/ready").json() == {"status": "ready"}


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/api/matches/ingest", {}),
    ("post", "/api/data-hub/preview", {}),
    ("post", "/api/data-hub/import", {}),
    ("post", "/api/data-hub/recover", {}),
    ("post", "/api/data-hub/matches/example/lifecycle", {}),
    ("post", "/api/sandbox/scenarios", {}),
    ("post", "/api/sandbox/sessions/example/commands", {}),
    ("post", "/api/insights/example/agent-run", {}),
    ("delete", "/api/data-hub/example", None),
    ("put", "/api/data-hub/example", {}),
    ("patch", "/api/data-hub/example", {}),
])
def test_public_demo_denies_mutations_even_with_privileged_headers(public_env, method, path, payload):
    with TestClient(main.app) as client:
        response = client.request(method.upper(), path, json=payload, headers={
            "Authorization": "Bearer " + "x" * 40, "X-Pulse-Deletion-ID": "a" * 32,
        })
        assert response.status_code == 403
        assert response.headers["cache-control"] == "no-store"


def test_public_demo_hides_operator_state_and_rejects_runtime_websocket(public_env):
    with TestClient(main.app) as client:
        assert client.get("/api/sandbox/sessions").status_code == 403
        assert client.get("/api/agent-traces").status_code == 403
        assert client.get("/openapi.json").status_code == 403
        assert client.get("/docs").status_code == 403
        with pytest.raises(WebSocketDisconnect) as closed:
            with client.websocket_connect("/api/sandbox/sessions/example/observe"):
                pass
        assert closed.value.code == 1008


def test_public_demo_keeps_same_origin_cors_and_reconstructs_fixtures_after_store_loss(public_env):
    with TestClient(main.app) as client:
        response = client.get("/api/matches/comeback-1107/events?limit=3", headers={"Origin": "https://untrusted.example"})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
        first = response.json()
    assert not Path(os.environ["PULSE_DB_PATH"]).exists()
    assert not Path(os.environ["PULSE_RUNTIME_DB_PATH"]).exists()
    for name in ("PULSE_DB_PATH", "PULSE_RUNTIME_DB_PATH"):
        path = Path(os.environ[name])
        if path.exists():
            path.unlink()
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(path) + suffix)
            if sidecar.exists():
                sidecar.unlink()
    with TestClient(main.app) as client:
        response = client.get("/api/matches/comeback-1107/events?limit=3")
        assert response.status_code == 200 and response.json() == first


def test_public_demo_never_reads_imported_library_or_match_records(public_env, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("public demo attempted to read imported SQLite records")

    monkeypatch.setattr(main, "imported_matches", forbidden)
    monkeypatch.setattr(main, "imported_match", forbidden)
    monkeypatch.setattr(main, "library_entries", forbidden)
    monkeypatch.setattr(main, "imported_snapshot", forbidden)
    with TestClient(main.app) as client:
        assert len(client.get("/api/matches").json()) == 3
        assert client.get("/api/data-hub").status_code == 200
        assert client.get("/api/matches/not-a-seed").status_code == 404
        assert client.get("/api/matches/comeback-1107/package").status_code == 200


def test_public_boundary_does_not_block_local_mode_writes(monkeypatch):
    monkeypatch.delenv("PULSE_DEPLOYMENT_MODE", raising=False)
    scope = {"type": "http", "method": "POST", "path": "/api/matches/ingest"}
    called = []

    async def app(scope, receive, send):
        called.append(True)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        pass

    asyncio.run(deployment.PublicDemoBoundary(app)(scope, receive, send))
    assert called


def test_public_demo_highlights_are_read_only_bounded_and_deterministic(public_env):
    path = "/api/matches/comeback-1107/highlights"
    with TestClient(main.app) as client:
        first = client.get(path)
        assert first.status_code == 200 and first.json()["provenance"]["external_assets"] == []
        # Reads are unmetered like the other GET analytics, so the response must stay small and
        # identical for identical input rather than depend on caller-controlled work.
        assert len(first.content) < 20_000
        assert {client.get(path).json()["manifest_sha256"] for _ in range(20)} == {first.json()["manifest_sha256"]}
        # Caller-controlled work is bounded at the validation layer.
        assert client.get(path + "?limit=0").status_code == 422
        assert client.get(path + "?limit=13").status_code == 422
        assert client.get(path + "?at_second=5401").status_code == 422
        assert client.get(path + "?limit=12&at_second=5400").status_code == 200
        assert client.get("/api/matches/not-a-match/highlights").status_code == 404
        # No write method is reachable, even with privileged-looking headers.
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            denied = client.request(method, path, json={}, headers={"Authorization": "Bearer " + "x" * 40})
            assert denied.status_code == 403 and denied.headers["cache-control"] == "no-store"


def test_deployment_mode_flag_is_public_readable_and_reveals_nothing_else(public_env, monkeypatch):
    with TestClient(main.app) as client:
        response = client.get("/api/deployment")
        assert response.status_code == 200 and response.json() == {"mode": "public-readonly"}
        assert client.post("/api/deployment", json={}).status_code == 403
    monkeypatch.setenv("PULSE_DEPLOYMENT_MODE", "local")
    assert TestClient(main.app).get("/api/deployment").json() == {"mode": "local"}
