# MCP 开发常用字段与配置方式

配套 `mcp/src/index.ts` 的逐字段注释,本文是字段级参考。面向 `@modelcontextprotocol/server` v2(TypeScript SDK)。接入/发布流程见 [`mcp-integration.md`](./mcp-integration.md)。

## 1. 三大能力

MCP server 向客户端暴露三种能力,分别用 `McpServer` 的三个注册方法声明:

| 能力 | 注册方法 | 语义 | 客户端对应请求 |
|------|---------|------|--------------|
| 工具 Tools | `registerTool` | 「执行动作」:带入参、有返回值、可触发副作用 | `tools/list`、`tools/call` |
| 资源 Resources | `registerResource` / `registerResourceTemplate` | 「读取数据」:配置、文档、文件等 | `resources/list`、`resources/read` |
| 提示 Prompts | `registerPrompt` | 「复用提示模板」:可带参数,填充成一段 message | `prompts/list`、`prompts/get` |

## 2. 创建服务器

```ts
new McpServer(serverInfo, options?)
```

### serverInfo(必填 name / version,可选 title)

| 字段 | 必填 | 含义 |
|------|------|------|
| `name` | ✅ | 服务器唯一标识,出现在 `initialize` 响应的 `serverInfo.name` |
| `version` | ✅ | 语义化版本号(`serverInfo.version`) |
| `title` | ❌ | 人类可读标题 |

### options(McpServerOptions,可选)

| 字段 | 含义 |
|------|------|
| `instructions` | 给客户端/模型的整体使用说明,随 `initialize` 返回 |
| `capabilities` | 显式声明能力 `{ tools? / resources? / prompts? / logging? ... }`;高层 `McpServer` 会按注册情况**自动补全**,通常无需手动声明 |
| `maxToolInputElements` | 限制单次 `tools/call` 入参的元素个数,防超大入参 |

### 如何查看 serverInfo

`serverInfo` 不是客户端配置出来的,而是 server 在 `initialize` 握手时上报的——`name` / `version` / `title` 来自 `new McpServer({...})`。查看方式:

1. **直接探 stdio**(最完整,能看到原始字段):

```bash
cd mcp
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0.0.0"}}}' \
  | node build/index.js 2>/dev/null
```

返回节选:

```json
{ "serverInfo": { "name": "weather", "version": "1.0.0", "title": "Weather MCP Server" }, "capabilities": { ... }, "instructions": "..." }
```

2. **`claude mcp get weather`**:查看连接状态、健康检查、工具数(通常含上报的 `name` / `version`)。
3. **`/mcp`**:显示状态图标 + 工具数(这里显示的 `weather` 是配置里的 key,不一定是 server 上报的 `name`)。

> 原理:stdio 下 server 从 stdin 读 JSON-RPC 消息、把响应写到 stdout。上面命令就是手动往 stdin 喂一行 `initialize` 请求,再看 stdout 的响应。

## 3. registerTool(name, config, handler)

### config 字段

| 字段 | 必填 | 含义 |
|------|------|------|
| `name`(第一参数) | ✅ | 工具唯一名,客户端按它调用 |
| `title` | ❌ | 人类可读标题 |
| `description` | 建议 | 给模型看的用途说明,模型据此判断何时调用、如何入参 |
| `inputSchema` | 建议 | 入参 zod schema → 转成 JSON Schema 在 `tools/list` 暴露,并在调用前校验 |
| `outputSchema` | ❌ | 输出 zod schema,声明后可在返回里用 `structuredContent` |
| `annotations` | ❌ | 语义标注,见下表 |
| `icons` | ❌ | 图标 |
| `_meta` | ❌ | 自定义元数据 |

### annotations(ToolAnnotations)

| 字段 | 含义 |
|------|------|
| `readOnlyHint` | `true`=只读无副作用,模型可放心多次调用 |
| `idempotentHint` | `true`=幂等,可安全重试 |
| `destructiveHint` | `true`=有破坏性(如删除),客户端可能需二次确认 |
| `openWorldHint` | `true`=可能涉及模型训练数据之外的外部世界信息 |

### handler 返回值

```ts
{
  content: ContentBlock[],      // 必填,返回给模型的内容块
  structuredContent?: object,   // 可选,结构化输出(需配 outputSchema)
  isError?: boolean,            // true 时客户端把本次调用当失败处理
}
```

