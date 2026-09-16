# Python 的 `|` 运算符与 Runnable 声明式组合

> 本文解释一个"看似魔法、实则朴素"的问题:为什么 LangChain 里写 `prompt | llm | parser` 就能把三个组件串成一条执行链?
>
> 答案分三层,由浅入深:`|` 本来是 Python 的按位或/并集运算符 → 它本质上是特殊方法 `__or__` 的语法糖,任何类都能重载 → LangChain 的 `Runnable` 重载了 `__or__`,把它从"或运算"改写成了"组合运算"。
>
> 验证环境:`langchain-core 1.6.2`、`langchain 1.4.x`(2026-09)。

---

## 一、`|` 在 Python 里的本来含义

`|` 是 Python 的内置二元运算符,最常见的三种用法都跟"合并/或"有关:

| 类型 | 表达式 | 结果 | 底层方法 |
|---|---|---|---|
| 整数 | `1 | 2` | `3`(按位或:`0b01 | 0b10 = 0b11`) | `int.__or__` |
| 集合 | `{1, 2} | {2, 3}` | `{1, 2, 3}`(并集) | `set.__or__` |
| 字典 | `{"a": 1} | {"b": 2}` | `{"a": 1, "b": 2}`(合并,Py3.9+) | `dict.__or__` |

注意区分 `|` 和 `or`:

- **`or`** 是短路逻辑运算,返回的是**两个操作数之一**(看谁真),不重载、不能自定义。
- **`|`** 是真正的运算符,返回的是**一个新对象**,而且能被自定义类重载。

```python
"" or "x"        # -> "x"(返回操作数本身)
set() or {"x"}   # -> {"x"}
{1, 2} | {3}     # -> {1, 2, 3}(返回一个新的并集对象)
```

这一层是大多数人对 `|` 的认知。但"按位或/并集"只是 `int`、`set`、`dict` 这几个内置类型**各自选择**的语义,不是 `|` 本身的规定。`|` 真正被定义的地方,在下一层。

---

## 二、`|` 的本质:特殊方法(dunder)的语法糖

Python 里,`a | b` 并不直接"做或运算",它只是**一次方法调用的语法糖**。求值顺序如下:

1. 先调左操作数的 `__or__`:`type(a).__or__(a, b)`。
2. 若 `a` 没有 `__or__`、或 `__or__` 返回 `NotImplemented`,则尝试**反向**方法:`type(b).__ror__(b, a)`。
3. 两者都 `NotImplemented`,才抛 `TypeError`。

对应的 `|=` 走 `__ior__`(原地更新)。这套机制统一在 Python 数据模型的 **"特殊方法协议"** 里:

```python
a | b     # 等价于 a.__or__(b),失败则 b.__ror__(a)
a |= b    # 等价于 a.__ior__(b)
```

> 补充一个边界:`|` 也受"反射方法优先"规则约束 —— 若右操作数的类型是左操作数类型的**子类**,且两者 `__or__`/`__ror__` 定义不同,Python 会**优先**调右边的 `__ror__`。对理解 LangChain 不是必需,知道存在即可。

关键结论:**`|` 的含义完全由 `__or__` 的返回值决定,而 `__or__` 的返回值可以是任何对象** —— 不一定是布尔、不一定是集合。

---

## 三、运算符重载:任何类都能自定义 `|`

给一个类写个 `__or__`,就能让 `|` 做出任何你想做的事:

```python
class Step:
    def __init__(self, name):
        self.name = name

    def __or__(self, other):
        # 返回值完全自定义:这里返回一个"拼接描述",而不是布尔
        return Step(f"{self.name} -> {other.name}")

    def __repr__(self):
        return f"Step({self.name!r})"

a = Step("加载数据")
b = Step("清洗数据")
c = Step("训练模型")

pipeline = a | b | c          # 看起来像在"或运算",实则在调 __or__
print(pipeline)               # Step('加载数据 -> 清洗数据 -> 训练模型')
```

这里发生了三件事,正是理解 LangChain 的钥匙:

1. **`|` 不再表示"或"** —— `a | b` 的语义被 `__or__` 重写成了"拼接/组合"。
2. **返回值是新对象** —— 每次 `|` 都返回一个新的 `Step`,而不是执行结果。原始对象 `a`、`b`、`c` 都原封不动。
3. **惰性(声明式)** —— `pipeline = a | b | c` 只是**描述**了一条流程,此刻什么都没"运行"。真正跑要另想办法(比如 `pipeline.run()`)。

LangChain 的 `Runnable | Runnable` 用的就是完全一样的思路,只是把 `Step` 换成了 `Runnable`。

---

