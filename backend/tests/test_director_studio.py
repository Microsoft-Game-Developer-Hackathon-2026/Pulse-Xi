import copy

from fastapi.testclient import TestClient

from app.main import app


TOKEN = "studio-test-token-at-least-32-characters"
client = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000))
headers = {"Authorization": f"Bearer {TOKEN}"}
BASE = "/api/matches/comeback-1107/studio"


def test_studio_requires_local_admin(isolated_application_environment, monkeypatch):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", TOKEN)
    monkeypatch.setenv("PULSE_ENABLE_LOCAL_DATA_ADMIN", "1")
    assert client.get(BASE).status_code == 403
    assert client.get(BASE, headers=headers).status_code == 200


def test_studio_draft_revision_approval_and_immutable_export(isolated_application_environment, monkeypatch):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", TOKEN)
    monkeypatch.setenv("PULSE_ENABLE_LOCAL_DATA_ADMIN", "1")
    original = client.get(BASE, headers=headers).json()
    assert original["revision"] == 0 and original["status"] == "draft"
    cues = original["cues"]
    payload = {"expected_revision": 0, "cues": [
        {key: cue[key] for key in ("cue_id", "order", "start_match_second", "show_duration_seconds", "priority", "visual_template", "safe_area", "transition")}
        for cue in cues
    ]}
    payload["cues"][0]["safe_area"] = "top_left"
    saved = client.put(BASE, headers=headers, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    assert saved.json()["cues"][0]["safe_area"] == "top_left"
    assert client.put(BASE, headers=headers, json=payload).status_code == 409

    approved = client.post(f"{BASE}/approve", headers=headers, json={"expected_revision": 1})
    assert approved.status_code == 200
    first_export = client.get(f"{BASE}/export?revision=1", headers=headers).json()
    assert first_export["schema_version"] == "director-studio-export/1"
    assert first_export["cues"][0]["safe_area"] == "top_left"
    assert client.get(f"{BASE}/export", headers=headers).json() == first_export

    second = copy.deepcopy(payload)
    second["expected_revision"] = 1
    second["cues"][0]["safe_area"] = "top_right"
    assert client.put(BASE, headers=headers, json=second).status_code == 200
    assert client.get(f"{BASE}/export?revision=1", headers=headers).json() == first_export
    assert client.get(BASE, headers=headers).json()["status"] == "draft"


def test_studio_rejects_unverified_unknown_and_overlapping_cues(isolated_application_environment, monkeypatch):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", TOKEN)
    monkeypatch.setenv("PULSE_ENABLE_LOCAL_DATA_ADMIN", "1")
    packet = client.get(BASE, headers=headers).json()
    cues = [{key: cue[key] for key in ("cue_id", "order", "start_match_second", "show_duration_seconds", "priority", "visual_template", "safe_area", "transition")}
            for cue in packet["cues"]]
    cues[0]["cue_id"] = "forged"
    assert client.put(BASE, headers=headers, json={"expected_revision": 0, "cues": cues}).status_code == 422
    cues[0]["cue_id"] = packet["cues"][0]["cue_id"]
    cues[1]["start_match_second"] = cues[0]["start_match_second"]
    response = client.put(BASE, headers=headers, json={"expected_revision": 0, "cues": cues})
    assert response.status_code == 422
    assert client.get(BASE, headers=headers).json()["revision"] == 0
