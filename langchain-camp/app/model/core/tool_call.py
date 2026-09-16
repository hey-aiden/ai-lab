"""
tool_call: docstring 是必须的，决定 llm 是否能触发该函数调用

为什么 @tool 之后可以 .invoke()？
经过 @tool 处理后，业务函数已经被转换成 langChain Tool 对象，当调用：
get_weather.invoke({
    "city": "北京"
})
时，实际是在使用 Tool 的统一调用接口
可以理解为：
Tool
├── name
├── description
├── args_schema
└── invoke()
       ↓
   原来的 Python 函数

如何接入 llm 中：
-------------------------------------------
model_with_tools = model.bind_tools([
    get_weather
])
-------------------------------------------
"""

from langchain.messages import HumanMessage, ToolMessage
from langchain.tools import tool

from app.log import log_msg


@tool
def get_weather(city: str):
    """获取指定城市的天气"""
    # 上面的 docstring 不是写给程序员看的，而是写给 LLM 看的"使用说明书"：
    # @tool 会把 函数名 -> Tool.name、docstring -> Tool.description、
    # 类型标注(city: str) -> args_schema，LLM 靠这三样判断"何时该调用、传什么参数"。
    # 所以：改了函数签名或 docstring，就等于改了工具对 LLM 的"自我描述"。
    weather_data = {"北京": "晴天，25°C", "深圳": "多云，28°C", "广州": "阴天，27°C"}
    return weather_data.get(city, f"{city} 暂无天气数据")


def print_tool_key():
    # 打印 @tool 包装后函数"多出来"的三个属性，直观看到装饰器到底做了什么
    print("tool.name: ", get_weather.name)  # get_weather
    print("tool.description: ", get_weather.description)  # 获取指定城市的天气
    print(
        "tool.args_schema: ", get_weather.args_schema
    )  #  <class 'langchain_core.utils.pydantic.get_weather'>
    # Tool 本身也是 Runnable，所以能用统一的 .invoke() 直接调用原来的函数
    result = get_weather.invoke({"city": "北京"})
    print(result)


def tool_exec(llm):
    print_tool_key()

    # 第 1 步：bind_tools() 把工具"挂"到模型上，告诉 LLM「你现在能调用 get_weather」
    # 关键坑：bind_tools 不会原地修改 llm，而是返回一个"绑定了工具的新模型"，
    # 所以必须接住返回值，否则工具永远不生效。
    model_with_tools = llm.bind_tools([get_weather])

    # 第 2 步：用绑定后的模型提问。注意这里只做了一件事——
    # 让模型"决定是否要调用工具"，并不会真正执行工具。
    result = model_with_tools.invoke("北京天气怎么样")

    # 模型想调用工具时，调用信息放在 result.tool_calls 里（列表，可能为空）。
    # 想看"是否触发"，最直接的是打印它；真正执行工具要自己来（或用 create_agent/ToolNode 自动编排）。
    print("tool_calls:", result.tool_calls)

    # 第 3 步（手动执行的完整写法）：取出第一个工具调用，用它的 args 真正跑一次 get_weather
    if result.tool_calls:
        tool_call_ = result.tool_calls[0]
        answer = get_weather.invoke(tool_call_["args"])
        print("工具执行结果:", answer)


def _render_message(m):
    """把一条 LangChain 消息转成可读的「角色: 内容」文本。

    AIMessage 发起工具调用时 content 是空串，真正信息在 tool_calls 里，所以要单独处理。
    """
    # getattr(m, "tool_calls", None)：安全地取 m.tool_calls 属性。
    # 等价于 m.tool_calls，但 HumanMessage/ToolMessage 没有 tool_calls 属性，
    # 直接写 m.tool_calls 会抛 AttributeError；getattr 在属性不存在时返回兜底值 None。
    if getattr(m, "tool_calls", None):
        names = [tc["name"] for tc in m.tool_calls]
        return f"{type(m).__name__} -> 调用 {names}"
    return f"{type(m).__name__}: {m.content}"


def tool_call(llm):
    """
    手动搭一遍「工具调用 → 回到 agent」的完整循环。

    agent 的本质是「模型 → 工具 → 模型 → …」的循环，而不是单次模型调用：
    模型先决定"要不要调工具"，工具执行后，结果以 ToolMessage 的形式追加回 messages 列表，
    再带着这条新消息调一次模型，模型才能基于工具结果生成最终回答。
    这里手写一遍，就是为了看清 create_agent 背后自动化掉的那套逻辑。
    """
    # 第 1 步：初始消息列表（就是 agent 的共享"记忆"，工具结果稍后要往这里回填）
    messages = [HumanMessage(content="北京天气怎么样")]

    # 第 2 步：绑定工具后先问一次，让模型"决定是否调用工具"
    model_with_tool = llm.bind_tools([get_weather])
    response = model_with_tool.invoke(messages)  # AIMessage，可能带 tool_calls
    messages.append(response)  # 把模型的回答也记进对话

    # 第 3 步：把模型想调用的每个工具真正执行掉，结果包成 ToolMessage 回填进 messages
    # 关键：ToolMessage 的 tool_call_id 必须对上 AIMessage.tool_calls 里对应那条的 id，
    #       模型靠这个 id 认出"这条结果是在回答我哪一次调用"，漏了或对不上会困惑。
    for tc in response.tool_calls:
        result = get_weather.invoke(tc["args"])
        messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    # 第 4 步：带着工具结果再调一次模型 —— 这就是"回到 agent"。
    # 此时模型手里有了 ToolMessage，就能生成最终的自然语言回答（通常不再带 tool_calls）。
    final = model_with_tool.invoke(messages)
    messages.append(final)  # 最终回答也记进对话，日志才完整

    # 控制台打印干净的最终回答；整段对话渲染后交给 log_msg（log_msg 内部会打印 + 写文件）
    print(final.content)
    msg_data = {
        "message_list": " | ".join(_render_message(m) for m in messages),
        "origin_result": final,
    }
    log_msg(msg_data)
