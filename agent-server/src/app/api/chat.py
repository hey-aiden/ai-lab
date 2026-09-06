"""OpenAI 兼容的 /chat/completions 接口(SSE 流式为主)。"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_model, get_session_factory
from app.schemas import (
    ChatCompletionChoice,
    ChatCompletionChoiceMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from app.services import stream_chat

router = APIRouter(tags=["chat"])


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    session_factory=Depends(get_session_factory),
    model=Depends(get_model),
):
    """OpenAI 兼容的对话补全接口,本服务的核心入口。

    处理流程:
        带 session_id 时从 MySQL 加载历史 → 拼接本次新消息 → 调 DeepSeek
        → 流式 / 非流式返回 → 把用户消息与助手回复写回 MySQL。

    请求体字段(见 ChatCompletionRequest):
        model       模型名,当前仅回显,实际用 settings.model_deepseek
        messages    本次消息,通常只含最新一条 user 消息
        stream      true(默认)SSE 流式;false 返回完整 JSON
        session_id  可选,会话窗口 ID,带它才加载 / 保存历史
        user_id     归属用户,默认 "anonymous"

    返回:
        stream=true  → text/event-stream,每个 `data:` 是一个
                       chat.completion.chunk,末尾 `data: [DONE]`
        stream=false → ChatCompletionResponse(完整 chat.completion,含 usage)
    """
    if request.stream:
        async def event_stream():
            async for chunk in stream_chat(session_factory, model, request):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # 非流式:收集流结果,组装完整响应
    completion_id = ""
    created = 0
    content = ""
    usage = None
    async for chunk in stream_chat(session_factory, model, request):
        if not completion_id:
            completion_id = chunk["id"]
            created = chunk["created"]
        content += chunk["choices"][0]["delta"].get("content", "")
        usage = chunk.get("usage") or usage

    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=request.model,
        choices=[
            ChatCompletionChoice(
                message=ChatCompletionChoiceMessage(content=content),
                finish_reason="stop",
            )
        ],
        usage=usage,
    )
