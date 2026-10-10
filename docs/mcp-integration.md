# mcp 服务接入文档

适用于 `ai-lab/mcp` 子项目:一个最小可用的 Model Context Protocol (MCP) server,通过 stdio 暴露一个 `get-alerts` 工具(当前返回写死的天气告警 demo 数据)。

## 1. 概览

| 项 | 值 |
|----|----|
| 位置 | `mcp/` |
| 技术栈 | TypeScript + `@modelcontextprotocol/server` v2 + zod |
| 传输方式 | stdio(标准输入/输出上的 JSON-RPC) |
| 工具 | `get-alerts`(入参 `state`:两字母州码,如 `CA`) |
| 编译产物 | `mcp/build/index.js`(带 shebang + 可执行位) |

## 2. 前置条件

- Node.js >= 20(已验证 Node 24)
- 首次接入,或修改过 `mcp/src/index.ts` 之后,需重新编译:

```bash
cd mcp
npm install
npm run build
```

> 客户端加载的是编译产物 `build/index.js`,改完源码记得重新 `npm run build`。

## 3. 接入方式

下面三种方式任选其一。命令/配置里的路径请替换为你本机的绝对路径(下面用本机路径 `/Users/aiden/Documents/code/ai-lab/mcp/build/index.js` 示例)。

### 3.1 Claude Code —— 项目级 `.mcp.json`(推荐,可提交共享)

在仓库根目录 `/Users/aiden/Documents/code/ai-lab/.mcp.json` 新建(或合并到已有):

```json
{
  "mcpServers": {
    "weather": {
      "command": "node",
      "args": ["/Users/aiden/Documents/code/ai-lab/mcp/build/index.js"]
    }
  }
}
```

重启 Claude Code 后,该 server 会以 **⏸ Pending approval** 状态出现,需在 `/mcp` 里批准一次才真正连接。

### 3.2 Claude Code —— CLI 命令

```bash
# 项目级(写入仓库,团队共享)
claude mcp add --scope project weather -- node /Users/aiden/Documents/code/ai-lab/mcp/build/index.js

# 仅当前用户(local,不提交)
claude mcp add weather -- node /Users/aiden/Documents/code/ai-lab/mcp/build/index.js
```

- `weather` 是 server 名,可自定义;`--` 之后是启动命令 + 参数。
- 默认 transport 即 stdio,无需显式指定。
- 因为 `build/index.js` 已带 shebang + 可执行位,也可省略 `node` 直接给路径,但显式写 `node` 更稳。

