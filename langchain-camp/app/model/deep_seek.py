from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver

from app.config import global_config

from .stream_output import stream_output
from .text_input import process_text
from .use_memory import langchain_memory


def create_chat(system_message="你是一个实用工具助手", checkpointer=None):
    deep_seek_config = global_config["deep_seek"]
    llm = ChatDeepSeek(
        model=deep_seek_config["MODEL"],
        temperature=deep_seek_config["TEMPERATURE"],
        api_key=deep_seek_config["API_KEY"],
    )
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=system_message,
        checkpointer=checkpointer,
    )
    return agent


def llm_process():
    agent = create_chat()
    process_text(agent)


def llm_memory():
    system_prompt = "你是一个python学习助手"
    agent = create_chat(system_prompt, checkpointer=InMemorySaver())
    langchain_memory(agent)


def llm_stream():
    system_prompt = "你是一个实用工具助手"
    agent = create_chat(system_prompt)
    stream_output(agent)


def in_deep_seek():
    llm_stream()
