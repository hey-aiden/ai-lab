from app.schemas import ChatCompletionRequest, ConversationCreateRequest


def test_chat_request_defaults():
    req = ChatCompletionRequest(messages=[{"role": "user", "content": "hi"}])
    assert req.model == "deepseek-chat"
    assert req.stream is True
    assert req.user_id == "anonymous"
    assert req.session_id is None


def test_chat_request_ignores_unknown_fields():
    """网关透传的 OpenAI 标准字段(如 max_tokens)应被忽略而非报错。"""
    req = ChatCompletionRequest(
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=100,
        top_p=0.9,
    )
    assert not hasattr(req, "max_tokens")


def test_chat_request_with_extensions():
    req = ChatCompletionRequest(
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        session_id="s1",
        user_id="u1",
    )
    assert req.stream is False
    assert req.session_id == "s1"
    assert req.user_id == "u1"


def test_conversation_create_defaults():
    req = ConversationCreateRequest()
    assert req.user_id == "anonymous"
    assert req.title == "新对话"
