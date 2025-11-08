import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .database import Base, engine
from .models import category as _category_model  # noqa: F401
from .models import event as _event_model  # noqa: F401
from .models import user as _user_model  # noqa: F401
from .routers import auth, categories, events
from .utils import schema as schema_utils

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

schema_utils.ensure_columns(
    engine,
    (
        schema_utils.ColumnRequirement("events", "category_id", "INTEGER"),
        schema_utils.ColumnRequirement("users", "email", "VARCHAR"),
    ),
)

app = FastAPI(
    title="Афиша мероприятий",
    description="API для управления мероприятиями",
    version="1.0.0",
)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

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
app.include_router(categories.router)
app.include_router(events.router)


@app.get("/")
def read_root():
    return {"message": "Афиша мероприятий API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
