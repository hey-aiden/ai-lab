"""
lang chain中的链式调用：
Runnable = 一个可以被调用的“执行单元”，它有统一的调度入口： result = runnable.invoke(input)
Runnable 最重要的思想：统一输入 → 输出; 两个 Runnable 可以连接

所以这些东西都可以成为 Runnable：
PromptTemplate
      ↓
ChatModel(llm)
      ↓
OutputParser
      ↓
自定义 Python 函数
      ↓
另一个 Chain

-------------------------
eg:
prompt = ChatPromptTemplate.from_template(
    "请介绍一下 {topic}"
)
model = ChatOpenAI()
chain = prompt | model
result = chain.invoke({
    "topic": "Redis"
})
-------------------------

「可以理解为：」

输入
{
    "topic": "Redis"
}

        ↓

PromptTemplate

        ↓

输出
ChatPromptValue

-------------------------
核心方法
1. invoke: 同步执行一次 (input) → output
2. ainvoke: 异步执行一次 (input) → output
eg: fastAPI:
@app.get("/chat")
async def chat():

    result = await chain.ainvoke({
        "topic": "Redis"
    })

    return result

3. 批量执行
eg:
inputs = [
    {"topic": "Redis"},
    {"topic": "Kafka"},
    {"topic": "MySQL"},
]
results = chain.batch(inputs)

4. 流式输出 chain.stream；通过 for in 遍历
for chunk in chain.stream({
    "topic": "Redis"
}):
    print(chunk)
-------------------------

Runnable的执行类型：
1. RunnableSequence：串行执行 chain = prompt | model | parser

2. RunnableParallel：并行执行
chain = RunnableParallel(
    summary=summary_chain,
    keywords=keyword_chain,
    category=category_chain
)

"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel


def runnable_call(llm):
    """
    链式调用的示例函数
    """
    # exec_normal(llm)
    # runnable_batch(llm)
    # runnable_stream(llm)
    runnable_parallel(llm)


def exec_normal(llm):
    prompt = ChatPromptTemplate.from_template("请介绍一下 {topic}, 30字以内")
    chain = prompt | llm
    result = chain.invoke({"topic": "Redis"})
    print(result.content)


def runnable_batch(llm):
    """
    批量调用的示例函数
    """
    prompt = ChatPromptTemplate.from_template("请介绍一下 {topic}, 50字以内")
    chain = prompt | llm
    inputs = [
        {"topic": "Redis"},
        {"topic": "Kafka"},
        {"topic": "MySQL"},
    ]
    results = chain.batch(inputs)
    for result in results:
        print(result.content, end="\n", flush=True)


def runnable_stream(llm):
    """
    流式输出的示例函数
    """
    prompt = ChatPromptTemplate.from_template("请介绍一下 {topic}, 100字以内")
    chain = prompt | llm
    for chunk in chain.stream({"topic": "Redis"}):
        # flush: 控制是否立即把 Python 的输出缓冲区刷新（flush）到终端/标准输出
        print(chunk.content, end="", flush=True)


def runnable_parallel(llm):
    """
    并行调用的示例函数
    """
    prompt_summary = ChatPromptTemplate.from_template("请总结一下 {topic}, 100字以内")
    summary_chain = prompt_summary | llm

    prompt_keywords = ChatPromptTemplate.from_template("请提取关键词 {topic}, 20个以内")
    keyword_chain = prompt_keywords | llm

    prompt_category = ChatPromptTemplate.from_template("请分类 {topic}, 10个以内")
    category_chain = prompt_category | llm

    chain = RunnableParallel(
        summary=summary_chain, keywords=keyword_chain, category=category_chain
    )

    result = chain.invoke({"topic": "Redis"})
    print(result.summary, result.keywords, result.category, end="\n", flush=True)
