/** firmware metadata helpers: units, docs, enum names and 64-bit error flag decoding */

export type PropMeta = { type: string; access: 'r' | 'rw'; unit?: string; brief?: string; doc?: string; enum?: string }
export type EnumDef =
  | { kind: 'enum'; values: Record<string, number>; docs: Record<string, string> }
  | { kind: 'flags'; nullflag: string; bits: Record<string, string>; docs: Record<string, string> }
export type Metadata = {
  fw: string
  props: Record<string, PropMeta>
  funcs: Record<string, { in: { name: string; type: string }[]; out: { name: string; type: string }[]; doc: string }>
  enums: Record<string, EnumDef>
}

export function toBig(v: unknown): bigint {
  if (typeof v === 'bigint') return v
  if (typeof v === 'number' && Number.isFinite(v)) return BigInt(Math.trunc(v))
  if (typeof v === 'string' && /^-?\d+$/.test(v)) return BigInt(v)
  return 0n
}

/** split an error bitfield into flag names; works above bit 31 (BigInt) */
export function decodeFlags(meta: Metadata | null, path: string, value: unknown): string[] {
  const v = toBig(value)
  if (v === 0n) return []
  const e = meta && meta.props[path]?.enum ? meta.enums[meta.props[path].enum!] : undefined
  const out: string[] = []
  let known = 0n
  if (e && e.kind === 'flags') {
    for (const [name, bit] of Object.entries(e.bits)) {
      const b = BigInt(bit)
      known |= b
      if (v & b) out.push(name)
    }
  }
  let rest = v & ~known
  let i = 0
  while (rest > 0n) {
    if (rest & 1n) out.push(`BIT_${i}`)
    rest >>= 1n
    i++
  }
  return out
}

/** doc string for one error flag */
export function flagDoc(meta: Metadata | null, path: string, flag: string): string {
  const e = meta && meta.props[path]?.enum ? meta.enums[meta.props[path].enum!] : undefined
  return e?.docs?.[flag] ?? ''
}

export function enumDef(meta: Metadata | null, path: string): EnumDef | undefined {
  const name = meta?.props[path]?.enum
  return name ? meta!.enums[name] : undefined
}

/** enum value -> name ('8' -> 'CLOSED_LOOP_CONTROL') */
export function enumName(meta: Metadata | null, path: string, value: unknown): string | undefined {
  const e = enumDef(meta, path)
  if (!e || e.kind !== 'enum') return undefined
  const n = Number(value)
  return Object.entries(e.values).find(([, v]) => v === n)?.[0]
}

export function unitOf(meta: Metadata | null, path: string): string {
  return meta?.props[path]?.unit ?? ''
}

export const AXIS_STATES: Record<number, string> = {
  0: 'UNDEFINED',
  1: 'IDLE',
  2: 'STARTUP',
  3: 'FULL_CALIBRATION',
  4: 'MOTOR_CALIBRATION',
  5: 'SENSORLESS',
  6: 'INDEX_SEARCH',
  7: 'ENCODER_OFFSET_CAL',
  8: 'CLOSED_LOOP',
  9: 'LOCKIN_SPIN',
  10: 'ENCODER_DIR_FIND',
  11: 'HOMING',
  12: 'HALL_POLARITY_CAL',
  13: 'HALL_PHASE_CAL',
}
