"""会话管理相关 DTO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: str = "anonymous"
    title: str = "新对话"


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    created_at: datetime


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime
