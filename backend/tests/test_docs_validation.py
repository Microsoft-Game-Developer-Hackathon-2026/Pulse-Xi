import sys
from tempfile import TemporaryDirectory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from validate_docs import anchors, contains_credential, validate_api_examples, validate_markdown


def test_anchor_slugs_and_duplicate_headings():
    assert anchors('# Intro\n\n# Intro\n\n## A `code` & test') == {'intro', 'intro-1', 'a-code-test'}


def test_credential_scan_checks_nested_examples():
    assert contains_credential({'metadata': [{'provider': {'api_token': 'private'}}]})
    assert not contains_credential({'match_id': 'synthetic-7', 'events': [{'type': 'pass'}]})


def test_repository_markdown_links_and_api_examples():
    root = Path(__file__).resolve().parents[2]
    assert validate_markdown(root) == []
    assert validate_api_examples(root) == []


def test_markdown_validator_reports_broken_file_and_anchor_links():
    with TemporaryDirectory() as folder:
        root = Path(folder)
        (root / 'index.md').write_text('# Present\n\n[valid](target.md#target) [bad](absent.md) [bad anchor](target.md#missing)\n')
        (root / 'target.md').write_text('# Target\n')
        errors = validate_markdown(root)
        assert any('missing local link target: absent.md' in error for error in errors)
        assert any('missing Markdown anchor: target.md#missing' in error for error in errors)


def test_runtime_database_path_is_not_required_in_clean_checkout(tmp_path):
    (tmp_path / 'README.md').write_text('The database is `backend/data/pulse_xi.sqlite`.\n')
    assert validate_markdown(tmp_path) == []


def test_generated_build_files_and_browser_artifacts_are_not_source_docs(tmp_path):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'deploy.md').write_text(
        'A failed readiness check means `frontend/dist/index.html` is absent.\n'
    )
    generated_docs = tmp_path / 'frontend' / 'test-results' / 'audit-tools'
    generated_docs.mkdir(parents=True)
    (generated_docs / 'README.md').write_text('[stale](../../../missing-tool.py)\n')
    assert validate_markdown(tmp_path) == []


def test_documented_health_openapi_and_fixture_read_smoke(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'matches.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(tmp_path / 'runtime.sqlite'))
    with TestClient(app) as client:
        assert client.get('/health').json()['simulation'] == 'synthetic'
        openapi = client.get('/openapi.json')
        assert openapi.status_code == 200
        assert openapi.json()['openapi'].startswith('3.')
        match = client.get('/api/matches/comeback-1107')
        assert match.status_code == 200 and match.json()['synthetic'] is True


def test_clean_graphics_artifact_inventories_match_checkout_bytes():
    import hashlib
    import json

    root = Path(__file__).resolve().parents[2] / 'docs/audit-evidence/graphics-rtx5070-clean-900-2026-10-23'
    inventories = list(root.glob('*/artifact-inventory.json'))
    assert len(inventories) >= 2
    for inventory in inventories:
        rows = json.loads(inventory.read_text(encoding='utf-8'))
        names = [row['file'] for row in rows]
        assert len(names) == len(set(names))
        assert {'report.json', 'build-hashes.json'} <= set(names)
        assert set(names) == {p.name for p in inventory.parent.iterdir()
                              if p.is_file() and p.name not in {'artifact-inventory.json', 'README.md'}}
        for row in rows:
            assert Path(row['file']).name == row['file']
            content = (inventory.parent / row['file']).read_bytes()
            assert len(content) == row['bytes']
            assert hashlib.sha256(content).hexdigest() == row['sha256'], str(inventory.parent / row['file'])
