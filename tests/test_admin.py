import pytest

from core.config import get_settings
from app.middlewares.auth import is_admin, is_owner


@pytest.mark.asyncio
async def test_owner_is_admin():
    settings = get_settings()
    assert await is_owner(settings.owner_id) is True


@pytest.mark.asyncio
async def test_unknown_user_is_not_admin():
    from database.session import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        assert await is_admin(session, 999999999999) is False
