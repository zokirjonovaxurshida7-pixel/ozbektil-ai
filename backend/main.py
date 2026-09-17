"""
O'zbekTil AI - MVP Backend
----------------------------------
Loyiha rejasidagi (LOYIHA REJASI.docx) 5-, 6-, 8- va 13-bo'limlarga
asoslangan MVP: imlo tekshiruv, oddiy grammatika tekshiruv, lug'at va
test tizimi. AI yordamchi moduli mavjud bo'lsa ANTHROPIC_API_KEY orqali
haqiqiy Claude modeliga, aks holda oddiy qoidaviy (rule-based) shablonga
murojaat qiladi.

Endi qo'shildi: SQLite ma'lumotlar bazasi, foydalanuvchilar uchun
ro'yxatdan o'tish/kirish (JWT) va administrator paneli (statistikalar,
foydalanuvchilar, lug'at va test savollarini boshqarish).

Ishga tushirish:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Birinchi marta ishga tushganda standart administrator yaratiladi:
    login:  admin   (yoki ADMIN_USERNAME muhit o'zgaruvchisi)
    parol:  admin123 (yoki ADMIN_PASSWORD muhit o'zgaruvchisi)
Ishlab chiqarishda ADMIN_PASSWORD va SECRET_KEY'ni albatta o'zgartiring!
"""

import datetime
import json
import os
import random
import re
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    get_current_admin,
    get_current_user,
    get_optional_user,
    hash_password,
    verify_password,
)
from db import Base, engine, get_db
from models import CheckLog, DictionaryWord, QuizQuestion, QuizResult, User
from seed import run_all_seeds

DATA_DIR = Path(__file__).parent / "data"

app = FastAPI(title="O'zbekTil AI API", version="0.2.0-mvp")

# Frontend boshqa portda ochilishi mumkin bo'lgani uchun CORS ochiq qoldirildi.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        run_all_seeds(db)
    finally:
        db.close()


