"""
ORM模型定义
1. 会话表
2. 历史消息表
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """返回当前北京时间(naive datetime,便于存入无时区的 DateTime 列)。"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


class ConversationModel(Base):
    """
    会话窗口表(conversations)
    """

    __tablename__ = "table_conversation"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="会话ID(UUID)"
    )
    user_id: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False, comment="归属用户ID"
    )
    title: Mapped[str] = mapped_column(
        String(255), default="新对话", comment="会话标题"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=beijing_now, comment="创建时间"
    )

    # 建立与消息的一对多关系 (级联删除：删除会话时同步删除其下的所有消息)
    messages: Mapped[list["ChatMessageModel"]] = relationship(
        "ChatMessageModel", back_populates="conversation", cascade="all, delete-orphan"
    )


class ChatMessageModel(Base):
    """
    聊天历史消息表(chat_message)
    """

    __tablename__ = "table_chat_message"
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="自增ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("table_conversation.id", ondelete="CASCADE"),
        nullable=False,
        comment="外键：会话ID",
    )
    message_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="消息类型: human/ai/system/tool"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息正文")
    tool_calls: Mapped[dict | list | None] = mapped_column(
        JSON, nullable=True, comment="工具调用详情(JSON)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=beijing_now, index=True, comment="消息发送时间"
    )

    # 反向关联
    conversation: Mapped["ConversationModel"] = relationship(
        "ConversationModel", back_populates="messages"
    )

    # 联合索引优化：按会话ID查询并按时间排序时性能极高
    __table_args__ = (Index("idx_session_created", "session_id", "created_at"),)
