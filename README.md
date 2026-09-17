# O‘zbekTil AI — MVP

Loyiha rejasidagi (5-, 6-, 8-, 13-, 15-bo‘limlar) asosiy funksiyalarning ishlaydigan
versiyasi: **matn tekshirish (imlo + oddiy grammatika), lug‘at, test tizimi,
AI yordamchi, foydalanuvchilar uchun ro‘yxatdan o‘tish/kirish, administrator
paneli va Telegram bot**.

## Tuzilma

```
ozbektil-ai/
├── backend/            # FastAPI server — barcha mantiq va ma'lumotlar shu yerda
│   ├── main.py          # API endpointlar
│   ├── db.py            # SQLAlchemy ulanishi (SQLite)
│   ├── models.py        # Jadval modellari (Users, Dictionary, Quiz, Results...)
│   ├── auth.py          # Parol xeshlash + JWT autentifikatsiya
│   ├── seed.py          # Bazani JSON fayllardan boshlang'ich to'ldirish
│   ├── requirements.txt
│   └── data/
│       ├── common_errors.json   # imlo xatolari lug'ati (statik qoida)
│       ├── dictionary.json      # boshlang'ich lug'at (faqat 1-marta bazaga seed qilinadi)
│       ├── quiz.json            # boshlang'ich test savollari (faqat 1-marta seed qilinadi)
│       └── app.db               # SQLite bazasi (avtomatik yaratiladi, .gitignore'ga qo'shing)
├── frontend/           # HTML/CSS/JS veb-sahifa (backend API'ga ulanadi)
│   ├── index.html       # asosiy sayt (kirish/ro'yxatdan o'tish bilan)
│   ├── admin.html        # administrator paneli
│   ├── style.css
│   ├── admin.css
│   ├── app.js
│   └── admin.js
└── telegram_bot/       # aiogram asosidagi Telegram bot (backend API'ga ulanadi)
    ├── bot.py
    └── requirements.txt
```

## 1. Backendni ishga tushirish

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Birinchi marta ishga tushganda `data/app.db` SQLite bazasi avtomatik yaratiladi,
`dictionary.json` va `quiz.json`dagi ma'lumotlar bazaga ko'chiriladi, va standart
**administrator hisobi** yaratiladi:

| Login | Parol      |
|-------|------------|
| admin | admin123   |

Bularni muhit o'zgaruvchilari orqali o'zgartirishingiz mumkin (tavsiya etiladi):

```bash
export ADMIN_USERNAME="mening_loginim"
export ADMIN_EMAIL="men@example.com"
export ADMIN_PASSWORD="kuchli-parol-123"
export SECRET_KEY="tasodifiy-uzun-maxfiy-satr"   # JWT tokenlarni imzolash uchun
```

> ⚠️ **Muhim:** `SECRET_KEY` va `ADMIN_PASSWORD`ni ishlab chiqarish (production)
> muhitida albatta o'zgartiring — standart qiymatlar faqat lokal test uchun.

Health-check: `http://localhost:8000/api/health`

### AI yordamchi uchun (ixtiyoriy)

`AI yordamchi` bo‘limi haqiqiy Claude javobini olishi uchun muhit o‘zgaruvchisini o‘rnating:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Kalit o‘rnatilmasa, tizim oddiy shablon asosidagi javob qaytaradi (fallback) — dastur
baribir ishlayveradi, faqat javob AI emas, qoidaviy bo‘ladi.

## 2. Frontendni ochish

Eng oson yo‘l — `frontend/index.html` faylini brauzerda to‘g‘ridan-to‘g‘ri ochish,
yoki mahalliy server orqali:

```bash
cd frontend
python3 -m http.server 5500
```

So‘ng brauzerda `http://localhost:5500` manzilini oching. Backend ishlab turgani kerak
(1-qadam), chunki frontend `http://localhost:8000` manziliga so‘rov yuboradi
(`frontend/app.js` va `frontend/admin.js` fayllaridagi `BASE_URL`ni boshqa manzilga
o'zgartirishingiz mumkin, masalan serverga joylashtirganda).

### Foydalanuvchi sifatida

Sahifa yuqorisidagi **"Ro‘yxatdan o‘tish"** tugmasi orqali hisob oching (login, email,
parol). Kirgandan so‘ng test natijalaringiz avtomatik saqlanadi va **"Mening
natijalarim"** bo‘limida ko'rinadi.

### Administrator paneli

`http://localhost:5500/admin.html` manziliga o'ting va standart (yoki siz
belgilagan) admin login/parol bilan kiring. Panelda:
- umumiy statistika (foydalanuvchilar, testlar, tekshiruvlar soni);
- foydalanuvchilar ro‘yxati va ularni o‘chirish;
- lug‘atga so‘z qo‘shish / tahrirlash / o‘chirish;
- test savollarini qo‘shish / tahrirlash / o‘chirish.

