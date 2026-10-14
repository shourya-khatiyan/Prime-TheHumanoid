import { useEffect, useMemo, useState } from 'react'
import { Button, Panel } from '../primitives'
import { StaticPlot } from '../components/Plot'
import { act, P, useApp } from '../lib/store'
import { rpc } from '../lib/rpc'
import { date } from '../lib/format'

const DEFAULT_CHANNELS = ['pos', 'vel', 'iq', 'iq_set', 'pos_set', 'vel_set', 'torque_set', 'shadow', 'count_in_cpr']

/** record any set of channels at the telemetry rate, replay them, export csv / parquet */
export function Recordings() {
  const ax = useApp((s) => s.axis)
  const recording = useApp((s) => s.status?.recording)
  const rate = useApp((s) => s.status?.device.rate_achieved)
  const [name, setName] = useState('session')
  const [extra, setExtra] = useState<string[]>(DEFAULT_CHANNELS.slice(0, 5))
  const [list, setList] = useState<any[]>([])
  const [loaded, setLoaded] = useState<{ meta: any; cols: Record<string, (number | null)[]> } | null>(null)
  const [show, setShow] = useState<string[]>([])
  const refresh = () => act<any[]>('rec_list', {}, true).then(setList).catch(() => undefined)
  useEffect(() => {
    refresh()
  }, [recording])

  const start = () => act('rec_start', { name, paths: extra.map((a) => P(`${a}.${ax}`)).filter(Boolean) })
  const stop = async () => {
    const r = await act<any>('rec_stop')
    if (r) open(r.id)
    refresh()
  }
  const open = async (id: string) => {
    const d = await act<any>('rec_load', { id })
    setLoaded(d)
    const numeric = Object.keys(d.cols).filter((c) => c !== 't')
    setShow(numeric.filter((c) => /pos_estimate|vel_estimate|Iq_measured/.test(c)).slice(0, 4))
  }
  const x = useMemo(() => {
    const t = (loaded?.cols.t ?? []) as number[]
    return t.map((v) => v - (t[0] ?? 0))
  }, [loaded])

  return (
    <div>
      <div className="view-head">
        <h1>recordings</h1>
        <span className="sub">records the full telemetry stream (~{Math.round(rate ?? 0)} Hz) plus chosen channels</span>
      </div>
      <div className="grid2" style={{ gridTemplateColumns: '1fr 2fr' }}>
        <div className="col">
          <Panel title="record">
            <div className="row">
              <input value={name} onChange={(e) => setName(e.target.value)} disabled={recording} />
              {recording ? (
                <Button kind="on" onClick={stop}>
                  stop
                </Button>
              ) : (
                <Button kind="primary" onClick={start}>
                  start
                </Button>
              )}
            </div>
            <div className="row" style={{ marginTop: 6 }}>
              {DEFAULT_CHANNELS.map((c) => (
                <label key={c} className="dim">
                  <input type="checkbox" checked={extra.includes(c)} disabled={recording} onChange={(e) => setExtra(e.target.checked ? [...extra, c] : extra.filter((x) => x !== c))} /> {c}
                </label>
              ))}
            </div>
            <span className="muted">axis{ax} channels; the safety base set (vbus, states, errors, temps) is always included</span>
          </Panel>
          <Panel title="saved">
            <table>
              <tbody>
                {list.map((r) => (
                  <tr key={r.id}>
                    <td style={{ cursor: 'pointer' }} onClick={() => open(r.id)}>
                      {r.name}
                    </td>
                    <td className="muted num">{date(r.started)}</td>
                    <td className="num muted">{r.samples}</td>
                    <td className="row">
                      <a href={`/api/recording/${r.id}.csv?token=${rpc.token}`}>csv</a>
                      <a href={`/api/recording/${r.id}.parquet?token=${rpc.token}`}>parquet</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>
        <Panel title={loaded ? `replay . ${loaded.meta.id} . drag to zoom, double-click to reset` : 'replay'} flush>
          {loaded ? (
            <div className="col" style={{ padding: 8, height: '100%' }}>
              <div className="row">
                {Object.keys(loaded.cols)
                  .filter((c) => c !== 't')
                  .map((c) => (
                    <label key={c} className="dim" style={{ fontSize: 'var(--fs-tick)' }}>
                      <input type="checkbox" checked={show.includes(c)} onChange={(e) => setShow(e.target.checked ? [...show, c].slice(-6) : show.filter((s) => s !== c))} /> {c}
                    </label>
                  ))}
              </div>
              <div className="h-plot-lg">
                <StaticPlot x={x} ys={show.map((c) => loaded.cols[c])} labels={show} scales={show.map((c) => c.split('.').slice(-1)[0])} />
              </div>
            </div>
          ) : (
            <div style={{ padding: 8 }} className="muted">
              open a recording
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
