"""
数据库连接与 session 管理
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# 声明基类
class Base(DeclarativeBase):
    """全局统一的 ORM 模型基类"""


def create_async_engine_and_sessionmaker(
    db_url: str, **engine_kwargs
) -> tuple[object, async_sessionmaker[AsyncSession]]:
    """按 URL 构建引擎与 session 工厂。

    拆成工厂方便测试注入 SQLite(aiosqlite),生产用 MySQL(aiomysql)。
    """
    engine = create_async_engine(db_url, **engine_kwargs)
    sessionmaker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,  # 防止提交后属性失效
        autoflush=False,
    )
    return engine, sessionmaker


# 生产环境默认实例 (格式: mysql+aiomysql://user:password@host:port/dbname)
engine, AsyncSessionLocal = create_async_engine_and_sessionmaker(
    settings.db_url,
    echo=False,  # 生产环境关闭 SQL 日志打印
    pool_pre_ping=True,  # 自动检测断开的连接并重连
    pool_size=10,
    max_overflow=20,
)


# FastApi 依赖注入工具函数(用于获取每个请求的数据库 Session)
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
