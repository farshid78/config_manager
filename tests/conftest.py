import pytest


@pytest.fixture(autouse=True)
def env_settings(monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("BOT_TOKEN", "7123456789:AAHtest_token_for_pytest_only")
    monkeypatch.setenv("OWNER_ID", "12345")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file.as_posix()}")

    from core.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"
