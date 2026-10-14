import type { ReactNode } from 'react'
import { Button, Panel, Tag, Value } from '../primitives'
import { act, useApp, useJobRunner, type JobInfo } from '../lib/store'
import { fmt } from '../lib/format'
import { EncoderCard } from './panels'
import { HealthTable } from './Health'

function JobState({ job }: { job: JobInfo | null }) {
  if (!job) return null
  const ok = job.state === 'done' && (job.result?.ok ?? true)
  return ok ? <Tag level="quiet">done</Tag> : <Tag level={job.state === 'done' ? 'warn' : 'alarm'}>{job.state === 'done' ? 'check results' : job.state}</Tag>
}

function Checks({ checks }: { checks?: { id: string; ok: boolean; msg: string }[] }) {
  if (!checks?.length) return null
  return (
    <div className="col">
      {checks.map((c) => (
        <div key={c.id} className={c.ok ? 'ok-text' : 'error-text'}>
          {c.ok ? 'PASS ' : 'FAIL '}
          {c.msg}
        </div>
      ))}
    </div>
  )
}

function Step({ n, title, children, done }: { n: number; title: string; children: ReactNode; done?: ReactNode }) {
  return (
    <Panel title={`step ${n} . ${title}`} tools={done}>
      <div className="col">{children}</div>
    </Panel>
  )
}

const WIRING: [string, string, string][] = [
  ['VDD 3V3', '3.3V', 'run the AS5047P board in 3.3 V mode'],
  ['GND', 'GND', 'common ground'],
  ['CLK', 'SCK', 'keep short; 20-50 ohm series resistor helps with noise'],
  ['MISO (DO)', 'MISO', 'stuck at 0 = shorted/unpowered, stuck at 16383 = floating'],
  ['MOSI (DI)', 'MOSI', 'may be tied to 3.3 V instead'],
  ['CSn', 'GPIO4', 'profile encoder.cs_gpio (GPIO1/2 are UART, do not use)'],
]

