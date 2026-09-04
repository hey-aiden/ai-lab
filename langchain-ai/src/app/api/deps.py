"""FastAPI 依赖:session 工厂与模型实例,便于测试覆盖。"""

from app.db import AsyncSessionLocal
from app.llm import load_model_ds


def get_session_factory():
    """返回异步 session 工厂(生产用 MySQL,测试覆盖为 SQLite)。"""
    return AsyncSessionLocal


def get_model():
    """返回聊天模型实例(默认纯对话)。"""
    return load_model_ds("chat")
