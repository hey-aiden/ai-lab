from app.memory import ConversationManager


async def test_create_session_persists_and_lists(session_factory):
    async with session_factory() as session:
        mgr = ConversationManager(session)
        sid = await mgr.create_session("u1", "第一个会话")
        assert sid

        sessions = await mgr.list_sessions("u1")
        assert [s.id for s in sessions] == [sid]
        assert sessions[0].title == "第一个会话"
        assert sessions[0].user_id == "u1"


async def test_list_sessions_scoped_by_user(session_factory):
    async with session_factory() as session:
        mgr = ConversationManager(session)
        s1 = await mgr.create_session("u1")
        s2 = await mgr.create_session("u2")
        s3 = await mgr.create_session("u1")

        assert {s.id for s in await mgr.list_sessions("u1")} == {s1, s3}
        assert {s.id for s in await mgr.list_sessions("u2")} == {s2}


async def test_delete_session(session_factory):
    async with session_factory() as session:
        mgr = ConversationManager(session)
        sid = await mgr.create_session("u1")
        assert await mgr.delete_session(sid) is True
        assert await mgr.list_sessions("u1") == []
        assert await mgr.delete_session(sid) is False
