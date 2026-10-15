import { act, useAliasLatest, useApp } from '../lib/store'
import { AXIS_STATES } from '../lib/meta'
import { fmt, num } from '../lib/format'

function AxisCell({ ax }: { ax: number }) {
  const [state, err] = useAliasLatest([`state.${ax}`, `error.${ax}`], 8)
  const active = useApp((s) => s.status?.safety.active_axes.includes(ax))
  const raw = state === undefined ? '--' : AXIS_STATES[num(state)] ?? String(state)
  const name = raw.replace('CONTROL_MODE_', '').replace('_CONTROL', '')
  const faulted = num(err) !== 0 && err !== undefined
  return (
    <div className={`cell ${faulted ? 'abnormal-alarm' : ''}`} title={faulted ? 'axis has errors, see alarms' : ''}>
      <span className="k">
        ax{ax}
        {active ? ' · armed' : ''}
      </span>
      <span className="v num">
        {faulted ? '■ ' : ''}
        {name}
      </span>
    </div>
  )
}

/** pinned top bar: link, bus voltage, axis states, sample rate, alarms, DISARM ALL */
export function StatusBar() {
  const status = useApp((s) => s.status)
  const link = useApp((s) => s.link)
  const profile = useApp((s) => s.profile)
  const [vbus] = useAliasLatest(['vbus'], 5)
  const dev = status?.device
  const alarms = status?.safety.alarms ?? []
  const unacked = alarms.filter((a) => !a.acked && a.level === 'alarm').length
  const bus = num(vbus)
  const busBad = profile && Number.isFinite(bus) && (bus < profile.power.bus_min_v || bus > profile.power.bus_max_v)
  const linkText = link !== 'open' ? link : dev?.connected ? (dev.info?.simulated ? 'SIM' : (dev.transport ?? 'USB').toUpperCase()) : 'OFFLINE'
  return (
    <div className="statusbar">
      <div className="cell" style={{ flexShrink: 0 }}>
        <span className="k">vayn</span>
        <span className="v brand">ODRV</span>
      </div>
      <div
        className={`cell ${link !== 'open' || !dev?.connected ? 'abnormal-warn' : ''}`}
        title={dev?.info ? `SN ${dev.info.serial} · FW ${dev.info.fw} · HW ${dev.info.hw}` : dev?.last_error}
      >
        <span className="k">link</span>
        <span className="v num">{linkText}</span>
      </div>
      <div className={`cell ${busBad ? 'abnormal-alarm' : ''}`}>
        <span className="k">vbus</span>
        <span className="v num">{fmt(vbus, 2)} V</span>
      </div>
      <AxisCell ax={0} />
      <AxisCell ax={1} />
      <div className="cell opt">
        <span className="k">rate</span>
        <span className="v num">{dev ? `${dev.rate_achieved.toFixed(0)} Hz` : '--'}</span>
      </div>
      <div
        className={`cell ${unacked ? 'abnormal-alarm' : alarms.length ? 'abnormal-warn' : ''}`}
        onClick={() => useApp.setState({ view: 'alarms' })}
        style={{ cursor: 'pointer' }}
      >
        <span className="k">alarms</span>
        <span className={`v num ${unacked ? 'blink' : ''}`}>{alarms.length ? `${alarms.length}` : '0'}</span>
      </div>
      {status?.recording && (
        <div className="cell">
          <span className="k">rec</span>
          <span className="v">●</span>
        </div>
      )}
      {!!status?.jobs.length && (
        <div className="cell">
          <span className="k">job</span>
          <span className="v">{status.jobs[0]}</span>
        </div>
      )}
      <div className="spacer" />
      <button className="disarm" onClick={() => act('disarm', { reason: 'operator button' })} title="put both axes into IDLE and abort jobs (Esc)">
        disarm<span className="key">esc</span>
      </button>
    </div>
  )
}
