from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


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

    # Связи
    creator = relationship("User", back_populates="events")
    category = relationship("Category", back_populates="events")
