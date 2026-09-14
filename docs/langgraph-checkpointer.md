# LangGraph Checkpointer 的实现机制

> 本文源于一次真实排查:`langchain-camp/app/model/use_memory.py` 里 `langchain_memory()` 执行报 `InvalidUpdateError: Expected dict, got [HumanMessage(...)]`,排查过程中发现除了输入格式错误外,`InMemorySaver` 根本没被接入 agent —— 记忆功能形同虚设。修复后整理出 checkpointer 的工作机制,便于后续学习与复用。
>
> 验证环境:`langgraph 1.2.x`、`langchain 1.4.x`(2026-09)。

---

## 一、结论先行

**Checkpointer 是 LangGraph 的"状态持久化层"**:它把每次 `invoke` / `stream` 结束时的图状态(State)快照保存下来,让下一次调用能"从上次断点继续",而不是从头开始。

| 问题 | 没有 checkpointer | 有 checkpointer |
|---|---|---|
| 多次 `invoke` 之间状态是否保留 | ❌ 每次都是全新状态 | ✅ 同 `thread_id` 下延续 |
| 多轮对话能否记住上文 | ❌ 记不住 | ✅ 能记住 |
| 能否"时间旅行"回到历史某一步 | ❌ | ✅ 通过 `checkpoint_id` / `parent_config` |

**核心三个要点:**

- 状态按 **`thread_id`** 分桶隔离:同一个 `thread_id` 下对话连续,不同 `thread_id` 完全隔离 —— 这让**一个 agent 实例可以同时服务多个用户**。
- 每次"超级步骤"(super-step)结束后,图调用 `checkpointer.put()` 写入一个 `Checkpoint`;下次调用先 `get_tuple()` 读回最新快照恢复状态。
- 快照之间通过 `parent_config` 串成一条**链(实为树/链表的父指针)**,这是"时间旅行"和回溯能力的数据基础。

---

## 二、先看项目里的实际用法

`langchain-camp` 中 checkpointer 的接入点有两处:

**1. 创建 agent 时传入 checkpointer**(`app/model/deep_seek.py`):

```python
from langgraph.checkpoint.memory import InMemorySaver

def create_chat(system_message="...", checkpointer=None):
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=system_message,
        checkpointer=checkpointer,   # 关键:把 checkpointer 挂到图上
    )
    return agent

def llm_memory():
    agent = create_chat(system_prompt, checkpointer=InMemorySaver())
    langchain_memory(agent)
```

**2. 调用时用 `config` 指定 `thread_id`**(`app/model/use_memory.py`):

```python
config = {"configurable": {"thread_id": "user-001"}}

result1 = agent.invoke({"messages": [HumanMessage(content="我是aiden, 正在学习ai")]}, config=config)
result2 = agent.invoke({"messages": [HumanMessage(content="我叫什么名字？我在学什么？")]}, config=config)
# 第二轮能正确回答 "你叫 Aiden,正在学 AI",正是 checkpointer 起了作用
```

> 注意:`create_agent` 返回的是 **LangGraph 编译图(compiled graph)**,`invoke` 的输入必须是状态字典 `{"messages": [...]}`,不能直接传裸列表 `[HumanMessage(...)]` —— 这正是当初报 `InvalidUpdateError` 的根因。

---

## 三、核心数据结构

Checkpointer 围绕三个 dataclass 工作(字段取自 `langgraph.checkpoint.base`):

### 1. `Checkpoint` —— 一次状态快照

```python
class Checkpoint:
    v: int                          # 快照 schema 版本号
    id: str                         # checkpoint 唯一 ID
    ts: str                         # 时间戳
    channel_values: dict[str, Any]  # 各 channel(状态键)的实际值
    channel_versions: dict[str, int|str]  # 各 channel 的版本号
    versions_seen: dict[str, dict]  # 每个节点见过的各 channel 版本
    updated_channels: list[str] | None  # 本次更新了哪些 channel
```

- **`channel_values`** 是真正要持久化的东西 —— 对 `MessagesState` 来说就是 `{"messages": [...]}`。
- **`channel_versions`** 是增量机制的基石:每个 channel 有一个单调递增的版本号,用来判断"哪个字段变了、变了多少次",从而实现增量读写与并发控制。

### 2. `CheckpointMetadata` —— 快照的元信息

```python
class CheckpointMetadata:
    source: Literal['input', 'loop', 'update', 'fork']  # 快照来源
    step: int                        # 第几个超级步骤
    parents: dict[str, str]          # 父 checkpoint 的 (namespace → id) 映射
    run_id: str                      # 本次运行 ID
    counters_since_delta_snapshot: dict  # 距上次增量快照的计数
```

- **`source`** 区分快照因何产生:`input`(输入)、`loop`(循环迭代)、`update`(外部状态更新)、`fork`(分叉)。
- **`parents`** 是关键:记录"这个快照是从哪个父快照派生的",配合下面的 `parent_config` 构成历史链。

### 3. `CheckpointTuple` —— checkpointer 读写返回的完整单元

```python
class CheckpointTuple:
    config: RunnableConfig            # 该快照对应的 config(含 thread_id / checkpoint_id)
    checkpoint: Checkpoint            # 快照本体
    metadata: CheckpointMetadata      # 元信息
    parent_config: RunnableConfig | None  # 父快照的 config(没有则 None)
    pending_writes: list[PendingWrite] | None  # 未落盘的中间写入
```

