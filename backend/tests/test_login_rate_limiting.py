"""Login budgets use disposable SQLite storage, never the configured database."""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import ExitStack
import multiprocessing

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.auth.auth import get_password_hash
from app.config import settings
from app.database import Base, get_db
from app.dependencies import get_login_limiter
from app.main import app
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.routers import auth
from app.services.login_limiter import LoginLimiter, LoginLimitExceeded, LoginLimiterUnavailable

PASSWORD = "local-test-login-password-42"


@pytest.fixture(scope="module")
def password_hash():
    return get_password_hash(PASSWORD)


@pytest.fixture
def storage(tmp_path, password_hash):
    engine = create_engine(f"sqlite:///{tmp_path / 'login.db'}", connect_args={"timeout": 15})
    # Schema creation is ONLY for this disposable test database. Migration tests
    # separately exercise the production Alembic revisions.
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        db.add_all([
            User(username="admin", password_hash=password_hash, is_admin=True),
            User(username="editor", password_hash=password_hash, is_admin=False),
        ])
    try:
        yield engine, sessions
    finally:
        engine.dispose()


@pytest.fixture
def clock():
    return [1_800_000_000.0]


@pytest.fixture
def limiter(storage, clock):
    return LoginLimiter(
        storage[0], secret=settings.secret_key, account_limit=3,
        source_limit=6, window_seconds=60, clock=lambda: clock[0],
    )


class PeerApp:
    """Set the transport peer, independently of any forwarded HTTP headers."""
    def __init__(self, peer):
        self.peer = peer

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope = dict(scope, client=(self.peer, 12345))
        await app(scope, receive, send)


@pytest.fixture
def clients(storage, limiter):
    previous = app.dependency_overrides.copy()

    def db_session():
        with storage[1]() as db:
            yield db

    app.dependency_overrides[get_db] = db_session
    app.dependency_overrides[get_login_limiter] = lambda: limiter
    with ExitStack() as stack:
        cache = {}

        def client(peer="198.51.100.1"):
            if peer not in cache:
                cache[peer] = stack.enter_context(TestClient(PeerApp(peer)))
            return cache[peer]

        try:
            yield client
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)


def login(client, username="admin", password="wrong-password", headers=None):
    return client.post("/auth/login", data={"username": username, "password": password}, headers=headers)


def counters(storage):
    with storage[0].connect() as conn:
        return conn.execute(select(LoginAttempt.__table__)).mappings().all()


def test_successful_login_keeps_token_contract(clients, storage):
    response = login(clients(), password=PASSWORD)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert jwt.decode(response.json()["access_token"], settings.secret_key, algorithms=[settings.algorithm])["sub"] == "admin"
    assert all(row["attempts"] == 0 for row in counters(storage))


def test_wrong_password_and_unknown_account_have_same_response(clients):
    known = login(clients())
    unknown = login(clients(), username="missing")
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json() == {"detail": "Incorrect username or password"}
    assert known.headers["www-authenticate"] == unknown.headers["www-authenticate"] == "Bearer"


def test_unknown_account_still_performs_password_verification(storage, monkeypatch):
    from app.auth import auth as password_auth

    calls = []
    original = password_auth.verify_password

    def verify(password, hashed):
        calls.append(hashed)
        return original(password, hashed)

    monkeypatch.setattr(password_auth, "verify_password", verify)
    with storage[1]() as db:
        assert password_auth.authenticate_user(db, "missing", "incorrect") is None
    assert len(calls) == 1


@pytest.mark.parametrize("username", ["admin", "missing"])
def test_account_limit_is_shared_across_sources(clients, storage, username):
    for i in range(3):
        assert login(clients(f"198.51.100.{i+1}"), username).status_code == 401
    blocked = login(clients("198.51.100.100"), username)
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"
    assert "access_token" not in blocked.json()
    # A denied account rolls back the source reservation as well.
    assert len(counters(storage)) == 4


def test_source_limit_covers_different_accounts(clients):
    for i in range(6):
        assert login(clients(), username=f"missing-{i}").status_code == 401
    blocked = login(clients(), username="editor", password=PASSWORD)
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"
    assert login(clients("198.51.100.2"), username="editor", password=PASSWORD).status_code == 200


def test_accounts_and_sources_are_independent_below_source_cap(clients):
    for _ in range(3):
        assert login(clients()).status_code == 401
    assert login(clients()).status_code == 429
    assert login(clients(), username="editor", password=PASSWORD).status_code == 200
    assert login(clients("198.51.100.2"), username="editor", password=PASSWORD).status_code == 200


def test_retry_after_decreases_and_window_expires_without_extension(clients, clock, storage):
    for _ in range(3):
        assert login(clients()).status_code == 401
    assert login(clients()).headers["retry-after"] == "60"
    clock[0] += 7
    assert login(clients()).headers["retry-after"] == "53"
    clock[0] += 53
    assert login(clients(), password=PASSWORD).status_code == 200
    assert all(row["attempts"] == 0 for row in counters(storage))


