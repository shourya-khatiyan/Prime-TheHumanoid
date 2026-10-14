/** number formatting for live values (fixed width, explicit nan/inf) */

export function fmt(v: unknown, digits = 3): string {
  if (v === undefined || v === null) return '--'
  if (typeof v === 'boolean') return v ? 'true' : 'false'
  if (typeof v === 'bigint') return v.toString()
  if (typeof v === 'number') {
    if (Number.isNaN(v)) return 'NaN'
    if (!Number.isFinite(v)) return v > 0 ? 'inf' : '-inf'
    if (Number.isInteger(v) && Math.abs(v) < 1e9) return String(v)
    const a = Math.abs(v)
    if (a !== 0 && (a < 1e-3 || a >= 1e6)) return v.toExponential(2)
    return v.toFixed(digits)
  }
  return String(v)
}

export function hex(v: unknown): string {
  if (typeof v === 'bigint') return '0x' + v.toString(16).toUpperCase()
  if (typeof v === 'number' && Number.isFinite(v)) return '0x' + Math.trunc(v).toString(16).toUpperCase()
  return '--'
}

export function time(ts: number): string {
  const d = new Date(ts * 1000)
  return d.toTimeString().slice(0, 8) + '.' + String(d.getMilliseconds()).padStart(3, '0')
}

export function date(ts: number): string {
  return new Date(ts * 1000).toISOString().replace('T', ' ').slice(0, 19)
}

export function num(v: unknown): number {
  if (typeof v === 'number') return v
  if (typeof v === 'bigint') return Number(v)
  if (typeof v === 'boolean') return v ? 1 : 0
  return NaN
}
