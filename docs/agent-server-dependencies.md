# agent-server 依赖库梳理

> 说明:梳理 `agent-server/` 用到的第三方库,按**功能分类**组织,并在每个依赖上标注其
> 属于运行时(`[project].dependencies`)、测试(`[dependency-groups].dev`)还是构建(`[build-system]`)。
> 依赖声明以 `agent-server/pyproject.toml` 为准。

## 分类总览

| 功能分类 | 依赖 | 类型 | 一句话作用 |
|----------|------|------|-----------|
| **Web 框架 / 服务** | `fastapi` | 运行时 | 路由、校验、依赖注入、SSE 流式 |
| | `uvicorn[standard]` | 运行时 | ASGI 服务器 |
| **LangChain / LLM** | `langchain` | 运行时 | Agent / Tool 封装 |
| | `langchain-core` | 运行时 | 消息 / 聊天历史抽象 |
| | `langchain-deepseek` | 运行时 | DeepSeek 模型(`ChatDeepSeek`) |
| **数据库 / MySQL** | `sqlalchemy` | 运行时 | ORM、异步引擎、session 工厂 |
| | `aiomysql` | 运行时 | MySQL 异步驱动 |
| | `greenlet` | 运行时 | 异步引擎的协程底层 |
| | `aiosqlite` | 测试 | SQLite 异步驱动(测试替代 MySQL) |
| **配置与数据校验** | `pydantic` | 运行时 | DTO / 数据模型校验(`BaseModel`) |
| | `pydantic-settings` | 运行时 | 读 `.env` / 环境变量并校验 |
| | `python-dotenv` | 运行时 | 解析 `.env`(pydantic-settings 底层用) |
| **测试** | `pytest` / `pytest-asyncio` | 测试 | 测试框架 + async 用例支持 |
| | `httpx` | 测试 | ASGI 测试客户端 |
| **构建** | `uv_build` | 构建 | uv 构建后端 |

## 依赖关系图

运行时依赖之间的调用/依赖关系(箭头 = 「使用/依赖」):

```
应用层 (src/app)
 │
 ├─ HTTP ───── fastapi ─────────────► uvicorn[standard]   (ASGI 服务器)
 │
 ├─ LLM ────── langchain ───────────► langchain-core      (消息 / 历史抽象)
 │                │                        ▲
 │                └► langchain-deepseek ───┘               (ChatDeepSeek)
 │
 ├─ 数据校验 ── pydantic ◄── pydantic-settings ──► python-dotenv
 │             (schemas/*.py 的 BaseModel)      (config.py 读 .env)
 │
 └─ DB ─────── sqlalchemy ──────────► aiomysql            (生产 MySQL 驱动)
 │                │                      └► aiosqlite      (测试替代, 仅测试)
 │                └► greenlet                              (异步协程底层)
```

> 补充:`fastapi` 的请求/响应校验同样基于 `pydantic`(其上又叠了 `pydantic-settings` 做配置),
> 三者同属 pydantic 生态,`pydantic` 是共同地基。

## 架构分层 ↔ 依赖映射

项目采用分层架构(详见 `agent-server/README.md`),各依赖与分层的对应关系:

| 分层 | 关键文件 | 使用到的依赖 |
|------|----------|--------------|
| `api/`(HTTP 层) | `chat.py`、`conversations.py`、`deps.py` | `fastapi`(路由/校验/DI/SSE) |
| `services/`(编排层) | `chat.py` | `langchain-core`(消息类型)、`sqlalchemy`(session 工厂类型) |
| `memory/`(历史 + 会话 DAO) | `history.py`、`manage.py` | `langchain-core`(历史基类/消息序列化)、`sqlalchemy`(查询) |
| `llm/`(模型工厂) | `deep_seek.py` | `langchain`(Agent/Tool)、`langchain-deepseek`(`ChatDeepSeek`) |
| `schemas/`(DTO) | `chat.py`、`conversation.py` | `pydantic`(`BaseModel`) |
| `models/`(ORM) | `chat.py` | `sqlalchemy`(`Mapped`/`mapped_column`/`relationship`) |
| `db/`(引擎/session) | `session.py` | `sqlalchemy`、`aiomysql`(驱动)、`greenlet`(协程底层) |
| 配置 | `config.py` | `pydantic-settings`、`python-dotenv` |
| 入口/启动 | `main.py` | `fastapi`、`uvicorn` |

