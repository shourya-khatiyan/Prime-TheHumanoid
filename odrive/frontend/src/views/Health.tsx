import { useEffect, useState } from 'react'
import { Button, Panel, Tag } from '../primitives'
import { act, startJob, useApp, waitJob } from '../lib/store'
import { rpc } from '../lib/rpc'
import { date } from '../lib/format'

type Check = { id: string; title: string; status: 'pass' | 'warn' | 'fail' | 'skip'; value: string; expect: string; hint: string }

/** pass / warn / fail table; normal results stay quiet, only problems get color */
export function HealthTable({ checks }: { checks: Check[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>check</th>
          <th>result</th>
          <th>value</th>
          <th>expected</th>
          <th>what to do</th>
        </tr>
      </thead>
      <tbody>
        {checks.map((c) => (
          <tr key={c.id}>
            <td>{c.title}</td>
            <td>{c.status === 'fail' ? <Tag level="alarm">fail</Tag> : c.status === 'warn' ? <Tag level="warn">warn</Tag> : <span className={c.status === 'skip' ? 'muted' : 'dim'}>{c.status}</span>}</td>
            <td className="num">{c.value}</td>
            <td className="muted">{c.expect}</td>
            <td className="muted">{c.hint}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** run the passive self-test and browse saved reports */
export function Health() {
  const ax = useApp((s) => s.axis)
  const [result, setResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [reports, setReports] = useState<any[]>([])
  const refresh = () => act<any[]>('reports', {}, true).then(setReports).catch(() => undefined)
  useEffect(() => {
    refresh()
  }, [])
  const run = async () => {
    setBusy(true)
    try {
      const j = await waitJob(await startJob('health', { axis: ax }))
      setResult(j.result)
      refresh()
    } catch {
      // shown in message bar
    } finally {
      setBusy(false)
    }
  }
  const open = async (id: string) => setResult(await act('report_load', { id }))
  return (
    <div>
      <div className="view-head">
        <h1>health check</h1>
        <span className="sub">passive: never energizes the motor</span>
        <div className="row" style={{ marginLeft: 'auto' }}>
          {[0, 1].map((a) => (
            <Button key={a} small kind={a === ax ? 'on' : ''} onClick={() => useApp.setState({ axis: a })}>
              axis{a}
            </Button>
          ))}
          <Button kind="primary" disabled={busy} onClick={run}>
            run health check
          </Button>
        </div>
      </div>
      <div className="grid2" style={{ gridTemplateColumns: '2fr 1fr' }}>
        <Panel
          title={result ? `report . axis${result.axis} . ${result.verdict}` : 'report'}
          tools={
            result?.report_id && (
              <a href={`/api/report/${result.report_id}.md?token=${rpc.token}`} target="_blank" rel="noreferrer">
                markdown
              </a>
            )
          }
        >
          {result ? <HealthTable checks={result.checks} /> : <span className="muted">run the check or open a saved report</span>}
        </Panel>
        <Panel title="saved reports">
          <table>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} style={{ cursor: 'pointer' }} onClick={() => open(r.id)}>
                  <td>{r.kind}</td>
                  <td>{r.verdict === 'fail' ? <Tag level="alarm">fail</Tag> : r.verdict === 'warn' ? <Tag level="warn">warn</Tag> : <span className="dim">{r.verdict}</span>}</td>
                  <td className="muted num">{r.created ? date(r.created) : r.id.slice(0, 15)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  )
}
