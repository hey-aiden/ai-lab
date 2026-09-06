"""
继承 LangChain 的 BaseChatMessageHistory,实现消息的增删改查,供 service 层直接调用。

说明:本实现是异步的(依赖 AsyncSession),生命周期为"请求作用域",勿做单例。
"""

import json

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessageModel


class MySqlChatMessageHistory(BaseChatMessageHistory):
    """基于 MySQL 的 LangChain 聊天记录实现。"""

    def __init__(self, db_session: AsyncSession, session_id: str):
        self.db_session = db_session
        self.session_id = session_id

    async def aget_messages(self) -> list[BaseMessage]:
        """异步读取历史消息,按发送时间升序。"""
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == self.session_id)
            .order_by(ChatMessageModel.created_at.asc(), ChatMessageModel.id.asc())
        )
        rows = (await self.db_session.scalars(stmt)).all()

        msg_dicts = [
            {"type": row.message_type, "data": {"content": row.content}} for row in rows
        ]
        return messages_from_dict(msg_dicts)

    async def aadd_messages(self, messages: list[BaseMessage]) -> None:
        """异步批量写入消息。"""
        for msg_dict in messages_to_dict(messages):
            content = msg_dict["data"].get("content", "")
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            self.db_session.add(
                ChatMessageModel(
                    session_id=self.session_id,
                    message_type=msg_dict["type"],
                    content=content,
                )
            )
        await self.db_session.commit()

    def clear(self) -> None:
        """同步接口不支持(本实现是异步的),请使用 aclear()。"""
        raise NotImplementedError("MySQL 历史记录是异步实现,请使用 aclear()")

    async def aclear(self) -> None:
        """异步清空当前会话的历史消息。"""
        stmt = delete(ChatMessageModel).where(
            ChatMessageModel.session_id == self.session_id
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()
