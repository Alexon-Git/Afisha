from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.event import Event
from ..models.user import User
from ..schemas.event import Event as EventSchema, EventCreate, EventUpdate, PaginatedEvents
from ..auth.auth import get_current_admin_user
import os
import shutil
from datetime import datetime

router = APIRouter(prefix="/events", tags=["events"])

# Создаем директорию для загрузки изображений
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/", response_model=PaginatedEvents)
def read_events(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    total_items = db.query(Event).count()
    total_pages = (total_items + limit - 1) // limit
    items = (
        db.query(Event)
        .order_by(Event.datetime.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total_items": total_items,
        "total_pages": total_pages,
    }


@router.get("/{event_id}", response_model=EventSchema)
def read_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/", response_model=EventSchema)
def create_event(
    event: EventCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    db_event = Event(**event.dict(), creator_id=current_user.id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


@router.put("/{event_id}", response_model=EventSchema)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    
    update_data = event_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_event, field, value)
    
    db.commit()
    db.refresh(db_event)
    return db_event


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Удаляем изображение если оно есть
    if db_event.image_url:
        image_path = os.path.join(UPLOAD_DIR, os.path.basename(db_event.image_url))
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.delete(db_event)
    db.commit()
    return {"message": "Event deleted successfully"}


@router.post("/upload-image")
def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user)
):
    # Проверяем тип файла
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Проверяем размер файла (5MB)
    file.file.seek(0, 2)  # Переходим в конец файла
    file_size = file.file.tell()
    file.file.seek(0)  # Возвращаемся в начало
    
    if file_size > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    # Генерируем уникальное имя файла
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Возвращаем URL для доступа к файлу
    image_url = f"/static/uploads/{filename}"
    return {"image_url": image_url}