Barcha o'zgarishlar bazaga darhol yoziladi va saytda shu zahoti ko'rinadi.

## 3. Telegram botni ishga tushirish

```bash
cd telegram_bot
pip install -r requirements.txt
export BOT_TOKEN="123456:ABC-..."      # @BotFather orqali oling
export API_BASE="http://localhost:8000"
python bot.py
```

## Nima ishlaydi (joriy versiya)

| Modul | Holati |
|---|---|
| Imlo tekshiruvi | ✅ 40+ keng tarqalgan xato + qo‘shimchali shakllar (masalan, "universtitetga") |
| Grammatika tekshiruvi | ✅ Sodda evristika (payt so‘zi ↔ fe’l zamoni mosligi) |
| Uslub tekshiruvi | ✅ Takroriy so‘z ("juda juda") va tinish belgisi yo‘qligi |
| Lug‘at (ma’no/sinonim/antonim) | ✅ Bazada saqlanadi, admin panel orqali boshqariladi |
| Kunning so‘zi | ✅ Har kuni lug‘atdan avtomatik tanlanadi (`/api/word-of-day`) |
| Test tizimi + tavsiya | ✅ Bazada saqlanadi, natijada mavzular bo‘yicha vizual diagramma |
| Foydalanuvchi ro‘yxatdan o‘tishi / kirishi | ✅ JWT asosida, parollar xeshlangan holda saqlanadi |
| Foydalanuvchi profili (natijalar tarixi) | ✅ "Mening natijalarim" bo‘limi |
| Administrator paneli | ✅ Statistika, foydalanuvchilar, lug‘at va test savollarini boshqarish |
| Ma'lumotlar bazasi | ✅ SQLite (backend/data/app.db), SQLAlchemy orqali |
| AI yordamchi (rasmiy/sodda/qisqa) | ✅ Claude API bilan (kalit bo‘lsa) yoki shablon bilan |
| Telegram bot | ✅ Asosiy menyu + barcha modullar, uslub xatolari va etimologiya bilan |
| Web dizayn | ✅ Registon koshinlaridan ilhomlangan geometrik naqsh, jonli "oldin/keyin" namoyish animatsiyasi bo‘lgan hero bo‘lim |
| Nutq → Matn / Matn → Nutq | ⏳ Keyingi bosqich (alohida STT/TTS xizmati kerak) |
| Telegram bot orqali ro'yxatdan o'tish | ⏳ Keyingi bosqich (hozircha faqat veb-saytda) |

## Ushbu versiyada tuzatilgan kamchiliklar

- **Test bahosi noto'g'ri hisoblanishi**: avval `submit_quiz` har doim to'liq 15
  savolga nisbatan hisoblardi — Telegram botdagi qisqartirilgan (5 savolli) test
  natijasi va veb-saytdagi qisman javob berilgan test noto'g'ri foiz ko'rsatardi.
  Endi faqat haqiqatda javob berilgan savollar hisobga olinadi.
- **Lug‘at/test JSON fayllarda qattiq yozilgan edi** — endi bazada saqlanadi va
  admin panel orqali dasturchisiz boshqariladi.
- **Foydalanuvchi tizimi yo'q edi** — endi ro'yxatdan o'tish, kirish va shaxsiy
  natijalar tarixi mavjud.
- Bosh sahifa pastidagi "MVP versiya" yozuvi olib tashlandi.

## Keyingi qadamlar

1. **PostgreSQL'ga o'tish** — hozir SQLite bilan ishlaydi; `DATABASE_URL` muhit
   o'zgaruvchisini o'rnatish orqali PostgreSQL'ga almashtirish mumkin
   (masalan: `postgresql+psycopg2://user:pass@host/dbname`), kod o'zgarishsiz ishlaydi.
2. **Haqiqiy NLP modeli** — hozirgi qoidaviy tekshiruv o‘rniga o‘zbek tili korpusida
   o‘qitilgan grammatika modelini ulash.
3. **Nutq moduli** — Matn↔Nutq uchun tashqi STT/TTS API (masalan, Whisper + TTS xizmati).
4. **Telegram bot orqali ham ro'yxatdan o'tish** — botni veb-hisob bilan bog'lash.
5. **Deployment** — backend Render/Railway’ga, frontend Vercel’ga, bot doimiy serverga
   joylashtiriladi. Deploy qilishda `SECRET_KEY`, `ADMIN_PASSWORD` va `DATABASE_URL`ni
   albatta muhit o'zgaruvchilari orqali sozlang.
