# MCP 与 Skill 接入开发文档

> 本文整理两种「给 agent 扩能力」的机制:**MCP(Model Context Protocol)** 与 **Skill**。它们层级不同 —— MCP 解决「怎么把外部系统接进来」(标准化协议),Skill 解决「怎么组织和复用能力」(指令 + 工具 + 可选子图)。
>
> 面向本仓库的 `agent-server`(FastAPI + LangChain + DeepSeek + LangGraph)与 `langchain-camp`(学习/实验)两个子项目,给出接入思路、方案与落地步骤。

---

## 一、结论先行

| | MCP | Skill |
|---|---|---|
| 解决什么 | 外部能力如何**标准化接入** | 能力如何**组织与复用** |
| 形态 | 一个协议 + 一组 server/client | 一个「描述 + 工具 + 提示词」的包 |
| 类比 | 插座的统一标准(USB-C) | 一个封装好的「工具箱」 |
| 落到你代码里 | `MultiServerMCPClient` → `get_tools()` → 塞进 `create_agent(tools=...)` | `SKILL.md`(Claude Code)或「Skill 数据类 + 子图」(自有 agent) |

**一句话**:MCP 负责「接进来」,Skill 负责「用起来」;两者常组合成「skill = 指令 + MCP 工具」。

---

## 二、MCP 接入

### 2.1 协议模型

MCP 是一套基于 **JSON-RPC** 的开放协议,核心是 Client / Server 两个角色:

- **MCP Server**:一个独立进程,对外暴露三类能力:
  - `tools` —— 可执行的动作(查数据、调 API、写文件);
  - `resources` —— 只读数据(文档、schema、配置);
  - `prompts` —— 可复用的提示词模板。
- **MCP Client**:你的 agent,连上 server 后把这些能力**当成本地工具**调用。

好处:接 GitHub、数据库、文件系统、浏览器等外部系统时,**不再各自写胶水代码**,统一走 MCP。

### 2.2 关键包:`langchain-mcp-adapters`

官方适配包 `langchain-mcp-adapters` 做了一件关键的事:**把 MCP 工具转成 LangChain 的 `BaseTool`**。于是它能直接塞进你已经会的 `create_agent(tools=...)` / `bind_tools` / `ToolNode`,和你手写的 `get_weather` 平起平坐。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async def load_mcp_tools():
    client = MultiServerMCPClient({
        # stdio:本地起一个子进程当 MCP server
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"],
            "transport": "stdio",
        },
        # 远程:连一个已经跑着的 MCP server
        "github": {
            "url": "https://api.githubcopilot.com/mcp/",
            "transport": "streamable_http",
            "headers": {"Authorization": f"Bearer {token}"},
        },
    })
    return await client.get_tools()   # 返回 LangChain BaseTool 列表


# 和本地工具合并,喂给现有 agent
tools = await load_mcp_tools()
agent = create_agent(model=llm, tools=[get_weather, *tools], ...)
```

### 2.3 transport 选型

| transport | 场景 | 说明 |
|---|---|---|
| `stdio` | 本地子进程 | 命令行启动的 MCP server,零网络开销 |
| `streamable_http` | 远程(生产推荐) | HTTP 长连接,替代旧 `sse`;`http` 是它的别名 |
| `sse` | 远程(旧) | Server-Sent Events,逐步被 streamable_http 取代 |

> `streamable_http` 支持 `headers` 传鉴权(如 `Authorization`),配置里还支持 `${ENV_VAR}` 环境变量展开,便于注入密钥。

### 2.4 接入点(对应 agent-server 分层)

```
MCP Server(独立进程:GitHub / DB / 文件系统 ...)
      ▲ MCP 协议(JSON-RPC)
      │
langchain_mcp_adapters  —— 把 MCP tool 转成 LangChain tool
      │
create_agent(tools=...)  —— services/chat.py 里已有的入口
      │
