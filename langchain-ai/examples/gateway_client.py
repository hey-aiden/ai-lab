"""网关侧对接示例:演示如何调用本服务的会话 + 流式聊天接口。

运行前提:
    1. 本服务已启动(uv run dev)
    2. .env 配好 DeepSeek key

用法:
    uv run python examples/gateway_client.py
"""

import asyncio
import json

import httpx

SERVICE_URL = "http://127.0.0.1:8000"


async def create_conversation(client: httpx.AsyncClient, user_id: str) -> str:
    """新建会话,拿到 session_id(后续聊天都挂在它下面)。"""
    resp = await client.post(
        f"{SERVICE_URL}/v1/conversations",
        json={"user_id": user_id, "title": "网关演示"},
    )
    resp.raise_for_status()
    return resp.json()["id"]


async def stream_chat(client: httpx.AsyncClient, session_id: str, message: str) -> None:
    """发起一次流式对话,实时打印 assistant 回复。"""
    print(f"user: {message}")
    print("assistant: ", end="", flush=True)

    async with client.stream(
        "POST",
        f"{SERVICE_URL}/v1/chat/completions",
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": message}],
            "stream": True,
            "session_id": session_id,
        },
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[len("data: ") :]
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            content = chunk["choices"][0]["delta"].get("content", "")
            if content:
                print(content, end="", flush=True)
    print()


async def main() -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        # 1. 新建会话
        session_id = await create_conversation(client, "u1")
        print(f"会话已创建: {session_id}\n")

        # 2. 两轮对话,第二轮自动带上历史(服务端从 MySQL 加载)
        await stream_chat(client, session_id, "你好,用一句话介绍你自己")
        await stream_chat(client, session_id, "刚才我说了什么?")

        # 3. 查看落库的历史消息
        resp = await client.get(f"{SERVICE_URL}/v1/conversations/{session_id}/messages")
        print("历史消息:")
        for m in resp.json():
            print(f"  [{m['role']}] {m['content']}")


if __name__ == "__main__":
    asyncio.run(main())
