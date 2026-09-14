from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek

from app.config import global_config


def in_deep_seek():
    deep_seek_config = global_config["deep_seek"]
    print(deep_seek_config)
    llm = ChatDeepSeek(
        model=deep_seek_config["MODEL"],
        temperature=deep_seek_config["TEMPERATURE"],
        api_key=deep_seek_config["API_KEY"],
    )

    prompt_extract = ChatPromptTemplate.from_template(
        # "Extract the technical specifications from the following text: \n\n{text_input}"
        "提取以下文本中的技术规格信息: \n\n{text_input}"
    )

    prompt_transform = ChatPromptTemplate.from_template(
        # "Transform the following specifications into a JSON object with 'cpu', 'memory', and 'storage' as keys: \n\n{specifications}"
        "将以下规格转换为一个 JSON 对象，并以 cpu、memory 和 storage 作为键: \n\n{specifications}"
    )

    # 处理流水线（pipeline），| 是 LCEL 的管道操作符，表示把前一个组件的输出传给后一个组件，LCEL 的核心思想就是把不同组件组合成 Runnable 链
    extraction_chain = prompt_extract | llm | StrOutputParser()

    full_chain = (
        {"specifications": extraction_chain}
        | prompt_transform
        | llm
        | StrOutputParser()
    )
    # input_text = "The new laptop model features a 3.5 GHz octa-core processor, 16GB of RAM, and 1TB NVMe SSD."
    input_text = "这款新型笔记本电脑配备了 3.5 GHz 八核处理器、16GB 内存和 1TB NVMe SSD"

    final_result = full_chain.invoke({"text_input": input_text})
    print("\n --- Final JSON Output ---")
    print(final_result)
