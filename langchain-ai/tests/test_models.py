from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import ChatMessageModel, ConversationModel
from app.models.chat import beijing_now


async def test_conversation_and_message_roundtrip(session_factory):
    """会话与消息能正确建表、写入,并按关系反查。"""
    async with session_factory() as session:
        conv = ConversationModel(id="c1", user_id="u1", title="你好")
        session.add(conv)
        await session.flush()  # 让 c1 先生成,消息外键才能引用

        session.add(ChatMessageModel(session_id="c1", message_type="human", content="hello"))
        await session.commit()

    async with session_factory() as session:
        stmt = (
            select(ConversationModel)
            .where(ConversationModel.id == "c1")
            .options(selectinload(ConversationModel.messages))
        )
        conv = (await session.execute(stmt)).scalar_one()
        assert conv.user_id == "u1"
        assert conv.title == "你好"
        assert [m.content for m in conv.messages] == ["hello"]


async def test_delete_conversation_cascades_messages(session_factory):
    """删除会话时级联删除其消息。"""
    async with session_factory() as session:
        conv = ConversationModel(id="c2", user_id="u1")
        session.add(conv)
        await session.flush()
        session.add(ChatMessageModel(session_id="c2", message_type="human", content="x"))
        await session.commit()

    async with session_factory() as session:
        conv = await session.get(ConversationModel, "c2")
        await session.delete(conv)
        await session.commit()

    async with session_factory() as session:
        remaining = (await session.execute(select(ChatMessageModel))).scalars().all()
        assert remaining == []


def test_beijing_now_is_utc_plus_8():
    """入库时间应为北京时间(UTC+8),且是 naive datetime(便于存 DateTime 列)。"""
    bj = beijing_now()
    assert bj.tzinfo is None  # naive
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((bj - utc_now).total_seconds() - 8 * 3600) < 60
