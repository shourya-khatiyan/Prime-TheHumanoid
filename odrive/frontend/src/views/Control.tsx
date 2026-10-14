import { useEffect, useRef, useState } from 'react'
import { Button, NumInput, Panel, PropInput, Tag, Value } from '../primitives'
import { act, P, startJob, useAliasLatest, useApp, useLatest } from '../lib/store'
import { AXIS_STATES, enumDef } from '../lib/meta'
import { fmt, num } from '../lib/format'
import { CurrentPlot, MotionPlot } from './panels'

const KIND = { 1: 'torque', 2: 'vel', 3: 'pos' } as const
const UNIT = { torque: 'Nm', vel: 'turn/s', pos: 'turn' } as const

/** live-editable property row */
function PropRow({ path, label }: { path: string; label?: string }) {
  const meta = useApp((s) => s.meta)
  const tree = useApp((s) => s.tree)
  const [v] = useLatest([path], 4)
  if (!path || !tree[path]) return null
  return (
    <div className="field">
      <label title={path}>{label ?? path.split('.').slice(-1)[0]}</label>
      <PropInput meta={meta} path={path} type={tree[path].type} value={v} onCommit={(nv) => act('write', { path, value: nv }).catch(() => undefined)} />
      <span className="unit">{meta?.props[path]?.unit ?? ''}</span>
    </div>
  )
}

/** setpoint slider + number, limited by the profile envelope */
function Setpoint({ ax, kind, active }: { ax: number; kind: 'pos' | 'vel' | 'torque'; active: boolean }) {
  const profile = useApp((s) => s.profile)!
  const [cur] = useAliasLatest([`input_${kind}.${ax}`], 8)
  const lo = kind === 'pos' ? profile.limits.pos_min_turns : kind === 'vel' ? -profile.limits.vel_max_turns_s : -profile.derived.torque_max_nm
  const hi = kind === 'pos' ? profile.limits.pos_max_turns : kind === 'vel' ? profile.limits.vel_max_turns_s : profile.derived.torque_max_nm
  const [slider, setSlider] = useState(0)
  useEffect(() => setSlider(num(cur) || 0), [cur])
  const send = (v: number) => act('setpoint', { axis: ax, kind, value: v }).catch(() => undefined)
  return (
    <div className="col">
      <div className="row">
        <span className="dim">input_{kind}</span>
        <NumInput value={fmt(cur, 4)} onCommit={send} disabled={!active} width={110} />
        <span className="muted">{UNIT[kind]}</span>
        <span className="muted">
          limits {fmt(lo, 2)} .. {fmt(hi, 2)}
        </span>
        <Button small disabled={!active} onClick={() => send(kind === 'pos' ? num(cur) : 0)}>
          {kind === 'pos' ? 'hold here' : 'zero'}
        </Button>
      </div>
      <input
        type="range"
        min={lo}
        max={hi}
        step={(hi - lo) / 2000}
        value={slider}
        disabled={!active}
        onChange={(e) => setSlider(Number(e.target.value))}
        onPointerUp={() => send(slider)}
        onKeyUp={() => send(slider)}
        style={{ width: '100%' }}
      />
    </div>
  )
}

function Jog({ ax, kind, active }: { ax: number; kind: 'pos' | 'vel' | 'torque'; active: boolean }) {
  const [posSet] = useAliasLatest([`input_pos.${ax}`], 8)
  const [jogV, setJogV] = useState(0.5)
  const send = (v: number) => act('setpoint', { axis: ax, kind, value: v }).catch(() => undefined)
  if (kind === 'pos')
    return (
      <div className="row">
        {[-1, -0.1, -0.01, 0.01, 0.1, 1].map((d) => (
          <Button key={d} small disabled={!active} onClick={() => send(num(posSet) + d)}>
            {d > 0 ? '+' : ''}
            {d}
          </Button>
        ))}
        <span className="muted">turn steps</span>
      </div>
    )
  if (kind === 'vel')
    return (
      <div className="row">
        <span className="dim">hold to jog</span>
        {[-1, 1].map((s) => (
          <button key={s} className="btn" disabled={!active} onPointerDown={() => send(s * jogV)} onPointerUp={() => send(0)} onPointerLeave={() => send(0)}>
            {s < 0 ? '<< rev' : 'fwd >>'}
          </button>
        ))}
        <NumInput value={jogV} onCommit={setJogV} width={70} />
        <span className="muted">turn/s</span>
      </div>
    )
  return <span className="muted">torque mode: use the setpoint above (velocity is limited by vel_limit if enabled)</span>
}

