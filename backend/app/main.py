from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
# Ensure all models are imported before metadata creation
from .models import user as _user_model  # noqa: F401
from .models import event as _event_model  # noqa: F401
from .routers import auth, events
from .config import settings
import os

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

# Обновление схемы: добавить колонку category в таблицу events при отсутствии (SQLite)
try:
    with engine.connect() as conn:
        res = conn.exec_driver_sql("PRAGMA table_info(events)")
        columns = {row[1] for row in res.fetchall()}
        if "category" not in columns:
            conn.exec_driver_sql("ALTER TABLE events ADD COLUMN category VARCHAR")
except Exception:
    # Тихо игнорируем, если база не SQLite или операция не поддерживается
    pass

app = FastAPI(
    title="Афиша мероприятий",
    description="API для управления мероприятиями",
    version="1.0.0"
)

# Настройка CORS
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

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(events.router)


@app.get("/")
def read_root():
    return {"message": "Афиша мероприятий API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
