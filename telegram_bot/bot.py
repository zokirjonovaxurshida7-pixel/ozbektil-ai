"""
O'zbekTil AI - Telegram bot (MVP)
----------------------------------
Loyiha rejasining 15-bo'limiga asoslangan: /start, matn tekshirish,
lug'at, AI yordamchi, test, natijalar.

Ishga tushirish:
    pip install -r requirements.txt
    export BOT_TOKEN="123456:ABC-..."          # @BotFather'dan olinadi
    export API_BASE="http://localhost:8000"    # backend manzili
    python bot.py
"""

import asyncio
from html import escape
import logging
import os
import random
import time

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_BASE = os.environ.get("API_BASE", "https://ozbektil-ai.onrender.com").rstrip("/")
API_TIMEOUT_SECONDS = 20


class BackendUnavailableError(Exception):
    """Backend request failed or returned an unexpected response."""


async def api_request(method: str, path: str, *, timeout: int = API_TIMEOUT_SECONDS, **kwargs) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, f"{API_BASE}{path}", **kwargs)
    except httpx.RequestError as exc:
        raise BackendUnavailableError from exc
    if response.status_code >= 500:
        raise BackendUnavailableError
    return response

router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Matn tekshirish"), KeyboardButton(text="📚 Lug‘at")],
        [KeyboardButton(text="🤖 AI yordamchi"), KeyboardButton(text="🎓 Test")],
        [KeyboardButton(text="📊 Natijalar")],
    ],
    resize_keyboard=True,
)


class Flow(StatesGroup):
    waiting_text_check = State()
    waiting_dict_word = State()
    waiting_ai_text = State()
    waiting_ai_mode = State()
    quiz_active = State()


# ---------- /start ----------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Assalomu alaykum! <b>O‘zbekTil AI</b> botiga xush kelibsiz.\n\n"
        "Men sizga:\n"
        "📝 matnni tekshirishga,\n"
        "📚 so‘z ma’nosini topishga,\n"
        "🤖 matnni qayta yozishga,\n"
        "🎓 bilimingizni sinashga\n"
        "yordam beraman.\n\nQuyidagi menyudan tanlang 👇",
        parse_mode="HTML",
        reply_markup=MAIN_MENU,
    )


# ---------- MATN TEKSHIRISH ----------
@router.message(F.text == "📝 Matn tekshirish")
async def start_text_check(message: Message, state: FSMContext):
    await state.set_state(Flow.waiting_text_check)
    await message.answer("Tekshirmoqchi bo‘lgan matningizni yuboring:")


@router.message(Flow.waiting_text_check)
async def handle_text_check(message: Message, state: FSMContext):
    await state.clear()
    try:
        resp = await api_request("POST", "/api/check-text", json={"text": message.text or ""})
        resp.raise_for_status()
        data = resp.json()
    except (BackendUnavailableError, httpx.HTTPError, ValueError):
        await message.answer("⚠️ Serverga ulanib bo‘lmadi. Keyinroq qayta urinib ko‘ring.")
        return

    lines = [f"✅ <b>To‘g‘rilangan matn:</b>\n{escape(data['corrected_text'])}\n"]
    if data["total_errors"] == 0:
        lines.append("Xato topilmadi. Ajoyib!")
    else:
        for err in data["spelling_errors"]:
            lines.append(f"❌ {escape(err['wrong'])} → ✅ {escape(err['correct'])}\n<i>{escape(err['explanation'])}</i>")
        for err in data["grammar_errors"]:
            lines.append(f"⚠️ {escape(err['issue'])} {escape(err['suggestion'])}")
        for err in data.get("style_errors", []):
            lines.append(f"✏️ {escape(err['issue'])} {escape(err['suggestion'])}")

    await message.answer("\n\n".join(lines), parse_mode="HTML", reply_markup=MAIN_MENU)


