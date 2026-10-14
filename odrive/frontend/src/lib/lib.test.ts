import { describe, expect, it } from 'vitest'
import { decodeFlags, enumName, type Metadata } from './meta'
import { m4 } from './telemetry'
import { fmt, hex } from './format'

const meta: Metadata = {
  fw: '0.5.1',
  props: {
    'axis0.motor.error': { type: 'uint64', access: 'rw', enum: 'ODrive.Motor.Error' },
    'axis0.current_state': { type: 'uint32', access: 'r', enum: 'ODrive.Axis.AxisState' },
  },
  funcs: {},
  enums: {
    'ODrive.Motor.Error': {
      kind: 'flags',
      nullflag: 'NONE',
      bits: { PHASE_RESISTANCE_OUT_OF_RANGE: '1', UNKNOWN_VBUS_VOLTAGE: '2147483648', UNBALANCED_PHASES: '34359738368' },
      docs: {},
    },
    'ODrive.Axis.AxisState': { kind: 'enum', values: { IDLE: 1, CLOSED_LOOP_CONTROL: 8 }, docs: {} },
  },
}

describe('decodeFlags', () => {
  it('decodes bits above 31 (the reference gui loses these)', () => {
    expect(decodeFlags(meta, 'axis0.motor.error', 34359738368n + 2147483648n + 1n)).toEqual(['PHASE_RESISTANCE_OUT_OF_RANGE', 'UNKNOWN_VBUS_VOLTAGE', 'UNBALANCED_PHASES'])
  })
  it('reports unknown bits instead of hiding them', () => {
    expect(decodeFlags(meta, 'axis0.motor.error', 4)).toEqual(['BIT_2'])
  })
  it('returns nothing for zero or missing values', () => {
    expect(decodeFlags(meta, 'axis0.motor.error', 0)).toEqual([])
    expect(decodeFlags(meta, 'axis0.motor.error', undefined)).toEqual([])
  })
})

describe('enumName', () => {
  it('maps values to names', () => {
    expect(enumName(meta, 'axis0.current_state', 8)).toBe('CLOSED_LOOP_CONTROL')
    expect(enumName(meta, 'axis0.current_state', 42)).toBeUndefined()
  })
})

describe('m4', () => {
  it('keeps the extremes of each bucket', () => {
    const n = 10000
    const t = new Float64Array(n).map((_, i) => i)
    const y = new Float64Array(n).map((_, i) => (i === 5000 ? 100 : Math.sin(i / 50)))
    const out = m4(t, [y], 100)
    expect(out.t.length).toBeLessThanOrEqual(400)
    expect(Math.max(...out.ys[0])).toBe(100)
  })
  it('passes small series through unchanged', () => {
    const t = new Float64Array([0, 1, 2])
    expect(m4(t, [new Float64Array([1, 2, 3])], 100).ys[0]).toEqual([1, 2, 3])
  })
})

describe('format', () => {
  it('shows non-finite values explicitly', () => {
    expect(fmt(Infinity)).toBe('inf')
    expect(fmt(NaN)).toBe('NaN')
    expect(fmt(undefined)).toBe('--')
    expect(hex(256)).toBe('0x100')
    expect(hex(34359738368n)).toBe('0x800000000')
  })
})
