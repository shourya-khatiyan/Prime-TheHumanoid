import { Button, Tag } from '../primitives'
import { LivePlot } from '../components/Plot'
import { act, P, startJob, useAliasLatest, useApp, useLatest } from '../lib/store'
import { AXIS_STATES, decodeFlags, enumName, explainFlag } from '../lib/meta'
import { fmt, hex, num, time } from '../lib/format'
import { applyErrorFix } from './Alarms'

/** live position and velocity chart for the selected axis */
export function MotionPlot({ ax, windowS, paused }: { ax: number; windowS: number; paused?: boolean }) {
  return (
    <LivePlot
      windowS={windowS}
      paused={paused}
      series={[
        { path: P(`pos.${ax}`), label: 'pos', scale: 'turn' },
        { path: P(`pos_set.${ax}`), label: 'set', scale: 'turn' },
        { path: P(`vel.${ax}`), label: 'vel', scale: 'turn/s' },
      ]}
    />
  )
}

/** live q-axis current setpoint and measurement chart */
export function CurrentPlot({ ax, windowS, paused }: { ax: number; windowS: number; paused?: boolean }) {
  return (
    <LivePlot
      windowS={windowS}
      paused={paused}
      series={[
        { path: P(`iq_set.${ax}`), label: 'set', scale: 'A' },
        { path: P(`iq.${ax}`), label: 'iq', scale: 'A' },
      ]}
    />
  )
}

/** live dc bus voltage and current chart */
export function PowerPlot({ windowS, paused }: { windowS: number; paused?: boolean }) {
  return (
    <LivePlot
      windowS={windowS}
      paused={paused}
      series={[
        { path: P('vbus'), label: 'vbus', scale: 'V' },
        { path: P('ibus'), label: 'ibus', scale: 'A' },
      ]}
    />
  )
}

/** live mosfet and motor temperature chart */
export function ThermalPlot({ ax, windowS, paused }: { ax: number; windowS: number; paused?: boolean }) {
  return (
    <LivePlot
      windowS={windowS}
      paused={paused}
      series={[
        { path: P(`fet_temp.${ax}`), label: 'fet', scale: 'C' },
        { path: P(`motor_temp.${ax}`), label: 'mot', scale: 'C' },
      ]}
    />
  )
}

/** discrete 24-segment tick meter with warning and alarm thresholds */
function SegMeter({
  label,
  rightText,
  value,
  max,
  warnAt = 0.75,
  alarmAt = 0.9,
}: {
  label: string
  rightText: string
  value: number
  max: number
  warnAt?: number
  alarmAt?: number
}) {
  const count = 24
  const ratio = Math.max(0, Math.min(1, Number.isFinite(value) && max > 0 ? Math.abs(value) / max : 0))
  const lit = Math.round(ratio * count)
  return (
    <div className="seg-row">
      <div className="seg-head num">
        <span>{label}</span>
        <span>{rightText}</span>
      </div>
      <div className="seg-track">
        {Array.from({ length: count }, (_, i) => {
          const frac = (i + 1) / count
          const active = i < lit
          const cls = !active ? '' : frac >= alarmAt ? 'alarm' : frac >= warnAt ? 'warn' : 'on'
          return <div key={i} className={`seg-tick ${cls}`} />
        })}
      </div>
    </div>
  )
}

