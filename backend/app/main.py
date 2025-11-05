import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .models import event as _event_model  # noqa: F401
from .models import user as _user_model  # noqa: F401
from .routers import auth, events

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

try:
    with engine.connect() as conn:
        res = conn.exec_driver_sql("PRAGMA table_info(events)")
        columns = {row[1] for row in res.fetchall()}
        if "category" not in columns:
            conn.exec_driver_sql("ALTER TABLE events ADD COLUMN category VARCHAR")
            conn.commit()
except Exception as exc:  # pylint: disable=broad-except
    logger.warning("Could not ensure category column exists: %s", exc)

app = FastAPI(
    title="Афиша мероприятий",
    description="API для управления мероприятиями",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://afisha.lalexonl.ru",
        "https://www.afisha.lalexonl.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router)
app.include_router(events.router)


@app.get("/")
def read_root():
    return {"message": "Афиша мероприятий API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
