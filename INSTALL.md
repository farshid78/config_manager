# INSTALL / راهنمای نصب و استقرار (به‌روز)

این فایل مکمل `README.md` است و قدم‌های نصب را دقیق‌تر و قابل اجرا روی هاست‌های مختلف (لینوکس/ویندوز) پوشش می‌دهد.

> نکته مهم: پیاده‌سازی این پروژه روی **Python 3.11+** و در محیط بهتر، از طریق **Docker Compose** انجام می‌شود. اگر Docker ندارید، روش نصب مستقیم هم ارائه شده است.

---

## 1) پیش‌نیازها

### 1.1. اطلاعات لازم
- `BOT_TOKEN` از طریق `@BotFather`
- `OWNER_ID` (آیدی عددی مالک ربات)
- `CHANNEL_USERNAME` نام کانال انتشار (مثلاً `@jojo_config`)

### 1.2. دسترسی شبکه
- پروژه از `api.telegram.org` برای polling ربات استفاده می‌کند.
- اگر از ایران اجرا می‌کنید و اتصال مشکل دارد، احتمالاً باید پروکسی فعال کنید.

---

## 2) نصب سریع با Docker (توصیه‌شده)

### 2.1. نصب Docker و Docker Compose روی لینوکس

#### اوبونتو/دیبیان (نمونه)
```bash
sudo apt update && sudo apt upgrade -y

# نصب Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# اضافه کردن کاربر به گروه docker (برای اجرای بدون sudo)
sudo usermod -aG docker $USER

# نصب Docker Compose (نسخه 1.29.2 مطابق راهنماهای پروژه)
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

> برای اینکه گروه docker روی ترمینال فعلی اثر کند، یک بار logout/login کنید یا:
```bash
newgrp docker
```

### 2.2. آماده‌سازی پروژه
```bash
cd /path/to/config_manager

# ساخت فایل env
cp .env.example .env
nano .env
```

حداقل مقادیر لازم در `.env`:
```env
BOT_TOKEN=...
OWNER_ID=...
CHANNEL_USERNAME=@...

# برای SQLite (پیش‌فرض)
DATABASE_URL=sqlite+aiosqlite:///data/main.db

# اگر نیاز به پروکسی دارید
SCRAPER_ENABLED=true
SCRAPER_PROXY=http://127.0.0.1:10808
```

### 2.3. اجرا
```bash
docker-compose up -d --build
```

### 2.4. مشاهده لاگ
```bash
docker-compose logs -f
```

### 2.5. مدیریت سرویس
- ری‌استارت:
```bash
docker-compose restart
```
- توقف:
```bash
docker-compose down
```
- پاک‌سازی کامل داده‌ها (با احتیاط):
```bash
docker-compose down -v
```

---

## 3) نصب بدون Docker (اجرای مستقیم با Python)

### 3.1. راه‌اندازی محیط مجازی
```bash
cd /path/to/config_manager
python3 -m venv venv
source venv/bin/activate
```

### 3.2. نصب وابستگی‌ها
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3. تنظیم `.env`
```bash
cp .env.example .env
nano .env
```

### 3.4. اجرای برنامه
```bash
python main.py
```

### 3.5. اطمینان از دسترسی نوشتن به data/
برای اینکه SQLite و لاگ‌ها ساخته شوند:
```bash
chmod 755 data/
```

---

## 4) اجرای خودکار با systemd (لینوکس)

### 4.1. ساخت فایل سرویس
```bash
sudo nano /etc/systemd/system/config-manager.service
```

مثال برای روش اجرای مستقیم:
```ini
[Unit]
Description=Config Manager Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/config_manager
ExecStart=/path/to/config_manager/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.2. فعال‌سازی و اجرا
```bash
sudo systemctl daemon-reload
sudo systemctl enable config-manager
sudo systemctl start config-manager

sudo journalctl -u config-manager -f
```

---

## 5) نکات ضروری برای رفع خطاهای رایج

### 5.1. خطای `Invalid BOT_TOKEN format`
- `BOT_TOKEN` را با فرمت درست (دارای `:`) در `.env` تنظیم کنید.

### 5.2. خطای دیتابیس SQLite
- مجوز نوشتن به `data/` را بررسی کنید.

### 5.3. Timeout برای Telegram
- اگر در ایران هستید، معمولاً نیاز به پروکسی دارید.
- `SCRAPER_PROXY` یا تنظیمات پروکسی محیطی را اصلاح کنید.

---

## 6) پیگیری وضعیت (چک لیست سریع)

1) `BOT_TOKEN` و `OWNER_ID` درست است؟
2) `.env` داخل همان مسیری است که اجرا می‌کنید؟
3) اگر Docker اجرا می‌کنید، volume ها برای data/logs فعال هستند؟
4) لاگ‌ها را بررسی کرده‌اید؟ (`docker-compose logs -f`)

---

## 7) تغییرات اخیر در INSTALL.md
- افزودن چک لیست پیش‌نیازها
- افزودن مراحل دقیق نصب Docker + Compose روی لینوکس
- افزودن راهنمای نصب مستقیم بدون Docker
- افزودن راه‌اندازی systemd با قالب آماده
- افزودن چک لیست خطاهای رایج

