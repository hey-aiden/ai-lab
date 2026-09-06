from app.config import global_config
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek


def in_deep_seek():
    # llm = ChatDeepSeek(
    #     model=global_config.model_deepseek,
    #     temperature=global_config.temperature,
    #     api_key=global_config.api_key_deepseek,
    # )
    print("hello word")