/** client-side square/sine generator on the active setpoint (backend still clamps every value) */
function Generator({ ax, kind, active }: { ax: number; kind: 'pos' | 'vel' | 'torque'; active: boolean }) {
  const [shape, setShape] = useState<'square' | 'sine'>('square')
  const [amp, setAmp] = useState(kind === 'pos' ? 0.1 : kind === 'vel' ? 0.5 : 0.02)
  const [freq, setFreq] = useState(0.5)
  const [offset, setOffset] = useState(0)
  const [running, setRunning] = useState(false)
  const timer = useRef(0)
  const [posNow] = useAliasLatest([`pos.${ax}`], 2)
  useEffect(() => {
    if (!running) return
    const t0 = performance.now()
    const base = kind === 'pos' ? num(posNow) + offset : offset
    timer.current = window.setInterval(() => {
      const t = (performance.now() - t0) / 1000
      const ph = 2 * Math.PI * freq * t
      const v = base + (shape === 'sine' ? amp * Math.sin(ph) : Math.sin(ph) >= 0 ? amp : -amp)
      act('setpoint', { axis: ax, kind, value: v }, true).catch(() => setRunning(false))
    }, 20)
    return () => clearInterval(timer.current)
  }, [running])
  useEffect(() => {
    if (!active) setRunning(false)
  }, [active])
  return (
    <div className="col">
      <div className="row">
        <select value={shape} onChange={(e) => setShape(e.target.value as 'square' | 'sine')} disabled={running}>
          <option value="square">square</option>
          <option value="sine">sine</option>
        </select>
        <span className="dim">amp</span>
        <NumInput value={amp} onCommit={setAmp} width={70} disabled={running} />
        <span className="dim">freq</span>
        <NumInput value={freq} onCommit={(v) => setFreq(Math.min(10, Math.max(0.05, v)))} width={60} disabled={running} />
        <span className="muted">Hz</span>
        <span className="dim">offset</span>
        <NumInput value={offset} onCommit={setOffset} width={60} disabled={running} />
        <Button kind={running ? 'on' : 'primary'} disabled={!active} onClick={() => setRunning(!running)}>
          {running ? 'stop' : 'start'}
        </Button>
      </div>
      <span className="muted" style={{ fontSize: 'var(--fs-tick)' }}>
        50 Hz host-side updates; for accurate response measurements use tests &gt; tuning
      </span>
    </div>
  )
}