`content` 内容块 `type` 可选:

| type | 形态 |
|------|------|
| `text` | `{ type: 'text', text }` |
| `image` | `{ type: 'image', data, mimeType }`(base64) |
| `audio` | `{ type: 'audio', data, mimeType }`(base64) |
| `resource` | `{ type: 'resource', resource: { uri, ... } }` |

## 4. registerResource / registerResourceTemplate

```ts
server.registerResource(name, uriOrTemplate, config, readCallback)
```

| 参数 | 含义 |
|------|------|
| `name` | 资源唯一名 |
| `uriOrTemplate` | 静态资源用固定 URI(如 `weather://config`);动态资源用 `ResourceTemplate`(带 `{param}` 占位) |
| `config` | `ResourceMetadata`:`title` / `description` / `mimeType` / `size` 等 |
| `readCallback` | 返回 `{ contents: [{ uri, mimeType?, text? \| blob? }] }` |

> 区别:静态资源 `registerResource(name, '固定URI', ...)`;动态(带参数)资源用 `new ResourceTemplate('weather://{city}', { list })` + `registerResource(name, template, ...)`。

## 5. registerPrompt(name, config, handler)

| 参数 | 含义 |
|------|------|
| `name` | 提示唯一名 |
| `config.title` | 人类可读标题 |
| `config.description` | 说明 |
| `config.argsSchema` | 可选参数(zod),客户端 `prompts/get` 时用实参填充 |

handler 返回:

```ts
{
  messages: [{ role: 'user' | 'assistant', content: { type: 'text', text } }]
}
```

## 6. 传输方式

| 方式 | 适用场景 | SDK 入口 |
|------|---------|---------|
| stdio | 本地进程(Claude Code / Desktop 拉起) | `@modelcontextprotocol/server/stdio` 的 `StdioServerTransport`(当前 demo) |
| SSE / Streamable HTTP | 远程部署、多客户端 | `WebStandardStreamableHTTPServerTransport` / `PerRequestHTTPServerTransport` 等,需自建 HTTP server |

> stdio 模式下 **stdout 保留给 JSON-RPC 协议帧**,所有日志必须走 `stderr`。

## 7. 常用配置方式速查

| 场景 | 方式 |
|------|------|
| 本地开发接入 | `.mcp.json` 项目级配置,或 `claude mcp add`(见 [`mcp-integration.md`](./mcp-integration.md)) |
| 传环境变量 | `claude mcp add -e KEY=value ...`,或 `.mcp.json` 的 `env` 字段 |
| 发布后用 | `npx -y <包名>` 作为启动命令,消费者免编译 |
| 服务内读配置 | 用 `process.env` 读环境变量(建议 `zod` 校验后使用) |

完整接入与发布步骤见 [`mcp-integration.md`](./mcp-integration.md)。

## 8. MCP 常用场景

MCP 的核心价值:让 AI 助手通过统一协议调用外部能力,把「模型」和「工具/数据」解耦。常见落地场景:

| 场景 | 说明 | 典型能力 |
|------|------|---------|
| 接入内部数据/服务 | 让 AI 查数据库、查内部 API、读内部文档 | 工具 + 资源 |
| 代码仓库与协作 | 查 PR、issue、CI 状态,创建 issue / 评论 | 工具 |
| 浏览器自动化 | 控制浏览器抓取/操作网页(Playwright / Puppeteer 等) | 工具 |
| 企业知识库 / RAG | 检索内部知识,回答问题 | 资源 + 工具 |
| 本地系统操作 | 文件读写、shell 命令、进程管理 | 工具 |
| 与现有后端桥接 | 把已有服务(如本项目 `agent-server` 的 DeepSeek 聊天)包装成工具 | 工具 |
| 提示模板复用 | 团队共享标准提示词 / 报告模板 | 提示 |

选择能力的一般原则:

- 要 AI **做一件事**(有副作用/有返回值)→ **工具 Tools**
- 要 AI **读一份数据**(配置/文档/文件)→ **资源 Resources**
- 要复用一段**标准提示词/模板** → **提示 Prompts**

同一个 server 可以同时提供三类能力(如本项目同时暴露工具、资源、提示)。
