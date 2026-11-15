"""Authenticated editorial access; public routes never accept a visibility flag."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..auth.auth import get_current_admin_user
from ..dependencies import get_event_service
from ..schemas.event import Event, EventStatusChange, PaginatedEvents, PublicationChange
from ..services.event_service import EventService
from ..services.exceptions import EventNotFoundError, InvalidDateFilterError, PublicationValidationError

router = APIRouter(prefix="/admin/events", tags=["admin-events"],
                   dependencies=[Depends(get_current_admin_user)])


def editorial_action(action):
    try:
        return action()
    except EventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc
    except PublicationValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "fields": exc.fields}) from exc


@router.get("/", response_model=PaginatedEvents)
def list_events(page: int = 1, limit: int = 10, date: Optional[str] = None,
                date_from: Optional[str] = None, date_to: Optional[str] = None,
                category: Optional[str] = None, sort: Optional[str] = "asc",
                service: EventService = Depends(get_event_service)):
    try:
        return service.list_events(page=page, limit=limit, date=date, date_from=date_from,
                                   date_to=date_to, category=category, sort=sort, include_unpublished=True)
    except InvalidDateFilterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{event_id}", response_model=Event)
def get_event(event_id: int, service: EventService = Depends(get_event_service)):
    return editorial_action(lambda: service.get_event(event_id, include_unpublished=True))


@router.post("/{event_id}/verify", response_model=Event)
def verify(event_id: int, service: EventService = Depends(get_event_service)):
    # There is no client timestamp/actor input: the service uses its UTC clock.
    return editorial_action(lambda: service.verify_event(event_id))


@router.patch("/{event_id}/publication", response_model=Event)
def publication(event_id: int, change: PublicationChange, service: EventService = Depends(get_event_service)):
    return editorial_action(lambda: service.change_publication(event_id, change.publication_status))


@router.patch("/{event_id}/status", response_model=Event)
def status(event_id: int, change: EventStatusChange, service: EventService = Depends(get_event_service)):
    return editorial_action(lambda: service.change_event_status(event_id, change.event_status))
