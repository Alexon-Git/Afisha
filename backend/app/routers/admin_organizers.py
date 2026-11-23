"""Minimal protected organizer picker; contacts and management are not exposed."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.auth import get_current_admin_user
from ..database import get_db
from ..models.organizer import Organizer

router = APIRouter(prefix="/admin/organizers", tags=["admin-organizers"],
                   dependencies=[Depends(get_current_admin_user)])


class OrganizerOption(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[OrganizerOption])
def list_organizers(db: Session = Depends(get_db)):
    return db.scalars(select(Organizer).order_by(Organizer.name, Organizer.id)).all()
