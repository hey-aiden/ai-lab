import json
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage

from app.api.deps import get_model, get_session_factory
from app.main import app
from app.memory import ConversationManager, MySqlChatMessageHistory


class FakeModel:
    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    async def astream(self, messages):
        for c in self._chunks:
            yield SimpleNamespace(content=c)


@pytest.fixture
async def client(session_factory):
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_chat_stream(client):
    """POST /v1/chat/completions 以 SSE 流式返回 OpenAI chunk。"""
    app.dependency_overrides[get_model] = lambda: FakeModel(["你", "好"])

    async with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    ) as resp:
        assert resp.status_code == 200
        body = (await resp.aread()).decode()

    lines = [l for l in body.splitlines() if l.startswith("data: ")]
    assert lines[-1] == "data: [DONE]"
    chunks = [json.loads(l[len("data: ") :]) for l in lines[:-1]]
    content = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert content == "你好"


async def test_create_and_list_conversations(client):
    r = await client.post(
        "/v1/conversations", json={"user_id": "u1", "title": "测试"}
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    r2 = await client.get("/v1/conversations", params={"user_id": "u1"})
    assert r2.status_code == 200
    assert [it["id"] for it in r2.json()] == [sid]


async def test_get_messages_and_delete(client, session_factory):
    async with session_factory() as session:
        sid = await ConversationManager(session).create_session("u1", "测试")
        await MySqlChatMessageHistory(session, sid).aadd_messages(
            [HumanMessage(content="你好"), AIMessage(content="你好呀")]
        )

    r = await client.get(f"/v1/conversations/{sid}/messages")
    assert r.status_code == 200
    assert [(m["role"], m["content"]) for m in r.json()] == [
        ("user", "你好"),
        ("assistant", "你好呀"),
    ]

    d = await client.delete(f"/v1/conversations/{sid}")
    assert d.status_code == 200
    r3 = await client.get("/v1/conversations", params={"user_id": "u1"})
    assert r3.json() == []


class UsageModel:
    async def astream(self, messages):
        yield SimpleNamespace(content="你")
        yield SimpleNamespace(
            content="",
            usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )


async def test_chat_non_stream_with_usage(client):
    """非流式(stream=false)返回完整 chat.completion,并带上 usage。"""
    app.dependency_overrides[get_model] = lambda: UsageModel()

    r = await client.post(
        "/v1/chat/completions",
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "你"
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["usage"] == {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
    }
