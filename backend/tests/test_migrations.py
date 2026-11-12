"""Alembic migration safety tests using disposable SQLite databases."""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

def run_upgrade(db_path: Path):
    env = dict(os.environ)
    env.update({
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "test-only-secret-value-with-at-least-32-chars",
        "ADMIN_PASSWORD": "test-only-admin-password-12345",
    })
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND, env=env, text=True, capture_output=True, check=False,
    )

def test_fresh_database_migrates_and_repeat_is_safe(tmp_path):
    db = tmp_path / "fresh.db"
    first = run_upgrade(db)
    assert first.returncode == 0, first.stderr
    with sqlite3.connect(db) as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        assert {"users", "events", "categories", "alembic_version"} <= tables
        cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
        assert {"title", "datetime", "category_id", "payment_url"} <= cols
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0001_initial"
    again = run_upgrade(db)
    assert again.returncode == 0, again.stderr

def test_legacy_database_is_not_modified(tmp_path):
    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO users (id, name) VALUES (1, 'existing')")
    result = run_upgrade(db)
    assert result.returncode != 0
    assert "Unversioned existing Afisha tables" in result.stderr
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name FROM users WHERE id=1").fetchone()[0] == "existing"
        cols = [row[1] for row in conn.execute("PRAGMA table_info(users)")]
        assert cols == ["id", "name"]
