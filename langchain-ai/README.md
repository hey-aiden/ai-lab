# langchain-ai 聊天服务

一个基于 LangChain + FastAPI + MySQL 的下游**对话服务**,提供 OpenAI 兼容的
`/v1/chat/completions` 接口(SSE 流式),并把会话历史持久化到 MySQL。

定位:本服务不直接面对终端用户,而是由**上游 AI 网关**(另一个 FastAPI 项目,负责
路由 / 鉴权 / 多模型分发)通过 HTTP 调用。

---

## 架构设计

### 分层架构

自上而下,每层只依赖它的下一层,职责单一:

```
              ┌──────────────────────────────┐
              │        上游 AI 网关(外部)       │
              │    路由 / 鉴权 / 多模型分发      │
              └──────────────┬───────────────┘
                             │ HTTP · OpenAI 兼容 · SSE
              ┌──────────────▼───────────────┐
              │       api/   接口层           │
              │  chat.py · conversations.py   │
              │  deps.py(依赖注入)             │
              └──────────────┬───────────────┘
                             │ 调用
              ┌──────────────▼───────────────┐
              │     services/  编排层          │
              │        stream_chat()          │
              └───┬──────────┬──────────┬─────┘
                  │          │          │
        ┌─────────▼───┐ ┌────▼─────┐ ┌──▼────────┐
        │  memory/    │ │  llm/    │ │ schemas/  │
        │ 历史+会话 DAO│ │ 模型工厂 │ │ DTO        │
        └─────┬───────┘ └──────────┘ └───────────┘
              │
        ┌─────▼───────┐
        │ models/ ORM │
        └─────┬───────┘
              │
        ┌─────▼───────┐
        │ db/ 引擎/session│
        └─────┬───────┘
              │
        ┌─────▼───────┐
        │    MySQL    │
        └─────────────┘
```

