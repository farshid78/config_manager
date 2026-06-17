-- database/migrations/schema.sql — اسکیمای پایگاه داده PostgreSQL
-- این فایل ساختار جداول مورد نیاز برای سیستم را تعریف می‌کند

-- جدول admins: ادمین‌های سیستم
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    added_by BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- جدول scraper_sources: منابع اسکرپر
CREATE TABLE IF NOT EXISTS scraper_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('telegram', 'subscription')),
    is_active BOOLEAN DEFAULT true,
    last_scraped TIMESTAMP WITH TIME ZONE,
    last_config_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, source_type)
);

-- جدول configs: کانفیگ‌های ذخیره شده
CREATE TABLE IF NOT EXISTS configs (
    id SERIAL PRIMARY KEY,
    config_hash VARCHAR(64) NOT NULL,
    country_code VARCHAR(2) NOT NULL,
    protocol VARCHAR(20) NOT NULL,
    host VARCHAR(255),
    port INTEGER,
    raw_config TEXT NOT NULL,
    watermarked_config TEXT NOT NULL,
    is_valid BOOLEAN DEFAULT true,
    source VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(config_hash)
);

-- شاخص‌ها برای افزایش عملکرد کوئری‌ها
CREATE INDEX IF NOT EXISTS idx_configs_country ON configs(country_code);
CREATE INDEX IF NOT EXISTS idx_configs_protocol ON configs(protocol);
CREATE INDEX IF NOT EXISTS idx_configs_host ON configs(host);
CREATE INDEX IF NOT EXISTS idx_configs_created_at ON configs(created_at);
CREATE INDEX IF NOT EXISTS idx_configs_source ON configs(source);

-- جدول stats: آمار سیستم
CREATE TABLE IF NOT EXISTS stats (
    id SERIAL PRIMARY KEY,
    stat_date DATE NOT NULL,
    total_configs INTEGER DEFAULT 0,
    valid_configs INTEGER DEFAULT 0,
    invalid_configs INTEGER DEFAULT 0,
    published_configs INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stat_date)
);

-- جدول system_logs: لاگ‌های سیستم
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    log_level VARCHAR(10) NOT NULL,
    log_message TEXT NOT NULL,
    service_name VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- توابع برای به‌روزرسانی خودکار فیلد updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- تریگرها برای به‌روزرسانی خودکار فیلد updated_at
CREATE TRIGGER update_admins_updated_at BEFORE UPDATE ON admins
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scraper_sources_updated_at BEFORE UPDATE ON scraper_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_configs_updated_at BEFORE UPDATE ON configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View برای نمایش آمار روزانه
CREATE OR REPLACE VIEW daily_stats AS
SELECT
    stat_date,
    total_configs,
    valid_configs,
    invalid_configs,
    published_configs,
    (valid_configs::FLOAT / NULLIF(total_configs, 0) * 100) AS validity_percentage
FROM stats
ORDER BY stat_date DESC;

-- View برای نمایش کانفیگ‌های جدید
CREATE OR REPLACE VIEW latest_configs AS
SELECT
    id,
    country_code,
    protocol,
    host,
    source,
    created_at
FROM configs
ORDER BY created_at DESC
LIMIT 50;
