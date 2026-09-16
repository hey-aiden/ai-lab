"""
基于 LangGraph 的终端对话机器人(支持工具调用 + 流式输出 + 历史落盘)。

把 make_graph.py 里学到的 State / Node / Edge 概念,组装成一个真正能聊天的 LLM 应用:

- State : messages 列表(带 add_messages reducer,更新 = 追加而非覆盖)
- Node  : chatbot(调 LLM)+ tools(执行工具)
- Edge  : START -> chatbot ->(条件边)-> tools -> chatbot ... -> END
- 记忆  : 用 checkpointer 按 thread_id 记住多轮历史
- 流式  : stream_mode="messages" 逐 token 打印(打字机效果)
- 落盘  : 每轮结束后把完整历史渲染写进 messages/ 目录
"""

from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class ChatState(TypedDict):
    # Annotated[list, add_messages] = 每次写回 messages 时"追加",而不是"覆盖"
    messages: Annotated[list, add_messages]


def _render_message(m):
    """把一条消息转成可读文本;AIMessage 发起工具调用时看 tool_calls 而非 content。"""
    if getattr(m, "tool_calls", None):
        names = [tc["name"] for tc in m.tool_calls]
        return f"{type(m).__name__} -> 调用 {names}"
    return f"{type(m).__name__}: {m.content}"


def build_chat_graph(
    llm,
    tools=None,
    system_prompt="你是一个乐于助人的 AI 助手",
    checkpointer=None,
):
    """构建对话图:START -> chatbot <-> tools(条件边)-> END。"""
    # 有工具就绑定到模型上,让模型"能决定调用";没工具就是纯聊天
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    def chatbot(state: ChatState):
        # 节点契约:接收 state,返回"部分更新";llm 通过闭包注入
        messages = state["messages"]
        if system_prompt:
            messages = [SystemMessage(content=system_prompt), *messages]
        response = llm_with_tools.invoke(messages)  # AIMessage,可能带 tool_calls
        return {"messages": [response]}

    builder = StateGraph(ChatState)
    builder.add_node("chatbot", chatbot)

    if tools:
        # tools 节点 = ToolNode:真正执行 tool_calls,产出 ToolMessage 回填
        builder.add_node("tools", ToolNode(tools))

        # 条件边:chatbot 结束后,若最后一条消息带 tool_calls -> tools,否则 -> END
        def should_continue(state: ChatState):
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        builder.add_conditional_edges("chatbot", should_continue, ["tools", END])
        builder.add_edge("tools", "chatbot")  # 工具执行完回到 chatbot,让模型基于结果作答
    else:
        builder.add_edge("chatbot", END)

    builder.add_edge(START, "chatbot")
    return builder.compile(checkpointer=checkpointer)


def save_history(messages, thread_id):
    """把完整对话历史渲染后落盘到 messages/ 目录(覆盖写,保证文件=当前完整对话)。"""
    log_dir = Path("messages")
    log_dir.mkdir(exist_ok=True)
    rendered = "\n".join(_render_message(m) for m in messages)
    with open(log_dir / f"chat-{thread_id}.log", "w", encoding="utf-8") as f:
        f.write(rendered + "\n\n")


def run_chat(
    llm,
    tools=None,
    system_prompt="你是一个乐于助人的 AI 助手",
    thread_id="terminal-chat-001",
):
    """终端交互入口:循环读输入 -> 流式调 graph -> 打印回复 -> 落盘历史。"""
    graph = build_chat_graph(
        llm, tools=tools, system_prompt=system_prompt, checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": thread_id}}  # 记忆按 thread_id 隔离

    print("==== 终端对话机器人 ====")
    print("输入 exit / quit / q 退出\n")

    while True:
        user_input = input("你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("再见!")
            break

        print("AI: ", end="", flush=True)
        # 流式输出:stream_mode="messages" 逐 token 产出增量,边生成边打印(打字机效果)
        for chunk, _meta in graph.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
            stream_mode="messages",
        ):
            # 只打印 AI 的文本增量;ToolMessage、以及工具调用阶段空 content 都跳过
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                print(chunk.content, end="", flush=True)
        print("\n")

        # 落盘:从 checkpointer 取出完整历史,渲染后写入 messages/ 目录
        history = graph.get_state(config).values["messages"]
        save_history(history, thread_id)
