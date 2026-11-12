"""Alembic migration safety tests using disposable SQLite databases."""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

def run_upgrade(db_path: Path, revision="head"):
    env = dict(os.environ)
    env.update({
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "test-only-secret-value-with-at-least-32-chars",
        "ADMIN_PASSWORD": "test-only-admin-password-12345",
    })
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
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
        assert {"users", "events", "categories", "login_attempts", "alembic_version"} <= tables
        cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
        assert {"title", "datetime", "category_id", "payment_url"} <= cols
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0002_login_attempts"
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


def test_login_counter_migration_preserves_existing_users(tmp_path):
    db = tmp_path / "versioned.db"
    initial = run_upgrade(db, "0001_initial")
    assert initial.returncode == 0, initial.stderr
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO users (id, username, password_hash) VALUES (1, 'existing', 'test-hash')")
    upgraded = run_upgrade(db)
    assert upgraded.returncode == 0, upgraded.stderr
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT id, username, password_hash FROM users").fetchall() == [(1, "existing", "test-hash")]
        assert conn.execute("SELECT COUNT(*) FROM login_attempts").fetchone()[0] == 0
        conn.execute("INSERT INTO login_attempts VALUES ('account:test-only-key', 1, 1800000000)")
    again = run_upgrade(db)
    assert again.returncode == 0, again.stderr
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT attempts FROM login_attempts").fetchone()[0] == 1
