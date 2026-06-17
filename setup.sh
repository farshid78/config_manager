#!/bin/bash

# اسکریپت نصب و راه‌اندازی خودکار پروژه روی سیستم‌های لینوکسی
# این اسکریپت Docker و Docker Compose را نصب کرده و پروژه را آماده اجرا می‌کند

set -e  # خروج در صورت خطا

# رنگ‌ها برای خروجی رنگی
RED='[0;31m'
GREEN='[0;32m'
YELLOW='[1;33m'
NC='[0m' # No Color

# تابع نمایش پیام
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# بررسی دسترسی root
if [[ $EUID -ne 0 ]]; then
   log_error "این اسکریپت باید با دسترسی root اجرا شود. لطفا با 'sudo' اجرا کنید."
   exit 1
fi

# بررسی وجود پکیج‌های مورد اولیه
check_dependencies() {
    log_info "بررسی وابستگی‌های اولیه..."

    if ! command -v curl &> /dev/null; then
        log_warn "curl نصب نیست. در حال نصب..."
        apt-get update
        apt-get install -y curl
    fi

    if ! command -v git &> /dev/null; then
        log_warn "git نصب نیست. در حال نصب..."
        apt-get update
        apt-get install -y git
    fi

    log_info "وابستگی‌های اولیه آماده هستند."
}

# نصب Docker
install_docker() {
    log_info "در حال نصب Docker..."

    # حذف نسخه‌های قدیمی Docker
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # نصب Docker از طریق رسمی repository
    apt-get update
    apt-get install -y         ca-certificates         curl         gnupg         lsb-release

    # اضافه کردن کلید GPG رسمی Docker
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # اضافه کردن repository Docker
    echo         "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu         $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # نصب Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # اضافه کردن کاربر به گروه docker
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker "$SUDO_USER"
        log_info "کاربر $SUDO_USER به گروه docker اضافه شد."
    fi

    log_info "Docker با موفقیت نصب شد."
}

# نصب Docker Compose
install_docker_compose() {
    log_info "در حال نصب Docker Compose..."

    # دانلود آخرین نسخه Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

    # تنظیم دسترسی اجرایی
    chmod +x /usr/local/bin/docker-compose

    log_info "Docker Compose با موفقیت نصب شد."
}

# ایجاد فایل محیطی
create_env_file() {
    log_info "ایجاد فایل محیطی..."

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_info "فایل .env از .env.example ایجاد شد."
            log_warn "لطفا فایل .env را با تنظیمات مورد نیاز ویرایش کنید."
        else
            log_warn "فایل .env.example یافت نشد. فایل .env خالی ایجاد می‌شود."
            touch .env
        fi
    else
        log_info "فایل .env از قبل وجود دارد."
    fi
}

# ساخت دایرکتوری‌های مورد نیاز
create_directories() {
    log_info "ایجاد دایرکتوری‌های مورد نیاز..."

    mkdir -p data/logs data/exports data/clean_ip_exports
    log_info "دایرکتوری‌های مورد نیاز ایجاد شدند."
}

# راه‌اندازی سرویس
start_service() {
    log_info "در حال راه‌اندازی سرویس..."

    # ساخت تصویر Docker
    docker-compose build

    # اجرا در پس‌زمینه
    docker-compose up -d

    log_info "سرویس با موفقیت راه‌اندازی شد."
}

# نمایش وضعیت سرویس
show_status() {
    log_info "وضعیت سرویس:"
    docker-compose ps

    log_info "برای مشاهده لاگ‌ها از دستور زیر استفاده کنید:"
    echo "  docker-compose logs -f"
}

# تابع اصلی
main() {
    log_info "شروع فرآیند نصب و راه‌اندازی پروژه..."

    check_dependencies
    install_docker
    install_docker_compose
    create_env_file
    create_directories
    start_service
    show_status

    log_info "نصب و راه‌اندازی با موفقیت انجام شد."
    log_info "برای مشاهده وضعیت سرویس از دستور 'docker-compose ps' استفاده کنید."
    log_info "برای مشاهده لاگ‌ها از دستور 'docker-compose logs -f' استفاده کنید."
}

# اجرای تابع اصلی
main "$@"