- **`parent_config` 指向上一层快照**,一层层往回指,就得到整条对话历史 —— 这是"时间旅行"的实现方式:给定任意 `checkpoint_id`,顺着 `parent_config` 就能重建到任意历史节点。

---

## 四、工作机制:写入与恢复

### 写入(`put`)

LangGraph 每次执行到一个"超级步骤"边界(节点批次跑完、遇到 `interrupt` 或图结束)时,会:

1. 收集当前状态所有 channel 的值 → 组装 `channel_values`;
2. 调用 `get_next_version()` 为变化的 channel 生成新版本号;
3. 调用 `checkpointer.put(config, checkpoint, metadata, new_versions)` 持久化;
4. `put` 返回一个 `CheckpointTuple`,`metadata.parents` 指向父快照。

### 恢复(`get_tuple` / `get`)

下一次 `invoke` 携带同样的 `config`(重点是同一个 `thread_id`)时,图会:

1. 调 `checkpointer.get_tuple(config)` 读回该 `thread_id` 下**最新**的快照;
2. 把 `channel_values` 灌回状态,从断点继续执行;
3. 若 `config` 里带了具体 `checkpoint_id`,则读到**指定历史快照**而非最新 —— 这就是回溯。

### `BaseCheckpointSaver` 的公开 API

`InMemorySaver` / `SqliteSaver` / `PostgresSaver` 都实现同一套接口(来自 `langgraph.checkpoint.base.BaseCheckpointSaver`):

| 方法 | 作用 |
|---|---|
| `put` / `aput` | 写入一个 checkpoint |
| `get` / `aget` | 读指定 `config` 的 checkpoint |
| `get_tuple` / `aget_tuple` | 读回 `CheckpointTuple`(含 `parent_config`) |
| `list` / `alist` | 列出某 `thread_id` 下所有 checkpoint |
| `put_writes` | 落盘中间写入(支持增量/故障恢复) |
| `get_next_version` | 生成下一个 channel 版本号 |
| `delete_thread` / `copy_thread` / `prune` | 删除 / 复制 / 清理线程 |

> 同步 / 异步各一套(`put` ↔ `aput` 等),异步版本供 `AsyncGraph` 使用。

### 序列化:`serde`

`BaseCheckpointSaver` 持有 `serde`(类型 `SerializerProtocol`),负责把 `channel_values` 里的 Python 对象(含 `Message` 等)序列化后再落盘。`InMemorySaver` 构造签名是:

```python
InMemorySaver(*, serde: SerializerProtocol | None = None, factory=defaultdict)
```

- `serde=None` 时使用默认序列化器;不同后端选择不同(JSON 系列更可移植,pickle 保真但不可跨语言/有安全风险)。
- 这也是为什么"内存里是个对象、落盘后是字节"——序列化层隔在中间。

---

## 五、`thread_id` 与 config 的约定

Checkpointer 靠 `config["configurable"]` 定位状态,三个关键字段:

```python
config = {
    "configurable": {
        "thread_id": "user-001",      # 必填:对话线程标识,状态隔离的最小单位
        "checkpoint_id": "...",       # 可选:定位到某个历史 checkpoint(时间旅行)
        "checkpoint_ns": "...",       # 可选:子图命名空间,避免父子图状态串号
    }
}
```

- **`thread_id` 是灵魂**:同一个值 = 同一段连续对话;换一个值 = 全新会话。项目里写死 `"user-001"` 是演示,生产里通常用 `user_id + session_id` 拼成。
- 这就是"**一个 agent 实例服务多用户**"的原理:状态存在 checkpointer 里、按 `thread_id` 分桶,agent 本身无状态。

---

## 六、不同后端的取舍

| 后端 | 存储 | 适用场景 |
|---|---|---|
| `InMemorySaver` | 内存(dict) | 开发、测试、单进程演示,重启即丢 |
| `SqliteSaver` | SQLite 文件 | 单机小规模、需要跨进程重启保留 |
| `PostgresSaver` | PostgreSQL | 生产、多副本、需并发与持久化 |

`langchain-camp` 当前用 `InMemorySaver`,因为项目定位是"学习/实验"——够用且零依赖;若要跨重启保留记忆,换成 `SqliteSaver` 即可,接口完全一致。

---

## 七、常见坑(排查要点)

1. **输入格式错误**:`create_agent` 的图要求状态字典 `{"messages": [...]}`,直接传 `[HumanMessage(...)]` 会报 `InvalidUpdateError: Expected dict`。
2. **只 `new` 不接线**:创建了 `InMemorySaver` 却没传给 `create_agent(checkpointer=...)`,`thread_id` 配置被忽略,记忆静默失效(不报错但记不住)。
3. **忘了传 config**:`invoke` 时不带 `config`(或 `thread_id` 每次随机),等于每次都开新线程,同样记不住。
4. **序列化不兼容**:换后端时若对象含不可 JSON 序列化的类型,pickle 保真但跨进程/跨语言有风险,需要时显式传 `serde`。

---

## 八、延伸阅读

- LangGraph 官方:`checkpoint` 概念与 `BaseCheckpointSaver`(`langgraph.checkpoint.base`)。
- 时间旅行 / 回溯:基于 `parent_config` 链与 `checkpoint_id` 定位。
- 持久化 + 恢复:结合 `put_writes` 的中间写入机制,支持长任务故障续跑。
