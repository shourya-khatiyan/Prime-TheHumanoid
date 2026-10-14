import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, HoldButton } from '../primitives'
import { act, useApp } from '../lib/store'
import { time } from '../lib/format'
import { VIEWS } from '../views/registry'

/** confirmation dialog for every action the backend marks as dangerous (hold to confirm) */
export function ConfirmDialog() {
  const req = useApp((s) => s.confirm)
  useEffect(() => {
    if (!req) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        req.resolve(false)
        useApp.setState({ confirm: null })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [req])
  if (!req) return null
  const close = (ok: boolean) => {
    req.resolve(ok)
    useApp.setState({ confirm: null })
  }
  return (
    <div className="modal-back">
      <div className="modal" role="alertdialog" aria-label="confirm action">
        <h3>▲ confirm</h3>
        <p className="mono-pre">{req.message}</p>
        <p className="muted" style={{ fontSize: 'var(--fs-tick)' }}>
          action: {req.action}
        </p>
        <div className="row" style={{ justifyContent: 'flex-end', marginTop: 12 }}>
          <Button onClick={() => close(false)} hotkey="esc">
            cancel
          </Button>
          <HoldButton onFire={() => close(true)}>hold to confirm</HoldButton>
        </div>
      </div>
    </div>
  )
}

/** bottom line: last message and a few counters */
export function MessageLine() {
  const msg = useApp((s) => s.message)
  const status = useApp((s) => s.status)
  return (
    <div className="msgline">
      {msg ? (
        <>
          <span className="muted">{time(msg.ts)}</span>
          <span className={msg.level === 'error' ? 'error' : msg.level === 'warn' ? 'warn' : ''}>{msg.text}</span>
        </>
      ) : (
        <span className="muted">ready</span>
      )}
      <span className="right">
        : palette . alt+1..9 views . esc disarm . profile {status?.profile ?? '--'}
      </span>
    </div>
  )
}

/** running job: logs, progress, prompts that need operator input, abort */
export function JobDock() {
  const jobs = useApp((s) => s.jobs)
  const [hidden, setHidden] = useState<string | null>(null)
  const job = useMemo(() => {
    const list = Object.values(jobs).sort((a, b) => b.started - a.started)
    return list.find((j) => j.state === 'running') ?? list.find((j) => j.ended && Date.now() / 1000 - j.ended < 8)
  }, [jobs])
  const [values, setValues] = useState<Record<string, string>>({})
  const logRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [job?.logs.length])
  if (!job || hidden === job.id + job.state) return null
  const answer = (choice: string) => {
    const vals = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, Number(v)]))
    act('job_answer', { id: job.id, data: { choice, values: vals } })
    setValues({})
  }
  return (
    <div className="jobdock">
      <div className="panel-head">
        <span className="panel-title">job {job.id}</span>
        <span className={job.state === 'failed' ? 'error-text' : job.state === 'aborted' ? 'warn-text' : 'dim'}>{job.state}</span>
        <div className="panel-tools">
          <span className="num muted">{Math.round(job.progress * 100)}%</span>
          {job.state === 'running' ? (
            <Button small kind="danger" onClick={() => act('job_abort', { id: job.id })}>
              abort
            </Button>
          ) : (
            <Button small onClick={() => setHidden(job.id + job.state)}>
              close
            </Button>
          )}
        </div>
      </div>
      <div className="bar">
        <div style={{ width: `${job.progress * 100}%` }} />
      </div>
      <div className="logs" ref={logRef}>
        {job.logs.map((l, i) => (
          <div key={i} className={l.level === 'alarm' ? 'error-text' : l.level === 'warn' ? 'warn-text' : ''}>
            <span className="muted">{time(l.ts)} </span>
            {l.msg}
          </div>
        ))}
        {job.error && <div className="error-text">{job.error}</div>}
      </div>
      {job.prompt && (
        <div className="prompt">
          <div>{job.prompt.text}</div>
          {job.prompt.inputs.map((inp) => (
            <div key={inp.key} className="row" style={{ marginTop: 6 }}>
              <span className="dim">{inp.label}</span>
              <input className="num" value={values[inp.key] ?? ''} onChange={(e) => setValues({ ...values, [inp.key]: e.target.value })} style={{ width: 120 }} autoFocus />
              <span className="muted">{inp.unit}</span>
            </div>
          ))}
          <div className="row" style={{ marginTop: 8 }}>
            {job.prompt.options.map((o) => (
              <Button key={o} kind="primary" onClick={() => answer(o)}>
                {o}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/** ':' / ctrl+k palette: jump to views and run common actions */
export function CommandPalette() {
  const open = useApp((s) => s.palette)
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const items = useMemo(() => {
    const base = [
      ...VIEWS.map((v) => ({ label: `go ${v.label}`, hint: v.key, run: () => useApp.setState({ view: v.id }) })),
      { label: 'disarm all', hint: 'esc', run: () => act('disarm', { reason: 'palette' }) },
      { label: 'clear errors (both axes)', hint: '', run: () => act('clear_errors', {}) },
      { label: 'acknowledge all alarms', hint: '', run: () => act('ack', {}) },
      { label: 'save configuration', hint: '', run: () => act('call', { path: 'save_configuration', args: [] }) },
      { label: 'reconnect device', hint: '', run: () => act('connect', { mode: 'auto' }) },
      { label: 'use simulated device', hint: '', run: () => act('connect', { mode: 'mock' }) },
      { label: 'use ascii transport', hint: '', run: () => act('connect', { mode: 'ascii' }) },
      { label: 'select axis0', hint: '', run: () => useApp.setState({ axis: 0 }) },
      { label: 'select axis1', hint: '', run: () => useApp.setState({ axis: 1 }) },
    ]
    const ql = q.toLowerCase()
    return base.filter((i) => i.label.includes(ql))
  }, [q])
  if (!open) return null
  const close = () => {
    useApp.setState({ palette: false })
    setQ('')
    setSel(0)
  }
  return (
    <div className="modal-back" style={{ alignItems: 'flex-start', background: 'rgba(4,8,6,.5)' }} onClick={close}>
      <div className="palette" onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          value={q}
          placeholder="command"
          onChange={(e) => {
            setQ(e.target.value)
            setSel(0)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') close()
            if (e.key === 'ArrowDown') setSel((s) => Math.min(items.length - 1, s + 1))
            if (e.key === 'ArrowUp') setSel((s) => Math.max(0, s - 1))
            if (e.key === 'Enter' && items[sel]) {
              items[sel].run()
              close()
            }
          }}
        />
        {items.slice(0, 14).map((it, i) => (
          <div
            key={it.label}
            className={`item ${i === sel ? 'sel' : ''}`}
            onMouseEnter={() => setSel(i)}
            onClick={() => {
              it.run()
              close()
            }}
          >
            <span>{it.label}</span>
            <span className="muted">{it.hint}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