def test_success_refunds_own_attempt_without_erasing_previous_failures(clients, storage):
    for _ in range(2):
        assert login(clients()).status_code == 401
    assert login(clients(), password=PASSWORD).status_code == 200
    assert all(row["attempts"] == 2 for row in counters(storage))
    assert login(clients()).status_code == 401
    assert login(clients()).status_code == 429


def test_successes_cannot_clear_source_failures_from_other_accounts(clients):
    for i in range(5):
        assert login(clients(), username=f"missing-{i}").status_code == 401
    for _ in range(3):
        assert login(clients(), username="editor", password=PASSWORD).status_code == 200
    assert login(clients(), username="another-missing").status_code == 401
    assert login(clients(), username="yet-another").status_code == 429


def test_forged_forwarded_headers_cannot_rotate_source(clients):
    for i in range(7):
        response = login(clients("127.0.0.1"), username=f"missing-{i}", headers={
            "X-Forwarded-For": f"203.0.113.{i+1}",
            "X-Real-IP": f"203.0.113.{i+1}",
            "Forwarded": f"for=203.0.113.{i+1}",
            "X-Forwarded-Proto": "https",
        })
        assert response.status_code == (401 if i < 6 else 429)


def test_missing_store_table_fails_closed_before_password_check(clients, storage, monkeypatch):
    LoginAttempt.__table__.drop(storage[0])

    def forbidden_auth(*args):
        pytest.fail("Authentication ran without working shared counters")

    monkeypatch.setattr(auth, "authenticate_user", forbidden_auth)
    response = login(clients(), password=PASSWORD)
    assert response.status_code == 503
    assert response.headers["retry-after"] == "60"
    assert "access_token" not in response.json()


def test_store_connection_failure_fails_closed(clients, limiter, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def unavailable():
        raise OperationalError("connection", {}, Exception("unavailable"))

    monkeypatch.setattr(limiter.engine, "begin", unavailable)
    response = login(clients(), password=PASSWORD)
    assert response.status_code == 503
    assert "access_token" not in response.json()


def test_refund_failure_does_not_issue_token(clients, limiter, storage, monkeypatch):
    original = limiter.refund

    def unavailable(reservation):
        LoginAttempt.__table__.drop(storage[0])
        original(reservation)

    monkeypatch.setattr(limiter, "refund", unavailable)
    response = login(clients(), password=PASSWORD)
    assert response.status_code == 503
    assert "access_token" not in response.json()


def test_late_success_does_not_refund_a_new_window(limiter, clock, storage):
    previous = limiter.reserve("admin", "198.51.100.1")
    clock[0] += 60
    limiter.reserve("admin", "198.51.100.1")
    limiter.refund(previous)
    assert all(row["attempts"] == 1 for row in counters(storage))


def test_raw_identifiers_passwords_and_tokens_are_not_logged_or_stored(clients, storage, caplog):
    caplog.set_level("INFO", logger="app.routers.auth")
    username = "private-username"
    password = "private-password"
    for _ in range(4):
        login(clients(), username=username, password=password)
    response = login(clients("198.51.100.2"), password=PASSWORD)
    assert response.status_code == 200
    assert username not in caplog.text
    assert password not in caplog.text
    assert PASSWORD not in caplog.text
    assert response.json()["access_token"] not in caplog.text
    assert "Login failed" in caplog.text and "Login throttled" in caplog.text
    for row in counters(storage):
        assert len(row["key"].split(":")[1]) == 64
        assert username not in row["key"] and "198.51.100" not in row["key"]


def _reserve_worker(args):
    """Each invocation opens its own connection/limiter, including in subprocesses."""
    url, username, source = args
    engine = create_engine(url, connect_args={"timeout": 15})
    limiter = LoginLimiter(engine, secret="test-only-key", account_limit=3, source_limit=6)
    try:
        limiter.reserve(username, source)
        return True
    except LoginLimitExceeded:
        return False
    finally:
        engine.dispose()


def test_source_budget_is_atomic_across_connections(storage):
    url = str(storage[0].url)
    with ThreadPoolExecutor(max_workers=8) as pool:
        allowed = list(pool.map(_reserve_worker, [(url, f"account-{i}", "198.51.100.1") for i in range(12)]))
    assert sum(allowed) == 6
    source = [row for row in counters(storage) if row["key"].startswith("source:")]
    assert source[0]["attempts"] == 6


def test_account_budget_is_shared_and_atomic_across_processes(storage):
    url = str(storage[0].url)
    with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("spawn")) as pool:
        allowed = list(pool.map(_reserve_worker, [(url, "admin", f"198.51.100.{i+1}") for i in range(12)]))
    assert sum(allowed) == 3
    rows = counters(storage)
    assert len(rows) == 4  # Denied requests did not consume independent source slots.
    assert next(row for row in rows if row["key"].startswith("account:"))["attempts"] == 3


def test_ipv4_mapped_ipv6_does_not_create_another_source_budget(limiter):
    for i in range(6):
        limiter.reserve(f"account-{i}", "198.51.100.1")
    with pytest.raises(LoginLimitExceeded):
        limiter.reserve("another", "::ffff:198.51.100.1")
