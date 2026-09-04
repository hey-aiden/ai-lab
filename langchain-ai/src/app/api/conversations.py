"""会话管理接口:新建、列表、历史消息、删除。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import get_session_factory
from app.memory import ConversationManager
from app.models import ChatMessageModel, ConversationModel
from app.schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

_ROLE_MAP = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreateRequest,
    session_factory=Depends(get_session_factory),
):
    """新建一个会话窗口,返回会话元数据(含 session_id)。

    网关在发起聊天前先调这里拿到 session_id,后续 /chat/completions 带上它
    即可实现多轮记忆。请求体:{"user_id", "title"(可选)}。
    """
    async with session_factory() as session:
        sid = await ConversationManager(session).create_session(body.user_id, body.title)
        conv = await session.get(ConversationModel, sid)
        return ConversationResponse.model_validate(conv)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    user_id: str,
    session_factory=Depends(get_session_factory),
):
    """返回某用户的会话列表,按创建时间倒序(新的在前)。"""
    async with session_factory() as session:
        convs = await ConversationManager(session).list_sessions(user_id)
        return [ConversationResponse.model_validate(c) for c in convs]


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    session_factory=Depends(get_session_factory),
):
    """返回指定会话的历史消息,按时间正序;role 由 message_type 映射(human→user 等)。"""
    async with session_factory() as session:
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at, ChatMessageModel.id)
        )
        rows = (await session.scalars(stmt)).all()
        return [
            MessageResponse(
                role=_ROLE_MAP.get(r.message_type, r.message_type),
                content=r.content,
                created_at=r.created_at,
            )
            for r in rows
        ]


@router.delete("/{session_id}")
async def delete_conversation(
    session_id: str,
    session_factory=Depends(get_session_factory),
):
    """删除会话并级联删除其下所有消息;会话不存在则返回 404。"""
    async with session_factory() as session:
        ok = await ConversationManager(session).delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
