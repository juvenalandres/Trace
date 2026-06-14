from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from trace_app.config import settings

is_postgres = settings.database_url.startswith("postgresql")

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    **(
        {"pool_size": settings.db_pool_size, "max_overflow": settings.db_max_overflow, "pool_pre_ping": True}
        if is_postgres
        else {}
    ),
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        yield session
