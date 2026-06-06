# database/crud.py — عملیات دیتابیس (CRUD)

from datetime import datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin, CleanIP, ProcessedConfig, User, UserStat, VipUser


# ─── Users ───────────────────────────────────────────


async def upsert_user(
    session: AsyncSession,
    user_id: int,
    first_name: str | None,
    username: str | None,
) -> None:
    existing = await session.get(User, user_id)
    if existing is None:
        session.add(User(user_id=user_id, first_name=first_name, username=username))
    else:
        existing.first_name = first_name
        existing.username = username
    await session.commit()


async def get_all_user_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(User.user_id))
    return [row[0] for row in result.all()]


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.user_id)))
    return result.scalar_one()


async def bump_user_start(session: AsyncSession, user_id: int) -> None:
    stat = await session.get(UserStat, user_id)
    now = datetime.utcnow()
    if stat is None:
        session.add(UserStat(user_id=user_id, start_count=1, last_activity=now))
    else:
        stat.start_count += 1
        stat.last_activity = now
    await session.commit()


async def total_starts(session: AsyncSession) -> int:
    result = await session.execute(select(func.coalesce(func.sum(UserStat.start_count), 0)))
    return int(result.scalar_one())


# ─── Admins ──────────────────────────────────────────


async def get_admin_ids(session: AsyncSession) -> set[int]:
    result = await session.execute(select(Admin.user_id))
    return {row[0] for row in result.all()}


async def add_admin(session: AsyncSession, user_id: int, added_by: int) -> bool:
    if await session.get(Admin, user_id):
        return False
    session.add(Admin(user_id=user_id, added_by=added_by))
    await session.commit()
    return True


async def remove_admin(session: AsyncSession, user_id: int) -> bool:
    admin = await session.get(Admin, user_id)
    if admin is None:
        return False
    await session.delete(admin)
    await session.commit()
    return True


# ─── VIP ─────────────────────────────────────────────


async def add_vip(session: AsyncSession, user_id: int) -> None:
    if await session.get(VipUser, user_id) is None:
        session.add(VipUser(user_id=user_id))
        await session.commit()


async def remove_vip(session: AsyncSession, user_id: int) -> bool:
    vip = await session.get(VipUser, user_id)
    if vip is None:
        return False
    await session.delete(vip)
    await session.commit()
    return True


async def list_vips(session: AsyncSession, limit: int = 50) -> list[VipUser]:
    result = await session.execute(
        select(VipUser).order_by(desc(VipUser.added_at)).limit(limit)
    )
    return list(result.scalars().all())


async def get_vip_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(VipUser.user_id))
    return [row[0] for row in result.all()]


# ─── Configs ─────────────────────────────────────────


async def config_exists(session: AsyncSession, config_hash: str) -> bool:
    result = await session.execute(
        select(ProcessedConfig.id).where(ProcessedConfig.config_hash == config_hash).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def save_config(
    session: AsyncSession,
    *,
    raw_config: str,
    watermarked_config: str,
    config_hash: str,
    country_code: str | None,
    protocol: str | None,
    host: str | None,
    source: str | None,
    is_valid: bool = True,
) -> ProcessedConfig:
    row = ProcessedConfig(
        raw_config=raw_config,
        watermarked_config=watermarked_config,
        config_hash=config_hash,
        country_code=country_code,
        protocol=protocol,
        host=host,
        source=source,
        is_valid=is_valid,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_last_configs(session: AsyncSession, limit: int) -> list[ProcessedConfig]:
    result = await session.execute(
        select(ProcessedConfig)
        .where(ProcessedConfig.is_valid == True)  # noqa: E712
        .order_by(desc(ProcessedConfig.id))
        .limit(limit)
    )
    return list(result.scalars().all())


async def filter_configs(
    session: AsyncSession,
    *,
    country_code: str | None = None,
    protocol: str | None = None,
    limit: int = 1000,
) -> list[ProcessedConfig]:
    query = select(ProcessedConfig).where(ProcessedConfig.is_valid == True)  # noqa: E712
    if country_code:
        query = query.where(ProcessedConfig.country_code == country_code.upper())
    if protocol:
        query = query.where(ProcessedConfig.protocol == protocol.lower())
    query = query.order_by(desc(ProcessedConfig.id)).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


# ─── Clean IP ────────────────────────────────────────


async def add_clean_ip(session: AsyncSession, ip: str) -> None:
    existing = (
        await session.execute(select(CleanIP).where(CleanIP.ip == ip).limit(1))
    ).scalar_one_or_none()
    if existing:
        return
    session.add(CleanIP(ip=ip))
    await session.commit()


async def count_clean_ips(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(CleanIP.id)))
    return result.scalar_one()


async def delete_old_clean_ips(session: AsyncSession, days: int = 5) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(select(CleanIP).where(CleanIP.created_at < cutoff))
    rows = list(result.scalars().all())
    for row in rows:
        await session.delete(row)
    await session.commit()
    return len(rows)
