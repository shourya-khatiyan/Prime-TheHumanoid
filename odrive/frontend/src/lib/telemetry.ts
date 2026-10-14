/**
 * telemetry ring buffers.
 * every column the backend has ever sent gets a Float64Array of the same length
 * as the shared time ring, so any set of signals can be plotted on one time axis.
 */

const CAP = 36000 // ~3 min at 200 Hz

export type TelFrame = { cols: string[]; ts: number[]; rows: unknown[][] }

function toNum(v: unknown): number {
  if (typeof v === 'number') return v
  if (typeof v === 'boolean') return v ? 1 : 0
  if (typeof v === 'bigint') return Number(v)
  return NaN
}

class Telemetry {
  t = new Float64Array(CAP)
  cols = new Map<string, Float64Array>()
  latest = new Map<string, unknown>()
  head = 0 // next write index
  len = 0
  version = 0
  lastTs = 0
  frames = 0
  private listeners = new Set<() => void>()

  push(f: TelFrame): void {
    const idx = new Map<string, number>()
    f.cols.forEach((c, i) => {
      idx.set(c, i)
      if (!this.cols.has(c)) this.cols.set(c, new Float64Array(CAP).fill(NaN))
    })
    const entries = [...this.cols.entries()].map(([c, arr]) => [arr, idx.get(c) ?? -1] as const)
    for (let r = 0; r < f.rows.length; r++) {
      const row = f.rows[r]
      const h = this.head
      this.t[h] = f.ts[r]
      for (const [arr, i] of entries) arr[h] = i >= 0 ? toNum(row[i]) : NaN
      this.head = (h + 1) % CAP
      if (this.len < CAP) this.len++
    }
    const last = f.rows[f.rows.length - 1]
    if (last) f.cols.forEach((c, i) => this.latest.set(c, last[i]))
    this.lastTs = f.ts[f.ts.length - 1] ?? this.lastTs
    this.frames++
    this.version++
    this.listeners.forEach((fn) => fn())
  }

  /** samples newer than `seconds` before the latest one, oldest first */
  window(paths: string[], seconds: number): { t: Float64Array; ys: Float64Array[] } {
    const n = this.len
    let count = 0
    const cutoff = this.lastTs - seconds
    // walk back from the newest sample until the cutoff
    for (let k = 1; k <= n; k++) {
      const i = (this.head - k + CAP) % CAP
      if (this.t[i] < cutoff) break
      count++
    }
    const t = new Float64Array(count)
    const ys = paths.map(() => new Float64Array(count))
    const cols = paths.map((p) => this.cols.get(p))
    const start = (this.head - count + CAP) % CAP
    for (let k = 0; k < count; k++) {
      const i = (start + k) % CAP
      t[k] = this.t[i]
      for (let s = 0; s < cols.length; s++) ys[s][k] = cols[s] ? cols[s]![i] : NaN
    }
    return { t, ys }
  }

  get(path: string): unknown {
    return this.latest.get(path)
  }

  subscribe(fn: () => void): () => void {
    this.listeners.add(fn)
    return () => this.listeners.delete(fn)
  }

  clear(): void {
    this.len = 0
    this.head = 0
    this.version++
  }
}

export const telemetry = new Telemetry()

/**
 * m4 downsampling: per pixel bucket keep first, min, max, last.
 * draws the same line as the full data with at most 4 points per pixel.
 */
export function m4(t: Float64Array, ys: Float64Array[], buckets: number): { t: number[]; ys: number[][] } {
  const n = t.length
  if (n <= buckets * 4 || n < 2) return { t: Array.from(t), ys: ys.map((y) => Array.from(y)) }
  const t0 = t[0]
  const span = t[n - 1] - t0 || 1
  const outT: number[] = []
  const outY: number[][] = ys.map(() => [])
  let i = 0
  for (let b = 0; b < buckets; b++) {
    const end = t0 + (span * (b + 1)) / buckets
    const s = i
    while (i < n && (t[i] <= end || b === buckets - 1)) i++
    if (i === s) continue
    // use the first series to choose min/max indices so all series stay aligned in time
    const y0 = ys[0]
    let mn = s
    let mx = s
    for (let k = s; k < i; k++) {
      if (y0[k] < y0[mn]) mn = k
      if (y0[k] > y0[mx]) mx = k
    }
    const picks = [...new Set([s, mn, mx, i - 1])].sort((a, z) => a - z)
    for (const k of picks) {
      outT.push(t[k])
      ys.forEach((y, j) => outY[j].push(y[k]))
    }
  }
  return { t: outT, ys: outY }
}
