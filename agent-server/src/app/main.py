"""应用入口:FastAPI 实例、生命周期建表、路由注册、启动命令。"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

import app.models  # 导入即注册 ORM 模型到 Base.metadata
from app.api import chat, conversations
from app.db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表(生产可用 Alembic 替代)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="langchain-ai chat service", lifespan=lifespan)

app.include_router(chat.router, prefix="/v1")
app.include_router(conversations.router, prefix="/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


def run() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000)