---

## 一、Web 框架 / 服务

### `fastapi`(运行时)

项目的 HTTP 层骨架,承担接口暴露、请求解析、响应组装与依赖注入:

- **路由定义**:`src/app/api/chat.py`(`/v1/chat/completions`)、`src/app/api/conversations.py`(`/v1/conversations` 系列)、`src/app/main.py`(`/health`、路由注册)。
- **参数校验与序列化**:配合 pydantic 的请求/响应模型(`src/app/schemas/*`),`response_model` 自动做 DTO 序列化与文档生成。
- **依赖注入**:`Depends(get_session_factory)` / `Depends(get_model)`(`src/app/api/deps.py`),让测试能通过 `app.dependency_overrides` 替换成 SQLite + 假模型。
- **SSE 流式响应**:`StreamingResponse(..., media_type="text/event-stream")`(`src/app/api/chat.py:50`)。
- **生命周期**:`lifespan` 里启动时 `Base.metadata.create_all` 建表(`src/app/main.py:13-18`)。

### `uvicorn[standard]`(运行时)

运行 FastAPI 应用的 ASGI 服务器。`[standard]` 额外带上 `uvloop`、`httptools`、`websockets` 等高性能组件。
入口在 `src/app/main.py:run()`:`uvicorn.run(app, host="127.0.0.1", port=8000)`,由 `uv run dev` 触发。

---

## 二、LangChain / LLM 调用

### `langchain`(运行时)

用于把模型封装成可调用工具/Agent 的能力(`src/app/llm/deep_seek.py`):

- `langchain.agents.create_agent`:基于模型 + 工具列表 + 系统提示构建一个 Agent。
- `langchain.tools.tool`:装饰器,把普通函数 `get_weather` 注册为 Agent 可调用的工具(从 docstring 提取工具描述)。

> 注意:当前主链路 `/v1/chat/completions` 走的是 `model_dict["chat"]` 即纯 `ChatDeepSeek` 对话,`create_agent`/`get_weather` 属于 `model_dict["agent"]` 的演示/实验代码。

### `langchain-core`(运行时)

LangChain 的核心基础包,项目直接 import 了两类能力:

- `langchain_core.chat_history.BaseChatMessageHistory`(`src/app/memory/history.py:9`):`MySqlChatMessageHistory` 的基类,把 MySQL 历史封装成 LangChain 标准聊天历史接口。
- `langchain_core.messages`(`src/app/memory/history.py:10`、`src/app/services/chat.py:9`):消息类型(`HumanMessage` / `AIMessage` / `SystemMessage` / `BaseMessage`)及 `messages_from_dict` / `messages_to_dict` 序列化工具。

原为 `langchain` / `langchain-deepseek` 的传递依赖,现已显式声明以锁定版本。

### `langchain-deepseek`(运行时)

LangChain 官方 DeepSeek 提供方集成,提供 `ChatDeepSeek` 模型类(`src/app/llm/deep_seek.py:8-14`),
用 `api_key` / `model` / `temperature` 实例化,支持 `astream()` 流式输出 token。

---

## 三、数据库 / MySQL

这一组是与数据持久化相关的依赖,生产连 MySQL,测试替换为 SQLite。按职责可再分三层:

| 职责 | 依赖 | 说明 |
|------|------|------|
| **ORM 层** | `sqlalchemy` | 定义表结构、异步引擎、session 工厂,屏蔽具体数据库差异 |
| **驱动层** | `aiomysql`(生产)/ `aiosqlite`(测试) | 真正连库的 DBAPI 驱动,由 URL 前缀选择 |
| **底层依赖** | `greenlet` | 让 SQLAlchemy 异步引擎能在协程里跑同步驱动 |

### `sqlalchemy`(运行时)— ORM 层

数据访问层核心,负责「对象 ↔ 表」的映射与查询:

- **声明式模型**:`DeclarativeBase` 基类(`src/app/db/session.py:12`),`Mapped` / `mapped_column` / `relationship` 定义表结构(`src/app/models/chat.py`)。
- **异步引擎与 session 工厂**:`create_async_engine` + `async_sessionmaker`(`src/app/db/session.py:16-40`),生产用 `mysql+aiomysql://`。
- **查询 DSL**:`select` / `delete` / `scalars` 等(`src/app/memory/*`、`src/app/api/conversations.py`)。

