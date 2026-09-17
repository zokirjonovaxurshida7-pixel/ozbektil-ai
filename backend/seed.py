"""
Bazani boshlang'ich ma'lumotlar bilan to'ldirish.
----------------------------------------------------
Birinchi ishga tushirishda data/*.json fayllaridagi lug'at va test savollari
bazaga ko'chiriladi (jadval bo'sh bo'lsagina). Shundan keyin admin panel orqali
kiritilgan o'zgarishlar to'g'ridan-to'g'ri bazada saqlanadi — JSON fayllar endi
faqat "boshlang'ich urug'" (seed) vazifasini bajaradi.

Admin foydalanuvchi ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD muhit
o'zgaruvchilari orqali (yoki standart qiymatlar bilan) avtomatik yaratiladi.
"""

import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from auth import hash_password
from models import DictionaryWord, QuizQuestion, User

DATA_DIR = Path(__file__).parent / "data"


def _load_json(name: str):
    path = DATA_DIR / name
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_dictionary(db: Session):
    if db.query(DictionaryWord).count() > 0:
        return
    data = _load_json("dictionary.json") or []
    for entry in data:
        db.add(DictionaryWord(
            word=entry["word"],
            turkum=entry.get("turkum", ""),
            talaffuz=entry.get("talaffuz", ""),
            meaning=entry.get("meaning", ""),
            synonyms_json=json.dumps(entry.get("synonyms", []), ensure_ascii=False),
            antonyms_json=json.dumps(entry.get("antonyms", []), ensure_ascii=False),
            example=entry.get("example", ""),
            kelib_chiqishi=entry.get("kelib_chiqishi", ""),
        ))
    db.commit()


def seed_quiz(db: Session):
    if db.query(QuizQuestion).count() > 0:
        return
    data = _load_json("quiz.json") or []
    for q in data:
        db.add(QuizQuestion(
            id=q["id"],
            topic=q["topic"],
            question=q["question"],
            options_json=json.dumps(q["options"], ensure_ascii=False),
            correct=q["correct"],
            explanation=q.get("explanation", ""),
        ))
    db.commit()


def seed_admin(db: Session):
    if db.query(User).filter(User.is_admin.is_(True)).first():
        return
    username = os.environ.get("ADMIN_USERNAME", "admin")
    email = os.environ.get("ADMIN_EMAIL", "admin@ozbektil.ai")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        existing.is_admin = True
        db.commit()
        return

    db.add(User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_admin=True,
    ))
    db.commit()


def run_all_seeds(db: Session):
    seed_dictionary(db)
    seed_quiz(db)
    seed_admin(db)
