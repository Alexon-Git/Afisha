from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import relationship

from ..database import Base


class Organizer(Base):
    """Editorial organizer data; public_contact is not automatically public API data."""

    __tablename__ = "organizers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    website_url = Column(String, nullable=True)
    public_contact = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # ORM deletion clears links even in local SQLite connections without FK
    # enforcement; PostgreSQL also enforces ON DELETE SET NULL for raw SQL.
    events = relationship("Event", back_populates="organizer")
