from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def make_sessionmaker(postgres_dsn: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(postgres_dsn, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)