- **api/** 只做 HTTP 事:解析请求、参数校验、组装响应/SSE,不含业务逻辑。
- **services/** 编排层:串起「加载历史 → 调模型 → 流式返回 → 落库」,是唯一理解完整业务流程的地方。
- **memory/** 面向 LangChain 消息对象的持久化 DAO,不关心 HTTP。
- **llm/** 模型工厂,屏蔽具体厂商实例化细节。
- **models/** 纯 ORM 表映射,不依赖 FastAPI / LangChain。
- **db/** 提供异步引擎与 session 工厂,可被测试注入 SQLite。

### 请求数据流

**聊天(带 `session_id`)**

```
网关 POST /v1/chat/completions (session_id + 新消息)
  → api/chat.py 解析请求,调 services.stream_chat(session_factory, model, request)
  → 生成器内打开 session,用 MySqlChatMessageHistory 按 session_id 加载历史
  → build_messages(history, incoming) 拼出完整消息列表
  → model.astream() 逐 token 产出 chat.completion.chunk
  → 流结束后把「本次用户消息 + 助手完整回复」写回 MySQL
  → 末尾分片带上 usage(token 统计)
```

**会话管理**

```
api/conversations.py → ConversationManager → ConversationModel / ChatMessageModel
                        (SQLAlchemy 异步 session)
```

### 关键设计决策

| 决策 | 理由 |
|------|------|
| **手动编排,而非 `RunnableWithMessageHistory`** | SSE 流式下自动回写时机难控;手动编排显式、可调试 |
| **session 在流式生成器内打开** | 避免 FastAPI 依赖清理与 `StreamingResponse` 生命周期错位(踩 `session is closed`) |
| **依赖注入 `get_session_factory` / `get_model`** | 测试时覆盖为 SQLite + 假模型,不依赖真实 MySQL / DeepSeek |
| **`MySqlChatMessageHistory` 请求作用域** | 底层绑定 `AsyncSession` 与 `session_id`,单例会跨请求污染(见 `memory/read.md`) |
| **OpenAI 兼容 + 扩展字段** | 网关可直接用 OpenAI SDK 对接;`session_id` / `user_id` 为扩展,历史由服务端托管 |

---

## 目录结构

```
langchain-ai/
├── src/app/
│   ├── main.py            # FastAPI 实例 + lifespan 建表 + 路由注册 + run()
│   ├── config.py          # pydantic-settings,读取 .env
│   ├── db/
│   │   └── session.py     # Base 基类、引擎/session 工厂、get_db 依赖
│   ├── models/
│   │   └── chat.py        # ConversationModel / ChatMessageModel 两张 ORM 表
│   ├── memory/
│   │   ├── history.py     # MySqlChatMessageHistory:消息增删查(LangChain 消息 ↔ DB)
│   │   ├── manage.py      # ConversationManager:会话新建/列表/删除
│   │   └── read.md        # 说明为何历史 DAO 不能做成单例
│   ├── llm/
│   │   └── deep_seek.py   # DeepSeek 模型工厂(chat / agent)
│   ├── schemas/
│   │   ├── chat.py        # OpenAI 兼容 chat.completion 请求/响应 DTO
│   │   └── conversation.py# 会话 / 消息 DTO
│   ├── services/
│   │   └── chat.py        # stream_chat 编排 + build_messages / make_chunk / extract_usage
│   └── api/
│       ├── deps.py        # get_session_factory / get_model 依赖
│       ├── chat.py        # POST /v1/chat/completions(SSE / 非流式)
│       └── conversations.py # 会话 CRUD 路由
├── examples/
│   └── gateway_client.py  # 网关侧调用示例(新建会话 → 流式对话 → 查历史)
└── tests/                 # pytest(SQLite + 假模型,不依赖外部服务)
```

---

## 核心模块设计

### 配置与入口

- **`config.py`** — `Settings` 用 `pydantic-settings` 从 `.env` 读配置,字段与环境变量一一对应:
  `api_key_deepseek` ↔ `API_KEY_DEEPSEEK`、`model_deepseek` ↔ `MODEL_DEEPSEEK`、
  `temperature` ↔ `TEMPERATURE`、`db_url` ↔ `DB_URL`。
- **`main.py`** — 构建 FastAPI `app`,`lifespan` 里 `Base.metadata.create_all` 建表;
  `run()` 用 uvicorn 启动。`import app.models` 触发模型注册到 `Base.metadata`。

### 数据层(db / models)

- **`db/session.py`** — `create_async_engine_and_sessionmaker(db_url, **kwargs)` 抽成工厂:
  生产传 MySQL 连接池参数,测试传 SQLite(不传 `pool_size`)。`get_db` 是标准 FastAPI
  yield 依赖(自动 commit / rollback)。
- **`models/chat.py`** 两张表:
  - `ConversationModel`(表 `table_conversation`):`id`(UUID 主键)、`user_id`、`title`、
    `created_at`;与消息是一对多关系。
  - `ChatMessageModel`(表 `table_chat_message`):`session_id`(外键 → `table_conversation.id`)、
    `message_type`(human/ai/system/tool)、`content`、`tool_calls`(JSON,预留)、
    `created_at`;联合索引 `(session_id, created_at)`;删除会话级联删消息。

### 记忆层(memory)

- **`history.py`** — `MySqlChatMessageHistory` 继承 LangChain `BaseChatMessageHistory`,
  实现异步 `aget_messages` / `aadd_messages` / `aclear`;同步 `clear()` 抛 `NotImplementedError`
  (本实现纯异步)。写入用 `messages_to_dict`,读取用 `messages_from_dict`。
- **`manage.py`** — `ConversationManager` 提供 `create_session` / `list_sessions` / `delete_session`。

### 模型层(llm)

- **`deep_seek.py`** — `create_chat()` 返回 `ChatDeepSeek` 聊天模型;`create_model()` 返回带工具的
  agent(`get_weather` 示例);`load_model_ds(type)` 按 `"chat" | "agent"` 分发。

### 编排层(services)

- **`chat.py`** 是业务核心,五个函数各司其职:
  - `to_langchain_message()` — OpenAI 消息 → LangChain 消息。
  - `build_messages()` — 历史 + 新消息按序拼接。
  - `make_chunk()` — 构造 `chat.completion.chunk` 分片。
  - `extract_usage()` — 从 `usage_metadata` 提取 token 统计。
  - `stream_chat()` — 编排:加载历史 → 流式 → 落库 → 返回 usage。

### 接口层(api / schemas)

- **`schemas/`** — `ChatCompletionRequest` 用 `extra="ignore"` 容忍网关透传的 OpenAI 标准字段;
  `ConversationResponse` 等用 `from_attributes=True` 直接从 ORM 对象序列化。
- **`api/deps.py`** — `get_session_factory` / `get_model` 两个依赖,测试时通过
  `app.dependency_overrides` 覆盖。
- **`api/chat.py`** — `stream=true` 走 `StreamingResponse`(SSE),`stream=false` 收集流组装完整 `chat.completion`。
- **`api/conversations.py`** — 会话 CRUD,复用 `ConversationManager`。

---

## 快速开始

```bash
uv sync               # 安装依赖
cp env.example .env   # 配置 DeepSeek key 与 MySQL 连接
uv run dev            # 启动服务(0.0.0.0:8000)
```

环境变量(见 `env.example`):

| 变量 | 说明 |
|------|------|
| `API_KEY_DEEPSEEK` | DeepSeek API Key |
| `MODEL_DEEPSEEK` | 模型名,默认 `deepseek-chat` |
| `TEMPERATURE` | 采样温度,默认 `0.0` |
| `DB_URL` | `mysql+aiomysql://user:pass@host:3306/db` |

## API

### `GET /health`

健康检查,返回 `{"status": "ok"}`。

### `POST /v1/chat/completions`(OpenAI 兼容)

请求体(扩展了 `session_id` / `user_id` 两个字段):

```json
{
  "model": "deepseek-chat",
  "messages": [{"role": "user", "content": "你好"}],
  "stream": true,
  "session_id": "可选,带此字段则加载/保存历史",
  "user_id": "anonymous"
}
```

- `stream: true`(默认):返回 `text/event-stream`,每个分片形如
  `data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"你"}}]}`,
  末尾 `data: [DONE]`;最终分片带 `usage`(token 统计)。
- `stream: false`:返回完整 JSON `chat.completion` 对象,含 `usage`。
- 带 `session_id` 时,服务从 MySQL 加载历史、拼接新消息、流式返回,并把
  本次用户消息与助手回复写回 MySQL。

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/conversations` | 新建会话,body `{"user_id","title"}` |
| GET | `/v1/conversations?user_id=xxx` | 会话列表 |
| GET | `/v1/conversations/{session_id}/messages` | 历史消息 |
| DELETE | `/v1/conversations/{session_id}` | 删除会话(级联删消息) |

## 网关对接

完整可运行示例见 `examples/gateway_client.py`。核心流程:

1. 网关先 `POST /v1/conversations` 新建会话,拿到 `session_id`。
2. 用该 `session_id` 调 `/v1/chat/completions`(SSE 流式),逐行解析 `data:` 事件,
   累积 `delta.content` 直到收到 `data: [DONE]`。
3. 同一 `session_id` 的后续请求,服务端会自动从 MySQL 加载历史并拼接。

```python
async with client.stream("POST", f"{SERVICE_URL}/v1/chat/completions", json={
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": message}],
    "stream": True,
    "session_id": session_id,
}) as resp:
    async for line in resp.aiter_lines():
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload == "[DONE]":
            break
        delta = json.loads(payload)["choices"][0]["delta"]
        if delta.get("content"):
            print(delta["content"], end="", flush=True)
```

## 测试

```bash
uv run pytest
```

测试使用 SQLite(aiosqlite)临时库 + 假模型,不依赖真实 MySQL / DeepSeek。
