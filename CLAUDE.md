# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库概览

`ai-lab` 是一个 monorepo,包含两个相互独立的子项目,各自有独立的依赖与锁文件,没有共享的 workspace 或根 package 配置:

- **`dongtu/`** — 多模态 AI 聊天前端(React 19 + Create React App,react-router-dom v6)。
- **`langchain-ai/`** — AI 对话后端(FastAPI + LangChain + DeepSeek + MySQL),提供 OpenAI 兼容的 `/v1/chat/completions` SSE 流式接口。

两者目前尚未打通:`dongtu` 是纯前端(mock 数据 + 占位回复),后续再接入 `langchain-ai` 的真实接口。

## 文档规范

- 所有文档类内容(说明、调研、配置差异对比、整理笔记等)统一放到仓库根目录 `docs/` 下,按主题命名(如 `docs/uv-init.md`)。
- 不在各子项目目录内散落文档;各子项目的 `README.md` 只保留该子项目自身的简介与入口说明。

## 常用命令

### `dongtu/`(前端)

包管理器是 **pnpm**(仓库里同时存在 `package-lock.json` 与 `pnpm-lock.yaml`,以 pnpm 为准)。

```bash
cd dongtu
pnpm install            # 安装依赖
pnpm start              # 开发服务器 http://localhost:3000
pnpm build              # 生产构建到 build/
CI=true pnpm test       # 跑测试(CI=true 使其单次运行,非 watch 模式)
CI=true pnpm test App.test.js   # 只跑单个测试文件
```

### `langchain-ai/`(后端)

包管理器是 **uv**,Python 3.11(`.python-version` 固定)。

```bash
cd langchain-ai
uv sync                 # 安装依赖
cp env.example .env     # 配置 API_KEY_DEEPSEEK / DB_URL 等(含密钥,已 gitignore)
uv run dev              # 启动服务 127.0.0.1:8000(等价 make run)
uv run pytest           # 跑测试(等价 make test;用 SQLite + 假模型,不依赖外部服务)
```

## 架构

### `dongtu/` — 前端

- 路由(react-router-dom v6):`/` 与 `/chat` 重定向到 `/chat/text`,`/chat/:modalityId` 渲染 `ChatPage`;`src/index.js` 用 `<BrowserRouter>` 包裹 `<App />`。
- **模态(tab)与 URL 绑定**,会话选中态放在组件内部 state(不在 URL)。
- 关键文件:
  - `src/pages/ChatPage.jsx` — 主布局 + 状态:按模态分桶的会话/消息、每个模态各自记住选中会话、发送逻辑。
  - `src/components/` — `ModalityTabs` / `ConversationSidebar` / `MessageList` / `MessageInput`。
  - `src/data/modalities.js` — 模态定义(text 文本对话 / image 文生图 / audio 语音)、mock 会话、`PLACEHOLDER_REPLY` 占位回复。
- 后续接入真实模型时,替换 `src/data/modalities.js` 里的 mock 数据与占位回复;每个模态的 AI 能力按模块独立迭代。

### `langchain-ai/` — 后端

分层架构,每层只依赖下一层:

```
api/(HTTP 层) → services/(编排) → memory/ llm/ schemas/ → models/(ORM) → db/(引擎) → MySQL
```

- `api/` 只做请求解析、参数校验、组装响应/SSE,不含业务逻辑;`services/chat.py` 的 `stream_chat()` 是唯一理解完整业务流程的编排点。
- 数据流:带 `session_id` 时,服务从 MySQL 加载历史,拼接新消息,`model.astream()` 逐 token 产出 SSE 分片,流结束后把用户消息 + 助手回复写回 MySQL。
- 依赖注入 `get_session_factory` / `get_model`(见 `api/deps.py`),测试通过 `app.dependency_overrides` 覆盖为 SQLite + 假模型。
- 配置:`src/app/config.py` 用 pydantic-settings 读 `.env`,字段与环境变量一一对应(`api_key_deepseek` ↔ `API_KEY_DEEPSEEK` 等)。
- ORM 表:`ConversationModel`(`table_conversation`)、`ChatMessageModel`(`table_chat_message`),删除会话级联删消息。

更详细的架构、API 与网关对接说明见 `langchain-ai/README.md`。