## 四、LangChain 把 `__or__` 重载成"组合"

`Runnable` 是所有可执行单元的抽象基类,它重载了 `__or__`,源码(节选自 `langchain_core/runnables/base.py`)只有一行:

```python
class Runnable:
    def __or__(self, other):
        # 组合 self 与 other,生成一条 RunnableSequence
        return RunnableSequence(self, coerce_to_runnable(other))

    def __ror__(self, other):
        # 反向组合:允许 "dict | runnable" 这种写法
        return RunnableSequence(coerce_to_runnable(other), self)
```

于是:

```python
prompt = ChatPromptTemplate.from_template("请介绍一下 {topic}")
model  = ChatDeepSeek()          # 项目里是 ChatDeepSeek / ChatOpenAI

chain = prompt | model           # 返回的是 RunnableSequence,不是回答
```

对照上一节的 `Step`:

| `Step` 版 | `Runnable` 版 |
|---|---|
| `a \| b` 返回新的 `Step` | `prompt \| model` 返回新的 `RunnableSequence` |
| 语义 = "拼接描述" | 语义 = "组合成链" |
| 惰性,不执行 | 惰性,不执行 |

**`chain = prompt | model` 这一行没有调用任何模型**,它只是构造了一个描述"先填模板、再喂模型"的对象。真正执行是后面的 `chain.invoke({"topic": "Redis"})` —— 这也是为什么"声明式"三个字对 LangChain 如此重要(详见第七节)。

### `__ror__`:让普通对象也能写在左边

注意 `__or__` 只在**左边**是 `Runnable` 时被调用。那 `{"context": ...} | prompt` 这种"左边是个 dict"的写法为什么能工作?

因为 Python 调 `dict.__or__` 失败后(对 dict 而言这不是合并语义),会转而调**右边** `prompt.__ror__(dict)` —— LangChain 用它把 dict 接在链的最前面。`__ror__` 的存在,正是为了覆盖"Runnable 在右边"的场景。

---

## 五、`coerce_to_runnable`:让"不是 Runnable 的东西"也能接上

`__or__` 里那一句 `coerce_to_runnable(other)` 是另一块关键拼图。它把右边"长得像 Runnable 的东西"自动转换成真 Runnable:

```python
def coerce_to_runnable(thing):
    if isinstance(thing, Runnable):        return thing          # 已经是 Runnable,原样用
    if is_async_generator(thing) or inspect.isgeneratorfunction(thing):
        return RunnableGenerator(thing)                          # 生成器函数 -> 流式
    if callable(thing):                    return RunnableLambda(thing)   # 普通函数 -> Runnable
    if isinstance(thing, dict):            return RunnableParallel(thing) # 字典 -> 并行
    raise TypeError(...)
```

这意味着 `|` 右边可以写四种东西,编译器/解释器层面并不会报错:

```python
chain1 = prompt | llm                          # Runnable | Runnable
chain2 = prompt | llm | StrOutputParser()       # ... | Runnable

chain3 = prompt | (lambda x: x.upper())         # Runnable | 函数  -> 被包成 RunnableLambda
chain4 = {"a": chain_a, "b": chain_b} | merge   # dict | Runnable -> dict 被包成 RunnableParallel
```

这就是 LangChain 常说的 **LCEL(LangChain Expression Language)** 的基础:因为 `|` 的右操作数会被 `coerce_to_runnable` 统一收编,所以你能把 Runnable、普通函数、dict 自由地混在同一串管道里。

---

## 六、`|` 的求值顺序与"扁平化"

`|` 是**左结合**的,`a | b | c` 等价于 `(a | b) | c`,分两步:

```python
seq1 = a | b          # RunnableSequence(first=a, last=b)
seq2 = seq1 | c       # 此时左边已是一个 RunnableSequence
```

如果 `RunnableSequence.__or__` 只是简单地再包一层,三次 `|` 会得到"套娃"式的嵌套结构。LangChain 特意在 `RunnableSequence` 里**扁平化**了它(节选):

```python
class RunnableSequence:
    def __or__(self, other):
        if isinstance(other, RunnableSequence):
            # 两个序列相连:把 first/middle/last 全部铺平
            return RunnableSequence(
                self.first, *self.middle, self.last,
                other.first, *other.middle, other.last,
            )
        return RunnableSequence(self.first, *self.middle, self.last, coerce_to_runnable(other))
```

效果:`prompt | llm | parser` 最终是一个**扁平的** `RunnableSequence(first=prompt, middle=[llm], last=parser)`,而不是两层嵌套。这对后续的 `invoke`/`stream`/`batch` 统一遍历、以及序列化都更友好。

---

## 七、声明式构建执行链:心智模型

