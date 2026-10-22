import copy
import sqlite3
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.database_backup import copy_database
from app.simulator import generate
from app.storage import connect, database_path


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


def test_shared_demo_producer_token_and_audit_actor(isolated_application_environment, monkeypatch):
    monkeypatch.setenv("PULSE_STUDIO_PRODUCER_TOKEN", TOKEN)
    remote = TestClient(app, base_url="https://demo.example", client=("203.0.113.7", 443))
    assert remote.get(BASE).status_code == 403
    producer = {"Authorization": f"Bearer {TOKEN}"}
    original = remote.get(BASE, headers=producer)
    assert original.status_code == 200
    cues = [{key: cue[key] for key in ("cue_id", "order", "start_match_second", "show_duration_seconds", "priority", "visual_template", "safe_area", "transition")}
            for cue in original.json()["cues"]]
    saved = remote.put(BASE, headers=producer, json={"expected_revision": 0, "cues": cues})
    assert saved.status_code == 200
    assert saved.json()["audit_history"][0]["actor"] == "producer_token"
    approved = remote.post(f"{BASE}/approve", headers=producer, json={"expected_revision": 1})
    assert approved.status_code == 200
    assert remote.get(f"{BASE}/export", headers=producer).status_code == 200
    assert remote.get(BASE, headers={"Authorization": "Bearer wrong-token"}).status_code == 403


def test_public_readonly_never_accepts_studio_producer_token(isolated_application_environment, monkeypatch):
    monkeypatch.setenv("PULSE_DEPLOYMENT_MODE", "public-readonly")
    monkeypatch.setenv("PULSE_STUDIO_PRODUCER_TOKEN", TOKEN)
    remote = TestClient(app, base_url="https://demo.example", client=("203.0.113.7", 443))
    assert remote.get(BASE, headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 403


def _import_studio_match():
    match, events = generate("comeback")
    match = match.model_copy(update={"match_id": "studio-backup-match"})
    events = [event.model_copy(update={"match_id": match.match_id}) for event in events]
    response = client.post("/api/data-hub/import", headers=headers, json={
        "schema_version": "pulse-xi-match-package/1",
        "match": match.model_dump(mode="json"),
        "events": [event.model_dump(mode="json", by_alias=True) for event in events],
        "provenance": {"source": "studio backup regression"},
    })
    assert response.status_code == 200, response.text
    return match, events


def _save_and_approve_studio(match_id: str):
    base = f"/api/matches/{match_id}/studio"
    original = client.get(base, headers=headers)
    assert original.status_code == 200, original.text
    cues = [{key: cue[key] for key in ("cue_id", "order", "start_match_second", "show_duration_seconds", "priority", "visual_template", "safe_area", "transition")}
            for cue in original.json()["cues"]]
    saved = client.put(base, headers=headers, json={"expected_revision": 0, "cues": cues})
    assert saved.status_code == 200, saved.text
    approved = client.post(f"{base}/approve", headers=headers, json={"expected_revision": 1})
    assert approved.status_code == 200, approved.text
    return client.get(f"{base}/export?revision=1", headers=headers).json()


def test_studio_schema_three_backup_restores_match_and_immutable_approval(isolated_application_environment, monkeypatch, tmp_path):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", TOKEN)
    monkeypatch.setenv("PULSE_ENABLE_LOCAL_DATA_ADMIN", "1")
    match, events = _import_studio_match()
    expected = _save_and_approve_studio(match.match_id)
    with connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3

    backup, restored = tmp_path / "studio-backup.sqlite", tmp_path / "studio-restored.sqlite"
    report = copy_database(database_path(), backup)
    assert report["schema_version"] == 3
    assert report["matches"] == 1 and report["events"] == len(events)
    copy_database(backup, restored, report["sha256"])
    monkeypatch.setenv("PULSE_DB_PATH", str(restored))

    studio = client.get(f"/api/matches/{match.match_id}/studio", headers=headers)
    assert studio.status_code == 200, studio.text
    assert studio.json()["approved_revision"] == 1
    assert client.get(f"/api/matches/{match.match_id}/studio/export?revision=1", headers=headers).json() == expected
    assert client.get(f"/api/matches/{match.match_id}/events").json() == [event.model_dump(mode="json", by_alias=True) for event in events]
    with sqlite3.connect(restored) as db:
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_schema_two_with_preexisting_studio_tables_is_a_valid_legacy_backup(isolated_application_environment, monkeypatch, tmp_path):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", TOKEN)
    monkeypatch.setenv("PULSE_ENABLE_LOCAL_DATA_ADMIN", "1")
    match, _ = _import_studio_match()
    expected = _save_and_approve_studio(match.match_id)
    with connect() as db:
        db.execute("PRAGMA user_version=2")

    backup, restored = tmp_path / "legacy-studio.sqlite", tmp_path / "legacy-studio-restored.sqlite"
    report = copy_database(database_path(), backup)
    assert report["schema_version"] == 2
    copy_database(backup, restored, report["sha256"])
    monkeypatch.setenv("PULSE_DB_PATH", str(restored))
    response = client.get(f"/api/matches/{match.match_id}/studio/export?revision=1", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == expected
    with connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3


def test_backup_rejects_corrupt_studio_payload_and_unknown_schema_objects(isolated_application_environment, monkeypatch, tmp_path):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", TOKEN)
    monkeypatch.setenv("PULSE_ENABLE_LOCAL_DATA_ADMIN", "1")
    match, _ = _import_studio_match()
    _save_and_approve_studio(match.match_id)
    with connect() as db:
        db.execute("PRAGMA ignore_check_constraints=ON")
        db.execute("UPDATE director_studio_state SET cues_json='not-json'")
    destination = tmp_path / "corrupt-studio.sqlite"
    with pytest.raises(ValueError, match="draft"):
        copy_database(database_path(), destination)
    assert not destination.exists()
    with connect() as db:
        db.execute("CREATE TABLE unknown_payload (value TEXT)")
    with pytest.raises(ValueError, match="unexpected schema objects"):
        copy_database(database_path(), tmp_path / "unknown-schema.sqlite")


def test_deleting_imported_match_removes_studio_identity_and_approval(isolated_application_environment, monkeypatch):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", TOKEN)
    monkeypatch.setenv("PULSE_ENABLE_LOCAL_DATA_ADMIN", "1")
    match, _ = _import_studio_match()
    _save_and_approve_studio(match.match_id)
    entry = next(item for item in client.get("/api/data-hub").json()["matches"]
                 if item["match"]["match_id"] == match.match_id)
    response = client.post(f"/api/data-hub/matches/{match.match_id}/lifecycle", headers=headers, json={
        "action": "delete", "confirm_match_id": match.match_id,
        "generation": entry["lifecycle"]["generation"], "revision": entry["lifecycle"]["revision"],
    })
    assert response.status_code == 200, response.text
    with connect() as db:
        for table in ("director_studio_state", "director_studio_approvals", "director_studio_audit"):
            assert db.execute(f"SELECT COUNT(*) FROM {table} WHERE match_id=?", (match.match_id,)).fetchone()[0] == 0
    assert client.get(f"/api/matches/{match.match_id}/studio", headers=headers).status_code == 404
