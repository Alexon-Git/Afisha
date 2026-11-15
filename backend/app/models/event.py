from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base
from .event_status import EventStatus, PublicationStatus


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    datetime = Column(DateTime, nullable=False, index=True)
    location = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    price = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    discount = Column(Integer, nullable=True)
    payment_url = Column(String, nullable=True)
    organizer_id = Column(Integer, ForeignKey("organizers.id", name="fk_events_organizer_id_organizers", ondelete="SET NULL"), nullable=True, index=True)
    event_url = Column(String, nullable=True)
    source = Column(String, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    publication_status = Column(
        Enum(PublicationStatus, values_callable=lambda cls: [item.value for item in cls],
             native_enum=False, create_constraint=True, validate_strings=True,
             name="ck_events_publication_status"),
        nullable=False, default=PublicationStatus.DRAFT, server_default="draft",
    )
    event_status = Column(
        Enum(EventStatus, values_callable=lambda cls: [item.value for item in cls],
             native_enum=False, create_constraint=True, validate_strings=True,
             name="ck_events_event_status"),
        nullable=False, default=EventStatus.SCHEDULED, server_default="scheduled",
    )

    # Связи
    creator = relationship("User", back_populates="events")
    category = relationship("Category", back_populates="events")
    organizer = relationship("Organizer", back_populates="events")
