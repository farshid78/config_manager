
<div align="center">

<br>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/Config%20Manager-v2.0-9333ea?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Config%20Manager-v2.0-7c3aed?style=for-the-badge&logo=python&logoColor=white">
</picture>

<br>

### 🛡️ Automated V2Ray Config Collector, Validator & Publisher

**جمع‌آوری خودکار • اعتبارسنجی هوشمند • انتشار فوری**

<br>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/jojo_config)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![SQLite](https://img.shields.io/badge/SQLite-Async-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)

<br>

<a href="https://t.me/jojo_config">
  <img src="https://img.shields.io/badge/%F0%9F%93%A2%20Channel-@jojo_config-2AABEE?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Channel">
</a>

<br><br>

</div>

---

## 📖 فهرست مطالب

- [🎯 درباره پروژه](#-درباره-پروژه)
- [✨ ویژگی‌ها](#-ویژگی‌ها)
- [🏗️ معماری و ساختار](#️-معماری-و-ساختار)
- [⚙️ نحوه کارکرد](#️-نحوه-کارکرد)
- [🚀 نصب و راه‌اندازی](#-نصب-و-راهاندازی)
  - [🐧 لینوکس](#-لینوکس)
  - [🪟 ویندوز](#-ویندوز)
  - [🍎 macOS](#-macos)
  - [🐳 Docker](#-docker)
- [🔧 پیکربندی](#-پیکربندی)
- [📋 دستورات ربات](#-دستورات-ربات)
- [🔐 امنیت](#-امنیت)
- [📊 لاگ‌ها](#-لاگها)
- [🐛 مشکل‌گیری](#-مشکلسنجی)
- [🤝 مشارکت](#-مشارکت)
- [👨‍💻 سازنده](#️-سازنده)

---

## 🎯 درباره پروژه

**Config Manager** یک سیستم کاملاً خودکار برای جمع‌آوری، اعتبارسنجی و انتشار کانفیگ‌های V2Ray است. این ربات تلگرامی به صورت دوره‌ای از ده‌ها کانال تلگرامی و منبع اشتراک (Subscription) کانفیگ‌ها را جمع‌آوری می‌کند، آنها را اعتبارسنجی و فیلتر می‌کند، و سپس کانفیگ‌های معتبر را با واترمارک اختصاصی در کانال شما منتشر می‌کند.

### چرا Config Manager؟

| مشکل | راه‌حل |
|------|--------|
| 🔴 کانفیگ‌های تکراری و قدیمی | ✅ سیستم Deduplication بر اساس هش MD5 |
| 🔴 کانفیگ‌های غیرفعال و ناکارآمد | ✅ اعتبارسنجی هوشمند با تشخیص کشور |
| 🔴 انتشار دستی و زمان‌بر | ✅ انتشار خودکار با Flood Control |
| 🔴 عدم دسته‌بندی کانفیگ‌ها | ✅ فیلتر بر اساس کشور و پروتکل |
| 🔴 بدون واترمارک | ✅ تزریق خودکار واترمارک کانال |

---

## ✨ ویژگی‌ها

### 🔍 اسکرپر هوشمند
- جمع‌آوری خودکار از **کانال‌های تلگرامی** و **منابع اشتراک**
- پشتیبانی از پروتکل‌های **VMess, VLESS, Trojan, Shadowsocks**
- تشخیص خودکار Base64 و رمزگشایی
- پشتیبانی از **پروکسی** برای دسترسی از ایران

### ✅ اعتبارسنجی پیشرفته
- تشخیص کشور بر اساس **IP** (با کش محلی برای سرعت بیشتر)
- حذف کانفیگ‌های تکراری با **MD5 Hash**
- اعتبارسنجی دسته‌ای **Async** با Semaphore
- تست اتصال TCP (اختیاری)

### 📢 انتشار حرفه‌ای
- انتشار خودکار در کانال تلگرام با **Flood Control**
- واترمارک اختصاصی با **پرچم کشور** و **لینک کانال**
- صف انتشار **Async** با تاخیر هوشمند
- Retry خودکار در صورت خطا

### 🤖 ربات تلگرام
- منوی کاربر: دریافت کانفیگ بر اساس **کشور، پروتکل، تعداد**
- منوی ادمین: مدیریت ادمین‌ها، آمار، broadcast، Clean IP
- سیستم **VIP** برای کاربران ویژه
- آپلود فایل **Clean IP** و اعمال خودکار

### 🛡️ زیرساخت
- معماری **Async/Await** — عملیات همزمان بدون مسدودسازی
- **SQLite** (محلی) یا **PostgreSQL** (تولید)
- لاگ‌گیری حرفه‌ای با **Loguru** — فایل روزانه + کنسول
- زمان‌بند **APScheduler** برای اجرای دوره‌ای

---

## 🏗️ معماری و ساختار

```
config_manager/
│
├── 📄 main.py                    # نقطه ورود — راه‌اندازی ربات + اسکرپر + ناشر
├── 📄 constants.py               # مقادیر ثابت سراسری
├── 📄 .env.example               # نمونه پیکربندی محیطی
├── 📄 requirements.txt           # وابستگی‌های پایتون
├── 📄 docker-compose.yml         # پیکربندی Docker
├── 📄 Dockerfile                 # ایمیج Docker
│
├── 📂 app/                       # 🤖 لایه ربات تلگرام
│   ├── 📂 bot/                   #    منوها و رابط کاربری
│   │   ├── keyboards.py          #      دکمه‌های شیشه‌ای و منوها
│   │   └── texts.py              #      متون فارسی ربات
│   ├── 📂 handlers/              #    هندلرهای پیام و callback
│   │   ├── admin.py              #      عملیات ادمین (broadcast, VIP, Clean IP)
│   │   ├── router.py             #      مسیریاب callback‌ها
│   │   └── user.py               #      عملیات کاربر (start, export, filter)
│   └── 📂 middlewares/           #    میان‌افزارها
│       └── auth.py               #      احراز هویت کاربر و ادمین
│
├── 📂 core/                      # ⚙️ لایه مرکزی
│   ├── config.py                 #    تنظیمات (pydantic-settings + .env)
│   ├── logger.py                 #    لاگ‌گیری (Loguru — کنسول + فایل)
│   ├── exceptions.py             #    خطاهای سفارشی
│   ├── utils.py                  #    توابع کمکی (هش، پرچم، GeoIP, IP manager)
│   └── ip_manager.py             #    مدیریت Clean IP
│
├── 📂 database/                  # 💾 لایه داده‌ها
│   ├── models.py                 #    مدل‌های SQLAlchemy (User, Config, Admin, Source)
│   ├── session.py                #    اتصال Async (SQLite / PostgreSQL)
│   └── crud.py                   #    عملیات CRUD (batch save, dedup, stats)
│
├── 📂 processor/                 # ⚡ لایه پردازش
│   ├── parser.py                 #    پارس کانفیگ + تزریق واترمارک
│   └── validator.py              #    اعتبارسنجی + deduplication + تشخیص کشور
│
├── 📂 scraper/                   # 🔍 لایه جمع‌آوری
│   ├── base.py                   #    اسکرپر اصلی (تلگرام + اشتراک)
│   ├── subscription.py           #    اسکرپر منابع اشتراک (Base64 decode)
│   └── sources.py                #    لیست منابع پیش‌فرض
│
├── 📂 publisher/                 # 📢 لایه انتشار
│   ├── queue.py                  #    صف Async (producer-consumer)
│   └── broadcaster.py            #    ارسال به کانال + flood control + retry
│
├── 📂 utils/                     # 🛠️ ابزارهای کمکی
│   └── health.py                 #    بررسی سلامت سیستم
│
└── 📂 data/                      # 📁 فایل‌های داده (git-ignored)
    ├── logs/                     #    لاگ‌های روزانه
    ├── exports/                  #    فایل‌های خروجی کاربران
    └── main.db                   #    دیتابیس SQLite
```

---

## ⚙️ نحوه کارکرد

### 🔄 جریان اصلی (Pipeline)

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCRAPER JOB                              │
│                    (هر 5 دقیقه خودکار)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   📡 جمع‌آوری از منابع          │
        │   • کانال‌های تلگرام (HTML)     │
        │   • منابع اشتراک (Base64)       │
        │   • پشتیبانی از پروکسی          │
        └──────────────┬─────────────────┘
                       │
                       ▼
        ┌────────────────────────────────┐
        │   ✅ اعتبارسنجی (Validator)     │
        │   • تشخیص پروتکل               │
        │   • Deduplication (MD5)         │
        │   • تشخیص کشور (ipwhois.app)   │
        │   • تست اتصال TCP (اختیاری)     │
        └──────────────┬─────────────────┘
                       │
                       ▼
        ┌────────────────────────────────┐
        │   💾 ذخیره در دیتابیس           │
        │   • Batch Save (یک commit)     │
        │   • فیلتر کانفیگ‌های تکراری     │
        └──────────────┬─────────────────┘
                       │
                       ▼
        ┌────────────────────────────────┐
        │   🏷️ تزریق واترمارک            │
        │   • 🇮🇷 پرچم کشور              │
        │   • 🔗 لینک کانال تلگرام        │
        │   • vmess: تغییر فیلد ps       │
        │   • سایر: تغییر fragment (#)   │
        └──────────────┬─────────────────┘
                       │
                       ▼
        ┌────────────────────────────────┐
        │   📢 انتشار در کانال            │
        │   • صف Async                   │
        │   • Flood Control (تاخیر)      │
        │   • Retry خودکار               │
        │   • فرمت HTML زیبا             │
        └────────────────────────────────┘
```

### 📤 نمونه خروجی در کانال

```
🇳🇱 Netherlands ┃ ⚙️ VLESS
━━━━━━━━━━━━━━━━━━━━
vless://a13df940-020c-...@185.176.24.64:443?...
━━━━━━━━━━━━━━━━━━━━
📢 t.me/jojo_config
```

### 🤖 جریان ربات تلگرام

```
کاربر /start ──► منوی اصلی
                    │
                    ├── 📦 آخرین 20 کانفیگ
                    ├── 🌍 فیلتر کشور (🇮🇷 🇩🇪 🇳🇱 ...)
                    ├── ⚙️ فیلتر پروتکل (VLESS VMess Trojan SS)
                    └── 🔢 تعداد سفارشی (1-100)

ادمین /start ──► منوی ادمین
                    │
                    ├── 👥 مدیریت ادمین‌ها
                    ├── 📊 آمار سیستم
                    ├── 📢 Broadcast
                    ├── ⭐ مدیریت VIP
                    ├── 🌐 Clean IP
                    └── 🔄 کنترل Scraper
```

---

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها

- **Python 3.11+**
- **پروکسی** (در ایران — برای دسترسی به Telegram API و GeoIP)
- **Bot Token** از [@BotFather](https://t.me/BotFather)

---

### 🐧 لینوکس

```bash
# 1. کلون کردن پروژه
git clone https://github.com/farshidnabipour/config-manager.git
cd config-manager

# 2. ساخت محیط مجازی
python3 -m venv venv
source venv/bin/activate

# 3. نصب وابستگی‌ها
pip install -r requirements.txt

# 4. پیکربندی
cp .env.example .env
nano .env  # یا vim .env

# 5. اجرا
python main.py
```

#### 🔄 اجرا به عنوان سرویس (Systemd)

```bash
# ساخت فایل سرویس
sudo nano /etc/systemd/system/config-manager.service
```

محتوای فایل:
```ini
[Unit]
Description=Config Manager Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/config-manager
ExecStart=/path/to/config-manager/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# فعال‌سازی و شروع
sudo systemctl daemon-reload
sudo systemctl enable config-manager
sudo systemctl start config-manager

# مشاهده لاگ
sudo journalctl -u config-manager -f
```

---

### 🪟 ویندوز

```powershell
# 1. کلون کردن پروژه
git clone https://github.com/farshidnabipour/config-manager.git
cd config-manager

# 2. ساخت محیط مجازی
python -m venv venv
.env\Scripts\Activate.ps1

# 3. نصب وابستگی‌ها
pip install -r requirements.txt

# 4. پیکربندی
copy .env.example .env
notepad .env

# 5. اجرا
python main.py
```

> ⚠️ **نکته ویندوز:** اگر خطای ExecutionPolicy گرفتید:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

### 🍎 macOS

```bash
# 1. کلون کردن پروژه
git clone https://github.com/farshidnabipour/config-manager.git
cd config-manager

# 2. ساخت محیط مجازی
python3 -m venv venv
source venv/bin/activate

# 3. نصب وابستگی‌ها
pip install -r requirements.txt

# 4. پیکربندی
cp .env.example .env
nano .env

# 5. اجرا
python main.py
```

> 💡 **نکته macOS:** اگر Python 3.11 نصب نیست:
> ```bash
> brew install python@3.11
> ```

---

### 🐳 Docker

#### حالت پیش‌فرض (SQLite):

```bash
# 1. پیکربندی
cp .env.example .env
# .env را ویرایش کنید

# 2. ساخت و اجرا
docker compose up -d --build

# 3. مشاهده لاگ
docker compose logs -f
```

#### حالت PostgreSQL:

1. در `docker-compose.yml` سرویس `db` را از کامنت خارج کنید
2. در `requirements.txt` خط `asyncpg` را از کامنت خارج کنید
3. در `.env` مقدار `DATABASE_URL` را تنظیم کنید:
   ```env
   DATABASE_URL=postgresql+asyncpg://configbot:configbot@db:5432/configbot
   ```
4. اجرا:
   ```bash
   docker compose up -d --build
   ```

---

## 🔧 پیکربندی

فایل `.env` را بر اساس نمونه زیر تکمیل کنید:

```env
# ═══════════════════════════════════════
# 🤖 Telegram Bot
# ═══════════════════════════════════════
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
OWNER_ID=123456789
CHANNEL_USERNAME=@jojo_config

# ═══════════════════════════════════════
# 💾 Database
# ═══════════════════════════════════════
# SQLite (محلی):
DATABASE_URL=sqlite+aiosqlite:///data/main.db
# PostgreSQL (تولید):
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/configbot

# ═══════════════════════════════════════
# 📱 App Settings
# ═══════════════════════════════════════
PROJECT_NAME=Config Manager
DEBUG=false
LOG_LEVEL=INFO

# ═══════════════════════════════════════
# 🔍 Scraper Settings
# ═══════════════════════════════════════
SCRAPER_ENABLED=true
SCRAPER_INTERVAL=300
SCRAPER_PROXY=http://127.0.0.1:10808
SCRAPER_PUBLISH_LIMIT=20
```

### توضیح متغیرها

| متغیر | توضیح | پیش‌فرض |
|-------|--------|---------|
| `BOT_TOKEN` | توکن ربات از @BotFather | — (اجباری) |
| `OWNER_ID` | آیدی عددی مالک ربات | — (اجباری) |
| `CHANNEL_USERNAME` | نام کانال انتشار (با @) | — (اجباری) |
| `DATABASE_URL` | نشانی دیتابیس | `sqlite+aiosqlite:///data/main.db` |
| `SCRAPER_ENABLED` | فعال/غیرفعال بودن اسکرپر | `true` |
| `SCRAPER_INTERVAL` | فاصله زمانی اسکرپ (ثانیه) | `300` |
| `SCRAPER_PROXY` | نشانی پروکسی HTTP/SOCKS5 | خالی |
| `SCRAPER_PUBLISH_LIMIT` | حداکثر کانفیگ از هر منبع | `20` |

---

## 📋 دستورات ربات

### دستورات عمومی

| دستور | توضیح | دسترسی |
|-------|--------|--------|
| `/start` | نمایش منوی اصلی | 👤 همه |
| `/health` | وضعیت سلامت سیستم | 🛡️ ادمین |

### 📦 منوی کاربر

| عملیات | توضیح |
|--------|--------|
| 📦 **آخرین 20 کانفیگ** | دریافت 20 کانفیگ اخیر |
| 🌍 **فیلتر کشور** | کانفیگ‌های یک کشور خاص |
| ⚙️ **فیلتر پروتکل** | کانفیگ‌های یک پروتکل خاص |
| 🔢 **تعداد سفارشی** | دریافت تعداد دلخواه (1-100) |

### 🛡️ منوی ادمین

| عملیات | توضیح |
|--------|--------|
| 👥 **مدیریت ادمین‌ها** | افزودن/حذف ادمین (فقط مالک) |
| 📊 **آمار سیستم** | تعداد کاربران، کانفیگ‌ها، استارت‌ها |
| 📢 **Broadcast** | ارسال پیام به تمام کاربران |
| ⭐ **VIP** | مدیریت کاربران ویژه |
| 🌐 **Clean IP** | آپلود و مدیریت IP‌های تمیز |
| 🔄 **Scraper** | کنترل و وضعیت اسکرپر |

---

## 🔐 امنیت

| ویژگی | توضیح |
|--------|--------|
| ✅ احراز هویت | فقط مالک می‌تواند ادمین اضافه کند |
| ✅ اعتبارسنجی IP | تطابق Regex برای Clean IP |
| ✅ Rate Limiting | محدودیت درخواست‌های GeoIP API |
| ✅ Flood Control | تاخیر بین انتشار کانفیگ‌ها در کانال |
| ✅ Error Logging | ثبت تمام خطاها در فایل لاگ |
| ✅ Deduplication | جلوگیری از ذخیره کانفیگ تکراری |

---

## 📊 لاگ‌ها

لاگ‌ها به صورت روزانه در `data/logs/` ذخیره می‌شوند:

```
data/
├── logs/
│   ├── bot_2026-06-06.log      # لاگ روزانه
│   └── bot_2026-06-07.log
├── exports/
│   └── last_20_20260606.txt    # فایل خروجی کاربر
└── main.db                     # دیتابیس SQLite
```

### نمونه لاگ کنسول:

```
00:44:14 | INFO  | Logging initialized | level=INFO
00:44:15 | INFO  | Starting Config Manager ...
00:44:16 | INFO  | Scrape complete | total_configs=2681
00:44:17 | INFO  | Validating filembad | configs=20
00:44:22 | INFO  | Validated filembad | valid=15
00:44:22 | INFO  | New configs from filembad: 8
00:44:23 | INFO  | Published config | country=NL
```

---

## 🐛 مشکل‌گیری

### ❌ BOT_TOKEN نامعتبر

```
ValueError: Invalid BOT_TOKEN format
```

**حل:** توکن معتبر از [@BotFather](https://t.me/BotFather) دریافت کنید.

---

### ❌ خطای اتصال به دیتابیس

```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError)
```

**حل:** مجوز دسترسی به پوشه `data/` را بررسی کنید:
```bash
chmod 755 data/
```

---

### ❌ اسکرپر نتیجه نمی‌دهد

**حل:**
1. `SCRAPER_ENABLED=true` در `.env` تنظیم کنید
2. پروکسی را بررسی کنید: `SCRAPER_PROXY=http://127.0.0.1:10808`
3. لاگ‌ها را در `data/logs/` بررسی کنید

---

### ❌ همه کانفیگ‌ها UN هستند

**حل:** پروکسی برای دسترسی به GeoIP API لازم است:
```env
SCRAPER_PROXY=http://127.0.0.1:10808
```

---

### ❌ خطای Connection Timeout

```
ConnectionTimeoutError: Connection timeout to host api.telegram.org
```

**حل:** ربات برای اتصال به Telegram API به پروکسی نیاز دارد — `SCRAPER_PROXY` را تنظیم کنید.

---

## 🤝 مشارکت

از مشارکت شما استقبال می‌شود! 🎉

1. پروژه را Fork کنید
2. شاخه جدید بسازید: `git checkout -b feature/amazing-feature`
3. تغییرات را Commit کنید: `git commit -m 'Add amazing feature'`
4. Push کنید: `git push origin feature/amazing-feature`
5. Pull Request باز کنید

---

## 📄 لایسنس

این پروژه تحت لایسنس **MIT** منتشر شده است — برای جزئیات فایل [LICENSE](LICENSE) را ببینید.

---

<div align="center">

## 👨‍💻 سازنده

<br>

<img src="https://img.shields.io/badge/Farshid%20Nabipour-Developer-6366f1?style=for-the-badge&logo=github&logoColor=white" alt="Farshid Nabipour">

<br><br>

**Farshid Nabipour** — توسعه‌دهنده و نگهدارنده پروژه

[![GitHub](https://img.shields.io/badge/GitHub-farshid78-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/farshid78)
[![Telegram](https://img.shields.io/badge/Telegram-@jojo__config-2AABEE?style=flat-square&logo=telegram&logoColor=white)](https://t.me/jojo_config)

<br>

### 📢 کانال تلگرام

[![Channel](https://img.shields.io/badge/📢%20کانال%20تلگرام-@jojo__config-2AABEE?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/jojo_config)

> کانفیگ‌های معتبر V2Ray با پرچم کشور — روزانه به‌روز می‌شود

<br>

---

⭐ اگر این پروژه مفید بود، ستاره بدهید!

**Made with ❤️ by [Farshid Nabipour](https://github.com/farshid78)**

</div>
