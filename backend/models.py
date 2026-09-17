"""SQLAlchemy jadval modellari: foydalanuvchilar, lug'at, testlar, natijalar."""

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(190), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    quiz_results = relationship("QuizResult", back_populates="user", cascade="all, delete-orphan")
    check_logs = relationship("CheckLog", back_populates="user", cascade="all, delete-orphan")


class DictionaryWord(Base):
    __tablename__ = "dictionary_words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(120), unique=True, index=True, nullable=False)
    turkum = Column(String(60), default="")
    talaffuz = Column(String(120), default="")
    meaning = Column(Text, default="")
    synonyms_json = Column(Text, default="[]")  # JSON matn sifatida saqlanadi
    antonyms_json = Column(Text, default="[]")
    example = Column(Text, default="")
    kelib_chiqishi = Column(Text, default="")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(80), nullable=False)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)  # {"A": "...", "B": "...", ...}
    correct = Column(String(4), nullable=False)
    explanation = Column(Text, default="")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    percent = Column(Integer, nullable=False)
    weak_topics_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="quiz_results")


class CheckLog(Base):
    __tablename__ = "check_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    error_count = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="check_logs")
