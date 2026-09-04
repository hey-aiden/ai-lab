from langchain_core.messages import AIMessage, HumanMessage

from app.memory import MySqlChatMessageHistory


async def test_save_and_load_messages_roundtrip(session_factory):
    """写入人机消息后能按顺序读回等价的 LangChain 消息。"""
    async with session_factory() as session:
        history = MySqlChatMessageHistory(session, "s1")
        await history.aadd_messages(
            [HumanMessage(content="你好"), AIMessage(content="你好呀")]
        )

    async with session_factory() as session:
        history = MySqlChatMessageHistory(session, "s1")
        loaded = await history.aget_messages()
        assert [type(m).__name__ for m in loaded] == ["HumanMessage", "AIMessage"]
        assert [m.content for m in loaded] == ["你好", "你好呀"]


async def test_clear_removes_only_target_session(session_factory):
    """清空只影响指定 session,不影响其它会话。"""
    async with session_factory() as session:
        h1 = MySqlChatMessageHistory(session, "s1")
        h2 = MySqlChatMessageHistory(session, "s2")
        await h1.aadd_messages([HumanMessage(content="a")])
        await h2.aadd_messages([HumanMessage(content="b")])
        await h1.aclear()

    async with session_factory() as session:
        assert await MySqlChatMessageHistory(session, "s1").aget_messages() == []
        assert len(await MySqlChatMessageHistory(session, "s2").aget_messages()) == 1
