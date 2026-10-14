import { Bar, Button, Tag, Value } from '../primitives'
import { LivePlot } from '../components/Plot'
import { act, P, useAliasLatest, useApp, useLatest } from '../lib/store'
import { AXIS_STATES, decodeFlags, enumName, flagDoc } from '../lib/meta'
import { fmt, hex, num, time } from '../lib/format'

/** position + velocity of the selected axis */
export function MotionPlot({ ax, windowS }: { ax: number; windowS: number }) {
  return (
    <LivePlot
      windowS={windowS}
      series={[
        { path: P(`pos.${ax}`), label: 'pos', scale: 'turn' },
        { path: P(`pos_set.${ax}`), label: 'pos_set', scale: 'turn' },
        { path: P(`vel.${ax}`), label: 'vel', scale: 'turn/s' },
      ]}
    />
  )
}

export function CurrentPlot({ ax, windowS }: { ax: number; windowS: number }) {
  return (
    <LivePlot
      windowS={windowS}
      series={[
        { path: P(`iq_set.${ax}`), label: 'Iq_set', scale: 'A' },
        { path: P(`iq.${ax}`), label: 'Iq', scale: 'A' },
      ]}
    />
  )
}

export function PowerPlot({ windowS }: { windowS: number }) {
  return (
    <LivePlot
      windowS={windowS}
      series={[
        { path: P('vbus'), label: 'vbus', scale: 'V' },
        { path: P('ibus'), label: 'ibus', scale: 'A' },
      ]}
    />
  )
}

export function ThermalPlot({ ax, windowS }: { ax: number; windowS: number }) {
  return (
    <LivePlot
      windowS={windowS}
      series={[
        { path: P(`fet_temp.${ax}`), label: 'fet', scale: 'C' },
        { path: P(`motor_temp.${ax}`), label: 'motor', scale: 'C' },
      ]}
    />
  )
}

/** state, modes, calibration flags and live values of one axis */
export function AxisCard({ ax }: { ax: number }) {
  const meta = useApp((s) => s.meta)
  const active = useApp((s) => s.status?.safety.active_axes.includes(ax))
  const [state, err, cm, im, cal, ready, pos, vel, iq, temp] = useAliasLatest(
    [`state.${ax}`, `error.${ax}`, `ctrl_mode.${ax}`, `input_mode.${ax}`, `motor_cal.${ax}`, `enc_ready.${ax}`, `pos.${ax}`, `vel.${ax}`, `iq.${ax}`, `fet_temp.${ax}`],
    10,
  )
  const faulted = num(err) !== 0 && err !== undefined
  return (
    <div className="col">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <Value k="state" v={AXIS_STATES[num(state)] ?? '--'} big />
        {faulted ? <Tag level="alarm">fault</Tag> : active ? <Tag level="info">gui active</Tag> : <Tag level="quiet">idle-safe</Tag>}
      </div>
      <div className="kv num">
        <span>control</span>
        <span>{enumName(meta, P(`ctrl_mode.${ax}`), cm) ?? fmt(cm)}</span>
        <span>input</span>
        <span>{enumName(meta, P(`input_mode.${ax}`), im) ?? fmt(im)}</span>
        <span>motor cal</span>
        <span>{cal === undefined ? '--' : cal ? 'yes' : 'no'}</span>
        <span>encoder</span>
        <span>{ready === undefined ? '--' : ready ? 'ready' : 'not ready'}</span>
      </div>
      <div className="vgrid">
        <Value k="pos" v={fmt(pos, 3)} u="turn" />
        <Value k="vel" v={fmt(vel, 2)} u="t/s" />
        <Value k="iq" v={fmt(iq, 2)} u="A" />
        <Value k="fet" v={fmt(temp, 1)} u="C" />
      </div>
    </div>
  )
}

/** motor-side values converted to the joint through the gear ratio */
export function JointCard({ ax }: { ax: number }) {
  const profile = useApp((s) => s.profile)
  const [pos, vel, iq, kt] = useAliasLatest([`pos.${ax}`, `vel.${ax}`, `iq.${ax}`, `kt.${ax}`], 10)
  if (!profile) return <span className="muted">NO DATA</span>
  const ratio = Number(profile.gear.ratio)
  const eff = Number(profile.gear.efficiency)
  const ktv = Number.isFinite(num(kt)) && num(kt) > 0 ? num(kt) : profile.derived.kt_nm_per_a
  const tMotor = num(iq) * ktv
  return (
    <div className="col">
      <div className="vgrid">
        <Value k="joint angle" v={fmt((num(pos) * 360) / ratio, 2)} u="deg" big />
        <Value k="joint speed" v={fmt((num(vel) * 360) / ratio, 1)} u="deg/s" big />
        <Value k="joint torque est" v={fmt(tMotor * ratio * eff, 2)} u="Nm" big />
      </div>
      <div className="kv num">
        <span>motor torque</span>
        <span>{fmt(tMotor, 3)} Nm (Iq x Kt {fmt(ktv, 4)})</span>
        <span>ratio / eff</span>
        <span>
          {ratio}:1 . {(eff * 100).toFixed(0)} % (profile)
        </span>
        <span>peak joint torque</span>
        <span>{fmt(profile.derived.joint_torque_peak_nm, 1)} Nm at {profile.motor.current_peak_a} A</span>
      </div>
      <span className="muted" style={{ fontSize: 'var(--fs-tick)' }}>
        angle is motor encoder / ratio; absolute joint angle needs the output encoder
      </span>
    </div>
  )
}

