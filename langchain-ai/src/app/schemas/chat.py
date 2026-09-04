"""OpenAI 兼容的 chat.completion 请求/响应模型。"""

from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    """OpenAI 风格的对话消息(纯文本)。"""

    role: str  # system | user | assistant
    content: str


class ChatCompletionRequest(BaseModel):
    """POST /v1/chat/completions 请求体。

    extra="ignore":网关可能透传 OpenAI SDK 的其它标准字段(max_tokens/top_p 等),
    忽略而非报错。session_id / user_id 是本服务扩展字段。
    """

    model_config = ConfigDict(extra="ignore")

    model: str = "deepseek-chat"
    messages: list[ChatMessage]
    stream: bool = True
    temperature: float | None = None
    session_id: str | None = None  # 扩展:会话窗口 ID,用于加载/保存历史
    user_id: str = "anonymous"  # 扩展:归属用户(本版不鉴权)


class ChatCompletionChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str = ""


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionChoiceMessage
    finish_reason: str | None = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """非流式(stream=false)时的完整响应。"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage | None = None
