# Config Manager v2

ربات جمع‌آوری، اعتبارسنجی و انتشار کانفیگ V2Ray — معماری async و لایه‌بندی‌شده.

## 🏗️ Stack

- **Bot:** python-telegram-bot v22 (async)
- **DB:** SQLAlchemy 2.0 async — SQLite (local) / PostgreSQL (Docker)
- **Scraper:** aiohttp + BeautifulSoup
- **Publisher:** asyncio Queue + flood control + retry logic
- **Scheduler:** APScheduler
- **Config:** pydantic-settings
- **Logging:** Loguru

## 📁 ساختار

```
├── main.py                 # نقطه ورود اصلی (bot + scraper + publisher)
├── constants.py            # مقادیر ثابت سراسری
├── .env.example           # نمونه پیکربندی
├── requirements.txt       # وابستگی‌های پروژه
│
├── app/                   # لایه ربات تلگرام
│   ├── bot/              # منوها و UI
│   ├── handlers/         # handler‌های ادمین و کاربر
│   └── middlewares/      # اعتبارسنجی و احراز هویت
│
├── core/                 # لایه مرکزی
│   ├── config.py         # تنظیمات (pydantic-settings)
│   ├── logger.py         # لاگ‌ با Loguru
│   ├── exceptions.py     # خطاهای سفارشی
│   └── utils.py          # توابع کمکی
│
├── database/             # لایه داده‌ها
│   ├── models.py         # مدل‌های SQLAlchemy
│   ├── session.py        # اتصال async
│   └── crud.py           # عملیات CRUD
│
├── processor/            # لایه پردازش
│   ├── parser.py         # پارس و واترمارک
│   └── validator.py      # اعتبارسنجی و deduplication
│
├── scraper/              # لایه جمع‌آوری
│   ├── base.py           # scraper اصلی
│   └── sources.py        # لیست منابع
│
├── publisher/            # لایه انتشار
│   ├── queue.py          # صف async
│   └── broadcaster.py    # ارسال به کانال + flood control
│
├── storage/              # ذخیره‌سازی فایل‌ها
├── shared_memory/        # حافظه اشتراکی (اختیاری)
├── tests/                # تست‌های واحد و یکپارچه
└── data/                 # فایل‌های داده (logs, exports, etc)
```

## 🚀 راه‌اندازی محلی

### 1️⃣ نصب وابستگی‌ها

```bash
python -m venv venv
source venv/bin/activate  # یا venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

### 2️⃣ پیکربندی

```bash
cp .env.example .env
```

سپس `.env` را ویرایش کنید و این مقادیر را وارد کنید:

- **BOT_TOKEN**: توکن ربات از @BotFather
- **OWNER_ID**: آیدی عددی صاحب ربات
- **CHANNEL_USERNAME**: نام کانالی که برای انتشار استفاده می‌شود (مثال: `@jojo_config`)

### 3️⃣ اجرا

```bash
python main.py
```

ربات شروع به کار کرد! استارت کنید: `/start`

## 🐳 Docker (PostgreSQL)

### 1️⃣ پیکربندی

```bash
cp .env.example .env
```

در `.env` تغییرات لازم را انجام دهید.

### 2️⃣ اجرا

```bash
docker compose up -d --build
```

## 🧪 تست‌کردن

```bash
pytest tests/ -v
```

### پوشش تست:
- ✅ مدل‌های دیتابیس
- ✅ CRUD عملیات
- ✅ پارس و اعتبارسنجی کانفیگ
- ✅ Handler‌های ادمین و کاربر
- ✅ اعتبارسنجی IP

## 📋 دستورات ربات

| دستور | توضیح | دسترسی |
|-------|--------|--------|
| `/start` | منوی اصلی | همه |
| `/health` | وضعیت سیستم | ادمین |

### منوی کاربر:
- 📦 **آخرین 20 کانفیگ** — export 20 کانفیگ اخیر
- 🌍 **فیلتر کشور** — کانفیگ‌های تفکیک شده بر اساس کشور
- ⚙️ **فیلتر پروتکل** — کانفیگ‌های تفکیک شده بر اساس پروتکل
- 🔢 **تعداد سفارشی** — export تعداد دلخواه

### منوی ادمین:
- 👤 **ادمین** — مدیریت ادمین‌ها (فقط مالک)
- 📊 **آمار** — تعداد کاربران و استارت‌ها
- 📢 **broadcast** — ارسال پیام به تمام کاربران
- ⭐ **VIP** — مدیریت کاربران VIP
- 🌐 **Clean IP** — آپلود و مدیریت IP‌های تمیز
- 🔄 **Scraper** — کنترل وضعیت scraper

## 🔧 تنظیمات

### `.env` - متغیرهای محیطی

```env
# Telegram
BOT_TOKEN=your_bot_token
OWNER_ID=your_user_id
CHANNEL_USERNAME=@your_channel

# Database (SQLite یا PostgreSQL)
DATABASE_URL=sqlite+aiosqlite:///data/main.db

# App
PROJECT_NAME=Config Manager
DEBUG=false
LOG_LEVEL=INFO

# Scraper
SCRAPER_ENABLED=true
SCRAPER_INTERVAL=300  # ثانیه
```

## 🔐 امنیت

- ✅ **احراز هویت:** فقط مالک می‌تواند ادمین اضافه کند
- ✅ **اعتبارسنجی IP:** تطابق Regex برای IP‌های Clean IP
- ✅ **Rate Limiting:** محدودیت برای API calls (ip-api.com)
- ✅ **Flood Control:** محدودیت انتشار در کانال
- ✅ **Error Logging:** تمام خطاها ثبت می‌شوند

## 📊 معماری

### Async Flow:

```
Telegram Event
    ↓
Handler (router)
    ↓
Auth Check
    ↓
Database / Processing
    ↓
Response / Queue
```

### Scraper Job (دوره‌ای):

```
Telegram Channels
    ↓
Scrape (aiohttp)
    ↓
Parse & Extract
    ↓
Validate (ping, dedup)
    ↓
Save to DB
    ↓
Publish Queue
    ↓
Broadcaster (with flood control)
```

## 🐛 مشکل‌گیری

### خطا: BOT_TOKEN نامعتبر

```
ValueError: فرمت BOT_TOKEN نامعتبر است.
```

**حل:** `BOT_TOKEN` خود را از @BotFather دریافت کرده و در `.env` قرار دهید.

### خطا: Database Connection

```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError)
```

**حل:** مجوزهای دسترسی به پوشه `data/` را بررسی کنید.

### Scraper نتایج نمی‌گذارد

**حل:**
1. مقدار `SCRAPER_INTERVAL` را کاهش دهید (مثال: 60)
2. منابع در `scraper/sources.py` را بررسی کنید
3. logs را در `data/logs/` مشاهده کنید

## 📝 لاگ‌ها

لاگ‌های هر روز در `data/logs/` ذخیره می‌شوند:

```
data/
├── logs/
│   ├── bot_2025-06-06.log
│   └── bot_2025-06-07.log
├── exports/
│   └── last_20_20250606_120000.txt
└── main.db
```

## 🤝 مشارکت

برای گزارش مشکل یا پیشنهاد بهبودی، issue باز کنید.

## 📄 لایسنس

این پروژه آزادانه برای استفاده، توسعه و توزیع است.
