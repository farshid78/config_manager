import pytest
from database import crud
from database.models import Admin, User, VipUser, ProcessedConfig
from database.session import get_session_factory, init_db


@pytest.mark.asyncio
async def test_init_db():
    """بررسی initialize شدن database."""
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        assert session is not None


@pytest.mark.asyncio
async def test_upsert_user():
    """تست upsert کاربر."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        await crud.upsert_user(session, 123, "John", "john123")
        user = await session.get(User, 123)
        assert user.user_id == 123
        assert user.first_name == "John"


@pytest.mark.asyncio
async def test_count_users():
    """تست شمارش کاربران."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        await crud.upsert_user(session, 111, "Alice", "alice")
        await crud.upsert_user(session, 222, "Bob", "bob")
        count = await crud.count_users(session)
        assert count >= 2


@pytest.mark.asyncio
async def test_add_admin():
    """تست افزودن ادمین."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        added = await crud.add_admin(session, 999, 12345)
        assert added is True
        
        duplicate = await crud.add_admin(session, 999, 12345)
        assert duplicate is False


@pytest.mark.asyncio
async def test_vip_operations():
    """تست عملیات VIP."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        await crud.add_vip(session, 500)
        vips = await crud.get_vip_ids(session)
        assert 500 in vips
        
        removed = await crud.remove_vip(session, 500)
        assert removed is True


@pytest.mark.asyncio
async def test_config_save_and_exists():
    """تست ذخیره و بررسی وجود کانفیگ."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        config = {
            "raw_config": "vmess://test",
            "watermarked_config": "vmess://test#marked",
            "config_hash": "abc123",
            "country_code": "IR",
            "protocol": "vmess",
            "host": "example.com",
        }
        saved = await crud.save_config(session, source="test", **config)
        assert saved.config_hash == "abc123"
        
        exists = await crud.config_exists(session, "abc123")
        assert exists is True
