from langchain_core.messages import HumanMessage


def langchain_memory(agent):
    # thread_id 是关键。同一个 thread_id 下的对话是连续的，不同 thread_id 之间的对话完全隔离。这让你可以用一个 Agent 实例同时服务多个用户。
    config = {"configurable": {"thread_id": "user-001"}}
    result1 = agent.invoke(
        {"messages": [HumanMessage(content="我是aiden, 正在学习ai")]},
        config=config,
    )
    print(f"第一轮: {result1['messages'][-1].content}")

    result2 = agent.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？我在学什么？")]},
        config=config,
    )

    print(f"第二轮: {result2['messages'][-1].content}")
