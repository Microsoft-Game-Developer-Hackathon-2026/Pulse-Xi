from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app.storage import connect, imported_matches


@pytest.mark.parametrize("attempt", range(3))
def test_concurrent_cold_database_migration(tmp_path, monkeypatch, attempt):
    monkeypatch.setenv("PULSE_DB_PATH", str(tmp_path / f"cold-{attempt}.sqlite"))
    barrier = Barrier(8)

    def read(_):
        barrier.wait(timeout=10)
        return imported_matches()

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(read, range(8))) == [[]] * 8
    with connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