### `aiomysql`(运行时)— 生产驱动

SQLAlchemy 异步引擎连 MySQL 时所需的 DBAPI 驱动。通过 URL 前缀 `mysql+aiomysql://` 指定
(`src/app/db/session.py:33-40`)。配合 `pool_pre_ping=True`、`pool_size=10`、`max_overflow=20` 做连接池管理。

### `aiosqlite`(测试)— 测试驱动

SQLite 异步驱动,只在测试时用来**替代 MySQL**:`tests/conftest.py:16-24` 用
`sqlite+aiosqlite:///{tmp_path}/chat.db` 在临时目录建一个独立 SQLite 库,复用
`create_async_engine_and_sessionmaker` 工厂注入,跑完即 drop。生产环境不使用。

### `greenlet`(运行时)— 底层依赖

SQLAlchemy 2.0 的异步扩展以及 `aiomysql` 底层都依赖 greenlet 做同步/异步之间的协程切换。
正常属于传递依赖,单独列出是为了锁定版本(`greenlet>=3.5.5`)、避免安装解析漂移。

---

## 四、配置与数据校验(pydantic 生态)

三者同属 pydantic 生态,`pydantic` 是共同地基,`pydantic-settings` 在其上做配置读取,`python-dotenv` 负责解析 `.env` 文件。

### `pydantic`(运行时)

数据校验 / DTO 建模基础库。`src/app/schemas/chat.py` 与 `src/app/schemas/conversation.py`
用 `BaseModel` + `ConfigDict` 定义请求/响应模型,`fastapi` 据此做请求体校验与响应序列化。
原为 `fastapi` / `pydantic-settings` 的传递依赖,现已显式声明(`pydantic>=2.13.4`)以锁定版本。

### `pydantic-settings`(运行时)

`BaseSettings` + `SettingsConfigDict(env_file=".env")`(`src/app/config.py`)把 `.env` / 环境变量
映射成强类型字段(`api_key_deepseek`、`model_deepseek`、`temperature`、`db_url`),并提供默认值。

### `python-dotenv`(运行时)

负责解析 `.env` 文件内容。实际由 `pydantic-settings` 底层调用,项目中未直接 `import`,
在 `pyproject.toml` 显式声明以锁定版本。

---

## 五、测试

### `pytest` + `pytest-asyncio`(测试)

- `pytest` 组织并运行 `tests/` 下的用例。
- `pytest-asyncio` 让 pytest 支持 `async def` 测试函数。`pyproject.toml` 里 `asyncio_mode = "auto"` 使 async 用例无需手动标记。

### `httpx`(测试)

`tests/test_api.py` 用 `ASGITransport(app=app)` + `AsyncClient` 直接对 ASGI 应用发请求,
无需真正起服务进程即可端到端测接口(含 SSE 流式、会话 CRUD)。

> 测试相关的 SQLite 驱动 `aiosqlite` 见上文「三、数据库 / MySQL」分类。

---

## 六、构建

### `uv_build`(构建)

`pyproject.toml` 的 `[build-system]` 指定 `uv_build` 作为构建后端,配合
`[tool.uv.build-backend]` 的 `module-name = "app"` 声明包名与目录名不一致(包名 `langchain-ai`、目录 `app`),
详见 `docs/uv-init.md`。

---

## 注意事项

1. **`uuid` 包已移除,仍使用标准库 `uuid` 模块**:代码里 `import uuid` 生成 `session_id`
   (`src/app/memory/manage.py:18`)与 `completion_id`(`src/app/services/chat.py:85`),
   走的是 Python 标准库自带的 `uuid` 模块。`pyproject.toml` 中冗余的 PyPI `uuid>=1.30`
   (标准库旧镜像)已删除。
2. **`greenlet` / `python-dotenv` 为「显式声明但间接使用」**:二者均由其它包底层调用,
   直接参与运行却非项目直接 `import`,显式列出只为锁定版本,避免升级时行为漂移。
3. **改动后需重新生成锁文件**:`pyproject.toml` 依赖变更后,运行 `uv lock`(或 `uv sync`)同步 `uv.lock`
   (移除 `uuid`、把 `langchain-core` 与 `pydantic` 提升为直接依赖)。
