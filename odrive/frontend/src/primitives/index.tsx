import { useEffect, useRef, useState, type ReactNode } from 'react'
import { enumDef, type Metadata } from '../lib/meta'
import './primitives.css'

/** flat panel with a numbered header row (index, title, optional tools) and a scrollable body */
export function Panel(props: {
  index?: string
  title: string
  subtitle?: string
  status?: 'ok' | 'warn' | 'alarm' | 'live'
  tools?: ReactNode
  children?: ReactNode
  flush?: boolean
  alarm?: boolean
  className?: string
}) {
  return (
    <section className={`panel ${props.alarm ? 'alarm' : ''} ${props.className ?? ''}`}>
      <header className="panel-head">
        {props.index && <span className="panel-idx num">{props.index}</span>}
        <span className="panel-title">{props.title}</span>
        {props.subtitle && <span className="panel-sub">{props.subtitle}</span>}
        <div className="panel-tools">
          {props.tools}
          {props.status && <span className={`panel-dot ${props.status}`} title={props.status} />}
        </div>
      </header>
      <div className={`panel-body ${props.flush ? 'flush' : ''}`}>{props.children}</div>
    </section>
  )
}

type BtnProps = {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  kind?: 'primary' | 'danger' | 'on' | ''
  small?: boolean
  title?: string
  hotkey?: string
}

/** plain button; `hotkey` only renders the key hint */
export function Button({ children, onClick, disabled, kind = '', small, title, hotkey }: BtnProps) {
  return (
    <button className={`btn ${kind} ${small ? 'small' : ''}`} onClick={onClick} disabled={disabled} title={title}>
      {children}
      {hotkey && <span className="key">{hotkey}</span>}
    </button>
  )
}

/** button that must be held for `ms` before it fires (for energizing / destructive actions) */
export function HoldButton({ children, onFire, ms = 900, disabled }: { children: ReactNode; onFire: () => void; ms?: number; disabled?: boolean }) {
  const [holding, setHolding] = useState(false)
  const fill = useRef<HTMLDivElement>(null)
  const timer = useRef(0)
  const start = () => {
    if (disabled) return
    setHolding(true)
    const el = fill.current
    if (el) {
      el.style.transition = `transform ${ms}ms linear`
      el.style.transform = 'scaleX(1)'
    }
    timer.current = window.setTimeout(() => {
      stop()
      onFire()
    }, ms)
  }
  const stop = () => {
    clearTimeout(timer.current)
    setHolding(false)
    const el = fill.current
    if (el) {
      el.style.transition = 'none'
      el.style.transform = 'scaleX(0)'
    }
  }
  useEffect(() => () => clearTimeout(timer.current), [])
  return (
    <button
      className={`btn danger hold ${holding ? 'holding' : ''}`}
      disabled={disabled}
      onPointerDown={start}
      onPointerUp={stop}
      onPointerLeave={stop}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && !e.repeat && start()}
      onKeyUp={(e) => (e.key === 'Enter' || e.key === ' ') && stop()}
    >
      <div className="fill" ref={fill} />
      <span>{children}</span>
    </button>
  )
}

/** label + value + unit readout */
export function Value({ k, v, u, big, cls }: { k: string; v: ReactNode; u?: string; big?: boolean; cls?: string }) {
  return (
    <div className="val">
      <span className="k">{k}</span>
      <span className={`v num ${big ? 'big' : ''} ${cls ?? ''}`}>
        {v}
        {u && <span className="u">{u}</span>}
      </span>
    </div>
  )
}

/** status tag; level 'alarm'/'warn' are the only filled (colored) variants */
export function Tag({ level, children, blink }: { level: 'alarm' | 'warn' | 'info' | 'quiet'; children: ReactNode; blink?: boolean }) {
  const glyph = level === 'alarm' ? '■ ' : level === 'warn' ? '▲ ' : ''
  return (
    <span className={`tag ${level} ${blink ? 'blink' : ''}`}>
      {glyph}
      {children}
    </span>
  )
}

export function Tabs({ tabs, value, onChange }: { tabs: [string, string][]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="tabs">
      {tabs.map(([id, label]) => (
        <button key={id} className={id === value ? 'active' : ''} onClick={() => onChange(id)}>
          {label}
        </button>
      ))}
    </div>
  )
}

/** numeric input that commits on enter/blur and accepts inf/nan */
export function NumInput({ value, onCommit, step, disabled, width }: { value: unknown; onCommit: (v: number) => void; step?: number; disabled?: boolean; width?: number }) {
  const [text, setText] = useState(String(value ?? ''))
  const [focus, setFocus] = useState(false)
  useEffect(() => {
    if (!focus) setText(value === undefined || value === null ? '' : String(value))
  }, [value, focus])
  const commit = () => {
    const t = text.trim().toLowerCase()
    const v = t === 'inf' ? Infinity : t === '-inf' ? -Infinity : t === 'nan' ? NaN : Number(t)
    if (t !== '' && (!Number.isNaN(v) || t === 'nan')) onCommit(v)
  }
  return (
    <input
      className="num"
      style={width ? { width } : undefined}
      value={text}
      disabled={disabled}
      inputMode="decimal"
      step={step}
      onFocus={() => setFocus(true)}
      onBlur={() => {
        setFocus(false)
        commit()
      }}
      onChange={(e) => setText(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
        if (e.key === 'Escape') {
          setText(String(value ?? ''))
          ;(e.target as HTMLInputElement).blur()
        }
      }}
    />
  )
}

/** editor for one device property, choosing input type from metadata */
export function PropInput({ meta, path, type, value, onCommit, disabled }: { meta: Metadata | null; path: string; type?: string; value: unknown; onCommit: (v: unknown) => void; disabled?: boolean }) {
  const e = enumDef(meta, path)
  if (e && e.kind === 'enum') {
    return (
      <select value={String(value ?? '')} disabled={disabled} onChange={(ev) => onCommit(Number(ev.target.value))}>
        {Object.entries(e.values).map(([name, v]) => (
          <option key={name} value={v}>
            {name}
          </option>
        ))}
        {!Object.values(e.values).includes(Number(value)) && <option value={String(value)}>{String(value)}</option>}
      </select>
    )
  }
  if (type === 'bool') {
    return <input type="checkbox" checked={!!value} disabled={disabled} onChange={(ev) => onCommit(ev.target.checked)} />
  }
  return <NumInput value={typeof value === 'bigint' ? value.toString() : value} disabled={disabled} onCommit={(v) => onCommit(type?.includes('int') ? Math.trunc(v) : v)} />
}

/** horizontal bar for a value between 0 and max */
export function Bar({ value, max }: { value: number; max: number }) {
  const pct = Math.max(0, Math.min(1, Number.isFinite(value) ? value / max : 0)) * 100
  return (
    <div className="bar">
      <div style={{ width: `${pct}%` }} />
    </div>
  )
}
