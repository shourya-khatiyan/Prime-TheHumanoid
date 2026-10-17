import { useEffect, useState } from 'react'
import { Button, Panel, Tabs, Tag } from '../primitives'
import { act, say, startJob, useApp } from '../lib/store'
import { date, fmt, time } from '../lib/format'
import { explainFlag, type ErrorGuide } from '../lib/meta'
import { EventsPanel } from './panels'

/** execute a one-click resolution action from an error guide and clear device errors */
export async function applyErrorFix(fix: NonNullable<ErrorGuide['fixes']>[number], axis: number) {
  if (fix.kind === 'write' && fix.path) {
    const path = fix.path.replace(/^axis\d\./, `axis${axis}.`)
    await act('write', { path, value: fix.value })
    await act('clear_errors', { axis })
    say(`applied ${path} = ${fix.value} and cleared errors`)
  } else if (fix.kind === 'job' && fix.job) {
    if (fix.job === 'calibrate') {
      await act('write', { path: `axis${axis}.encoder.config.calib_range`, value: 0.15 }).catch(() => undefined)
    }
    await startJob(fix.job, { axis, ...(fix.params ?? {}) })
  } else if (fix.kind === 'clear') {
    await act('clear_errors', { axis })
  }
}

/** alarms (ack, shelve with expiry, first-out), detailed root-cause + fix guide, event log and audit trail */
export function Alarms() {
  const safety = useApp((s) => s.status?.safety)
  const meta = useApp((s) => s.meta)
  const ax = useApp((s) => s.axis)
  const [tab, setTab] = useState('alarms')
  const [audit, setAudit] = useState<any[]>([])
  const [kind, setKind] = useState('')
  useEffect(() => {
    if (tab === 'audit') act<any[]>('audit', { limit: 500, kind: kind || undefined }, true).then(setAudit).catch(() => undefined)
  }, [tab, kind])
  const alarms = safety?.alarms ?? []
  return (
    <div>
      <div className="view-head">
        <h1>alarms . events . audit</h1>
        <span className="sub">{alarms.length} active . first-out = first alarm since the last clear</span>
        <div className="row" style={{ marginLeft: 'auto' }}>
          <Button small onClick={() => act('ack', {})}>
            ack all
          </Button>
          <Button small kind="primary" onClick={() => act('clear_errors', {})}>
            clear device errors
          </Button>
        </div>
      </div>
      <Tabs
        tabs={[
          ['alarms', 'alarms'],
          ['events', 'events'],
          ['audit', 'audit log'],
        ]}
        value={tab}
        onChange={setTab}
      />
      <div style={{ marginTop: 6 }}>
        {tab === 'alarms' && (
          <Panel title="active alarms & resolution guide">
            {alarms.length === 0 && <span className="ok-text">● no active alarms — all subsystems nominal</span>}
            <table>
              <tbody>
                {alarms.map((a) => {
                  const axisMatch = a.key.match(/^axis(\d)\./)
                  const errAxis = axisMatch ? Number(axisMatch[1]) : ax
                  return (
                    <tr key={a.key}>
                      <td style={{ width: 150 }}>
                        <Tag level={a.level === 'alarm' ? 'alarm' : 'warn'} blink={!a.acked}>
                          {a.level}
                        </Tag>
                        {safety?.first_out === a.key && (
                          <>
                            {' '}
                            <Tag level="info">first-out</Tag>
                          </>
                        )}
                        <div className="muted num" style={{ marginTop: 4, fontSize: 'var(--fs-micro)' }}>
                          {time(a.ts)}
                        </div>
                      </td>
                      <td>
                        <div className="num" style={{ fontWeight: 600, color: 'var(--text)' }}>
                          {a.msg}
                        </div>
                        {a.flags.map((f) => {
                          const g = explainFlag(meta, a.key, f)
                          return (
                            <div
                              key={f}
                              style={{
                                marginTop: 6,
                                padding: '6px 8px',
                                background: 'var(--surface-2)',
                                borderLeft: '2px solid var(--warn)',
                                fontSize: 'var(--fs-tick)',
                              }}
                            >
                              <div>
                                <span className="error-text" style={{ fontWeight: 600 }}>
                                  {f}
                                </span>{' '}
                                — <span className="dim">{g.summary}</span>
                              </div>
                              <div className="muted" style={{ marginTop: 2 }}>
                                <strong>WHY:</strong> {g.why}
                              </div>
                              <div style={{ marginTop: 2, color: 'var(--text-2)' }}>
                                <strong>HOW TO FIX:</strong> {g.fix}
                              </div>
                              {g.fixes && g.fixes.length > 0 && (
                                <div className="row" style={{ marginTop: 6 }}>
                                  {g.fixes.map((fx) => (
                                    <Button key={fx.label} small kind="primary" onClick={() => applyErrorFix(fx, errAxis).catch(() => undefined)}>
                                      {fx.label}
                                    </Button>
                                  ))}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </td>
                      <td style={{ width: 170 }}>
                        <div className="row">
                          <Button small onClick={() => act('ack', { key: a.key })}>
                            ack
                          </Button>
                          <Button small onClick={() => act('shelve', { key: a.key, seconds: 600 })}>
                            shelve 10m
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {(safety?.shelved.length ?? 0) > 0 && (
              <div style={{ marginTop: 8 }} className="muted">
                shelved: {safety!.shelved.map((a) => `${a.key} until ${time(a.shelved_until)}`).join(', ')}
              </div>
            )}
          </Panel>
        )}
        {tab === 'events' && (
          <Panel title="events">
            <EventsPanel />
          </Panel>
        )}
        {tab === 'audit' && (
          <Panel
            title={`audit . ${audit.length} entries`}
            tools={
              <select value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="">all</option>
                {['write', 'call', 'safety', 'job', 'config'].map((k) => (
                  <option key={k}>{k}</option>
                ))}
              </select>
            }
          >
            <table>
              <thead>
                <tr>
                  <th>time</th>
                  <th>kind</th>
                  <th>source</th>
                  <th>path</th>
                  <th>old</th>
                  <th>new</th>
                  <th>detail</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((r) => (
                  <tr key={r.id} className={r.ok ? '' : 'error-text'}>
                    <td className="num muted">{date(r.ts)}</td>
                    <td>{r.kind}</td>
                    <td className="muted">{r.source}</td>
                    <td>{r.path}</td>
                    <td className="num">{fmt(r.old)}</td>
                    <td className="num">{typeof r.new === 'object' ? JSON.stringify(r.new) : fmt(r.new)}</td>
                    <td className="muted">{r.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        )}
      </div>
    </div>
  )
}
