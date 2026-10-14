import { useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '../primitives'
import { act, useApp } from '../lib/store'
import { decodeFlags, enumName } from '../lib/meta'
import { fmt, hex } from '../lib/format'
import './inspector.css'

type Line = { kind: 'in' | 'out' | 'err'; text: string }
const HIST_KEY = 'odrv.console.history.v1'

const QUICK: [string, string][] = [
  ['errors', 'axis0.error'],
  ['vbus', 'vbus_voltage'],
  ['state', 'axis0.current_state'],
  ['encoder', 'axis0.encoder.pos_estimate'],
  ['spi', 'axis0.encoder.spi_error_rate'],
  ['R / L', 'axis0.motor.config.phase_resistance'],
  ['idle', 'axis0.requested_state = IDLE'],
  ['clear', 'axis0.clear_errors()'],
]

/**
 * odrivetool-style console.
 *   path            read
 *   path = value    write (enum names allowed, e.g. CONTROL_MODE_POSITION_CONTROL)
 *   fn(a, b)        call
 * tab completes paths, up/down walks history. every write still goes through the safety layer.
 */
export function Console() {
  const tree = useApp((s) => s.tree)
  const meta = useApp((s) => s.meta)
  const [lines, setLines] = useState<Line[]>([{ kind: 'out', text: 'odrivetool-style console. "help" for syntax.' }])
  const [input, setInput] = useState('')
  const [hist, setHist] = useState<string[]>(() => JSON.parse(localStorage.getItem(HIST_KEY) ?? '[]'))
  const [hi, setHi] = useState(-1)
  const [sel, setSel] = useState(0)
  const out = useRef<HTMLDivElement>(null)
  useEffect(() => out.current?.scrollTo(0, out.current.scrollHeight), [lines])

  const token = input.replace(/^odrv0\./, '').split(/[\s=(]/)[0]
  const suggestions = useMemo(() => {
    if (!token || input.includes('=') || input.includes('(')) return []
    return Object.keys(tree)
      .filter((p) => p.startsWith(token))
      .sort()
      .slice(0, 30)
  }, [token, tree, input])

  const print = (l: Line) => setLines((s) => [...s.slice(-800), l])
  const describe = (path: string, v: unknown) => {
    const m = meta?.props[path]
    if (m?.enum && meta?.enums[m.enum]?.kind === 'flags') return `${hex(v)}  ${decodeFlags(meta, path, v).join(' | ') || 'NONE'}`
    const en = enumName(meta, path, v)
    return `${fmt(v, 6)}${en ? `  (${en})` : ''}${m?.unit ? ' ' + m.unit : ''}`
  }

  const run = async (raw: string) => {
    const cmd = raw.trim().replace(/^odrv0\./, '')
    if (!cmd) return
    print({ kind: 'in', text: raw })
    const nh = [raw, ...hist.filter((h) => h !== raw)].slice(0, 200)
    setHist(nh)
    localStorage.setItem(HIST_KEY, JSON.stringify(nh))
    setHi(-1)
    try {
      if (cmd === 'help') {
        print({ kind: 'out', text: 'path            -> read\npath = value    -> write (true/false, inf, enum names)\nfn(args)        -> call\nclear           -> clear screen\nls prefix       -> list paths' })
        return
      }
      if (cmd === 'clear') {
        setLines([])
        return
      }
      if (cmd.startsWith('ls')) {
        const pre = cmd.slice(2).trim()
        print({ kind: 'out', text: Object.keys(tree).filter((p) => p.startsWith(pre)).sort().join('\n') || '(nothing)' })
        return
      }
      const call = cmd.match(/^([\w.]+)\((.*)\)$/)
      if (call) {
        const args = call[2]
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
          .map((s) => (s === 'True' || s === 'true' ? true : s === 'False' || s === 'false' ? false : Number(s)))
        const r = await act('call', { path: call[1], args, source: 'console' }, true)
        print({ kind: 'out', text: r === null || r === undefined ? 'ok' : fmt(r, 6) })
        return
      }
      const asg = cmd.match(/^([\w.]+)\s*=\s*(.+)$/)
      if (asg) {
        const r = await act<any>('write', { path: asg[1], value: asg[2].trim(), source: 'console' }, true)
        print({ kind: 'out', text: `${asg[1]}: ${fmt(r.old)} -> ${fmt(r.value)}${r.warning ? '  [' + r.warning + ']' : ''}` })
        return
      }
      if (!tree[cmd]) throw new Error(`unknown path '${cmd}' (tab to complete, ls to list)`)
      const r = await act<Record<string, unknown>>('read', { paths: [cmd] }, true)
      print({ kind: 'out', text: describe(cmd, r[cmd]) })
    } catch (e) {
      print({ kind: 'err', text: String((e as Error).message) })
    }
  }

  return (
    <div>
      <div className="view-head">
        <h1>console</h1>
        <span className="sub">tab: complete . up/down: history . writes pass the safety layer</span>
        <div className="row" style={{ marginLeft: 'auto' }}>
          {QUICK.map(([label, c]) => (
            <Button key={label} small onClick={() => run(c)}>
              {label}
            </Button>
          ))}
        </div>
      </div>
      <div className="console" ref={out}>
        {lines.map((l, i) => (
          <pre key={i} className={`mono-pre ${l.kind === 'in' ? 'in' : l.kind === 'err' ? 'error-text' : 'dim'}`}>
            {l.text}
          </pre>
        ))}
      </div>
      <div className="console-input">
        <span className="prompt">odrv0&gt;</span>
        <input
          autoFocus
          value={input}
          spellCheck={false}
          onChange={(e) => {
            setInput(e.target.value)
            setSel(0)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              run(input)
              setInput('')
            } else if (e.key === 'Tab') {
              e.preventDefault()
              if (suggestions[sel]) setInput(suggestions[sel])
            } else if (e.key === 'ArrowUp') {
              e.preventDefault()
              if (suggestions.length) setSel((s) => Math.max(0, s - 1))
              else {
                const n = Math.min(hist.length - 1, hi + 1)
                setHi(n)
                setInput(hist[n] ?? '')
              }
            } else if (e.key === 'ArrowDown') {
              e.preventDefault()
              if (suggestions.length) setSel((s) => Math.min(suggestions.length - 1, s + 1))
              else {
                const n = Math.max(-1, hi - 1)
                setHi(n)
                setInput(n < 0 ? '' : hist[n])
              }
            }
          }}
        />
        {suggestions.length > 0 && suggestions[0] !== input && (
          <div className="suggest">
            {suggestions.map((s, i) => (
              <div key={s} className={i === sel ? 'sel' : ''} onMouseDown={() => setInput(s)}>
                {s} <span className="muted">{tree[s]?.kind === 'func' ? 'fn' : tree[s]?.type}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
