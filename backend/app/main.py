import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from .database import Base, engine
from .models import event as _event_model  # noqa: F401
from .models import user as _user_model  # noqa: F401
from .routers import auth, events

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


def _ensure_column(engine, table_name: str, column_name: str, column_definition: str) -> None:
    """Ensure that a column exists on the given table, creating it if needed."""

    inspector = inspect(engine)
    try:
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not inspect table %s: %s", table_name, exc)
        return

    if column_name in existing_columns:
        return

    try:
        with engine.begin() as connection:
            connection.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
            )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "Could not ensure column %s.%s exists: %s", table_name, column_name, exc
        )


_ensure_column(engine, "events", "category", "category VARCHAR")
_ensure_column(engine, "users", "email", "email VARCHAR")

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