/** guided bring-up for a new actuator, in the order that avoids surprises */
export function Commission() {
  const ax = useApp((s) => s.profile?.axis ?? 0)
  const status = useApp((s) => s.status)
  const profile = useApp((s) => s.profile)
  const diff = useJobRunner('commission.diff')
  const apply = useJobRunner('commission.apply')
  const turn = useJobRunner('commission.turn')
  const health = useJobRunner('commission.health')
  const calM = useJobRunner('commission.calM')
  const calE = useJobRunner('commission.calE')
  const spin = useJobRunner('commission.spin')
  const info = status?.device.info
  const rows: any[] = diff.job?.result?.rows ?? []
  const save = () => act('call', { path: 'save_configuration', args: [] }).catch(() => undefined)
  return (
    <div>
      <div className="view-head">
        <h1>commissioning</h1>
        <span className="sub">
          axis{ax} . {profile?.name}
        </span>
      </div>
      <div className="grid2">
        <Step n={1} title="identify" done={info ? <Tag level="quiet">connected</Tag> : <Tag level="warn">no device</Tag>}>
          <div className="kv num">
            <span>transport</span>
            <span>{status?.device.transport ?? '--'}</span>
            <span>serial</span>
            <span>{info?.serial ?? '--'}</span>
            <span>firmware</span>
            <span>{info?.fw ?? '--'} (latest for v3.6: 0.5.6)</span>
            <span>hardware</span>
            <span>{info?.hw ?? '--'}</span>
          </div>
          <span className="muted">power the board from the bench psu with its current limit set (start ~3 A). do not connect the gearbox yet.</span>
        </Step>

        <Step n={2} title="encoder wiring" done={<JobState job={turn.job} />}>
          <table>
            <thead>
              <tr>
                <th>AS5047P</th>
                <th>ODrive</th>
                <th>note</th>
              </tr>
            </thead>
            <tbody>
              {WIRING.map(([a, b, c]) => (
                <tr key={a}>
                  <td>{a}</td>
                  <td>{b}</td>
                  <td className="muted">{c}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <EncoderCard ax={ax} />
          <div className="row">
            <Button disabled={turn.busy} onClick={() => turn.run('encoder_turn', { axis: ax })}>
              hand-turn test
            </Button>
            <span className="muted">needs step 3 applied first (cs pin / cpr)</span>
          </div>
          <Checks checks={turn.job?.result?.checks} />
        </Step>

        <Step n={3} title="apply actuator profile" done={<JobState job={apply.job} />}>
          <div className="row">
            <Button disabled={diff.busy} onClick={() => diff.run('profile_diff', { axis: ax })}>
              compare with device
            </Button>
            <Button kind="primary" disabled={apply.busy || !rows.some((r) => r.change)} onClick={async () => {
              await apply.run('apply_profile', { axis: ax })
              diff.run('profile_diff', { axis: ax })
            }}>
              apply {rows.filter((r) => r.change).length} changes
            </Button>
          </div>
          {rows.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>path</th>
                  <th>device</th>
                  <th>profile</th>
                  <th>why</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.path} className={r.change ? '' : 'muted'}>
                    <td>{r.path}</td>
                    <td className="num">{fmt(r.current)}</td>
                    <td className={`num ${r.change ? 'dim' : ''}`}>{fmt(r.value)}</td>
                    <td className="muted">{r.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Step>

        <Step n={4} title="save + reboot">
          <span className="muted">the encoder cs pin and cpr take effect reliably only after a save and reboot. the gui reconnects by itself.</span>
          <div className="row">
            <Button kind="primary" onClick={save}>
              save configuration
            </Button>
          </div>
        </Step>

        <Step n={5} title="health check (passive)" done={health.job?.result ? <Tag level={health.job.result.verdict === 'fail' ? 'alarm' : health.job.result.verdict === 'warn' ? 'warn' : 'quiet'}>{health.job.result.verdict}</Tag> : undefined}>
          <div className="row">
            <Button disabled={health.busy} onClick={() => health.run('health', { axis: ax })}>
              run health check
            </Button>
          </div>
          {health.job?.result && <HealthTable checks={health.job.result.checks} />}
        </Step>

        <Step n={6} title="motor calibration" done={<JobState job={calM.job} />}>
          <span className="muted">
            measures phase R and L at {profile?.motor.calibration_current_a} A. the motor beeps; the rotor must be free (no gearbox load).
          </span>
          <div className="row">
            <Button disabled={calM.busy} onClick={() => calM.run('calibrate', { axis: ax, kind: 'motor' })}>
              run motor calibration
            </Button>
          </div>
          <Checks checks={calM.job?.result?.checks} />
        </Step>

        <Step n={7} title="encoder offset calibration" done={<JobState job={calE.job} />}>
          <span className="muted">the rotor turns slowly back and forth; a CPR / pole-pair mismatch error means wrong pole_pairs, cpr, or a slipping magnet.</span>
          <div className="row">
            <Button disabled={calE.busy} onClick={() => calE.run('calibrate', { axis: ax, kind: 'encoder', mark_precalibrated: true })}>
              run encoder calibration
            </Button>
          </div>
          <Checks checks={calE.job?.result?.checks} />
          {calE.job?.result?.ok && (
            <div className="row">
              <span className="dim">pre_calibrated set.</span>
              <Button kind="primary" onClick={save}>
                save configuration
              </Button>
            </div>
          )}
        </Step>

        <Step n={8} title="first spin" done={<JobState job={spin.job} />}>
          <span className="muted">velocity step to 0.5 turn/s for 2 s with the bring-up current limit. watch the current plot; it should stay well below the limit.</span>
          <div className="row">
            <Button disabled={spin.busy} onClick={() => spin.run('step_response', { axis: ax, mode: 'velocity', amplitude: 0.5, hold_s: 2 })}>
              spin 0.5 turn/s
            </Button>
          </div>
          {spin.job?.result && (
            <div className="row">
              <Value k="rise" v={fmt(spin.job.result.metrics.rise_s, 3)} u="s" />
              <Value k="overshoot" v={fmt(spin.job.result.metrics.overshoot_pct, 1)} u="%" />
              <Value k="peak Iq" v={fmt(spin.job.result.metrics.iq_peak, 2)} u="A" />
            </div>
          )}
        </Step>
      </div>
    </div>
  )
}
