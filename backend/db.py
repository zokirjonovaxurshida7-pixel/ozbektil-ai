"""
Ma'lumotlar bazasi ulanishi (SQLite + SQLAlchemy).
----------------------------------------------------
MVP uchun SQLite ishlatiladi (fayl: backend/data/app.db) — alohida server
o'rnatishni talab qilmaydi. Kelajakda PostgreSQL'ga o'tish uchun faqat
DATABASE_URL muhit o'zgaruvchisini almashtirish yetarli (masalan:
"postgresql+psycopg2://user:pass@host/dbname").
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
