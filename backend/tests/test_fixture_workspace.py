from fastapi.testclient import TestClient

from app.main import app


def test_workspace_seed_generation_is_reproducible_and_validated():
    client = TestClient(app)
    for seed in (0, 4411, 2_147_483_647):
        first = client.post("/api/matches/generate", json={"seed": seed})
        assert first.status_code == 200
        match_id = first.json()["match_id"]
        original = client.get(f"/api/matches/{match_id}/events?limit=1000").json()
        assert client.post("/api/matches/generate", json={"seed": seed}).json() == first.json()
        assert client.get(f"/api/matches/{match_id}/events?limit=1000").json() == original
        assert client.get(f"/api/matches/{match_id}/metrics?at_second=0").json()["home"]["goals"] == 0
    for seed in (-1, 2_147_483_648):
        assert client.post("/api/matches/generate", json={"seed": seed}).status_code == 422