def load_json(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


COMMON_ERRORS: Dict[str, dict] = load_json("common_errors.json")

# Fe'l zamoni nomuvofiqligini aniqlash uchun oddiy evristika (5-6-bo'lim, MVP darajasida)
PAST_TIME_MARKERS = ["kecha", "o'tgan", "o‘tgan", "bultur", "avvalgi", "ilgari"]
FUTURE_TIME_MARKERS = ["ertaga", "kelasi", "yaqinda", "tez orada", "keyin"]
PRESENT_FUTURE_VERB_ENDINGS = ("adi", "ydi", "aman", "yman", "asan", "ysan")
PAST_VERB_ENDINGS = ("di", "dim", "ding", "gan", "gan edi", "moqchi edi")


# =====================================================================
# Pydantic sxemalar
# =====================================================================
class TextCheckRequest(BaseModel):
    text: str


class QuizSubmitRequest(BaseModel):
    answers: Dict[int, str]


class AIAssistRequest(BaseModel):
    text: str
    mode: str = "rasmiy"  # rasmiy | sodda | qisqa


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Login kamida 3 ta belgidan iborat bo'lishi kerak.")
        if not re.fullmatch(r"[A-Za-z0-9_]+", v):
            raise ValueError("Login faqat lotin harflari, raqam va pastki chiziqdan iborat bo'lishi kerak.")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Parol kamida 6 ta belgidan iborat bo'lishi kerak.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class DictionaryWordIn(BaseModel):
    word: str
    turkum: str = ""
    talaffuz: str = ""
    meaning: str = ""
    synonyms: List[str] = []
    antonyms: List[str] = []
    example: str = ""
    kelib_chiqishi: str = ""


class QuizQuestionIn(BaseModel):
    topic: str
    question: str
    options: Dict[str, str]
    correct: str
    explanation: str = ""


# =====================================================================
# Yordamchi funksiyalar (matn tekshiruvi)
# =====================================================================
def strip_punct(token: str) -> str:
    return re.sub(r"^[^\w'’‘]+|[^\w'’‘]+$", "", token, flags=re.UNICODE)


MAX_SUFFIX_LEN = 4  # o'zbek tilidagi qo'shimchalar uchun taxminiy chegara (masalan, -ga, -lar, -dan)


def find_error_entry(lookup: str) -> Optional[dict]:
    """To'g'ridan-to'g'ri moslikni, so'ng qo'shimcha qo'shilgan shaklni tekshiradi."""
    if lookup in COMMON_ERRORS:
        return COMMON_ERRORS[lookup]
    for wrong_root, info in COMMON_ERRORS.items():
        if lookup.startswith(wrong_root) and 0 < len(lookup) - len(wrong_root) <= MAX_SUFFIX_LEN:
            suffix = lookup[len(wrong_root):]
            return {**info, "correct": info["correct"] + suffix}
    return None


def check_spelling(text: str) -> List[dict]:
    errors = []
    tokens = text.split()
    cursor = 0
    for raw_token in tokens:
        start = text.find(raw_token, cursor)
        cursor = start + len(raw_token)
        word = strip_punct(raw_token)
        if not word:
            continue
        lookup = word.lower()
        info = find_error_entry(lookup)
        if info and info["correct"].lower() != lookup:
            errors.append({
                "type": "imlo",
                "wrong": word,
                "correct": info["correct"],
                "explanation": info["explanation"],
                "position": start,
            })
    return errors


def check_grammar(text: str) -> List[dict]:
    errors = []
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for sentence in sentences:
        if not sentence.strip():
            continue
        s_lower = sentence.lower()
        words = sentence.split()
        if not words:
            continue
        last_word_clean = strip_punct(words[-1])
        last_word = last_word_clean.lower()

        has_past_marker = any(m in s_lower for m in PAST_TIME_MARKERS)
        has_future_marker = any(m in s_lower for m in FUTURE_TIME_MARKERS)

        if has_past_marker and last_word.endswith(PRESENT_FUTURE_VERB_ENDINGS):
            errors.append({
                "type": "grammatika",
                "sentence": sentence.strip(),
                "issue": f"“{last_word_clean}” — gapdagi payt (o‘tgan zamon) bilan fe’l zamoni mos kelmayapti.",
                "suggestion": "Fe’lni o‘tgan zamon shakliga (masalan, “-di/-dim”) o‘zgartiring.",
            })
        elif has_future_marker and last_word.endswith(PAST_VERB_ENDINGS):
            errors.append({
                "type": "grammatika",
                "sentence": sentence.strip(),
                "issue": f"“{last_word_clean}” — gapdagi payt (kelasi zamon) bilan fe’l zamoni mos kelmayapti.",
                "suggestion": "Fe’lni kelasi zamon shakliga (masalan, “-adi/-aman”) o‘zgartiring.",
            })
    return errors


def check_repeated_words(text: str) -> List[dict]:
    errors = []
    tokens = text.split()
    for i in range(len(tokens) - 1):
        w1 = strip_punct(tokens[i]).lower()
        w2 = strip_punct(tokens[i + 1]).lower()
        if w1 and w1 == w2:
            errors.append({
                "type": "uslub",
                "sentence": f"{tokens[i]} {tokens[i + 1]}",
                "issue": f"“{tokens[i]}” so‘zi ketma-ket ikki marta yozilgan.",
                "suggestion": "Ortiqcha takrorlangan so‘zni o‘chiring.",
            })
    return errors


def check_punctuation(text: str) -> List[dict]:
    errors = []
    fragments = re.split(r"(?<=[.!?])\s+", text.strip())
    for frag in fragments:
        frag = frag.strip()
        if len(frag.split()) >= 3 and frag and frag[-1] not in ".!?":
            errors.append({
                "type": "uslub",
                "sentence": frag,
                "issue": "Gap oxirida tinish belgisi (., !, ?) qo‘yilmagan.",
                "suggestion": "Gapni mos tinish belgisi bilan yakunlang.",
            })
    return errors


def dict_word_to_json(entry: DictionaryWord) -> dict:
    return {
        "word": entry.word,
        "turkum": entry.turkum,
        "talaffuz": entry.talaffuz,
        "meaning": entry.meaning,
        "synonyms": json.loads(entry.synonyms_json or "[]"),
        "antonyms": json.loads(entry.antonyms_json or "[]"),
        "example": entry.example,
        "kelib_chiqishi": entry.kelib_chiqishi,
    }


def quiz_question_to_json(q: QuizQuestion, with_answer: bool = False) -> dict:
    data = {
        "id": q.id,
        "topic": q.topic,
        "question": q.question,
        "options": json.loads(q.options_json),
    }
    if with_answer:
        data["correct"] = q.correct
        data["explanation"] = q.explanation
    return data


# =====================================================================
# Umumiy
# =====================================================================
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "O'zbekTil AI MVP"}


