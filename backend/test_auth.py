"""Password hashing regression tests (no credentials in logs)."""
from app.auth.auth import get_password_hash, verify_password


def test_password_hashing():
    password = "long-test-only-password-123456"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("incorrect-password", hashed)
