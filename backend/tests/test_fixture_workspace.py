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
def test_generated_replay_proof_is_match_scoped_and_cutoff_checked():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    assert client.post('/api/matches/generate', json={'seed': 0}).status_code == 200
    insights = client.get('/api/matches/custom-0/insights').json()
    assert insights
    insight = insights[-1]
    path = f"/api/matches/custom-0/insights/{insight['insight_id']}/evidence"
    result = client.get(f"{path}?at_second={insight['match_second']}")
    assert result.status_code == 200, result.text
    packet = result.json()
    assert packet['insight'] == insight
    assert {event['event_id'] for event in packet['source_events']} == set(insight['supporting_event_ids'])
    assert all(event['match_id'] == 'custom-0' and event['match_second'] <= insight['match_second'] for event in packet['source_events'])
    assert client.get(f"{path}?at_second={insight['match_second'] - 1}").status_code == 404
    assert client.get(path.replace('matches/custom-0/', 'matches/comeback-1107/')).status_code == 404
    assert client.get(f'{path}?at_second=5401').status_code == 422

