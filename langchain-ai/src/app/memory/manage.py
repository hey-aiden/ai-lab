"""
会话管理 - 负责会话元数据(Conversations)的增删改查:
新建会话、获取用户会话列表、删除会话。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConversationModel


class ConversationManager:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_session(self, user_id: str, title: str = "新对话") -> str:
        """为用户创建一个新会话,持久化后返回 session_id。"""
        session_id = str(uuid.uuid4())
        self.db_session.add(
            ConversationModel(id=session_id, user_id=user_id, title=title)
        )
        await self.db_session.commit()
        return session_id

    async def list_sessions(self, user_id: str) -> list[ConversationModel]:
        """返回某用户的会话列表,按创建时间倒序(新的在前)。"""
        stmt = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
        )
        return list((await self.db_session.scalars(stmt)).all())

    async def delete_session(self, session_id: str) -> bool:
        """删除会话(级联删除其消息),返回是否真实删除。"""
        conv = await self.db_session.get(ConversationModel, session_id)
        if conv is None:
            return False
        await self.db_session.delete(conv)
        await self.db_session.commit()
        return True