你的 FastAPI /v1/chat/completions
```

对你来说,接入 MCP 就是**在 `create_agent` 之前多一步 `load_mcp_tools()`,把返回的工具合并进 tools 列表**。后面的 `ToolNode`、流式、checkpointer 全部照旧。

### 2.5 注意点

- **`>= 0.2.0` 起,`get_tools()` 每次调用自动管理会话**,无需手动 `__aenter__/__aexit__`;客户端应在**应用启动时创建一次**(单例),不要每个请求 new 一个(增加延迟、可能耗尽 server 连接)。
- 无状态 server 用 `get_tools()`(每次新建会话);有状态、需要复用会话的 server 用旧版的 `load_mcp_tools(session)`(仅 `< 0.2.0`)。

---

## 三、Skill 接入

### 3.1 先厘清「skill」指哪个

有两层含义,都可能遇到:

**A. Claude Code 的 skill(扩展 Claude Code 本身)**

一个 skill = 一个 `name` + `description` + 指令正文(可带脚本)。Claude Code 在对话里根据 `description` 决定何时加载它。**本质是「按需注入提示词」**:

```markdown
# .claude/skills/weather/SKILL.md
---
name: weather
description: 查询城市天气。当用户问天气/气温时使用。
---

## 步骤
1. 调用工具 `get_weather` 拿数据
2. 用一句话总结天气
```

**B. 泛化到自有 agent 的「skill」**

在 LangGraph agent 里,一个 skill 最自然的落地形式是 **「描述 + 工具 + 可选子图」的复用包**。`langchain-camp` 的 `core/` 下 `stream_output` / `structure_output` / `tool_call` 已经是小能力,缺的是加一层「何时用、怎么用」的描述。

### 3.2 落地:把 skill 抽象成可复用单元

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Skill:
    name: str
    description: str        # 路由用:主 agent 靠它判断何时启用
    tools: list = field(default_factory=list)   # 这个 skill 提供的工具
    prompt: str = ""        # 使用说明(注入 system prompt)
    graph: Any = None       # 复杂 skill 可自带一个子图(subgraph)
```

复杂度递进:

| 复杂度 | 做法 |
|---|---|
| 简单 skill | 一个 `@tool` 函数 + 一句 description |
| 中等 skill | prompt(说明)+ 多个 tool + 一个 LangGraph 子图 |
| 复杂 skill | 独立 subgraph,用 `add_node("skill_x", skill_graph)` 挂进主图 |

---

## 四、两者如何配合

- **MCP 负责「接进来」**:把一个外部系统的能力标准化成 tool。
- **Skill 负责「用起来」**:决定什么时候、用什么方式、按什么流程去调这些 tool。

典型组合:**skill = 指令 + MCP 工具**。比如「查 GitHub PR」这个 skill,内部就是一段「先搜 PR、再总结改动」的指令 + 一个来自 GitHub MCP server 的工具。

```
        ┌──────────────────────────────┐
        │  Skill(指令:何时/怎么用)      │
        │   ├─ 本地 tool:get_weather    │
        │   └─ MCP tool:github_search   │ ← 来自 MCP server
        └──────────────────────────────┘
```

---

## 五、落地步骤(agent-server 版)

1. **接 MCP(最小改动)**
   `uv add langchain-mcp-adapters` → 在 `services/chat.py` 里加 `load_mcp_tools()`,启动时建单例 client,把返回的 tools 合并进 `create_agent` 的 tools。

2. **把高频能力包成 skill**
   把 `core/` 里散落的能力整理成「description + 工具 + 子图」的复用单元,由主 agent 按 description 路由加载。

3. **能力多了之后上多 agent**
   用一个「路由主 agent + 若干 skill 子 agent」的结构(LangGraph subgraph / `Send`),避免单个 agent 的 prompt 和 tool 列表爆炸。

---

## 六、参考资料

- [langchain-mcp-adapters 仓库(DeepWiki)](https://deepwiki.com/langchain-ai/langchain-mcp-adapters/5.3-langgraph-api-server-deployment)
- [LangGraph API Server Deployment 接入示例](https://deepwiki.com/langchain-ai/langchain-mcp-adapters/5.3-langgraph-api-server-deployment)
- [MCP Transport Types 说明](https://deepwiki.com/microsoft/langchain-for-beginners/7.1-mcp-transport-types)
- [Model Context Protocol 入门](https://deepwiki.com/microsoft/langchain-for-beginners/7-model-context-protocol-(mcp))
- [LangChain MCP 客户端官方文档(DeepWiki)](https://deepwiki.com/langchain-ai/langchain-mcp-adapters)
