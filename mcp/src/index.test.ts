import { describe, it, expect } from 'vitest'
import { InMemoryTransport } from '@modelcontextprotocol/server'
import { createServer } from './index.js'

type RpcMessage = Record<string, any>

interface TestClient {
    send: (msg: RpcMessage) => Promise<void>
    received: RpcMessage[]
}

function createTestClient(): TestClient {
    const server = createServer()
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair()

    const received: RpcMessage[] = []
    clientTransport.onmessage = (msg) => {
        received.push(msg as unknown as RpcMessage)
    }

    // Fire-and-forget: the in-memory transport has no open handles, so no close is needed.
    void server.connect(serverTransport)

    return {
        send: (msg) => clientTransport.send(msg as never),
        received,
    }
}

async function waitFor(received: RpcMessage[], id: number): Promise<RpcMessage> {
    for (let i = 0; i < 200; i++) {
        const found = received.find((m) => m.id === id)
        if (found) return found
        await new Promise((resolve) => setTimeout(resolve, 0))
    }
    throw new Error(`no response received for id ${id}`)
}

async function handshake(client: TestClient): Promise<void> {
    await client.send({
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
            protocolVersion: '2025-06-18',
            capabilities: {},
            clientInfo: { name: 'test', version: '0.0.0' },
        },
    })
    await waitFor(client.received, 1)
    await client.send({ jsonrpc: '2.0', method: 'notifications/initialized' })
}

describe('weather MCP server', () => {
    it('negotiates initialize and reports server info', async () => {
        const client = createTestClient()
        await handshake(client)

        const init = client.received.find((m) => m.id === 1)
        expect(init?.result?.serverInfo).toMatchObject({ name: 'weather', version: '1.0.0' })
        expect(init?.result?.capabilities?.tools).toBeTruthy()
    })

    it('lists the get-alerts tool', async () => {
        const client = createTestClient()
        await handshake(client)

        await client.send({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} })
        const res = await waitFor(client.received, 2)

        const tools = res.result?.tools as Array<Record<string, any>>
        expect(tools.map((t) => t.name)).toContain('get-alerts')

        const tool = tools.find((t) => t.name === 'get-alerts')
        expect(tool?.description).toBe('Get weather alerts for a US state.')
        expect(tool?.inputSchema?.properties?.state).toMatchObject({
            type: 'string',
            minLength: 2,
            maxLength: 2,
        })
    })

    it('calls get-alerts and returns an alert for the state', async () => {
        const client = createTestClient()
        await handshake(client)

        await client.send({
            jsonrpc: '2.0',
            id: 3,
            method: 'tools/call',
            params: { name: 'get-alerts', arguments: { state: 'CA' } },
        })
        const res = await waitFor(client.received, 3)

        expect(res.result?.isError).toBeUndefined()
        const content = res.result?.content as Array<Record<string, any>>
        expect(content[0]?.type).toBe('text')

        const alert = JSON.parse(content[0]?.text)
        expect(alert[0]).toMatchObject({ event: 'Heat Advisory', area: 'CA' })
    })
})
