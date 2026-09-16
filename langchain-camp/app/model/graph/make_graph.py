"""
langGraph核心概念： State / Node / Edge / Graph
LangGraph = 用 State + Node + Edge 描述一个可循环、可分支、有状态的 AI 工作流

State: 整个 AI 工作流共享的数据
eg:
class State(TypedDict):
    messages: list

Node: 本质就是 一个接收 State，然后修改 State 的函数


Edge: 决定下一步走哪里


Graph: State + Node + Edge

"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    message: str


def node_parse_input(state: State):
    return {"message": state["message"] + "world"}


def node_tool_call(state: State):
    return 1


def basic_workflow():
    # 1. 创建 State
    builder = StateGraph(State)
    # 2. 添加 Node
    builder.add_node("node_parse_input", node_parse_input)
    # builder.add_node("node_tool_call", node_tool_call)
    # 3. 连接
    builder.add_edge(START, "node_parse_input")
    # builder.add_edge("node_parse_input", "node_tool_call")
    # builder.add_edge("node_tool_call", END)
    builder.add_edge("node_parse_input", END)
    # 4. 构建
    graph = builder.compile()

    result = graph.invoke({"message": "hello"})

    print(result)


def create_workflow():
    # basic_workflow()
    class State(TypedDict):
        message: str

    def node_parse_input(state: State):
        return {"message": state["message"] + "world!001"}

    builder = StateGraph(State)
    builder.add_node("node_parse_input", node_parse_input)
    builder.add_edge(START, "node_parse_input")
    builder.add_edge("node_parse_input", END)
    graph = builder.compile()
    result = graph.invoke({"message": "hello"})
    print(result)
