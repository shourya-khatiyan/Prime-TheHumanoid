import { useEffect, useState } from 'react'
import { Button, Panel, Tabs, Tag } from '../primitives'
import { act, useApp } from '../lib/store'
import { date, fmt, time } from '../lib/format'
import { flagDoc } from '../lib/meta'
import { EventsPanel } from './panels'

/** alarms (ack, shelve with expiry, first-out), event log and the write audit trail */
export function Alarms() {
  const safety = useApp((s) => s.status?.safety)
  const meta = useApp((s) => s.meta)
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
          <Button small onClick={() => act('clear_errors', {})}>
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
          <Panel title="active">
            {alarms.length === 0 && <span className="ok-text">no active alarms</span>}
            <table>
              <tbody>
                {alarms.map((a) => (
                  <tr key={a.key}>
                    <td style={{ width: 140 }}>
                      <Tag level={a.level === 'alarm' ? 'alarm' : 'warn'} blink={!a.acked}>
                        {a.level}
                      </Tag>
                      {safety?.first_out === a.key && (
                        <>
                          {' '}
                          <Tag level="info">first-out</Tag>
                        </>
                      )}
                    </td>
                    <td className="muted num">{time(a.ts)}</td>
                    <td>
                      <div>{a.msg}</div>
                      {a.flags.map((f) => (
                        <div key={f} className="muted" style={{ fontSize: 'var(--fs-tick)' }}>
                          {f}: {flagDoc(meta, a.key, f).split('\n')[0]}
                        </div>
                      ))}
                    </td>
                    <td className="row">
                      <Button small onClick={() => act('ack', { key: a.key })}>
                        ack
                      </Button>
                      <Button small onClick={() => act('shelve', { key: a.key, seconds: 600 })}>
                        shelve 10 min
                      </Button>
                    </td>
                  </tr>
                ))}
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
