from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    
    # Связь с мероприятиями (если нужно будет отслеживать кто создал)
    events = relationship("Event", back_populates="creator")