/** axis state, load bar, quick commands, and live telemetry strip */
export function AxisCard({ ax }: { ax: number }) {
  const meta = useApp((s) => s.meta)
  const profile = useApp((s) => s.profile)
  const active = useApp((s) => s.status?.safety.active_axes.includes(ax))
  const [state, err, cm, pos, vel, iq, temp] = useAliasLatest(
    [`state.${ax}`, `error.${ax}`, `ctrl_mode.${ax}`, `pos.${ax}`, `vel.${ax}`, `iq.${ax}`, `fet_temp.${ax}`],
    10,
  )
  const faulted = num(err) !== 0 && err !== undefined
  const stateName = AXIS_STATES[num(state)] ?? '--'
  const shortState = stateName.replace('CONTROL_MODE_', '').replace('_CONTROL', '')
  const ctrlName = (enumName(meta, P(`ctrl_mode.${ax}`), cm) ?? fmt(cm)).replace('CONTROL_MODE_', '').replace('_CONTROL', '')
  const peakA = profile?.motor.current_peak_a ?? 22

  return (
    <div className="inst-card">
      <div className="inst-hero-row">
        <div className="hero-stat">
          <span className="lbl">{ctrlName} MODE</span>
          <span className={`num-lg num ${faulted ? 'error-text' : active ? 'ok-text' : ''}`}>{shortState}</span>
        </div>
        <div className="row" style={{ gap: 4 }}>
          <Button small kind={num(state) === 1 ? 'on' : ''} onClick={() => act('write', { path: P(`req_state.${ax}`), value: 1 })}>
            idle
          </Button>
          <Button
            small
            kind={num(state) === 9 ? 'on' : ''}
            title="Spin motor open-loop (2 turns @ 0.5 t/s, 3 A) without encoder"
            onClick={() => startJob('open_loop', { axis: ax, current_a: 3.0, vel_turns_s: 0.5, turns: 2.0 }).catch(() => undefined)}
          >
            open
          </Button>
          <Button small kind={num(state) === 8 ? 'primary' : ''} onClick={() => act('write', { path: P(`req_state.${ax}`), value: 8 })}>
            loop
          </Button>
        </div>
      </div>

      <SegMeter label="LOAD" rightText={`${fmt(Math.abs(num(iq)), 1)} / ${peakA} A`} value={num(iq)} max={peakA} />

      <div className="stat-strip num">
        <div className="cell">
          <span className="k">pos</span>
          <span className="v">{fmt(pos, 2)}</span>
        </div>
        <div className="cell">
          <span className="k">vel</span>
          <span className="v">{fmt(vel, 2)}</span>
        </div>
        <div className="cell">
          <span className="k">iq</span>
          <span className="v">{fmt(iq, 2)}A</span>
        </div>
        <div className="cell">
          <span className="k">fet</span>
          <span className="v">{fmt(temp, 1)}°</span>
        </div>
      </div>
    </div>
  )
}

/** output joint angle, velocity, and torque converted through the actuator gear ratio */
export function JointCard({ ax }: { ax: number }) {
  const profile = useApp((s) => s.profile)
  const [pos, vel, iq, kt] = useAliasLatest([`pos.${ax}`, `vel.${ax}`, `iq.${ax}`, `kt.${ax}`], 10)
  if (!profile) return <span className="muted">NO DATA</span>
  const ratio = Number(profile.gear.ratio)
  const eff = Number(profile.gear.efficiency)
  const ktv = Number.isFinite(num(kt)) && num(kt) > 0 ? num(kt) : profile.derived.kt_nm_per_a
  const tMotor = Number.isFinite(num(iq)) ? num(iq) * ktv : undefined
  const tJoint = tMotor !== undefined ? tMotor * ratio * eff : undefined
  const angleDeg = Number.isFinite(num(pos)) ? (num(pos) * 360) / ratio : undefined
  const speedDeg = Number.isFinite(num(vel)) ? (num(vel) * 360) / ratio : undefined
  const peakNm = Number(profile.derived.joint_torque_peak_nm || 50)

  return (
    <div className="inst-card">
      <div className="inst-hero-row">
        <div className="hero-stat">
          <span className="lbl">ANGLE</span>
          <span className="num-lg num">
            {fmt(angleDeg, 1)}
            <span className="unit">°</span>
          </span>
        </div>
        <div className="hero-stat" style={{ textAlign: 'right' }}>
          <span className="lbl">TORQUE</span>
          <span className="num-lg num">
            {fmt(tJoint, 2)}
            <span className="unit">Nm</span>
          </span>
        </div>
      </div>

      <SegMeter label="ENVELOPE" rightText={`${fmt(tJoint !== undefined ? Math.abs(tJoint) : undefined, 1)} / ${fmt(peakNm, 0)} Nm`} value={tJoint ?? 0} max={peakNm} />

      <div className="stat-strip num">
        <div className="cell">
          <span className="k">vel</span>
          <span className="v">{fmt(speedDeg, 1)}°/s</span>
        </div>
        <div className="cell">
          <span className="k">motor</span>
          <span className="v">{fmt(tMotor, 2)}Nm</span>
        </div>
        <div className="cell">
          <span className="k">ratio</span>
          <span className="v">{ratio}:1</span>
        </div>
      </div>
    </div>
  )
}