### 3.3 Claude Desktop

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "weather": {
      "command": "node",
      "args": ["/Users/aiden/Documents/code/ai-lab/mcp/build/index.js"]
    }
  }
}
```

改完重启 Claude Desktop。

### 3.4 mcpServers 配置字段详解

`.mcp.json`(及 Claude Desktop 的 `claude_desktop_config.json`)里,每个 server 的字段按传输类型分两类。

**stdio(本地进程)字段:**

| 字段 | 必填 | 含义 |
|------|------|------|
| `type` | ❌ | `"stdio"`;省略即按 stdio 处理 |
| `command` | ✅ | 启动命令:`node` / `npx` / 可执行文件路径 |
| `args` | ❌ | 命令参数数组 |
| `env` | ❌ | 传给进程的环境变量 map |
| `timeout` | ❌ | 单次调用超时(ms) |

**远程(HTTP / SSE / WebSocket)字段:**

| 字段 | 必填 | 含义 |
|------|------|------|
| `type` | ✅(有 `url` 时必须) | `"http"` / `"sse"` / `"ws"`(别名 `"streamable-http"` = `"http"`) |
| `url` | ✅ | 服务地址 |
| `headers` | ❌ | 请求头,如 `{ "Authorization": "Bearer ..." }` |

> 注意:`type` 的值是 `"http"`,**不是** `"streamableHttp"`(驼峰写法无效);有 `url` 却没写 `type` 会被当作 stdio 而跳过并报错。

**配置作用域 scope:**

| scope | 生效范围 | 是否共享给团队 | 存储位置 |
|-------|---------|--------------|---------|
| `local`(默认) | 仅当前项目 | 否 | `~/.claude.json` |
| `project` | 仅当前项目 | 是(随 VCS) | 项目根 `.mcp.json` |
| `user` | 你的所有项目 | 否 | `~/.claude.json` |

优先级:local → project → user → plugin → claude.ai connectors。

## 4. 验证与使用

### 4.1 触发方式:直接用自然语言

连接后**不需要任何特殊语法**,像平时一样说就行,模型会自动判断并调用 MCP 工具。例如:

- 「用 get-alerts 查一下 CA 的天气告警」→ 模型调用 `get-alerts(state="CA")`
- 「看看服务器暴露了哪些资源」→ 模型调用 `resources/list`
- 「给我一份 NY 的天气报告模板」→ 模型调用 `prompts/get`

工具对模型可见后,会像内置工具一样被自动调度。

> 进阶:在权限规则 / `allowed-tools` / 子代理 `tools` 配置里引用某个工具时,用命名约定 `mcp__<server名>__<工具名>`,例如 `mcp__weather__get-alerts`(日常使用无需关心)。

### 4.2 查看与管理:`/mcp` 与 `claude mcp` 命令

- **`/mcp`**:在 Claude Code 里查看各 server 状态并管理。常见状态:
  - `✔ Connected` 已连接
  - `⏸ Pending approval` 待批准(项目级 `.mcp.json` 首次会这样,需批准一次)
  - `✘ Failed to connect` 连接失败
  - `! Needs authentication` 需要登录(OAuth)
  - `⊘ Disabled for this project` 已禁用
  - 菜单可 Disable / Reconnect / 重新认证;`/mcp reconnect all` 重试所有失败项。

- **CLI 命令**:

```bash
claude mcp list                  # 列出所有配置的 server 及其状态
claude mcp get weather           # 查看某个 server 详情 / 健康检查
claude mcp remove weather        # 移除
claude mcp login weather         # OAuth 登录(HTTP/SSE 需要时)
claude mcp logout weather
claude mcp add-from-claude-desktop  # 从 Claude Desktop 导入
```

### 4.3 验证连接

`claude mcp get weather` 会做健康检查并返回连接状态与工具数量;`/mcp` 面板同样显示每个 server 的工具数(若声明了工具却一个都没暴露,面板会提示)。

## 5. 注意事项

- **stdout 保留给协议帧**:server 的所有日志应写 stderr(当前实现已如此),不要把日志打到 stdout,否则会破坏 JSON-RPC 通信。
- **改动需重编译**:接入的是 `build/index.js` 编译产物,改 `src/index.ts` 后要重新 `npm run build`,必要时在客户端重连。
- **路径用绝对路径**:客户端配置中的 `command`/`args` 建议用绝对路径,避免工作目录不同导致的找不到文件。
- **`.mcp.json` 需审批**:项目级配置首次会处于 pending 状态,需人工批准(安全机制)。
- **当前是 demo stub**:`get-alerts` 返回写死数据;若后续对接 `agent-server` 的 DeepSeek 聊天能力,接入方式(命令+路径)不变,只改 `src/index.ts` 里的实现。

## 6. 发布与安装(可选)

前面第 3 节的接入方式都依赖本机的 `build/index.js`(需 clone + 编译)。如果想让别人、或别的机器**不 clone、不编译**就能用,可以发布到 npm,用 `npx` 一键拉起。

### 6.1 发布前准备(已配好)

`mcp/package.json` 已包含发布所需的两项关键配置:

- **`"files": ["build"]`** —— 因为 `build/` 在 `.gitignore` 里,而 npm 发布时默认**不打包被 gitignore 的文件**。不显式声明的话,发出去的包会缺 `build/index.js`(而 `bin` 又指向它),装完即坏。
- **`"prepublishOnly": "npm run build"`** —— 每次 `npm publish` 前自动重新编译,保证产物是最新代码。

> 想确认打包内容,用 `npm pack --dry-run`(只预览不真正发布),应看到 tarball 含 `build/index.js`、`README.md`、`package.json`,且不含 `node_modules`/`src`。

### 6.2 发布流程

```bash
cd mcp
npm login           # 首次:登录 npm 账号
npm version patch   # 升版本(顺带打 git tag);也可 minor / major
npm publish         # 发布到公共 npm(会自动跑 prepublishOnly 重新 build)
```

### 6.3 发布后的接入(消费者视角)

别人不再需要 build,直接用 `npx` 拉起:

- Claude Code(`.mcp.json`):

```json
{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": ["-y", "mcp-weather"]
    }
  }
}
```

- Claude Code CLI:

```bash
claude mcp add weather -- npx -y mcp-weather
```

- Claude Desktop:`command` 填 `npx`,`args` 填 `["-y", "mcp-weather"]`。

`npx -y` 会从 registry 下载 `mcp-weather` 并执行其 `bin` 入口,消费者无需任何本地构建。

### 6.4 私有 registry(可选)

若发布到私有源(公司 npm / verdaccio / GitHub Packages 等):

- **发布方**:`package.json` 加 `"publishConfig": { "registry": "https://你的源" }`,或在命令里指定 `npm publish --registry=https://你的源`。
- **消费方**:让 `npx` 也能访问该源——在项目(或用户)`.npmrc` 里配 `registry=https://你的源`,否则 `npx mcp-weather` 会去公共 npm 找而找不到。
