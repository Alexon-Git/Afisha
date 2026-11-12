"""Shared, expiring login budgets; keys contain no plaintext usernames/IPs."""

from sqlalchemy import BigInteger, Column, Integer, String

from ..database import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    key = Column(String(72), primary_key=True)
    attempts = Column(Integer, nullable=False)
    expires_at = Column(BigInteger, nullable=False, index=True)