# =====================================================================
# Matn tekshirish
# =====================================================================
@app.post("/api/check-text")
def check_text(
    payload: TextCheckRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    if not payload.text.strip():
        raise HTTPException(400, "Matn bo'sh bo'lishi mumkin emas.")
    spelling_errors = check_spelling(payload.text)
    grammar_errors = check_grammar(payload.text)
    style_errors = check_repeated_words(payload.text) + check_punctuation(payload.text)

    corrected = payload.text
    for err in spelling_errors:
        corrected = re.sub(rf"\b{re.escape(err['wrong'])}\b", err["correct"], corrected)

    total = len(spelling_errors) + len(grammar_errors) + len(style_errors)

    # Statistikaga faqat sonlar yoziladi — foydalanuvchi matnining o'zi saqlanmaydi (maxfiylik).
    db.add(CheckLog(
        user_id=user.id if user else None,
        error_count=total,
        char_count=len(payload.text),
    ))
    db.commit()

    return {
        "original_text": payload.text,
        "corrected_text": corrected,
        "spelling_errors": spelling_errors,
        "grammar_errors": grammar_errors,
        "style_errors": style_errors,
        "total_errors": total,
    }


# =====================================================================
# Lug'at
# =====================================================================
@app.get("/api/dictionary")
def dictionary_lookup(q: Optional[str] = None, db: Session = Depends(get_db)):
    if not q:
        words = db.query(DictionaryWord.word).order_by(DictionaryWord.word).all()
        return {"words": [w[0] for w in words]}
    q_lower = q.strip().lower()
    entry = db.query(DictionaryWord).filter(DictionaryWord.word.ilike(q_lower)).first()
    if entry:
        return dict_word_to_json(entry)
    prefix = q_lower[:3]
    suggestions = [
        w.word for w in db.query(DictionaryWord).filter(DictionaryWord.word.ilike(f"{prefix}%")).limit(8)
    ]
    raise HTTPException(404, detail={"message": "So'z topilmadi.", "suggestions": suggestions})


@app.get("/api/word-of-day")
def word_of_day(db: Session = Depends(get_db)):
    words = db.query(DictionaryWord).order_by(DictionaryWord.id).all()
    if not words:
        raise HTTPException(404, "Lug'at bo'sh.")
    day_index = datetime.date.today().timetuple().tm_yday
    return dict_word_to_json(words[day_index % len(words)])


@app.get("/api/dictionary/random")
def dictionary_random(db: Session = Depends(get_db)):
    words = db.query(DictionaryWord).all()
    if not words:
        raise HTTPException(404, "Lug'at bo'sh.")
    seed = datetime.date.today().isoformat()
    rnd = random.Random(seed)
    return dict_word_to_json(rnd.choice(words))


# =====================================================================
# Test tizimi
# =====================================================================
@app.get("/api/quiz")
def get_quiz(db: Session = Depends(get_db)):
    questions = db.query(QuizQuestion).order_by(QuizQuestion.id).all()
    return [quiz_question_to_json(q) for q in questions]


@app.post("/api/quiz/submit")
def submit_quiz(
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    all_questions = {q.id: q for q in db.query(QuizQuestion).all()}

    # Faqat haqiqatda javob berilgan savollar bo'yicha baholaymiz — shu tarzda
    # ham veb-saytdagi qisman topshiriq, ham Telegram botdagi qisqartirilgan
    # (5 ta savolli) test to'g'ri foiz bilan hisoblanadi.
    answered_ids = [qid for qid in payload.answers.keys() if qid in all_questions]
    if not answered_ids:
        raise HTTPException(400, "Hech qanday savolga javob berilmagan.")

    correct_count = 0
    weak_topics: Dict[str, int] = {}
    results = []

    for qid in answered_ids:
        q = all_questions[qid]
        given = payload.answers.get(qid)
        is_correct = given == q.correct
        if is_correct:
            correct_count += 1
        else:
            weak_topics[q.topic] = weak_topics.get(q.topic, 0) + 1
        results.append({
            "id": q.id,
            "topic": q.topic,
            "correct": is_correct,
            "correct_answer": q.correct,
            "explanation": q.explanation,
        })

    total = len(answered_ids)
    percent = round((correct_count / total) * 100) if total else 0
    weakest = max(weak_topics, key=weak_topics.get) if weak_topics else None
    recommendation = (
        f"Sizda \"{weakest}\" mavzusida xatolar ko'proq. Ushbu mavzu bo'yicha qo'shimcha mashq qiling."
        if weakest else "Barcha mavzular bo'yicha yaxshi natija! Davom eting."
    )

    db.add(QuizResult(
        user_id=user.id if user else None,
        score=correct_count,
        total=total,
        percent=percent,
        weak_topics_json=json.dumps(weak_topics, ensure_ascii=False),
    ))
    db.commit()

    return {
        "score": correct_count,
        "total": total,
        "percent": percent,
        "weak_topics": weak_topics,
        "recommendation": recommendation,
        "results": results,
    }


# =====================================================================
# AI yordamchi
# =====================================================================
def call_claude(prompt: str) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            return "\n".join(parts).strip() or None
    except Exception:
        return None


FALLBACK_TEMPLATES = {
    "rasmiy": "Mazkur masala yuzasidan quyidagi ma'lumot taqdim etiladi: {text}",
    "sodda": "Qisqacha aytganda: {text}",
    "qisqa": "{text}",
}


@app.post("/api/ai-assist")
def ai_assist(payload: AIAssistRequest):
    if not payload.text.strip():
        raise HTTPException(400, "Matn bo'sh bo'lishi mumkin emas.")

    mode_prompts = {
        "rasmiy": f"Quyidagi o'zbekcha matnni rasmiy uslubga o'tkazib qayta yoz, faqat natijani yoz:\n\n{payload.text}",
        "sodda": f"Quyidagi o'zbekcha matnni sodda va tushunarli tilga o'tkazib qayta yoz, faqat natijani yoz:\n\n{payload.text}",
        "qisqa": f"Quyidagi o'zbekcha matnni asosiy fikrni yo'qotmagan holda qisqartir, faqat natijani yoz:\n\n{payload.text}",
    }
    prompt = mode_prompts.get(payload.mode, mode_prompts["rasmiy"])

    ai_result = call_claude(prompt)
    if ai_result:
        return {"result": ai_result, "source": "claude-api"}

    template = FALLBACK_TEMPLATES.get(payload.mode, FALLBACK_TEMPLATES["rasmiy"])
    return {
        "result": template.format(text=payload.text.strip()),
        "source": "fallback-template",
        "note": "Haqiqiy AI javobi uchun ANTHROPIC_API_KEY muhit o'zgaruvchisini o'rnating.",
    }


# =====================================================================
# Autentifikatsiya (ro'yxatdan o'tish / kirish)
# =====================================================================
@app.post("/api/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, "Bu login band qilingan.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Bu email allaqachon ro'yxatdan o'tgan.")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "email": user.email, "is_admin": user.is_admin},
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Login yoki parol noto'g'ri.")
    token = create_access_token(user.id)
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "email": user.email, "is_admin": user.is_admin},
    }


@app.get("/api/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "is_admin": user.is_admin}


@app.get("/api/me/quiz-results")
def my_quiz_results(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = (
        db.query(QuizResult)
        .filter(QuizResult.user_id == user.id)
        .order_by(QuizResult.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": r.id,
            "score": r.score,
            "total": r.total,
            "percent": r.percent,
            "weak_topics": json.loads(r.weak_topics_json or "{}"),
            "created_at": r.created_at.isoformat(),
        }
        for r in results
    ]


# =====================================================================
# ADMIN PANEL
# =====================================================================
@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    total_users = db.query(User).count()
    total_checks = db.query(CheckLog).count()
    total_quiz = db.query(QuizResult).count()
    avg_percent_row = db.query(QuizResult).all()
    avg_percent = (
        round(sum(r.percent for r in avg_percent_row) / len(avg_percent_row))
        if avg_percent_row else 0
    )
    return {
        "total_users": total_users,
        "total_checks": total_checks,
        "total_quiz_attempts": total_quiz,
        "avg_quiz_percent": avg_percent,
        "total_dictionary_words": db.query(DictionaryWord).count(),
        "total_quiz_questions": db.query(QuizQuestion).count(),
    }


@app.get("/api/admin/users")
def admin_list_users(db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat(),
            "quiz_attempts": len(u.quiz_results),
        }
        for u in users
    ]


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    if user_id == admin.id:
        raise HTTPException(400, "O'zingizni o'chira olmaysiz.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Foydalanuvchi topilmadi.")
    db.delete(user)
    db.commit()
    return {"status": "deleted"}


# ---------- Lug'atni boshqarish ----------
@app.get("/api/admin/dictionary")
def admin_list_dictionary(db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    words = db.query(DictionaryWord).order_by(DictionaryWord.word).all()
    return [dict_word_to_json(w) | {"id": w.id} for w in words]


@app.post("/api/admin/dictionary")
def admin_add_word(payload: DictionaryWordIn, db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    if db.query(DictionaryWord).filter(DictionaryWord.word.ilike(payload.word)).first():
        raise HTTPException(400, "Bu so'z lug'atda mavjud.")
    entry = DictionaryWord(
        word=payload.word,
        turkum=payload.turkum,
        talaffuz=payload.talaffuz,
        meaning=payload.meaning,
        synonyms_json=json.dumps(payload.synonyms, ensure_ascii=False),
        antonyms_json=json.dumps(payload.antonyms, ensure_ascii=False),
        example=payload.example,
        kelib_chiqishi=payload.kelib_chiqishi,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return dict_word_to_json(entry) | {"id": entry.id}


@app.put("/api/admin/dictionary/{word_id}")
def admin_update_word(word_id: int, payload: DictionaryWordIn, db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    entry = db.query(DictionaryWord).filter(DictionaryWord.id == word_id).first()
    if not entry:
        raise HTTPException(404, "So'z topilmadi.")
    entry.word = payload.word
    entry.turkum = payload.turkum
    entry.talaffuz = payload.talaffuz
    entry.meaning = payload.meaning
    entry.synonyms_json = json.dumps(payload.synonyms, ensure_ascii=False)
    entry.antonyms_json = json.dumps(payload.antonyms, ensure_ascii=False)
    entry.example = payload.example
    entry.kelib_chiqishi = payload.kelib_chiqishi
    db.commit()
    return dict_word_to_json(entry) | {"id": entry.id}


@app.delete("/api/admin/dictionary/{word_id}")
def admin_delete_word(word_id: int, db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    entry = db.query(DictionaryWord).filter(DictionaryWord.id == word_id).first()
    if not entry:
        raise HTTPException(404, "So'z topilmadi.")
    db.delete(entry)
    db.commit()
    return {"status": "deleted"}


# ---------- Test savollarini boshqarish ----------
@app.get("/api/admin/quiz")
def admin_list_quiz(db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    questions = db.query(QuizQuestion).order_by(QuizQuestion.id).all()
    return [quiz_question_to_json(q, with_answer=True) for q in questions]


@app.post("/api/admin/quiz")
def admin_add_question(payload: QuizQuestionIn, db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    max_id_row = db.query(QuizQuestion.id).order_by(QuizQuestion.id.desc()).first()
    next_id = (max_id_row[0] + 1) if max_id_row else 1
    q = QuizQuestion(
        id=next_id,
        topic=payload.topic,
        question=payload.question,
        options_json=json.dumps(payload.options, ensure_ascii=False),
        correct=payload.correct,
        explanation=payload.explanation,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return quiz_question_to_json(q, with_answer=True)


@app.put("/api/admin/quiz/{question_id}")
def admin_update_question(question_id: int, payload: QuizQuestionIn, db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    q = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not q:
        raise HTTPException(404, "Savol topilmadi.")
    q.topic = payload.topic
    q.question = payload.question
    q.options_json = json.dumps(payload.options, ensure_ascii=False)
    q.correct = payload.correct
    q.explanation = payload.explanation
    db.commit()
    return quiz_question_to_json(q, with_answer=True)


@app.delete("/api/admin/quiz/{question_id}")
def admin_delete_question(question_id: int, db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    q = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not q:
        raise HTTPException(404, "Savol topilmadi.")
    db.delete(q)
    db.commit()
    return {"status": "deleted"}
