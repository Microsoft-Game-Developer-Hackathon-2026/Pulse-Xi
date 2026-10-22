import sys
from tempfile import TemporaryDirectory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from validate_docs import anchors, validate_api_examples, validate_markdown


def test_anchor_slugs_and_duplicate_headings():
    assert anchors('# Intro\n\n# Intro\n\n## A `code` & test') == {'intro', 'intro-1', 'a-code-test'}


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
