"""
聊天编排层:整合 DB 读取、Memory 加载、LLM 流式调用与消息落库。
"""

import time
import uuid
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.memory import MySqlChatMessageHistory
from app.schemas import ChatCompletionRequest, ChatMessage


def to_langchain_message(msg: ChatMessage) -> BaseMessage:
    """把 OpenAI 风格消息转成 LangChain 消息。"""
    if msg.role == "user":
        return HumanMessage(content=msg.content)
    if msg.role == "assistant":
        return AIMessage(content=msg.content)
    if msg.role == "system":
        return SystemMessage(content=msg.content)
    raise ValueError(f"不支持的 role: {msg.role}")


def build_messages(
    history: list[BaseMessage], incoming: list[BaseMessage]
) -> list[BaseMessage]:
    """历史消息 + 本次新消息,按顺序拼接。"""
    return [*history, *incoming]


def make_chunk(
    completion_id: str,
    model: str,
    created: int,
    *,
    delta: dict,
    finish_reason: str | None = None,
) -> dict:
    """构造 OpenAI chat.completion.chunk 格式的分片。"""
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def extract_usage(chunk) -> dict | None:
    """从 LangChain 消息分片的 usage_metadata 提取 OpenAI 风格 usage。"""
    um = getattr(chunk, "usage_metadata", None)
    if not um:
        return None
    return {
        "prompt_tokens": um.get("input_tokens", 0),
        "completion_tokens": um.get("output_tokens", 0),
        "total_tokens": um.get("total_tokens", 0),
    }


async def stream_chat(
    session_factory: async_sessionmaker,
    model,
    request: ChatCompletionRequest,
) -> AsyncIterator[dict]:
    """流式执行一次对话,产出 OpenAI chat.completion.chunk 分片(核心编排)。

    流程:
        1. 带 session_id 时从 MySQL 加载历史
        2. 拼接本次新消息 → model.astream() 逐 token 产出分片
        3. 末尾分片带 finish_reason="stop",并从 usage_metadata 提取 usage
        4. 带 session_id 时,把本次用户消息 + 助手完整回复写回 MySQL

    参数:
        session_factory 异步 session 工厂(生产 MySQL,测试注入 SQLite)
        model           聊天模型(需有 astream()),测试注入假模型
        request         ChatCompletionRequest(含 session_id / messages 等)

    产出:
        OpenAI chunk dict,顺序:role 分片 → 若干 content 分片 → stop 分片(含 usage)
    """
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    # 1. 加载历史(仅在指定 session 时)
    history: list[BaseMessage] = []
    if request.session_id:
        async with session_factory() as session:
            history = await MySqlChatMessageHistory(
                session, request.session_id
            ).aget_messages()

    # 2. 组装消息
    incoming = [to_langchain_message(m) for m in request.messages]
    messages = build_messages(history, incoming)

    # 3. 流式调用
    yield make_chunk(completion_id, request.model, created, delta={"role": "assistant"})

    full_content = ""
    usage = None
    async for chunk in model.astream(messages):
        delta = chunk.content if isinstance(chunk.content, str) else ""
        full_content += delta
        if delta:
            yield make_chunk(
                completion_id, request.model, created, delta={"content": delta}
            )
        usage = extract_usage(chunk) or usage

    final_chunk = make_chunk(
        completion_id, request.model, created, delta={}, finish_reason="stop"
    )
    if usage:
        final_chunk["usage"] = usage
    yield final_chunk

    # 4. 落库:本次新消息 + 助手完整回复
    if request.session_id:
        async with session_factory() as session:
            await MySqlChatMessageHistory(session, request.session_id).aadd_messages(
                [*incoming, AIMessage(content=full_content)]
            )
