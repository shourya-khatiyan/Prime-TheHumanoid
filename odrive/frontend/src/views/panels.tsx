import { Button, Tag } from '../primitives'
import { LivePlot } from '../components/Plot'
import { act, P, useAliasLatest, useApp, useLatest } from '../lib/store'
import { AXIS_STATES, decodeFlags, enumName, flagDoc } from '../lib/meta'
import { fmt, hex, num, time } from '../lib/format'

/** live position and velocity chart for the selected axis */
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

/** live q-axis current setpoint and measurement chart */
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

/** live dc bus voltage and current chart */
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

/** live mosfet and motor temperature chart */
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

/** axis state, mode badges, current load meter, quick commands, and live telemetry strip */
export function AxisCard({ ax }: { ax: number }) {
  const meta = useApp((s) => s.meta)
  const profile = useApp((s) => s.profile)
  const active = useApp((s) => s.status?.safety.active_axes.includes(ax))
  const [state, err, cm, cal, ready, pos, vel, iq, temp] = useAliasLatest(
    [`state.${ax}`, `error.${ax}`, `ctrl_mode.${ax}`, `motor_cal.${ax}`, `enc_ready.${ax}`, `pos.${ax}`, `vel.${ax}`, `iq.${ax}`, `fet_temp.${ax}`],
    10,
  )
  const faulted = num(err) !== 0 && err !== undefined
  const stateName = AXIS_STATES[num(state)] ?? '--'
  const shortState = stateName.replace('CONTROL_MODE_', '').replace('_CONTROL', '')
  const ctrlName = (enumName(meta, P(`ctrl_mode.${ax}`), cm) ?? fmt(cm)).replace('CONTROL_MODE_', '')
  const peakA = profile?.motor.current_peak_a ?? 22

  return (
    <div className="inst-card">
      <div className="inst-hero-row">
        <div className="hero-stat">
          <span className="lbl">STATE // {ctrlName}</span>
          <span className={`num-lg num ${faulted ? 'error-text' : active ? 'ok-text' : ''}`}>{shortState}</span>
        </div>
        <div className="row" style={{ gap: 4 }}>
          <Button small kind={num(state) === 1 ? 'on' : ''} onClick={() => act('write', { path: P(`req_state.${ax}`), value: 1 })}>
            idle
          </Button>
          <Button small kind={num(state) === 8 ? 'primary' : ''} onClick={() => act('write', { path: P(`req_state.${ax}`), value: 8 })}>
            loop
          </Button>
        </div>
      </div>

      <SegMeter
        label={`CURRENT LOAD · MOT ${cal ? 'CAL' : 'UNCAL'} · ENC ${ready ? 'RDY' : 'UNRDY'}`}
        rightText={`${fmt(Math.abs(num(iq)), 2)} / ${peakA} A`}
        value={num(iq)}
        max={peakA}
      />

      <div className="stat-strip num">
        <div className="cell">
          <span className="k">pos</span>
          <span className="v">
            {fmt(pos, 3)}
            <span className="u">trn</span>
          </span>
        </div>
        <div className="cell">
          <span className="k">vel</span>
          <span className="v">
            {fmt(vel, 2)}
            <span className="u">t/s</span>
          </span>
        </div>
        <div className="cell">
          <span className="k">iq</span>
          <span className="v">
            {fmt(iq, 2)}
            <span className="u">A</span>
          </span>
        </div>
        <div className="cell">
          <span className="k">fet</span>
          <span className="v">
            {fmt(temp, 1)}
            <span className="u">°C</span>
          </span>
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
  const peakNm = Number(profile.derived.joint_torque_peak_nm || 35)

  return (
    <div className="inst-card">
      <div className="inst-hero-row">
        <div className="hero-stat">
          <span className="lbl">JOINT ANGLE ({ratio}:1)</span>
          <span className="num-lg num">
            {fmt(angleDeg, 2)}
            <span className="unit">deg</span>
          </span>
        </div>
        <div className="hero-stat" style={{ textAlign: 'right' }}>
          <span className="lbl">EST. TORQUE</span>
          <span className="num-lg num">
            {fmt(tJoint, 2)}
            <span className="unit">Nm</span>
          </span>
        </div>
      </div>

      <SegMeter label="TORQUE ENVELOPE" rightText={`${fmt(tJoint !== undefined ? Math.abs(tJoint) : undefined, 1)} / ${fmt(peakNm, 1)} Nm`} value={tJoint ?? 0} max={peakNm} />

      <div className="stat-strip num">
        <div className="cell">
          <span className="k">joint vel</span>
          <span className="v">
            {fmt(speedDeg, 1)}
            <span className="u">°/s</span>
          </span>
        </div>
        <div className="cell">
          <span className="k">motor trq</span>
          <span className="v">
            {fmt(tMotor, 3)}
            <span className="u">Nm</span>
          </span>
        </div>
        <div className="cell">
          <span className="k">eff / kt</span>
          <span className="v">
            {(eff * 100).toFixed(0)}%<span className="u">{fmt(ktv, 3)}</span>
          </span>
        </div>
      </div>
    </div>
  )
}

/** AS5047P SPI absolute encoder radar dial, link quality, and raw counts */
export function EncoderCard({ ax }: { ax: number }) {
  const meta = useApp((s) => s.meta)
  const [spi, abs, cnt, shadow, mode, cpr, cs] = useAliasLatest(
    [`spi_err.${ax}`, `pos_abs.${ax}`, `count_in_cpr.${ax}`, `shadow.${ax}`, `enc_mode.${ax}`, `enc_cpr.${ax}`, `enc_cs.${ax}`],
    10,
  )
  const rate = num(spi)
  const absCount = num(abs)
  const cprVal = num(cpr) > 0 ? num(cpr) : 16384
  const mechDeg = Number.isFinite(absCount) ? (absCount / 16384) * 360 : 0
  const mechRad = (mechDeg * Math.PI) / 180
  const elecRad = mechRad * 20
  const stuckHigh = absCount === 16383
  const fault = rate > 0.05 || stuckHigh
  const linkQuality = Number.isFinite(rate) ? Math.max(0, (1 - Math.min(1, rate)) * 100) : 0
  const modeStr = (enumName(meta, P(`enc_mode.${ax}`), mode) ?? fmt(mode)).replace('MODE_', '')

  // concentric dotted polar radar points
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
        <svg width="82" height="82" viewBox="0 0 104 104" style={{ flexShrink: 0 }}>
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

        <div className="col" style={{ flex: 1, minWidth: 0, gap: 6 }}>
          <div className="inst-hero-row">
            <div className="hero-stat">
              <span className="lbl">MECH ANGLE</span>
              <span className="num-lg num">
                {fmt(mechDeg, 1)}
                <span className="unit">°</span>
              </span>
            </div>
            {fault ? <Tag level="alarm">spi fail</Tag> : rate > 0.01 ? <Tag level="warn">noisy</Tag> : <Tag level="quiet">spi ok</Tag>}
          </div>
          <div className="chip-row num">
            <span className="tech-chip on">{modeStr}</span>
            <span className={`tech-chip ${ num(cs) === 4 ? 'on' : 'warn' }`}>CS GPIO{fmt(cs, 0)}</span>
            <span className={`tech-chip ${ cprVal === 16384 ? 'on' : 'warn' }`}>CPR {fmt(cpr, 0)}</span>
          </div>
          {stuckHigh && <span className="error-text" style={{ fontSize: 'var(--fs-micro)' }}>MISO HIGH (16383): CHECK CS GPIO4</span>}
        </div>
      </div>

      <div className="stat-strip num">
        <div className="cell">
          <span className="k">pos_abs</span>
          <span className="v">{fmt(abs, 0)}</span>
        </div>
        <div className="cell">
          <span className="k">in_cpr</span>
          <span className="v">{fmt(cnt, 0)}</span>
        </div>
        <div className="cell">
          <span className="k">shadow</span>
          <span className="v">{fmt(shadow, 0)}</span>
        </div>
        <div className="cell">
          <span className="k">spi link</span>
          <span className={`v ${fault ? 'error-text' : ''}`}>
            {linkQuality.toFixed(1)}
            <span className="u">%</span>
          </span>
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
  const maxV = profile?.power.bus_max_v ?? 26.5
  const warnTemp = profile?.thermal.fet_warn_c ?? 70
  const abortTemp = profile?.thermal.fet_abort_c ?? 85

  const pwr = Number.isFinite(v * i) ? v * i : undefined

  return (
    <div className="inst-card">
      <div className="inst-hero-row">
        <div className="hero-stat">
          <span className="lbl">DC BUS VOLTAGE</span>
          <span className="num-lg num">
            {fmt(vbus, 2)}
            <span className="unit">V</span>
          </span>
        </div>
        <div className="hero-stat" style={{ textAlign: 'right' }}>
          <span className="lbl">BUS POWER</span>
          <span className="num-lg num">
            {fmt(pwr, 1)}
            <span className="unit">W</span>
          </span>
        </div>
      </div>

      <SegMeter label="FET0 THERMAL MARGIN" rightText={`${fmt(f0, 1)} / ${abortTemp} °C`} value={num(f0)} max={abortTemp} warnAt={warnTemp / abortTemp} alarmAt={0.95} />

      <div className="stat-strip num">
        <div className="cell">
          <span className="k">ibus</span>
          <span className="v">
            {fmt(ibus, 2)}
            <span className="u">A</span>
          </span>
        </div>
        <div className="cell">
          <span className="k">brake</span>
          <span className={`v ${armed ? '' : 'warn-text'}`}>{armed === undefined ? '--' : armed ? 'ARMED' : 'OFF'}</span>
        </div>
        <div className="cell">
          <span className="k">fet 0 / 1</span>
          <span className="v">
            {fmt(f0, 1)} / {fmt(f1, 1)}
            <span className="u">°C</span>
          </span>
        </div>
        <div className="cell">
          <span className="k">bus max</span>
          <span className="v">
            {maxV}
            <span className="u">V</span>
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
    { label: 'MOTOR', alias: `motor_error.${ax}` },
    { label: 'ENCODER', alias: `enc_error.${ax}` },
    { label: 'CTRL', alias: `ctrl_error.${ax}` },
    { label: 'SYSTEM', alias: 'sys_error' },
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
              {r.label} {bad ? hex(vals[i]) : 'OK'}
            </span>
          )
        })}
      </div>

      <div className="col" style={{ flex: 1, overflowY: 'auto', gap: 6 }}>
        {activeRows.length === 0 && extraAlarms.length === 0 && (
          <div className="ok-text num" style={{ fontSize: 'var(--fs-tick)', padding: '6px 0' }}>
            ● ALL SUBSYSTEM REGISTERS NOMINAL ON AXIS {ax}
          </div>
        )}
        {activeRows.map((r) => (
          <div key={r.path} style={{ borderLeft: '2px solid var(--error)', paddingLeft: 8 }}>
            <div className="row" style={{ gap: 6 }}>
              <Tag level="alarm" blink={!safety?.alarms.find((a) => a.key === r.path)?.acked}>
                {r.label}
              </Tag>
              <span className="num muted">{hex(r.value)}</span>
              {safety?.first_out === r.path && <Tag level="warn">first-out</Tag>}
            </div>
            {decodeFlags(meta, r.path, r.value).map((f) => (
              <div key={f} className="num" style={{ fontSize: 'var(--fs-tick)', marginTop: 2 }} title={flagDoc(meta, r.path, f)}>
                <span className="error-text">{f}</span>{' '}
                <span className="muted">{flagDoc(meta, r.path, f).split('\n')[0].slice(0, 92)}</span>
              </div>
            ))}
          </div>
        ))}
        {extraAlarms.map((a) => (
          <div key={a.key} className="row" style={{ fontSize: 'var(--fs-tick)' }}>
            <Tag level={a.level === 'alarm' ? 'alarm' : 'warn'}>{a.key}</Tag>
            <span>{a.msg}</span>
          </div>
        ))}
      </div>

      <div className="row" style={{ borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 'auto' }}>
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

/** reverse-chronological event stream panel */
export function EventsPanel() {
  const events = useApp((s) => s.events)
  return (
    <div className="col num" style={{ fontSize: 'var(--fs-tick)', gap: 4 }}>
      {events.length === 0 && <span className="muted">NO EVENTS RECORDED</span>}
      {[...events]
        .reverse()
        .slice(0, 80)
        .map((e, i) => (
          <div key={i} className={e.level === 'alarm' ? 'error-text' : e.level === 'warn' ? 'warn-text' : ''} style={{ borderBottom: '1px solid var(--grid-major)', paddingBottom: 3 }}>
            <span className="muted">{time(e.ts)} </span>
            <span className="dim">[{e.src}] </span>
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
