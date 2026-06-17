@echo off
REM اسکریپت نصب و راه‌اندازی خودکار پروژه روی ویندوز
REM این اسکریپت Docker Desktop را نصب کرده و پروژه را آماده اجرا می‌کند

echo ========================================
echo      نصب و راه‌اندازی پروژه
echo ========================================
echo.

REM بررسی دسترسی ادمین
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] دسترسی ادمین تایید شد.
) else (
    echo [ERROR] این اسکریپت باید با دسترسی ادمین اجرا شود.
    echo لطفا Command Prompt را با Run as Administrator اجرا کنید.
    pause
    exit /b 1
)

REM بررسی نصب Docker
echo [INFO] بررسی نصب Docker...
docker --version >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] Docker قبلا نصب شده است.
) else (
    echo [WARN] Docker نصب نیست. در حال نصب Docker Desktop...

    REM دانلود Docker Desktop Installer
    echo [INFO] در حال دانلود Docker Desktop...
    powershell -Command "Invoke-WebRequest -Uri 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe' -OutFile 'DockerInstaller.exe'"

    echo [INFO] در حال نصب Docker Desktop...
    start /wait DockerInstaller.exe install quiet

    echo [INFO] Docker Desktop با موفقیت نصب شد.
    echo [INFO] لطفا سیستم را ریستارت کرده و دوباره این اسکریپت را اجرا کنید.
    pause
    exit /b 0
)

REM بررسی نصب Docker Compose
echo [INFO] بررسی نصب Docker Compose...
docker compose version >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] Docker Compose قبلا نصب شده است.
) else (
    echo [WARN] Docker Compose نصب نیست. در حال نصب Docker Compose...

    REM دانلود Docker Compose
    echo [INFO] در حال دانلود Docker Compose...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/docker/compose/releases/latest/download/docker-compose-windows-x86_64.exe' -OutFile 'docker-compose.exe'"

    REM کپی به مسیر Docker
    copy docker-compose.exe "%ProgramFiles%\Docker\Dockeresourcesin\docker-compose.exe"

    echo [INFO] Docker Compose با موفقیت نصب شد.
)

REM ایجاد فایل محیطی
echo [INFO] بررسی فایل محیطی...
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] ایجاد فایل .env از .env.example...
        copy ".env.example" ".env"
        echo [WARN] لطفا فایل .env را با تنظیمات مورد نیاز ویرایش کنید.
    ) else (
        echo [INFO] ایجاد فایل .env خالی...
        echo. > ".env"
    )
) else (
    echo [INFO] فایل .env از قبل وجود دارد.
)

REM ایجاد دایرکتوری‌های مورد نیاز
echo [INFO] ایجاد دایرکتوری‌های مورد نیاز...
if not exist "data" mkdir data
if not exist "data\logs" mkdir "data\logs"
if not exist "data\exports" mkdir "data\exports"
if not exist "data\clean_ip_exports" mkdir "data\clean_ip_exports"

REM ساخت و اجرای Docker
echo [INFO] در حال ساخت تصویر Docker...
docker compose build

echo [INFO] در حال راه‌اندازی سرویس...
docker compose up -d

echo [INFO] سرویس با موفقیت راه‌اندازی شد.
echo.
echo ========================================
echo      نصب و راه‌اندازی کامل شد
echo ========================================
echo.
echo برای مشاهده وضعیت سرویس از دستور زیر استفاده کنید:
echo   docker compose ps
echo.
echo برای مشاهده لاگ‌ها از دستور زیر استفاده کنید:
echo   docker compose logs -f
echo.
echo برای توقف سرویس از دستور زیر استفاده کنید:
echo   docker compose down
echo.
pause
