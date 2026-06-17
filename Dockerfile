# استفاده از پایه‌های رسمی پایتون با پشتیبانی از معماری‌های مختلف
ARG TARGETPLATFORM=linux/amd64
FROM --platform=$TARGETPLATFORM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# نصب وابستگی‌های سیستمی مورد نیاز
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# کپی و نصب وابستگی‌های پایتون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد پروژه
COPY . .

# ایجاد دایرکتوری‌های مورد نیاز
RUN mkdir -p data/logs data/exports data/clean_ips

# دستور اجرای برنامه
CMD ["python", "main.py"]
