import os

# 必须在 import 任何 app.* 之前设置,避免读到真实 .env / 触发 MySQL 连接
os.environ["DB_URL"] = "mysql+aiomysql://test:test@127.0.0.1:3306/test_chat"
os.environ["API_KEY_DEEPSEEK"] = "test-key"
os.environ["MODEL_DEEPSEEK"] = "deepseek-chat"
os.environ["TEMPERATURE"] = "0.0"

import pytest

from app.db import Base, create_async_engine_and_sessionmaker

import app.models  # noqa: F401  # 导入即注册 ORM 模型到 Base.metadata


@pytest.fixture
async def session_factory(tmp_path):
    """每次测试一个独立的 SQLite 临时库,建好表后交出 session 工厂。"""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'chat.db'}"
    engine, factory = create_async_engine_and_sessionmaker(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield factory
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