/** encoder radar dial (supports both INCREMENTAL A/B/Z on J4 and SPI_ABS_AMS on J3) */
export function EncoderCard({ ax }: { ax: number }) {
  const [spi, abs, cnt, shadow, mode, cpr, cs, encErr, hall] = useAliasLatest(
    [`spi_err.${ax}`, `pos_abs.${ax}`, `count_in_cpr.${ax}`, `shadow.${ax}`, `enc_mode.${ax}`, `enc_cpr.${ax}`, `enc_cs.${ax}`, `enc_error.${ax}`, `hall_state.${ax}`],
    10,
  )
  const rate = num(spi)
  const absCount = num(abs)
  const inCpr = num(cnt)
  const cprVal = num(cpr) > 0 ? num(cpr) : 4000
  const isSpi = num(mode) >= 256
  const rawCount = isSpi ? absCount : ((inCpr % cprVal) + cprVal) % cprVal
  const denom = isSpi ? 16384 : cprVal
  const mechDeg = Number.isFinite(rawCount) && denom > 0 ? (rawCount / denom) * 360 : 0
  const mechRad = (mechDeg * Math.PI) / 180
  const elecRad = mechRad * 20
  const stuckHigh = isSpi && absCount === 16383
  const hasErr = num(encErr) !== 0 && encErr !== undefined
  const fault = hasErr || (isSpi && (rate > 0.05 || stuckHigh))
  const linkQuality = isSpi && Number.isFinite(rate) ? Math.max(0, (1 - Math.min(1, rate)) * 100) : 100
  const h = Number.isFinite(num(hall)) ? Math.trunc(num(hall)) : 0
  const abzPins = `${h & 1}/${(h >> 1) & 1}/${(h >> 2) & 1}`

  const outerDots = Array.from({ length: 32 }, (_, i) => {
    const a = (i / 32) * Math.PI * 2 - Math.PI * 0.5
    return { x: 52 + Math.cos(a) * 42, y: 52 + Math.sin(a) * 42, major: i % 8 === 0 }
  })
  const innerDots = Array.from({ length: 20 }, (_, i) => {
    const a = (i / 20) * Math.PI * 2 - Math.PI * 0.5
    return { x: 52 + Math.cos(a) * 26, y: 52 + Math.sin(a) * 26 }
  })
  const nx = 52 + Math.cos(mechRad - Math.PI * 0.5) * 40
  const ny = 52 + Math.sin(mechRad - Math.PI * 0.5) * 40
  const ex = 52 + Math.cos(elecRad - Math.PI * 0.5) * 24
  const ey = 52 + Math.sin(elecRad - Math.PI * 0.5) * 24

  return (
    <div className="inst-card">
      <div className="row" style={{ gap: 12, alignItems: 'center', flexWrap: 'nowrap' }}>
        <svg width="74" height="74" viewBox="0 0 104 104" style={{ flexShrink: 0 }}>
          {outerDots.map((d, i) => (
            <circle key={i} cx={d.x} cy={d.y} r={d.major ? 1.8 : 1.1} fill={fault ? '#ff5a4f' : d.major ? '#3df57a' : '#456b53'} />
          ))}
          {innerDots.map((d, i) => (
            <circle key={i} cx={d.x} cy={d.y} r={1} fill="#335040" />
          ))}
          <line x1="52" y1="52" x2={ex} y2={ey} stroke="#59c8ff" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="52" y1="52" x2={nx} y2={ny} stroke={fault ? '#ff5a4f' : '#3df57a'} strokeWidth="2" />
          <circle cx={nx} cy={ny} r="3" fill={fault ? '#ff5a4f' : '#3df57a'} />
          <circle cx="52" cy="52" r="3" fill={fault ? '#ff5a4f' : '#3df57a'} />
        </svg>

        <div className="col" style={{ flex: 1, minWidth: 0, gap: 4 }}>
          <div className="inst-hero-row">
            <div className="hero-stat">
              <span className="lbl">SHAFT</span>
              <span className="num-lg num">
                {fmt(mechDeg, 1)}
                <span className="unit">°</span>
              </span>
            </div>
            {fault ? <Tag level="alarm">fail</Tag> : <Tag level="quiet">{isSpi ? 'spi ok' : 'abz ok'}</Tag>}
          </div>
          <span className="muted num" style={{ fontSize: '8.5px', letterSpacing: '0.08em' }}>
            {isSpi ? `SPI CS GPIO${fmt(cs, 0)} · CPR ${fmt(cpr, 0)}` : `J4 M0 A/B/Z · CPR ${fmt(cpr, 0)}`}
          </span>
        </div>
      </div>

      <div className="stat-strip num">
        <div className="cell">
          <span className="k">{isSpi ? 'abs' : 'shadow'}</span>
          <span className="v">{fmt(isSpi ? abs : shadow, 0)}</span>
        </div>
        <div className="cell">
          <span className="k">cnt</span>
          <span className="v">{fmt(cnt, 0)}</span>
        </div>
        <div className="cell">
          <span className="k">{isSpi ? 'spi' : 'a/b/z'}</span>
          <span className={`v ${fault ? 'error-text' : ''}`}>{isSpi ? `${linkQuality.toFixed(0)}%` : abzPins}</span>
        </div>
      </div>
    </div>
  )
}

