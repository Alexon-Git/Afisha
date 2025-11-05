from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from ..auth.auth import get_current_admin_user
from ..dependencies import get_event_service
from ..models.user import User
from ..schemas.event import Event as EventSchema, EventCreate, EventUpdate, PaginatedEvents
from ..services.event_service import EventService
from ..services.exceptions import EventNotFoundError, InvalidImageError

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=PaginatedEvents)
def read_events(
    page: int = 1,
    limit: int = 10,
    date: Optional[str] = Query(None, description="today | tomorrow | weekend | YYYY-MM-DD"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    category: Optional[str] = Query(None),
    sort: Optional[str] = Query("asc", description="asc | desc"),
    event_service: EventService = Depends(get_event_service),
):
    return event_service.list_events(
        page=page,
        limit=limit,
        date=date,
        date_from=date_from,
        date_to=date_to,
        category=category,
        sort=sort,
    )


@router.get("/{event_id}", response_model=EventSchema)
def read_event(event_id: int, event_service: EventService = Depends(get_event_service)):
    try:
        return event_service.get_event(event_id)
    except EventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc


@router.post("/", response_model=EventSchema)
def create_event(
    event: EventCreate,
    current_user: User = Depends(get_current_admin_user),
    event_service: EventService = Depends(get_event_service),
):
    return event_service.create_event(event, creator_id=current_user.id)


@router.put("/{event_id}", response_model=EventSchema)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    current_user: User = Depends(get_current_admin_user),
    event_service: EventService = Depends(get_event_service),
):
    try:
        return event_service.update_event(event_id, event_update)
    except EventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),
    event_service: EventService = Depends(get_event_service),
):
    try:
        event_service.delete_event(event_id)
    except EventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc
    return {"message": "Event deleted successfully"}


@router.post("/upload-image")
def upload_image(
    file: UploadFile,
    current_user: User = Depends(get_current_admin_user),
    event_service: EventService = Depends(get_event_service),
):
    try:
        image_url = event_service.save_image(file)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"image_url": image_url}
