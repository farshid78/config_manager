# راهنمای اجرای پروژه روی پلتفرم‌های مختلف

این راهنما به شما کمک می‌کند تا پروژه را روی هاست، سرور لینوکسی و سرور ویندوز اجرا کنید.

## پیش‌نیازها

- Docker و Docker Compose نصب شده روی سیستم مقصد
- دسترسی به اینترنت برای دانده تصاویر و وابستگی‌ها
- فایل‌های پروژه (شامل Dockerfile و docker-compose.yml)

## 1. اجرا روی هاست (Cloud Hosting)

### استفاده از سرویس‌های ابری با پشتیبانی از Docker

#### Docker Cloud (Docker Hub)

1. **ساخت حساب کاربری در Docker Hub**
   - به [Docker Hub](https://hub.docker.com/) بروید و ثبت‌نام کنید

2. **آپلود پروژه به Docker Hub**
   ```bash
   # ساخت تصویر Docker
   docker build -t your-username/config-manager .

   # تگ‌گذاری برای پوشه ابری
   docker tag your-username/config-manager your-username/config-manager:latest

   # لاگین به Docker Hub
   docker login

   # آپلود تصویر
   docker push your-username/config-manager:latest
   ```

3. **استفاده از Docker Cloud**
   - به حساب کاربری خود در Docker Cloud وارد شوید
   - سرویس جدیدی با استفاده از تصویر آپلود شده ایجاد کنید
   - منابع مورد نیاز (CPU، RAM) را تنظیم کنید
   - دامنه و تنظیمات شبکه را وارد کنید

#### Google Cloud Run

1. **ساخت تصویر Docker**
   ```bash
   docker build -t gcr.io/your-project/config-manager .
   ```

2. **آپلود به Google Container Registry**
   ```bash
   docker push gcr.io/your-project/config-manager
   ```

3. **استفاده از Google Cloud Run**
   - به کنسول Google Cloud بروید
   - Cloud Run را انتخاب کنید
   - سرویس جدیدی با استفاده از تصویر آپلود شده ایجاد کنید
   - تنظیمات لازم را وارد و سرویس را مستقر کنید

#### AWS ECS (Elastic Container Service)

1. **ساخت تصویر Docker**
   ```bash
   docker build -t your-account.dkr.ecr.your-region.amazonaws.com/config-manager .
   ```

2. **آپلود به Amazon ECR**
   ```bash
   docker push your-account.dkr.ecr.your-region.amazonaws.com/config-manager
   ```

3. **استفاده از AWS ECS**
   - به کنسول AWS بروید
   - ECS را انتخاب کنید
   - Task Definition جدیدی ایجاد کنید
   - سرویس جدیدی با استفاده از Task Definition ایجاد کنید

## 2. اجرا روی سرور لینوکسی

### نصب Docker و Docker Compose

```bash
# به‌روزرسانی سیستم
sudo apt update && sudo apt upgrade -y

# نصب Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# اضافه کردن کاربر به گروه Docker
sudo usermod -aG docker $USER

# نصب Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### راه‌اندازی پروژه

1. **کپی پروژه روی سرور**
   ```bash
   # با استفاده از git
   git clone https://github.com/your-username/config-manager.git

   # یا آپلود مستقیم فایل‌ها
   scp -r /path/to/local/config-user/ user@server:/path/to/remote/
   ```

2. **تنظیم فایل‌ها**
   ```bash
   cd config-manager

   # ایجاد فایل محیطی
   cp .env.example .env

   # ویرایش فایل .env برای تنظیمات لازم
   nano .env
   ```

3. **ساخت و اجرای Docker**
   ```bash
   # ساخت تصویر
   docker-compose build

   # اجرای سرویس
   docker-compose up -d
   ```

### مدیریت سرویس با systemd

برای اجرای خودکار و مدیریت بهتر سرویس:

```bash
# ایجاد فایل سرویس systemd
sudo nano /etc/systemd/system/config-manager.service
```

محتوای فایل:

```ini
[Unit]
Description=Config Manager Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/config-manager
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0
User=root
Group=docker

[Install]
WantedBy=multi-user.target
```

فعال‌سازی سرویس:

```bash
sudo systemctl daemon-reload
sudo systemctl enable config-manager
sudo systemctl start config-manager
```

## 3. اجرا روی سرور ویندوز

### استفاده از Docker Desktop for Windows

1. **نصب Docker Desktop**
   - از [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop) دانلود و نصب کنید
   - در هنگام نصب، گزینه‌های مربوط به WSL 2 و Hyper-V را فعال کنید

2. **راه‌اندازی پروژه**
   - پروژه را در یک دایرکتوری روی ویندوز کپی کنید
   - PowerShell یا Command Prompt را با دسترسی ادمین باز کنید
   - به دایرکتوری پروژه بروید
   - دستورات زیر را اجرا کنید:

   ```powershell
   # ساخت تصویر Docker
   docker-compose build

   # اجرای سرویس
   docker-compose up -d
   ```

### استفاده از WSL 2 (Windows Subsystem for Linux)

1. **نصب WSL 2**
   ```powershell
   # در PowerShell با دسترسی ادمین
   wsl --install
   ```

2. **نصب Docker در WSL**
   ```bash
   # پس از نصب WSL، اوبونتو را باز کنید
   sudo apt update && sudo apt upgrade -y

   # نصب Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # اضافه کردن کاربر به گروه Docker
   sudo usermod -aG docker $USER
   ```

3. **راه‌اندازی پروژه**
   ```bash
   # کپی پروژه به WSL
   cp -r /mnt/c/path/to/config-manager ~/
   cd ~/config-manager

   # ساخت و اجرای Docker
   docker-compose build
   docker-compose up -d
   ```

## نکات مهم برای اجرا روی پلتفرم‌های مختلف

1. **مدیریت داده‌ها**:
   - همیشه از volumes برای ذخیره داده‌های مهم استفاده کنید
   - داده‌ها بین اجراهای مختلف باقی می‌مانند

2. **تنظیمات شبکه**:
   - در محیط‌های ابری، پورت‌ها را به درستی تنظیم کنید
   - از تنظیمات امنیتی مناسب برای دسترسی به سرویس استفاده کنید

3. **پیکربندی منابع**:
   - بر اساس منابع سرور، محدودیت‌های CPU و RAM را تنظیم کنید
   - در صورت نیاز، مقیاس‌پذیری را فعال کنید

4. **پشتیبانی از معماری**:
   - برای معماری‌های مختلف (x86, ARM) از پارامتر TARGETPLATFORM استفاده کنید
   - در هنگام build از معماری صحیح استفاده کنید

5. **به‌روزرسانی**:
   - برای به‌روزرسانی سرویس، از دستور زیر استفاده کنید:
   ```bash
   docker-compose pull && docker-compose up -d
   ```

## عیب‌یابی (Troubleshooting)

1. **بررسی لاگ‌ها**:
   ```bash
   docker-compose logs -f
   ```

2. **بررسی وضعیت سرویس‌ها**:
   ```bash
   docker-compose ps
   ```

3. **دسترسی به محیط داخل کانتینر**:
   ```bash
   docker-compose exec bot bash
   ```

4. **پاک کردن داده‌ها** (در صورت نیاز):
   ```bash
   docker-compose down -v
   ```

با رعایت این راهنما، پروژه شما باید به راحتی روی هر پلتفرم‌ای اجرا شود.
