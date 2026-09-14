"""
流式输出
"""

from langchain.messages import HumanMessage


def stream_output(agent):
    user_input = "请帮我写一个python函数，计算两个数的和"
    human_message = HumanMessage(content=user_input)

    # stream_mode="messages" 会逐 token 产出增量 chunk
    for chunk, metadata in agent.stream(
        {"messages": [human_message]},
        stream_mode="messages",
    ):
        # chunk 是 AIMessageChunk，content 是本次新增的文本片段
        if chunk.content:
            print(chunk.content, end="", flush=True)

    print()  # 结束后换行