/** dc bus voltage, current, power, brake resistor state, and mosfet temperatures */
export function PowerCard() {
  const profile = useApp((s) => s.profile)
  const [vbus, ibus, armed, f0, f1] = useAliasLatest(['vbus', 'ibus', 'brake_armed', 'fet_temp.0', 'fet_temp.1'], 5)
  const v = num(vbus)
  const i = num(ibus)
  const warnTemp = profile?.thermal.fet_warn_c ?? 70
  const abortTemp = profile?.thermal.fet_abort_c ?? 85
  const pwr = Number.isFinite(v * i) ? v * i : undefined

  return (
    <div className="inst-card">
      <div className="inst-hero-row">
        <div className="hero-stat">
          <span className="lbl">VBUS</span>
          <span className="num-lg num">
            {fmt(vbus, 2)}
            <span className="unit">V</span>
          </span>
        </div>
        <div className="hero-stat" style={{ textAlign: 'right' }}>
          <span className="lbl">POWER</span>
          <span className="num-lg num">
            {fmt(pwr, 1)}
            <span className="unit">W</span>
          </span>
        </div>
      </div>

      <SegMeter label="THERMAL" rightText={`${fmt(f0, 1)} / ${abortTemp} °C`} value={num(f0)} max={abortTemp} warnAt={warnTemp / abortTemp} alarmAt={0.95} />

      <div className="stat-strip num">
        <div className="cell">
          <span className="k">ibus</span>
          <span className="v">{fmt(ibus, 2)}A</span>
        </div>
        <div className="cell">
          <span className="k">brake</span>
          <span className={`v ${armed ? '' : 'warn-text'}`}>{armed === undefined ? '--' : armed ? 'OK' : 'OFF'}</span>
        </div>
        <div className="cell">
          <span className="k">fet 0/1</span>
          <span className="v">
            {fmt(f0, 0)}/{fmt(f1, 0)}°
          </span>
        </div>
      </div>
    </div>
  )
}

