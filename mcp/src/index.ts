#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/server'
import { StdioServerTransport } from '@modelcontextprotocol/server/stdio'
import * as z from 'zod/v4'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

export function createServer(): McpServer {
    // ── 1. 创建服务器 ─────────────────────────────────────────────
    // new McpServer(serverInfo, options?)
    //
    // serverInfo(Implementation,必填 name / version,可选 title):
    //   - name:    服务器唯一标识,会出现在 initialize 响应的 serverInfo.name
    //   - version: 语义化版本号(serverInfo.version)
    //   - title:   可选,人类可读标题
    //
    // options(McpServerOptions,可选)常用:
    //   - instructions: 给客户端看的整体使用说明(随 initialize 返回,模型可参考)
    //   - capabilities: 显式声明能力 { tools? / resources? / prompts? / logging? ... }
    //                   注意:用高层 McpServer 时,registerTool/registerResource/registerPrompt
    //                   会自动补全对应 capability,通常无需手动声明
    //   - maxToolInputElements: 限制单次 tools/call 入参的元素个数(防超大入参)
    const server = new McpServer(
        {
            name: 'weather',
            version: '1.0.0',
            title: 'Weather MCP Server',
        },
        {
            instructions: '天气示例服务器:工具 get-alerts / calculate-bmi,资源 weather://config,提示 weather-report。',
        }
    )

    // ── 2. 注册工具 registerTool(name, config, handler) ────────────
    //   - name:                 工具唯一名(必填),客户端按这个名字调用
    //   - config.title:         人类可读标题(可选)
    //   - config.description:   给模型看的用途说明 —— 模型据此判断何时调用、如何入参,尽量写清
    //   - config.inputSchema:   入参的 zod schema,SDK 会转成 JSON Schema 在 tools/list 里暴露,
    //                           并在调用前做参数校验(不合法会直接报错,不进 handler)
    //   - config.outputSchema:  结构化的输出 schema(可选),声明后可在返回里用 structuredContent
    //   - config.annotations:   语义标注(可选),见下方 ToolAnnotations 各字段含义
    //
    // 触发方式(所有工具通用):
    //   1) 客户端启动时经 tools/list 拿到本工具的 name/description/inputSchema;
    //   2) 模型根据 description 判断当前任务是否需要它,需要时发起 tools/call,
    //      入参必须满足 inputSchema,否则 SDK 在进入 handler 前就报错;
    //   3) handler 返回 content(供模型阅读),可附 structuredContent / isError。
    //
    // 作用: 查询美国某州的天气预警(示例固定返回一条 Heat Advisory)。
    // 触发: 用户问「某州天气/预警」时,模型传 state(2 位州代码,如 CA/NY)。
    server.registerTool(
        'get-alerts',
        {
            title: 'Get Weather Alerts',
            description: 'Get weather alerts for a US state.',
            // zod 会生成 JSON Schema:length(2) → minLength/maxLength=2,
            // describe(...) → 字段的 description(模型读它来理解该入参含义)
            inputSchema: z.object({
                state: z.string().length(2).describe('Two-letter state code (e.g. CA, NY)'),
            }),
            // ToolAnnotations 各字段含义:
            //   - readOnlyHint:      true=只读,无副作用(模型可放心多次调用)
            //   - idempotentHint:    true=幂等,可安全重试
            //   - destructiveHint:   true=有破坏性(如删除数据),客户端可能需二次确认
            //   - openWorldHint:     true=可能涉及模型训练数据之外的外部世界信息
            annotations: {
                readOnlyHint: true,
                idempotentHint: true,
                destructiveHint: false,
                openWorldHint: true,
            },
        },
        async ({ state }) => {
            // handler 第一个参数是校验后的入参(按 inputSchema 解构)
            const alerts = [
                {
                    event: 'Heat Advisory',
                    area: state,
                    severity: 'Moderate',
                    description: `A heat advisory is in effect for ${state}.`,
                },
            ]

            return {
                // content: 返回给模型的内容块数组。type 可选:
                //   - { type: 'text',  text }                     纯文本
                //   - { type: 'image', data, mimeType }           图片(base64)
                //   - { type: 'audio', data, mimeType }           音频(base64)
                //   - { type: 'resource', resource: { uri, ... } } 引用资源
                content: [
                    {
                        type: 'text' as const,
                        text: JSON.stringify(alerts, null, 2),
                    },
                ],
                // isError: 设为 true 时,客户端会把本次调用当作失败处理(默认 false 可省略)
            }
        }
    )

    // ── 3. 带结构化输出的工具示例 ─────────────────────────────────
    // 声明 outputSchema 后,可在返回值里带 structuredContent(结构化对象),
    // 便于客户端/上层代码直接取字段,而不必解析 content 里的文本。
    //
    // 作用: 按体重(kg)与身高(m)计算 BMI,返回数值 + 分类(偏低/正常/超重)。
    // 触发: 用户给出体重、身高时,模型传 weightKg / heightM(均需正数,
    //       否则 inputSchema 校验失败,不会进入 handler)。
    server.registerTool(
        'calculate-bmi',
        {
            description: 'Calculate Body Mass Index from weight and height.',
            inputSchema: z.object({
                weightKg: z.number().positive().describe('Weight in kilograms'),
                heightM: z.number().positive().describe('Height in meters'),
            }),
            outputSchema: z.object({
                bmi: z.number(),
                category: z.string(),
            }),
        },
        async ({ weightKg, heightM }) => {
            const bmi = weightKg / (heightM * heightM)
            const category = bmi < 18.5 ? 'underweight' : bmi < 25 ? 'normal' : 'overweight'

            return {
                content: [{ type: 'text' as const, text: `BMI = ${bmi.toFixed(1)} (${category})` }],
                structuredContent: { bmi: Number(bmi.toFixed(1)), category },
            }
        }
    )

    // ── 4. 注册资源 registerResource ───────────────────────────────
    // 资源 = 服务器暴露给客户端「读取」的数据(配置、文档、文件等),区别于「工具」(执行动作)。
    //   - name:          资源唯一名
    //   - uriOrTemplate: 资源的 URI;客户端按 URI 读取(readResource)
    //   - config:        ResourceMetadata:title / description / mimeType(内容类型)
    //   - readCallback:  返回 { contents: [{ uri, mimeType?, text? | blob? }] }
    server.registerResource(
        'config',
        'weather://config',
        {
            title: 'Weather Config',
            description: 'Server configuration',
            mimeType: 'application/json',
        },
        async (uri) => ({
            contents: [
                {
                    uri: uri.href,
                    mimeType: 'application/json',
                    text: JSON.stringify({ units: 'metric', refreshIntervalSec: 300 }),
                },
            ],
        })
    )

    // ── 5. 注册提示 registerPrompt ─────────────────────────────────
    // 提示 = 服务器提供的「可复用的提示模板」,带参数时用 argsSchema 声明,
    // 客户端 getPrompt 时用实参填充,返回一串 message(供用户/模型接着对话)。
    //   - name:        提示唯一名
    //   - config:      title / description / argsSchema(可选参数)
    //   - callback:    返回 { messages: [{ role: 'user' | 'assistant', content: { type, text } }] }
    server.registerPrompt(
        'weather-report',
        {
            title: 'Weather Report',
            description: 'Generate a weather report prompt for a state.',
            argsSchema: z.object({
                state: z.string().length(2).describe('Two-letter state code'),
            }),
        },
        ({ state }) => ({
            messages: [
                {
                    role: 'user' as const,
                    content: {
                        type: 'text' as const,
                        text: `请生成 ${state} 的天气报告。`,
                    },
                },
            ],
        })
    )

    return server
}

async function main() {
    const transport = new StdioServerTransport()
    await createServer().connect(transport)

    // stderr is safe to log to: stdio MCP reserves stdout for protocol messages.
    console.error('Weather MCP server is running on stdio...')
}

// Only start the stdio server when run directly, not when imported by tests.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
    main().catch((err) => {
        console.error('Server startup failed:', err)
        process.exit(1)
    })
}
