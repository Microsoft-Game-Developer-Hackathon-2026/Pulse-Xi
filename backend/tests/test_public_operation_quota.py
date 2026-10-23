"""A shared budget must not depend on spoofable client forwarding headers."""
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app import deployment
from concurrent.futures import ThreadPoolExecutor


def test_public_post_budget_is_shared_across_peers_and_forwarded_headers(monkeypatch):
    monkeypatch.setenv("PULSE_DEPLOYMENT_MODE", "public-readonly")
    monkeypatch.setattr(deployment, "PUBLIC_OPERATION_LIMIT", 3, raising=False)
    seen = []

    async def terminal(scope, receive, send):
        seen.append(scope["path"])
        await JSONResponse({"ok": True})(scope, receive, send)

    app = deployment.PublicDemoBoundary(terminal)
    a = TestClient(app, client=("proxy-a", 5000))
    b = TestClient(app, client=("proxy-b", 5000))
    for index in range(3):
        assert a.post("/api/matches/generate", headers={"X-Forwarded-For": f"192.0.2.{index}"}).status_code == 200
    response = b.post("/api/matches/comeback-1107/recap", headers={
        "Forwarded": "for=198.51.100.1", "X-Real-IP": "203.0.113.2"})
    assert response.status_code == 429
    assert response.headers["Cache-Control"] == "no-store"
    assert 1 <= int(response.headers["Retry-After"]) <= 60
    assert len(seen) == 3
    assert b.get("/health").status_code == 200
    assert b.get("/api/matches").status_code == 200
    assert b.post("/api/data-hub/import").status_code == 403


def test_window_reset_uses_monotonic_boundary_and_retry_after():
    now = [10.0]
    quota = deployment.PublicOperationQuota(limit=2, clock=lambda: now[0])
    assert [quota.retry_after(), quota.retry_after(), quota.retry_after()] == [0, 0, 60]
    now[0] = 69.5
    assert quota.retry_after() == 1
    now[0] = 70.0
    assert quota.retry_after() == 0
    assert quota.retry_after() == 0
    assert quota.retry_after() == 60
    now[0] = 0.0
    assert quota.retry_after() == 60  # a backwards clock never refills the budget


def test_concurrent_admission_cannot_overspend_shared_budget():
    quota = deployment.PublicOperationQuota(limit=30, clock=lambda: 0.0)
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: quota.retry_after(), range(200)))
    assert results.count(0) == 30
    assert results.count(60) == 170


def test_client_identity_cardinality_never_grants_more_requests(monkeypatch):
    monkeypatch.setenv("PULSE_DEPLOYMENT_MODE", "public-readonly")
    quota = deployment.PublicOperationQuota(limit=1, clock=lambda: 0.0)

    async def terminal(scope, receive, send):
        await JSONResponse({"ok": True})(scope, receive, send)

    client = TestClient(deployment.PublicDemoBoundary(terminal, quota=quota))
    assert client.post("/api/matches/generate").status_code == 200
    for i in range(100):
        assert client.post("/api/matches/generate", headers={
            "X-Forwarded-For": f"spoof-{i}", "Forwarded": f"for=spoof-{i}"}).status_code == 429
    assert quota.retry_after() == 60


def test_local_mode_and_readiness_do_not_consume_public_post_budget(monkeypatch):
    now = [0.0]
    quota = deployment.PublicOperationQuota(limit=1, clock=lambda: now[0])

    async def terminal(scope, receive, send):
        await JSONResponse({"ok": True})(scope, receive, send)

    client = TestClient(deployment.PublicDemoBoundary(terminal, quota=quota))
    monkeypatch.setenv("PULSE_DEPLOYMENT_MODE", "local")
    for _ in range(4):
        assert client.post("/api/matches/generate").status_code == 200
    monkeypatch.setenv("PULSE_DEPLOYMENT_MODE", "public-readonly")
    for path in ("/health", "/ready", "/", "/assets/app.js", "/api/matches"):
        assert client.get(path).status_code == 200
    assert client.post("/api/matches/generate").status_code == 200
    assert client.post("/api/matches/generate").status_code == 429
    now[0] = 60.0
    assert client.post("/api/matches/generate").status_code == 200
