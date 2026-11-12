"""Keep tests isolated from real databases and secrets.

Pytest loads this before collecting modules that import app.config.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-only-secret-value-with-at-least-32-chars"
os.environ["ADMIN_PASSWORD"] = "test-only-admin-password-12345"