export function Control() {
  const ax = useApp((s) => s.axis)
  const meta = useApp((s) => s.meta)
  const profile = useApp((s) => s.profile)
  const active = useApp((s) => !!s.status?.safety.active_axes.includes(ax))
  const [state, cm, im, err] = useAliasLatest([`state.${ax}`, `ctrl_mode.${ax}`, `input_mode.${ax}`, `error.${ax}`], 8)
  const kind = KIND[num(cm) as 1 | 2 | 3] ?? 'pos'
  const imDef = enumDef(meta, P(`input_mode.${ax}`))
  const reqState = (s: number) => act('write', { path: P(`req_state.${ax}`), value: s }).catch(() => undefined)
  if (!profile) return <span className="muted">waiting for device</span>
  return (
    <div>
      <div className="view-head">
        <h1>control</h1>
        <span className="sub">
          axis{ax} . {AXIS_STATES[num(state)] ?? '--'}
        </span>
        <div className="row" style={{ marginLeft: 'auto' }}>
          {[0, 1].map((a) => (
            <Button key={a} small kind={a === ax ? 'on' : ''} onClick={() => useApp.setState({ axis: a })}>
              axis{a}
            </Button>
          ))}
        </div>
      </div>
      <div className="grid2">
        <Panel title="state" tools={num(err) ? <Tag level="alarm">errors</Tag> : active ? <Tag level="info">gui active, watchdog fed</Tag> : undefined}>
          <div className="col">
            <div className="row">
              <Button onClick={() => reqState(1)}>idle</Button>
              <Button kind="primary" onClick={() => reqState(8)}>
                closed loop
              </Button>
              <Button onClick={() => act('clear_errors', { axis: ax })}>clear errors</Button>
            </div>
            <div className="row">
              <span className="muted">calibration</span>
              <Button onClick={() => startJob('calibrate', { axis: ax, kind: 'motor' }).catch(() => undefined)}>motor R/L</Button>
              <Button onClick={() => startJob('calibrate', { axis: ax, kind: 'encoder' }).catch(() => undefined)}>encoder offset</Button>
              <Button onClick={() => startJob('calibrate', { axis: ax, kind: 'full' }).catch(() => undefined)}>full</Button>
            </div>
            <div className="field">
              <label>control mode</label>
              <PropInput meta={meta} path={P(`ctrl_mode.${ax}`)} value={cm} onCommit={(v) => act('write', { path: P(`ctrl_mode.${ax}`), value: v })} />
              <span />
            </div>
            <div className="field">
              <label>input mode</label>
              <select value={String(im ?? '')} onChange={(e) => act('write', { path: P(`input_mode.${ax}`), value: Number(e.target.value) })}>
                {imDef?.kind === 'enum' &&
                  Object.entries(imDef.values).map(([n, v]) => (
                    <option key={n} value={v}>
                      {n}
                    </option>
                  ))}
              </select>
              <span />
            </div>
            {!active && <span className="muted">setpoints unlock once this GUI puts the axis into closed loop</span>}
          </div>
        </Panel>
        <Panel title={`setpoint . ${kind}`}>
          <div className="col">
            <Setpoint ax={ax} kind={kind} active={active} />
            <Jog ax={ax} kind={kind} active={active} />
            <Generator key={kind} ax={ax} kind={kind} active={active} />
          </div>
        </Panel>
        <Panel title="motion">
          <div className="h-plot">
            <MotionPlot ax={ax} windowS={10} />
          </div>
        </Panel>
        <Panel title="current">
          <div className="h-plot">
            <CurrentPlot ax={ax} windowS={10} />
          </div>
        </Panel>
        <Panel title="gains">
          <PropRow path={P(`pos_gain.${ax}`)} />
          <PropRow path={P(`vel_gain.${ax}`)} />
          <PropRow path={P(`vel_int_gain.${ax}`)} label="vel_integrator_gain" />
          <PropRow path={`axis${ax}.controller.config.input_filter_bandwidth`} />
          <PropRow path={`axis${ax}.controller.config.vel_ramp_rate`} />
          <PropRow path={`axis${ax}.controller.config.torque_ramp_rate`} />
        </Panel>
        <Panel title="limits (profile capped)">
          <PropRow path={P(`vel_limit.${ax}`)} />
          <PropRow path={P(`current_lim.${ax}`)} />
          <PropRow path={P(`torque_mode_vel_limit.${ax}`)} label="torque-mode vel limit" />
          <PropRow path={`axis${ax}.trap_traj.config.vel_limit`} label="trap vel_limit" />
          <PropRow path={`axis${ax}.trap_traj.config.accel_limit`} label="trap accel_limit" />
          <PropRow path={`axis${ax}.trap_traj.config.decel_limit`} label="trap decel_limit" />
          <div className="row" style={{ marginTop: 6 }}>
            <Value k="profile vel max" v={profile.limits.vel_max_turns_s} u="turn/s" />
            <Value k="profile current peak" v={profile.motor.current_peak_a} u="A" />
            <Value k="torque max" v={fmt(profile.derived.torque_max_nm, 3)} u="Nm" />
          </div>
        </Panel>
      </div>
    </div>
  )
}
