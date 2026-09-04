from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from app.memory import MySqlChatMessageHistory
from app.schemas import ChatCompletionRequest, ChatMessage
from app.services import build_messages, extract_usage, stream_chat, to_langchain_message


class FakeModel:
    """记录收到的 messages,并按预设片段流式输出。"""

    def __init__(self, chunks: list[str]):
        self._chunks = chunks
        self.received: list | None = None

    async def astream(self, messages):
        self.received = list(messages)
        for c in self._chunks:
            yield SimpleNamespace(content=c)


def test_to_langchain_message_roles():
    assert isinstance(
        to_langchain_message(ChatMessage(role="user", content="hi")), HumanMessage
    )
    assert isinstance(
        to_langchain_message(ChatMessage(role="assistant", content="hi")), AIMessage
    )


def test_build_messages_appends_incoming_to_history():
    history = [HumanMessage(content="之前"), AIMessage(content="之前答")]
    incoming = [HumanMessage(content="新问题")]
    out = build_messages(history, incoming)
    assert [m.content for m in out] == ["之前", "之前答", "新问题"]


async def test_stream_chat_stateless(session_factory):
    """无 session_id 时不落库,按 OpenAI chunk 格式流式返回。"""
    model = FakeModel(["你", "好"])
    req = ChatCompletionRequest(messages=[{"role": "user", "content": "hi"}])

    chunks = [c async for c in stream_chat(session_factory, model, req)]

    assert chunks[0]["choices"][0]["delta"] == {"role": "assistant"}
    contents = [c["choices"][0]["delta"].get("content", "") for c in chunks[1:-1]]
    assert "".join(contents) == "你好"
    assert chunks[-1]["choices"][0]["delta"] == {}
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"

    assert [m.content for m in model.received] == ["hi"]
    assert [m.type for m in model.received] == ["human"]


async def test_stream_chat_with_history_persists(session_factory):
    """带 session_id 时加载历史、拼接新消息、流式返回并落库。"""
    async with session_factory() as session:
        await MySqlChatMessageHistory(session, "s1").aadd_messages(
            [HumanMessage(content="之前"), AIMessage(content="之前答")]
        )

    model = FakeModel(["好"])
    req = ChatCompletionRequest(
        messages=[{"role": "user", "content": "新问题"}], session_id="s1"
    )

    chunks = [c async for c in stream_chat(session_factory, model, req)]
    assert "".join(
        c["choices"][0]["delta"].get("content", "") for c in chunks
    ) == "好"

    # 模型收到的是 历史 + 新问题
    assert [m.content for m in model.received] == ["之前", "之前答", "新问题"]
    assert [m.type for m in model.received] == ["human", "ai", "human"]

    # 落库后应有 4 条:之前 human/ai + 新 human/ai
    async with session_factory() as session:
        loaded = await MySqlChatMessageHistory(session, "s1").aget_messages()
        assert [m.content for m in loaded] == ["之前", "之前答", "新问题", "好"]
        assert [type(m).__name__ for m in loaded] == [
            "HumanMessage",
            "AIMessage",
            "HumanMessage",
            "AIMessage",
        ]


class UsageModel:
    """最后一个分片携带 usage_metadata 的假模型。"""

    async def astream(self, messages):
        yield SimpleNamespace(content="你")
        yield SimpleNamespace(
            content="",
            usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )


def test_extract_usage():
    chunk = SimpleNamespace(
        usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    )
    assert extract_usage(chunk) == {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
    }
    assert extract_usage(SimpleNamespace()) is None


async def test_stream_chat_includes_usage_when_present(session_factory):
    """模型给出 usage_metadata 时,最终分片应携带 usage。"""
    req = ChatCompletionRequest(messages=[{"role": "user", "content": "hi"}])
    chunks = [c async for c in stream_chat(session_factory, UsageModel(), req)]
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
    assert chunks[-1]["usage"] == {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
    }
