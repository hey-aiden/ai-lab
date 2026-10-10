# mcp/ 代码 review 记录

- 日期:2026-10-11
- 范围:`mcp/` 目录(初始 `package.json`、`tsconfig.json`、`src/index.ts`)
- 结论:初始代码是官方 MCP TypeScript quickstart 的 weather 示例副本,SDK 用法本身正确,但**模块体系/构建脚本/工具命名存在多处错位**,导致 `npm start` 直接跑不起来。已修复并冒烟验证通过。

---

## 一、问题清单

### 1. `package.json`

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 1.1 | `"type": "commonjs"` 与源码/依赖 ESM 冲突 | 高 | 源码用 ESM `import` 语法;`@modelcontextprotocol/server@2.3.1` 是纯 ESM 包(`"type": "module"`,主入口 `.mjs`)。`commonjs` 下 TS 会把 `import` 编译成 `require()`,虽依赖恰好提供 `.cjs` 兜底能跑,但语义错位、脆弱。 |
| 1.2 | `"start": "node ./src/index.js"` 指向不存在的文件 | 高 | 源码是 `src/index.ts`,编译产物在 `build/`,根目录无 `index.js`。直接 `npm start` 会 `MODULE_NOT_FOUND`。 |
| 1.3 | 缺 `build` 脚本 | 高 | tsconfig 配了 `outDir: ./build`,但没有任何脚本编译 TS,`start` 也不会先编译。 |
| 1.4 | `"main": "index.js"` 指向不存在的文件 | 中 | 根目录无 `index.js`。 |
| 1.5 | `"test"` 是占位且必失败 | 低 | `echo "Error: no test specified" && exit 1`,一跑就挂。 |
| 1.6 | 元数据空/占位 | 低 | `description: ""`、无 `author`、`name: "mcp"`(太泛且与 npm 已有包冲突)、`license: "ISC"`。 |
| 1.7 | 缺 `bin` | 中 | 无 `bin` 字段,MCP 客户端(如 Claude Desktop)无法以命令方式启动 stdio server。 |

### 2. `tsconfig.json`

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 2.1 | `module`/`moduleResolution: Node16` 与 `type: commonjs` 组合错位 | 高 | Node16 下模块格式由 package.json 的 `type` 决定;`commonjs` 会把 `.ts` 当 CJS,与 ESM 源码意图相反。 |
| 2.2 | 未排除 `build/` | 低 | `include` 只含 `src/**/*` 其实不会误编译,但明确 `exclude` 更清晰。 |

### 3. `src/index.ts`

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 3.1 | 工具名 `get-alters` 拼写错误 | 高 | `description` 写 "weather alerts"、变量名 `alerts`,工具名却是 `get-alters`(alter=更改 / alert=警报)。客户端调 `get-alerts` 会找不到工具。 |
| 3.2 | mock 数据与 schema 脱节 | 低 | schema 声明 `state` 为 2 字母州码,但 handler 未用入参做任何查询,只回写死数组;作为 demo 可接受,但应明确标注是 stub。 |
| 3.3 | `console.error` 写日志(非 bug,说明) | — | stdio MCP 的 **stdout 保留给 JSON-RPC 协议帧**,日志必须走 stderr。原代码这一点其实正确,予以保留。 |

### 4. 结构/仓库层面

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 4.1 | 缺 `.gitignore` | 中 | `node_modules/`、`build/` 会进入版本控制(整个 `mcp/` 目录当前还是 untracked)。 |
| 4.2 | 缺 README | 低 | 无 build/start、MCP 客户端配置说明。 |

---

## 二、已应用的修复

- **`package.json`**
  - `"type": "commonjs"` → `"module"`。
  - `"start": "node ./build/index.js"`(先 build 再跑)。
  - 新增 `"build": "tsc"`、`"typecheck": "tsc --noEmit"`;移除必失败的 `"test"` 占位。
  - `"main"` → `./build/index.js`;新增 `"bin": { "mcp-weather": "./build/index.js" }`。
  - `name` → `mcp-weather`;补 `description`;`license` → `MIT`。
- **`tsconfig.json`**:`module` / `moduleResolution` → `NodeNext`(与 `type: module` 对齐);`exclude` 增加 `build`。
- **`src/index.ts`**:工具名 `get-alters` → `get-alerts`;mock 返回内容引用入参 `state`,并加注释明确是 demo stub;源码首行加 `#!/usr/bin/env node` shebang(供 `bin` 使用,tsc 会保留)。
- **新增 `.gitignore`**:`node_modules/`、`build/`、`.env`。
- **`package-lock.json`**:`npm install --package-lock-only` 同步根条目 `name`/`license`。

---

## 三、验证结果

| 项 | 结果 |
|----|------|
| `npm run build` | exit 0,产出 `build/index.js`(保留 shebang,ESM 输出) |
| `npm run typecheck` | 通过 |
| stdio 冒烟测试 | `initialize` → 正确返回协议版本/能力;`tools/list` → 返回 `get-alerts` 及正确 JSON Schema;`tools/call`(`state: CA`)→ 返回告警内容 |
| 日志流向 | 启动日志走 stderr,stdout 仅协议帧,exit 0 |

冒烟测试样例(已手动验证):

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get-alerts","arguments":{"state":"CA"}}}
```

---

## 四、遗留 / 可选后续

1. 仍是 demo stub:`get-alerts` 返回写死数据;若要真实能力需接数据源,或对接 `agent-server` 的 DeepSeek 聊天(需另行确认需求)。

以下三项已于同日补齐:

2. ~~无自动化测试~~ → 已引入 vitest,`src/index.test.ts` 覆盖 initialize / tools/list / tools/call 三条用例(`npm test` 通过)。为可测试性,`src/index.ts` 重构出 `createServer()` 工厂,并用 `process.argv[1] === fileURLToPath(import.meta.url)` 守卫 `main()`(仅直接运行时才启动 stdio)。
3. ~~`build/index.js` 无执行权限~~ → 已加 `postbuild: chmod +x build/index.js`,直接 `./build/index.js` 可运行(依赖 shebang)。
4. ~~缺 README~~ → 已补 `README.md`(build/start/test 命令 + Claude Desktop 配置示例)。
