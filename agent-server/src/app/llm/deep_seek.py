from langchain.agents import create_agent
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek

from app.config import settings


def create_chat():
    model = ChatDeepSeek(
        model=settings.model_deepseek,
        temperature=settings.temperature,
        api_key=settings.api_key_deepseek,
    )
    return model


"""
在 LangChain 或类似框架 中，当你将函数作为工具（Tool）传递给 Agent 时，框架需要知道这个函数是做什么的，以便让 AI 模型理解何时以及如何调用它:
框架获取函数描述的方式有两种：
 · 从函数的 docstring（文档字符串）中自动提取
 · 通过 description 参数手动提供
如果你的函数既没有 docstring，也没有手动提供 description，框架就无法生成工具描述，从而抛出这个错误。

方案1：为函数添加 docstring（推荐）

方案2：使用 @tool 装饰器（LangChain 推荐）
"""


@tool
def get_weather(city: str) -> str:
    # 为函数添加 docstring
    """获取指定城市的实时天气信息。
    Args:
        city: 城市名称，如"深圳"、"北京"
    Returns:
        该城市的天气情况描述
    """
    return f"{city}的天气是晴天"


def create_model():
    model = create_chat()
    agent = create_agent(
        model=model,
        tools=[get_weather],
        system_prompt="你是一个实用工具助手",
    )
    return agent


model_dict = {
    "chat": create_chat,
    "agent": create_model,
}


def load_model_ds(type: str):
    """初始化 DeepSeek 模型。"""
    handler = model_dict.get(type)
    return handler()
