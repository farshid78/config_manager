# CLEANUP_REPORT.md

## Scope & approach
- No files were deleted or modified.
- Repo was inspected at the file/folder level.
- A dependency/entry-point map was inferred by reading runtime entrypoints and key modules.
- Because fast full-text search (ripgrep) isn’t available in the environment, deeper cross-referencing was done by manually reading high-impact files (e.g., `main.py`, core config/utils, and bot handlers).

## Runtime entry points (confirmed)
- `main.py`
  - Entry via `if __name__ == "__main__": main()`.
  - Creates Telegram `Application`.
  - Registers handlers:
    - `CommandHandler("start", start_command)`
    - `CommandHandler("health", health_command)`
    - `CallbackQueryHandler(callback_router)`
    - `MessageHandler(filters.TEXT & ~filters.COMMAND, message_router)`
    - `MessageHandler(filters.Document.ALL, handle_document)`
  - Background services in `post_init()`:
    - `init_db()`
    - `migrate_admins_json()`
    - `seed_default_sources()`
    - `Broadcaster().start()`
    - `AsyncIOScheduler` running `scraper_job()` every `settings.scraper_interval`.

## Component/module dependency sketch (partial, based on inspected files)
### Bot layer
- `app/handlers/router.py`
  - Depends on:
    - `app.bot.menus_refactor.main_menu`
    - `app.handlers.admin` and `app.handlers.user` (callback & text dispatch)
    - `app.middlewares.auth.is_admin`
    - `database.session.get_session_factory`
- `app/handlers/user.py`
  - Depends on:
    - `app.bot.menus_refactor` (menus)
    - `app.middlewares.auth.is_admin`
    - `database.crud.filter_configs`, `database.crud.get_last_configs`
    - `core.config.BASE_DIR`
    - `core.utils.get_flag`, `core.utils.detect_protocol`
- `app/handlers/admin.py`
  - Depends on:
    - `app.bot.menus_refactor` (many menu builders)
    - `app.middlewares.auth` (admin/owner guards)
    - `core.utils.generate_config`
    - `database.crud` (many operations)
    - `database.models` (`CleanIP`, `ProcessedConfig`)
    - `utils.health`
    - `core.ip_manager.apply_ips_to_configs`
    - `core.white_configs_perf_tester` (white perf)

### Core layer
- `core/config.py`
  - Loads `.env` from `BASE_DIR/.env`.
  - Caches settings via `lru_cache`.
- `core/utils.py`
  - Provides config parsing helpers and GeoIP/country utils.

### Scraper/processor/publisher/data
- Entrypoint uses:
  - `scraper.base.TelegramChannelScraper`
  - `processor.validator.ConfigValidator`
  - `publisher.queue.PublishQueue`
  - `publisher.broadcaster.Broadcaster`
  - `database.crud.batch_save_configs`, `crud.list_scraper_sources`, `crud.add_scraper_source`, etc. (referenced from `main.py`)

## Candidate unused items (not deleted)
Because full static analysis across imports/dynamic usage wasn’t possible without ripgrep, confidence levels are conservative.

### 1) Possibly unused: `tmp_init_test.py`
- Path: `tmp_init_test.py`
- Reason (appears unused): Looks like an ad-hoc test/helper (name suggests temporary init test). Not referenced from `main.py` or `setup.py` during inspected reads.
- Confidence: Medium
- What could break if removed:
  - If CI/tests import it indirectly, or developers rely on it for manual testing.

### 2) Possibly unused: `data/` directory (as a folder)
- Path: `data/`
- Reason (appears unused): Folder exists but contents are not visible in the file list; however runtime config uses `DATA_DIR` for SQLite DB/logs/exports.
- Confidence: Low
- What could break if removed:
  - `core/config.py` creates/uses `BASE_DIR / "data"`.
  - Runtime may fail on missing directories for DB/log exports.

### 3) Possibly unused: `processor/validator.py` vs `core/white_configs_perf_tester*.py` (verify)
- Path(s):
  - `processor/validator.py`
  - `core/white_configs_perf_tester.py`
  - `core/_white_configs_perf_tester_export_fix.py`
- Reason (appears unused): White-perf tester looks specialized; internal helper `_white_configs_perf_tester_export_fix.py` might be legacy or unused.
- Confidence: Medium
- What could break if removed:
  - Admin white-perf feature in `app/handlers/admin.py` imports `core.white_configs_perf_tester`.
  - Internal helper could be imported by that module (not confirmed yet).

### 4) Possibly unused: `core/_white_configs_perf_tester_export_fix.py`
- Path: `core/_white_configs_perf_tester_export_fix.py`
- Reason (appears unused): Prefix `_` suggests internal/experimental/legacy; may not be imported directly.
- Confidence: Medium
- What could break if removed:
  - If `core/white_configs_perf_tester.py` imports it.

### 5) Possibly unused: `publisher/broadcaster.py` vs `services/broadcaster`-like redundancy
- Path(s):
  - `publisher/broadcaster.py`
  - `services/publisher_service.py`
- Reason (appears unused): Two layers may duplicate responsibility. `main.py` directly imports `publisher.broadcaster.Broadcaster` and uses `Broadcaster().start()`.
- Confidence: Medium
- What could break if removed:
  - If `services/publisher_service.py` is used by something else (tests, alternative runtime path, or future refactor).

### 6) Possibly unused: `service/` package
- Path: `service/main.py`
- Reason (appears unused): There is both `service/main.py` and `services/main.py`, while runtime entrypoint uses top-level `main.py`. Without further inspection, `service/main.py` may be legacy.
- Confidence: Medium
- What could break if removed:
  - If packaged as console script or used in Docker/alternative deployments.

### 7) Possibly unused scripts: `setup.bat`, `setup.sh`, `setup.bat`, `setup.sh`, `setup.bat`, `setup.py` (partial)
- Path(s):
  - `setup.bat`
  - `setup.sh`
- Reason (appears unused): Runtime uses `main.py`; packaging uses `setup.py` only. Shell/bat scripts may be convenience wrappers.
- Confidence: Low
- What could break if removed:
  - Developer workflows / deployment steps that rely on these scripts.

### 8) Possibly unused assets/binaries under `bin/`
- Path(s):
  - `bin/xray.exe`, `bin/xray`, `bin/Xray-windows-64_2.zip`, `bin/xray_no_window.ps1`, `bin/xray_no_window.vbs`, `bin/wintun.dll`, `bin/geoip.dat`, `bin/geosite.dat`
- Reason (appears unused): Not all are referenced by inspected code, but admin white-perf feature checks for `BASE_DIR/bin/xray` or `BASE_DIR/bin/xray.exe`.
- Confidence: Medium
- What could break if removed:
  - White perf feature will fail without the xray binary.
  - Xray dependencies (geoip/geosite/wintun) may be required at runtime.

## Unused dependencies (npm/pip) — preliminary
- Pip packages in `requirements.txt` were not fully cross-referenced against imports throughout the codebase (ripgrep unavailable), so this section is intentionally empty or low-confidence.

Potentially removable only after full import tracing:
- Confidence: Low
- Risk: High (removing packages may break runtime imports).

## Duplicate/legacy code — preliminary
- Confidence is limited by lack of full-text search.

Not enough evidence yet to assert duplicates/unused without confirming import graph across all modules.

---

## Report limitations
- Full dependency graph verification requires scanning all modules for imports, dynamic imports, and configuration references.
- The environment lacks ripgrep, limiting comprehensive static analysis.
- Next pass should read remaining key modules (db models/crud/session, scraper, processor, publisher, services, middlewares, bot menus) and then produce high-confidence unused candidates.