前面铺垫这么多,可以收敛成一个核心结论:

> **`prompt | llm | parser` 是"描述"一条链,而不是"执行"一条链。**

| | 命令式(imperative) | 声明式(declarative) |
|---|---|---|
| 你在写什么 | 每一步**怎么做**(取数 → 调模型 → 解析) | 每一步**是什么**(有哪些步骤、顺序如何) |
| 何时运行 | 边写边运行 | 写完不运行,`invoke()` 才运行 |
| 对应代码 | 手写 for/if 逐步调用 | `chain = prompt \| llm \| parser` |

`|` 在这里起的作用,和 shell 的管道 `|`、函数式编程里的 `compose` 是同一个心智模型:**数据从左边流入,经过每个环节加工,从右边流出**。

```python
chain = prompt | llm | StrOutputParser()
#        输入         加工           加工           输出
#      {"topic"}   ChatPromptValue  AIMessage      str
```

"声明式"带来的实际收益:

- **组合与复用**:每个环节是独立 `Runnable`,可单独 `invoke`,也可和其他环节任意拼接。
- **一套对象、多种执行方式**:`invoke` / `stream` / `batch` 及对应的 `a` 前缀异步版,都从同一个 `chain` 派生 —— 因为链本身只是"描述",执行策略是后面再选的。
- **可序列化 / 可编排**:`RunnableSequence` 是 `RunnableSerializable`,能把整条链的描述存下来或交给 LangGraph 去调度。

---

## 八、逐步拆解一个真实例子

回到项目 `app/model/runnable_chain.py` 里的写法:

```python
prompt = ChatPromptTemplate.from_template("请介绍一下 {topic}, 30字以内")
chain  = prompt | llm | StrOutputParser()
result = chain.invoke({"topic": "Redis"})
```

按 `|` 的规则一步步走:

1. `prompt | llm`
   - 左 `prompt` 是 `Runnable`,调 `prompt.__or__(llm)`
   - `llm` 已是 `Runnable`,`coerce_to_runnable` 原样返回
   - 得 `RunnableSequence(first=prompt, last=llm)`,**不执行**

2. `... | StrOutputParser()`
   - 左边是 `RunnableSequence`,走它的 `__or__`,把 `StrOutputParser` 追加到末尾
   - 得扁平的 `RunnableSequence(first=prompt, middle=[llm], last=StrOutputParser)`,**仍不执行**

3. `chain.invoke({"topic": "Redis"})`
   - 这才是"跑"的时刻:输入 dict → `prompt` 填出 `ChatPromptValue` → `llm` 产出 `AIMessage` → `StrOutputParser` 抽出纯文本 `str`

整条链的类型流:

```
{"topic": "Redis"}   --prompt-->   ChatPromptValue   --llm-->   AIMessage   --parser-->   "Redis 是……"
   (dict)                          (PromptValue)               (Message)                 (str)
```

每一步的输出正好是下一步的输入,`Runnable` 的"统一接口(输入 → 输出)"让任意两个环节都能对上。

---

## 九、常见坑与注意点

1. **把 `|` 当成 `or`**:`prompt or llm` 不会组合,只会返回其中一个对象(短路)。必须用 `|`。
2. **以为 `chain = prompt | llm` 会调用模型**:不会,这行只是构造描述;忘记 `invoke` 是"写好了链却从不执行"的头号原因。
3. **左右类型要能被收编**:`|` 右边如果既不是 `Runnable`、也不是 callable/dict/generator,`coerce_to_runnable` 会抛 `TypeError`。普通数字、字符串不能直接接在 `|` 后面。
4. **`NotImplemented` 的细节**:LangChain 的 `__or__` 故意**不返回 `NotImplemented`**,而是对无法收编的对象直接抛 `TypeError`。这是刻意的 —— 它要保证 LCEL 的组合语义"赢"过左操作数可能存在的无关 `__or__` 实现,避免被意外的反向方法劫持。
5. **`|=` 不被用于组合**:`Runnable` 没有把 `__ior__` 定义成"原地拼接",别期望 `chain |= x` 的语义;链式组合一律用 `|`。

---

## 十、延伸阅读

- Python 数据模型 / 特殊方法协议:`__or__`、`__ror__`、`__ior__`(Python 官方文档 Data model)。
- `langchain_core/runnables/base.py`:`Runnable.__or__` / `__ror__` / `pipe`、`RunnableSequence`、`coerce_to_runnable`。
- LCEL 官方文档:LangChain Expression Language 的 `|` 组合语义。
- 相关记忆/文档:`docs/langgraph-checkpointer.md`(Runnable 之上,如何编排复杂工作流)。