# ---------- LUG'AT ----------
@router.message(F.text == "📚 Lug‘at")
async def start_dict(message: Message, state: FSMContext):
    await state.set_state(Flow.waiting_dict_word)
    await message.answer("Qaysi so‘zning ma’nosini bilmoqchisiz?")


@router.message(Flow.waiting_dict_word)
async def handle_dict(message: Message, state: FSMContext):
    await state.clear()
    word = (message.text or "").strip()
    if not word:
        await message.answer("So‘z yuboring.", reply_markup=MAIN_MENU)
        return
    try:
        resp = await api_request("GET", "/api/dictionary", params={"q": word})
    except BackendUnavailableError:
        await message.answer("⚠️ Serverga ulanib bo‘lmadi. Keyinroq qayta urinib ko‘ring.", reply_markup=MAIN_MENU)
        return

    if resp.status_code == 404:
        detail = resp.json().get("detail", {})
        suggestions = detail.get("suggestions", [])
        text = f"“{escape(word)}” lug‘atda topilmadi."
        if suggestions:
            text += "\nEhtimol: " + ", ".join(suggestions)
        await message.answer(text, reply_markup=MAIN_MENU)
        return

    entry = resp.json()
    text = (
        f"<b>{escape(entry['word'])}</b> ({escape(entry['turkum'])}, {escape(entry['talaffuz'])})\n\n"
        f"{escape(entry['meaning'])}\n\n"
        f"🔁 Sinonim: {escape(', '.join(entry['synonyms']) or '—')}\n"
        f"🔀 Antonim: {escape(', '.join(entry['antonyms']) or '—')}\n\n"
        f"✏️ Misol: {escape(entry['example'])}"
    )
    if entry.get("kelib_chiqishi"):
        text += f"\n\n🕰 Kelib chiqishi: {escape(entry['kelib_chiqishi'])}"
    await message.answer(text, parse_mode="HTML", reply_markup=MAIN_MENU)


# ---------- AI YORDAMCHI ----------
@router.message(F.text == "🤖 AI yordamchi")
async def start_ai(message: Message, state: FSMContext):
    await state.set_state(Flow.waiting_ai_text)
    await message.answer("Qanday matn bilan ishlaymiz? Matningizni yuboring:")


@router.message(Flow.waiting_ai_text)
async def handle_ai_text(message: Message, state: FSMContext):
    await state.update_data(ai_text=message.text)
    await state.set_state(Flow.waiting_ai_mode)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Rasmiy", callback_data="mode:rasmiy"),
        InlineKeyboardButton(text="Sodda", callback_data="mode:sodda"),
        InlineKeyboardButton(text="Qisqa", callback_data="mode:qisqa"),
    ]])
    await message.answer("Qaysi uslubga o‘girib beray?", reply_markup=kb)


@router.callback_query(F.data.startswith("mode:"))
async def handle_ai_mode(callback, state: FSMContext):
    mode = callback.data.split(":", 1)[1]
    data = await state.get_data()
    text = data.get("ai_text", "")
    await state.clear()
    await callback.message.edit_reply_markup()

    try:
        resp = await api_request("POST", "/api/ai-assist", timeout=30, json={"text": text, "mode": mode})
        resp.raise_for_status()
        result = resp.json()
    except (BackendUnavailableError, httpx.HTTPError, ValueError):
        await callback.message.answer("⚠️ Serverga ulanib bo‘lmadi. Keyinroq qayta urinib ko‘ring.")
        await callback.answer()
        return

    await callback.message.answer(escape(result["result"]), reply_markup=MAIN_MENU)
    await callback.answer()


# ---------- TEST ----------
quiz_state: dict = {}  # oddiy, xotirada saqlanadigan holat (MVP uchun yetarli)


