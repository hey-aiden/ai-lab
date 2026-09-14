from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver

from app.config import global_config

from .stream_output import stream_output
from .structure_output import CourseInfo, structure_output
from .text_input import process_text
from .use_memory import langchain_memory


def load_llm():
    deep_seek_config = global_config["deep_seek"]
    llm = ChatDeepSeek(
        model=deep_seek_config["MODEL"],
        temperature=deep_seek_config["TEMPERATURE"],
        api_key=deep_seek_config["API_KEY"],
    )
    return llm


def create_chat(system_message="你是一个实用工具助手", checkpointer=None):
    llm = load_llm()
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=system_message,
        checkpointer=checkpointer,
    )
    return agent


def create_chat_with_structure(system_message, structure_model):
    llm = load_llm()
    agent = create_agent(
        model=llm,
        system_prompt=system_message,
        response_format=structure_model,
    )
    return agent


def create_agent_with_tools(system_message, tools):
    llm = load_llm()
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_message,
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


def llm_structure():
    system_prompt = "你是菜鸟教程 RUNOOB 的课程助手，从用户描述中提取课程信息。"
    agent = create_chat_with_structure(system_prompt, CourseInfo)

    structured_data = structure_output(agent)
    print(structured_data)


def llm_tool():
    system_prompt = "你是一个实用工具助手"
    tools = []  # 在这里添加你的工具列表
    agent = create_agent_with_tools(system_prompt, tools)
    process_text(agent)


def in_deep_seek():
    llm_structure()
