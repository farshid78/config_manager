# TODO - بهینه‌سازی سرعت ارسال کانفیگ به کانال

- [x] 1) افزودن کانفیگ concurrency به `constants.py` (پیش‌فرض 3)
- [x] 2) تغییر منطق worker در `publisher/broadcaster.py` برای ارسال همزمان با concurrency محدود
- [x] 3) کاهش اثر bottleneck ناشی از `PUBLISH_DELAY_SECONDS` در حالت همزمانی

- [ ] 4) تست سبک: اجرای unit/test یا اجرای کوتاه و بررسی لاگ‌ها برای 429
- [ ] 5) در صورت نیاز: تنظیم مجدد `PUBLISH_DELAY_SECONDS` / `PUBLISH_BATCH_*` بر اساس لاگ