/** active subsystem fault matrix with decoded error flags and first-out marker */
export function ErrorsPanel({ ax }: { ax: number }) {
  const meta = useApp((s) => s.meta)
  const safety = useApp((s) => s.status?.safety)
  const regs = [
    { label: 'AXIS', alias: `error.${ax}` },
    { label: 'MOT', alias: `motor_error.${ax}` },
    { label: 'ENC', alias: `enc_error.${ax}` },
    { label: 'CTRL', alias: `ctrl_error.${ax}` },
    { label: 'SYS', alias: 'sys_error' },
  ]
  const vals = useAliasLatest(
    regs.map((r) => r.alias),
    5,
  )
  const activeRows = regs
    .map((r, i) => ({ ...r, path: P(r.alias), value: vals[i] }))
    .filter((r) => r.path && r.value !== undefined && num(r.value) !== 0)
  const extraAlarms = (safety?.alarms ?? []).filter((a) => !a.key.includes('.error') && a.key !== 'error')

  return (
    <div className="inst-card">
      <div className="chip-row num">
        {regs.map((r, i) => {
          const bad = vals[i] !== undefined && num(vals[i]) !== 0
          return (
            <span key={r.label} className={`tech-chip ${bad ? 'alarm' : 'on'}`}>
              {bad ? '■ ' : '● '}
              {r.label}
            </span>
          )
        })}
      </div>

      <div className="col" style={{ flex: 1, overflowY: 'auto', gap: 4 }}>
        {activeRows.length === 0 && extraAlarms.length === 0 && (
          <div className="ok-text num" style={{ fontSize: 'var(--fs-micro)', padding: '4px 0' }}>
            ● NOMINAL
          </div>
        )}
        {activeRows.map((r) => (
          <div key={r.path} style={{ borderLeft: '2px solid var(--error)', paddingLeft: 6 }}>
            <div className="row" style={{ gap: 6 }}>
              <span className="error-text num" style={{ fontSize: 'var(--fs-micro)', fontWeight: 600 }}>
                {r.label} {hex(r.value)}
              </span>
              {safety?.first_out === r.path && <Tag level="warn">1st</Tag>}
            </div>
            <div className="col" style={{ gap: 4, marginTop: 2 }}>
              {decodeFlags(meta, r.path, r.value).map((f) => {
                const g = explainFlag(meta, r.path, f)
                return (
                  <div key={f} style={{ fontSize: '9.5px', lineHeight: 1.35 }} title={`${g.summary}\nWHY: ${g.why}\nFIX: ${g.fix}`}>
                    <div>
                      <span className="error-text num" style={{ fontWeight: 600 }}>
                        {f}
                      </span>{' '}
                      <span className="muted">— {g.fix}</span>
                    </div>
                    {g.fixes && g.fixes.length > 0 && (
                      <div className="row" style={{ gap: 4, marginTop: 2 }}>
                        {g.fixes.map((fx) => (
                          <Button key={fx.label} small kind="primary" onClick={() => applyErrorFix(fx, ax).catch(() => undefined)}>
                            {fx.label}
                          </Button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
        {extraAlarms.map((a) => (
          <div key={a.key} className="row" style={{ fontSize: '9px' }}>
            <Tag level={a.level === 'alarm' ? 'alarm' : 'warn'}>{a.key}</Tag>
            <span className="muted">{a.msg}</span>
          </div>
        ))}
      </div>

      <div className="row" style={{ borderTop: '1px solid var(--border)', paddingTop: 6, marginTop: 'auto' }}>
        <Button small onClick={() => act('clear_errors', { axis: ax })}>
          clear
        </Button>
        <Button small onClick={() => act('ack', {})}>
          ack
        </Button>
      </div>
    </div>
  )
}

/** reverse-chronological event stream panel */
export function EventsPanel() {
  const events = useApp((s) => s.events)
  return (
    <div className="col num" style={{ fontSize: '9.5px', gap: 3 }}>
      {events.length === 0 && <span className="muted">NO EVENTS</span>}
      {[...events]
        .reverse()
        .slice(0, 60)
        .map((e, i) => (
          <div key={i} className={e.level === 'alarm' ? 'error-text' : e.level === 'warn' ? 'warn-text' : ''} style={{ borderBottom: '1px solid var(--grid-major)', paddingBottom: 2 }}>
            <span className="muted">{time(e.ts)} </span>
            {e.msg}
          </div>
        ))}
    </div>
  )
}

/** generic live readout of arbitrary device property paths */
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
