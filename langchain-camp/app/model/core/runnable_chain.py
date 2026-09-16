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
runnable 核心方法
1. invoke: 同步执行一次 (input) → output
2. ainvoke: 异步执行一次 (input) → output
eg: fastAPI:
@app.get("/chat")
async def chat():

    result = await chain.ainvoke({
        "topic": "Redis"
    })

    return result
3. 批量同步执行-batch    批量异步执行-abatch
eg:
inputs = [
    {"topic": "Redis"},
    {"topic": "Kafka"},
    {"topic": "MySQL"},
]
results = chain.batch(inputs)

4. 流式输出 chain.stream() - 同步流式执行，逐步返回结果；    astream()-异步流式执行，逐步返回结果
流式输出，返回一个迭代器，边输出边返回结果
通过 for in 遍历;
for chunk in chain.stream({
    "topic": "Redis"
}):
    print(chunk)
-------------------------

Runnable的执行类型：
1. RunnableSequence：串行执行 chain = prompt | model | parser

2. RunnableParallel：并行执行；
构造时接收 {key: Runnable} 形式的 dict，给每个 key 指定一个"处理器"（Runnable），每个处理器都接收同一份输入，各自产出结果，最后把结果按 key 组装成一个 dict 输出
chain = RunnableParallel(
    summary=summary_chain,
    keywords=keyword_chain,
    category=category_chain
)

3. RunnablePassthrough: 原样传递
常见用法：
· 原样透传（无参）
· 透传时做变换（位置参数，可调用） RunnablePassthrough(lambda x: x["topic"])   # 透传，但先做变换
· assign 才是「保留输入 + 追加字段」

4. RunnableLambda: 把普通 Python 函数变成 Runnable, 方便于把业务逻辑插进 LangChain




如何理解 Chain 和 Runnable 到底是什么关系？
· Runnable 是抽象标准，Chain 是多个 Runnable 组合形成的执行流程。

Runnable
   ↓
RunnableSequence
   ↓
一个 Chain

Runnable 的真正价值：统一接口


Runnable 和 LangGraph 的关系：

Runnable
    ↓
解决“组件怎么执行/组合”

LangGraph
    ↓
解决“复杂 Agent 工作流怎么运行”

"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)


def runnable_call(llm):
    """
    链式调用的示例函数
    """
    # exec_normal(llm)
    # runnable_batch(llm)
    # runnable_stream(llm)
    # runnable_parallel(llm)
    runnable_passthrough(llm)


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

    prompt_keywords = ChatPromptTemplate.from_template(
        "请提取关键词 {topic}, 20个字以内"
    )
    keyword_chain = prompt_keywords | llm

    prompt_category = ChatPromptTemplate.from_template("请分类 {topic}, 10个字以内")
    category_chain = prompt_category | llm

    chain = RunnableParallel(
        summary=summary_chain, keywords=keyword_chain, category=category_chain
    )

    # 如果 invoke 调用的话，需要等所有分支都完成后，才返回最终结果
    # result = chain.invoke({"topic": "Redis"})
    # for key, val in result.items():
    #     print(key, ":", val.content, end="\n", flush=True)

    # 如果是 stream 调用的话，可以边输出边返回结果
    char_list = list()
    for chunk in chain.stream({"topic": "Redis"}):
        print(chunk, end="\n", flush=True)
        for key, val in chunk.items():
            print(key, ":", val.content, end="\n", flush=True)
            char_list.append(val.content)
    print(char_list, end="\n", flush=True)

    # print(
    #     result["summary"].model_dump(),
    #     "\n",
    #     "直接class对象打印：",
    #     result["summary"].content,
    #     "\n",
    #     type(result),  # <class 'dict'>
    #     type(result["summary"]), # <class 'langchain_core.messages.ai.AIMessage'>
    #     end="\n",
    #     flush=True,
    # )


def runnable_passthrough(llm):
    """
    原样传递的示例函数：RunnablePassthrough 本身不会自动构建 {"original": ..., "answer": ...} 这种结构，它只是把输入原样传递下去
    """
    prompt = ChatPromptTemplate.from_template("请介绍一下 {topic}, 30字以内")
    chain = prompt | llm | RunnablePassthrough()
    result = chain.invoke({"topic": "Redis"})
    print(result, end="\n", flush=True)

    # 正确构造方式
    #
    # 输出：{'topic': 'Redis', 'answer': 'Redis 是高性能的内存键值数据库，常用于缓存。'}
    chain = RunnablePassthrough.assign(answer=prompt | llm | StrOutputParser())
    res = chain.invoke({"topic": "Redis"})
    print(res, end="\n", flush=True)

    # 构造自定义字段 {'original': 'Redis', 'answer': 'Redis 是高性能的内存键值数据库，常用于缓存。'}
    chain = (
        {
            "original": RunnablePassthrough()  # RunnablePassthrough()：原样透传 → {"topic": "Redis"}
            | RunnableLambda(
                lambda x: x["topic"]
            ),  # 从 dict 里取 topic → "Redis", 如果没有这个，那么得到的 original 就是整个 dict {"topic": "Redis"} ->  'original': {'topic': 'Redis'}
            "answer": prompt | llm | StrOutputParser(),
        }
        | RunnablePassthrough()
    )  # 通过 runnable 调用链，返回一个 runnable 对象
    res2 = chain.invoke({"topic": "Redis"})
    print(res2, end="\n", flush=True)

    # 更简单的方式 - 单独使用 dict 时，用 RunnableParallel 显式包装
    chain = RunnableParallel(
        original=RunnableLambda(lambda x: x["topic"]),
        answer=prompt | llm | StrOutputParser(),
    )
    res3 = chain.invoke({"topic": "Redis"})
    print("res3: ", res3, end="\n", flush=True)
