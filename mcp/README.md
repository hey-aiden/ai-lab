# mcp-weather

一个最小可用的 Model Context Protocol (MCP) server 示例,暴露一个 `get-alerts` 工具(返回写死的天气告警 demo 数据)。用于学习 MCP server 的搭建、测试与客户端接入方式。

## 前置

- Node.js >= 20(已验证 Node 24)
- npm

## 常用命令

```bash
npm install        # 安装依赖
npm run build      # 编译 TS 到 build/,并给 build/index.js 加可执行位
npm run typecheck  # 仅类型检查,不产出
npm test           # 跑单测(vitest)
npm start          # 以 stdio 方式启动 server(需先 build)
```

## 作为 MCP 客户端配置

以 Claude Desktop 为例(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "weather": {
      "command": "node",
      "args": ["/绝对路径/mcp/build/index.js"]
    }
  }
}
```

也可以把 `bin` 链接成命令后直接启动:

```bash
npm link
mcp-weather          # 等价于 node build/index.js
```

## 目录结构

```
mcp/
├── src/
│   ├── index.ts       # server 入口 + createServer() 工厂(供测试复用)
│   └── index.test.ts  # vitest 单测(InMemoryTransport)
├── build/             # tsc 产物(gitignored)
├── records/           # 代码 review 记录
├── README.md
└── tsconfig.json
```

## 说明

- `get-alerts` 目前是 demo stub,返回写死数据;真实能力待接入。
- stdio 模式下 stdout 保留给 JSON-RPC 协议帧,日志请走 stderr。
