from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Связь с пользователем
    creator = relationship("User", back_populates="events")