/** active alarms with decoded flags; the first alarm since the last clear is marked first-out */
export function ErrorsPanel({ ax }: { ax: number }) {
  const meta = useApp((s) => s.meta)
  const safety = useApp((s) => s.status?.safety)
  const regs = [`error.${ax}`, `motor_error.${ax}`, `enc_error.${ax}`, `ctrl_error.${ax}`, 'sys_error']
  const vals = useAliasLatest(regs, 5)
  const rows = regs
    .map((a, i) => ({ alias: a, path: P(a), value: vals[i] }))
    .filter((r) => r.path && r.value !== undefined && num(r.value) !== 0)
  return (
    <div className="col">
      {rows.length === 0 && <span className="ok-text">no errors on axis{ax}</span>}
      {rows.map((r) => (
        <div key={r.path}>
          <div className="row">
            <Tag level="alarm" blink={!safety?.alarms.find((a) => a.key === r.path)?.acked}>
              {r.path}
            </Tag>
            <span className="num muted">{hex(r.value)}</span>
            {safety?.first_out === r.path && <Tag level="warn">first-out</Tag>}
          </div>
          {decodeFlags(meta, r.path, r.value).map((f) => (
            <div key={f} style={{ paddingLeft: 12 }} title={flagDoc(meta, r.path, f)}>
              <span className="error-text">{f}</span> <span className="muted">{flagDoc(meta, r.path, f).split('\n')[0].slice(0, 110)}</span>
            </div>
          ))}
        </div>
      ))}
      {(safety?.alarms ?? [])
        .filter((a) => !a.key.includes('.error') && a.key !== 'error')
        .map((a) => (
          <div key={a.key} className="row">
            <Tag level={a.level === 'alarm' ? 'alarm' : 'warn'}>{a.key}</Tag>
            <span>{a.msg}</span>
          </div>
        ))}
      <div className="row">
        <Button small onClick={() => act('clear_errors', { axis: ax })}>
          clear errors
        </Button>
        <Button small onClick={() => act('ack', {})}>
          ack all
        </Button>
      </div>
    </div>
  )
}

/** AS5047P link quality and raw counts */
export function EncoderCard({ ax }: { ax: number }) {
  const meta = useApp((s) => s.meta)
  const [spi, abs, cnt, shadow, mode, cpr, cs] = useAliasLatest(
    [`spi_err.${ax}`, `pos_abs.${ax}`, `count_in_cpr.${ax}`, `shadow.${ax}`, `enc_mode.${ax}`, `enc_cpr.${ax}`, `enc_cs.${ax}`],
    10,
  )
  const rate = num(spi)
  const stuck = num(abs) === 16383 ? 'stuck high (MISO floating / CS wrong)' : ''
  return (
    <div className="col">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <Value k="spi error rate" v={fmt(rate, 4)} cls={rate > 0.05 ? 'error-text' : rate > 0.01 ? 'warn-text' : ''} />
        {rate > 0.05 ? <Tag level="alarm">spi fail</Tag> : rate > 0.01 ? <Tag level="warn">noisy</Tag> : <Tag level="quiet">link ok</Tag>}
      </div>
      <Bar value={num(abs)} max={16384} />
      <div className="kv num">
        <span>pos_abs</span>
        <span>
          {fmt(abs)} <span className="error-text">{stuck}</span>
        </span>
        <span>count_in_cpr</span>
        <span>{fmt(cnt)}</span>
        <span>shadow_count</span>
        <span>{fmt(shadow)}</span>
        <span>config</span>
        <span>
          {enumName(meta, P(`enc_mode.${ax}`), mode) ?? fmt(mode)} . cpr {fmt(cpr)} . cs gpio{fmt(cs)}
        </span>
      </div>
    </div>
  )
}

export function PowerCard() {
  const [vbus, ibus, armed, f0, f1] = useAliasLatest(['vbus', 'ibus', 'brake_armed', 'fet_temp.0', 'fet_temp.1'], 5)
  return (
    <div className="vgrid">
      <Value k="vbus" v={fmt(vbus, 2)} u="V" big />
      <Value k="ibus" v={fmt(ibus, 2)} u="A" big />
      <Value k="power" v={fmt(num(vbus) * num(ibus), 1)} u="W" big />
      <Value k="brake" v={armed === undefined ? '--' : armed ? 'armed' : 'not armed'} />
      <Value k="fet0" v={fmt(f0, 1)} u="C" />
      <Value k="fet1" v={fmt(f1, 1)} u="C" />
    </div>
  )
}

export function EventsPanel() {
  const events = useApp((s) => s.events)
  return (
    <div style={{ fontSize: 'var(--fs-tick)' }}>
      {events.length === 0 && <span className="muted">no events</span>}
      {[...events]
        .reverse()
        .slice(0, 80)
        .map((e, i) => (
          <div key={i} className={e.level === 'alarm' ? 'error-text' : e.level === 'warn' ? 'warn-text' : ''}>
            <span className="muted">{time(e.ts)} </span>
            <span className="muted">{e.src} </span>
            {e.msg}
          </div>
        ))}
    </div>
  )
}

/** generic live readout of arbitrary paths */
export function Readout({ paths }: { paths: string[] }) {
  const vals = useLatest(paths, 10)
  return (
    <div className="kv num">
      {paths.map((p, i) => [
        <span key={p + 'k'}>{p}</span>,
        <span key={p + 'v'}>{fmt(vals[i])}</span>,
      ])}
    </div>
  )
}

