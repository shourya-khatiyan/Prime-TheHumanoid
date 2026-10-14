import { decode, encode } from '@msgpack/msgpack'

/** error returned by the backend; code 'confirm' means the action needs user confirmation */
export class RpcError extends Error {
  code: string
  action?: string
  constructor(message: string, code: string, action?: string) {
    super(message)
    this.code = code
    this.action = action
  }
}

type Pending = { resolve: (v: unknown) => void; reject: (e: unknown) => void; timer: number }
export type ServerMsg = { t: string; [k: string]: unknown }
export type LinkState = 'connecting' | 'open' | 'closed' | 'unauthorized'

function sessionToken(): string {
  return document.querySelector('meta[name="odrv-token"]')?.getAttribute('content') ?? ''
}

/**
 * websocket client for the backend.
 * - call(op, args): request/response over msgpack
 * - onMessage(fn): telemetry, status, events and job updates
 * reconnects automatically and pings every 500 ms (the backend disarms if pings stop).
 */
class Rpc {
  private ws: WebSocket | null = null
  private n = 0
  private pending = new Map<number, Pending>()
  private listeners = new Set<(m: ServerMsg) => void>()
  private stateListeners = new Set<(s: LinkState) => void>()
  private backoff = 300
  state: LinkState = 'closed'

  connect(): void {
    const token = sessionToken()
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    this.setState('connecting')
    const ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(token)}`)
    ws.binaryType = 'arraybuffer'
    this.ws = ws
    ws.onopen = () => {
      this.backoff = 300
      this.setState('open')
    }
    ws.onmessage = (ev) => this.handle(ev.data as ArrayBuffer)
    ws.onclose = (ev) => {
      this.ws = null
      for (const [, p] of this.pending) {
        clearTimeout(p.timer)
        p.reject(new RpcError('connection closed', 'closed'))
      }
      this.pending.clear()
      if (ev.code === 4403) {
        // stale token after a backend restart: reload picks up the new one
        this.setState('unauthorized')
        setTimeout(() => location.reload(), 1500)
        return
      }
      this.setState('closed')
      setTimeout(() => this.connect(), this.backoff)
      this.backoff = Math.min(this.backoff * 1.6, 3000)
    }
  }

  private setState(s: LinkState) {
    this.state = s
    this.stateListeners.forEach((fn) => fn(s))
  }

  private handle(buf: ArrayBuffer) {
    let msg: ServerMsg
    try {
      msg = decode(new Uint8Array(buf), { useBigInt64: true }) as ServerMsg
    } catch {
      return
    }
    if (msg.t === 'res') {
      const p = this.pending.get(msg.id as number)
      if (!p) return
      this.pending.delete(msg.id as number)
      clearTimeout(p.timer)
      if (msg.ok) p.resolve(msg.data)
      else p.reject(new RpcError(String(msg.error ?? 'error'), String(msg.code ?? 'error'), msg.action as string | undefined))
      return
    }
    this.listeners.forEach((fn) => fn(msg))
  }

  /** send one request; rejects with RpcError on failure or timeout */
  call<T = unknown>(op: string, args: Record<string, unknown> = {}, timeoutMs = 20000): Promise<T> {
    const ws = this.ws
    if (!ws || ws.readyState !== WebSocket.OPEN) return Promise.reject(new RpcError('not connected to backend', 'closed'))
    const id = ++this.n
    return new Promise<T>((resolve, reject) => {
      const timer = window.setTimeout(() => {
        this.pending.delete(id)
        reject(new RpcError(`${op} timed out`, 'timeout'))
      }, timeoutMs)
      this.pending.set(id, { resolve: resolve as (v: unknown) => void, reject, timer })
      ws.send(encode({ id, op, args }, { useBigInt64: true }))
    })
  }

  onMessage(fn: (m: ServerMsg) => void): () => void {
    this.listeners.add(fn)
    return () => this.listeners.delete(fn)
  }

  onState(fn: (s: LinkState) => void): () => void {
    this.stateListeners.add(fn)
    return () => this.stateListeners.delete(fn)
  }

  /** session token, for download links */
  get token(): string {
    return sessionToken()
  }
}

export const rpc = new Rpc()

// heartbeat: the backend uses it to detect a dead gui and disarm
setInterval(() => {
  if (rpc.state === 'open') rpc.call('ping', {}, 2000).catch(() => undefined)
}, 500)