@router.message(F.text == "🎓 Test")
async def start_quiz(message: Message, state: FSMContext):
    try:
        resp = await api_request("GET", "/api/quiz")
        resp.raise_for_status()
        questions = resp.json()
    except (BackendUnavailableError, httpx.HTTPError, ValueError):
        await message.answer("⚠️ Testlarni yuklab bo‘lmadi. Keyinroq qayta urinib ko‘ring.", reply_markup=MAIN_MENU)
        return
    if not questions:
        await message.answer("Hozircha test savollari mavjud emas.", reply_markup=MAIN_MENU)
        return
    random.shuffle(questions)
    questions = questions[:5]  # botda qisqaroq test, tezroq tugaydi
    quiz_state[message.from_user.id] = {
        "questions": questions,
        "index": 0,
        "answers": {},
        "started_at": time.monotonic(),
    }
    await state.set_state(Flow.quiz_active)
    await send_quiz_question(message, message.from_user.id)


async def send_quiz_question(message: Message, user_id: int):
    qs = quiz_state[user_id]
    q = qs["questions"][qs["index"]]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{k}) {v}", callback_data=f"quiz:{q['id']}:{k}")]
        for k, v in q["options"].items()
    ])
    await message.answer(f"({qs['index']+1}/{len(qs['questions'])}) {q['question']}", reply_markup=kb)


@router.callback_query(F.data.startswith("quiz:"))
async def handle_quiz_answer(callback, state: FSMContext):
    try:
        _, q_id, choice = callback.data.split(":")
        q_id = int(q_id)
    except (AttributeError, ValueError):
        await callback.answer("Bu javob tugmasi yaroqsiz.", show_alert=True)
        return
    user_id = callback.from_user.id
    qs = quiz_state.get(user_id)
    if not qs:
        await callback.answer("Test sessiyasi topilmadi, /start bosing.")
        return
    if time.monotonic() - qs["started_at"] > 1800:
        del quiz_state[user_id]
        await state.clear()
        await callback.answer("Test sessiyasi muddati tugagan. Qayta boshlang.", show_alert=True)
        return

    if qs["index"] >= len(qs["questions"]):
        await callback.answer("Bu test allaqachon yakunlangan.")
        return
    current_question = qs["questions"][qs["index"]]
    if current_question["id"] != q_id or choice not in current_question["options"]:
        await callback.answer("Bu javob endi yaroqsiz.", show_alert=True)
        return
    qs["answers"][q_id] = choice
    qs["index"] += 1
    await callback.message.edit_reply_markup()

    if qs["index"] < len(qs["questions"]):
        await send_quiz_question(callback.message, user_id)
    else:
        try:
            resp = await api_request("POST", "/api/quiz/submit", json={"answers": qs["answers"]})
            resp.raise_for_status()
            result = resp.json()
        except (BackendUnavailableError, httpx.HTTPError, ValueError):
            del quiz_state[user_id]
            await state.clear()
            await callback.message.answer("⚠️ Natijani saqlab bo‘lmadi. Keyinroq qayta urinib ko‘ring.", reply_markup=MAIN_MENU)
            await callback.answer()
            return
        text = (
            f"📊 Natija: {result['score']}/{len(qs['answers'])} to‘g‘ri javob berilgan savollardan\n\n"
            f"{escape(result['recommendation'])}"
        )
        await callback.message.answer(text, reply_markup=MAIN_MENU)
        del quiz_state[user_id]
        await state.clear()
    await callback.answer()


# ---------- NATIJALAR (soddalashtirilgan, MVP) ----------
@router.message(F.text == "📊 Natijalar")
async def show_results(message: Message):
    await message.answer(
        "Statistika moduli keyingi bosqichda (foydalanuvchi profili va PostgreSQL "
        "integratsiyasi bilan) qo‘shiladi. Hozircha har bir test yakunida natijangiz "
        "shu yerda ko‘rsatiladi.",
        reply_markup=MAIN_MENU,
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "/start — botni qayta boshlash\n"
        "Menyudan bo‘limni tanlang: matn tekshirish, lug‘at, AI yordamchi, test.",
    )


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan. @BotFather'dan token oling.")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
