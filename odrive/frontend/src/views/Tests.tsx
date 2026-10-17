import { useState, type ReactNode } from 'react'
import { Button, NumInput, Panel, Segmented, Tabs, Value } from '../primitives'
import { StaticPlot } from '../components/Plot'
import { CharacterizationTwin, ThermalTwin, TuningTwin } from '../components/SimTwins'
import { useApp, useJobRunner } from '../lib/store'
import { fmt } from '../lib/format'
import { ThermalPlot } from './panels'

function F({ label, unit, children }: { label: string; unit?: string; children: ReactNode }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      <span className="unit">{unit}</span>
    </div>
  )
}

function parseList(s: string): number[] {
  return s
    .split(/[ ,;]+/)
    .map(Number)
    .filter((x) => Number.isFinite(x))
}

function Tuning({ ax }: { ax: number }) {
  const step = useJobRunner('tests.step')
  const sweep = useJobRunner('tests.sweep')
  const sine = useJobRunner('tests.sine')
  const [mode, setMode] = useState('position')
  const [amp, setAmp] = useState(0.1)
  const [hold, setHold] = useState(1)
  const [gain, setGain] = useState('vel_gain')
  const [values, setValues] = useState('0.02, 0.04, 0.08, 0.16')
  const [sel, setSel] = useState(0)
  const [sAmp, setSAmp] = useState(0.05)
  const [freqs, setFreqs] = useState('0.5, 1, 2, 4, 8')
  const tr = step.result?.trace
  const sweepRows: any[] = sweep.result?.rows ?? []
  const sTr = sweepRows[sel]?.trace
  const activeTrace = tr ?? sTr
  const activeMetrics = step.result?.metrics ?? sweepRows[sel]?.metrics

  return (
    <div className="col" style={{ gap: 10 }}>
      <TuningTwin ax={ax} trace={activeTrace} metrics={activeMetrics} mode={mode} />

      <div className="grid2">
        <Panel index="01" title="STEP RESPONSE">
          <F label="mode">
            <Segmented
              options={[
                ['position', 'position'],
                ['velocity', 'velocity'],
              ]}
              value={mode}
              onChange={setMode}
            />
          </F>
          <F label="amplitude" unit={mode === 'position' ? 'turn' : 'turn/s'}>
            <NumInput value={amp} onCommit={setAmp} />
          </F>
          <F label="hold duration" unit="s">
            <NumInput value={hold} onCommit={setHold} />
          </F>
          <div className="row" style={{ marginTop: 4 }}>
            <Button kind="primary" disabled={step.busy} onClick={() => step.run('step_response', { axis: ax, mode, amplitude: amp, hold_s: hold })}>
              {step.busy ? 'running step...' : 'run step'}
            </Button>
          </div>
          {step.result && (
            <>
              <div className="row" style={{ margin: '6px 0' }}>
                <Value k="rise 10-90" v={fmt(step.result.metrics.rise_s, 4)} u="s" />
                <Value k="overshoot" v={fmt(step.result.metrics.overshoot_pct, 1)} u="%" />
                <Value k="settle 2%" v={fmt(step.result.metrics.settle_s, 3)} u="s" />
                <Value k="ss error" v={fmt(step.result.metrics.sse, 4)} />
                <Value k="peak Iq" v={fmt(step.result.metrics.iq_peak, 2)} u="A" />
              </div>
              <div className="h-plot">
                <StaticPlot x={tr.t} ys={[tr.target, tr.y, tr.iq]} labels={['target', 'measured', 'Iq']} scales={[mode === 'position' ? 'turn' : 'turn/s', mode === 'position' ? 'turn' : 'turn/s', 'A']} />
              </div>
            </>
          )}
        </Panel>

        <Panel index="02" title="AUTOMATED GAIN SWEEP">
          <F label="gain parameter">
            <select value={gain} onChange={(e) => setGain(e.target.value)}>
              <option value="pos_gain">pos_gain</option>
              <option value="vel_gain">vel_gain</option>
              <option value="vel_integrator_gain">vel_integrator_gain</option>
            </select>
          </F>
          <F label="candidate values">
            <input value={values} onChange={(e) => setValues(e.target.value)} />
          </F>
          <div className="row" style={{ marginTop: 4 }}>
            <Button kind="primary" disabled={sweep.busy} onClick={() => sweep.run('gain_sweep', { axis: ax, mode, gain, values: parseList(values), amplitude: amp, hold_s: Math.min(hold, 1) })}>
              {sweep.busy ? 'sweeping...' : 'run sweep'}
            </Button>
            <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>
              original gain restored after sweep
            </span>
          </div>
          {sweepRows.length > 0 && (
            <>
              <table style={{ marginTop: 6 }}>
                <thead>
                  <tr>
                    <th>{gain}</th>
                    <th>overshoot %</th>
                    <th>settle s</th>
                    <th>iae</th>
                    <th>peak Iq</th>
                  </tr>
                </thead>
                <tbody>
                  {sweepRows.map((r, i) => (
                    <tr key={i} onClick={() => setSel(i)} style={{ cursor: 'pointer' }} className={i === sel ? 'dim' : ''}>
                      <td className="num">
                        {r.value}
                        {r.value === sweep.result.best ? ' (best)' : ''}
                      </td>
                      <td className="num">{fmt(r.metrics?.overshoot_pct, 1)}</td>
                      <td className="num">{fmt(r.metrics?.settle_s, 3)}</td>
                      <td className="num">{fmt(r.metrics?.iae, 4)}</td>
                      <td className="num">{fmt(r.metrics?.iq_peak, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {sTr && (
                <div className="h-plot">
                  <StaticPlot x={sTr.t} ys={[sTr.target, sTr.y]} labels={['target', `measured @ ${sweepRows[sel].value}`]} />
                </div>
              )}
            </>
          )}
        </Panel>

        <Panel index="03" title="SINE FREQUENCY RESPONSE (POSITION)">
          <F label="amplitude" unit="turn">
            <NumInput value={sAmp} onCommit={setSAmp} />
          </F>
          <F label="frequencies" unit="Hz">
            <input value={freqs} onChange={(e) => setFreqs(e.target.value)} />
          </F>
          <div className="row" style={{ marginTop: 4 }}>
            <Button kind="primary" disabled={sine.busy} onClick={() => sine.run('sine_response', { axis: ax, amplitude: sAmp, freqs: parseList(freqs) })}>
              {sine.busy ? 'running sine...' : 'run sine sweep'}
            </Button>
          </div>
          {sine.result && (
            <>
              <table style={{ marginTop: 6 }}>
                <thead>
                  <tr>
                    <th>Hz</th>
                    <th>gain dB</th>
                    <th>phase deg</th>
                    <th>setpoint rate</th>
                  </tr>
                </thead>
                <tbody>
                  {sine.result.rows.map((r: any) => (
                    <tr key={r.freq}>
                      <td className="num">{r.freq}</td>
                      <td className="num">{fmt(r.gain_db, 2)}</td>
                      <td className="num">{fmt(r.phase_deg, 1)}</td>
                      <td className="num">{fmt(r.cmd_rate_hz, 0)} Hz</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="h-plot">
                <StaticPlot x={sine.result.rows.map((r: any) => r.freq)} ys={[sine.result.rows.map((r: any) => r.gain_db), sine.result.rows.map((r: any) => r.phase_deg)]} labels={['gain dB', 'phase deg']} scales={['dB', 'deg']} xLabel="Hz" />
              </div>
            </>
          )}
        </Panel>

        <Panel index="04" title="CASCADED LOOP TUNING PROCEDURE">
          <ol className="dim" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
            <li>start with pos_gain 20, vel_gain 0.16 × (your Kt / 0.04), vel_integrator_gain 0.</li>
            <li>raise vel_gain 30 % per step until it buzzes or vibrates, then back off 50 %.</li>
            <li>raise pos_gain 30 % per step until position steps overshoot, then back off a little.</li>
            <li>set vel_integrator_gain = 0.5 × bandwidth × vel_gain, bandwidth ≈ 1 / settle time.</li>
            <li>repeat with the 30:1 (6:1 × 5:1) planetary gearbox attached: reflected inertia scales with ratio² (900×).</li>
          </ol>
        </Panel>
      </div>
    </div>
  )
}

function Thermal({ ax }: { ax: number }) {
  const t = useJobRunner('tests.t')
  const [current, setCurrent] = useState(6)
  const [minutes, setMinutes] = useState(30)
  const [motion, setMotion] = useState(0.25)
  const rows: any[] = t.result?.rows ?? []
  return (
    <div className="col" style={{ gap: 10 }}>
      <ThermalTwin ax={ax} currentCmd={current} maxMotion={motion} fits={t.result?.fits} />

      <div className="grid2">
        <Panel index="01" title="THERMAL HOLD (LOCKED ROTOR)">
          <F label="hold current" unit="A">
            <div className="row" style={{ gap: 6 }}>
              <NumInput value={current} onCommit={setCurrent} width={80} />
              {[6, 8, 12].map((a) => (
                <Button key={a} small kind={current === a ? 'on' : 'chip'} onClick={() => setCurrent(a)}>
                  {a} A
                </Button>
              ))}
            </div>
          </F>
          <F label="duration" unit="min">
            <NumInput value={minutes} onCommit={setMinutes} />
          </F>
          <F label="abort if rotor moves" unit="turn">
            <NumInput value={motion} onCommit={setMotion} />
          </F>
          <div className="row" style={{ marginTop: 6 }}>
            <Button kind="primary" disabled={t.busy} onClick={() => t.run('thermal', { axis: ax, current_a: current, duration_min: minutes, max_motion_turns: motion })}>
              {t.busy ? 'holding current...' : 'start thermal test'}
            </Button>
          </div>
          <span className="muted" style={{ fontSize: 'var(--fs-tick)', marginTop: 4 }}>
            Aborts automatically on rotor motion, FET/motor temperature limits, any fault, or lost GUI heartbeat.
          </span>
          {t.result && (
            <table style={{ marginTop: 8 }}>
              <thead>
                <tr>
                  <th>sensor</th>
                  <th>T0 C</th>
                  <th>rise C</th>
                  <th>tau s</th>
                  <th>steady state C</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(t.result.fits).map(([k, f]: [string, any]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td className="num">{fmt(f.t0, 1)}</td>
                    <td className="num">{fmt(f.dT, 1)}</td>
                    <td className="num">{fmt(f.tau_s, 0)}</td>
                    <td className="num">{fmt(f.t_inf, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
        <Panel index="02" title="LIVE TEMPERATURE STREAM (10 MIN)" flush>
          <div className="h-plot-lg">
            <ThermalPlot ax={ax} windowS={600} />
          </div>
        </Panel>
        {rows.length > 0 && (
          <Panel index="03" title={`CAPTURED THERMAL CURVE · ${t.result.stop_reason}`} flush>
            <div className="h-plot">
              <StaticPlot x={rows.map((r) => r.t)} ys={[rows.map((r) => r.fet_c), rows.map((r) => r.motor_c), rows.map((r) => r.iq)]} labels={['fet C', 'motor C', 'Iq A']} scales={['C', 'C', 'A']} />
            </div>
          </Panel>
        )}
      </div>
    </div>
  )
}

function Characterize({ ax }: { ax: number }) {
  const fr = useJobRunner('tests.fr')
  const kt = useJobRunner('tests.kt')
  const bl = useJobRunner('tests.bl')
  const [simMode, setSimMode] = useState<'friction' | 'kt' | 'backlash'>('friction')
  const [maxT, setMaxT] = useState(0.3)
  const [currents, setCurrents] = useState('1, 2, 3, 4')
  const [arm, setArm] = useState(0.2)
  const [blT, setBlT] = useState(0.1)

  return (
    <div className="col" style={{ gap: 10 }}>
      <CharacterizationTwin
        ax={ax}
        mode={simMode}
        onModeChange={setSimMode}
        frResult={fr.result}
        ktResult={kt.result}
        blResult={bl.result}
        armLengthM={arm}
        testTorqueNm={blT}
      />

      <div className="grid3">
        <Panel index="01" title="FRICTION / BREAKAWAY">
          <F label="max torque" unit="Nm">
            <NumInput value={maxT} onCommit={setMaxT} />
          </F>
          <div className="row" style={{ marginTop: 4 }}>
            <Button
              kind="primary"
              disabled={fr.busy}
              onClick={() => {
                setSimMode('friction')
                fr.run('friction', { axis: ax, max_torque_nm: maxT })
              }}
            >
              {fr.busy ? 'measuring...' : 'run friction test'}
            </Button>
          </div>
          {fr.result && (
            <div className="kv num" style={{ marginTop: 8 }}>
              <span>breakaway +</span>
              <span>{fmt(fr.result.breakaway.positive, 4)} Nm</span>
              <span>breakaway -</span>
              <span>{fmt(fr.result.breakaway.negative, 4)} Nm</span>
              <span>coulomb</span>
              <span>{fmt(fr.result.coulomb_nm, 4)} Nm</span>
              <span>viscous</span>
              <span>{fmt(fr.result.viscous_nm_per_turn_s, 5)} Nm/(turn/s)</span>
            </div>
          )}
        </Panel>

        <Panel index="02" title="EFFECTIVE KT & EFFICIENCY (30:1)">
          <F label="currents" unit="A">
            <input value={currents} onChange={(e) => setCurrents(e.target.value)} />
          </F>
          <F label="torque arm" unit="m">
            <NumInput value={arm} onCommit={setArm} />
          </F>
          <div className="row" style={{ marginTop: 4 }}>
            <Button
              kind="primary"
              disabled={kt.busy}
              onClick={() => {
                setSimMode('kt')
                kt.run('kt_efficiency', { axis: ax, currents: parseList(currents), arm_length_m: arm })
              }}
            >
              {kt.busy ? 'holding arm...' : 'run Kt test'}
            </Button>
          </div>
          <span className="muted" style={{ fontSize: 'var(--fs-tick)', marginTop: 4 }}>
            Enter each load-cell / scale reading in the job prompt dock.
          </span>
          {kt.result && (
            <div className="kv num" style={{ marginTop: 8 }}>
              <span>Kt at output</span>
              <span>{fmt(kt.result.kt_out_nm_per_a, 3)} Nm/A</span>
              <span>ideal (30:1)</span>
              <span>{fmt(kt.result.kt_ideal_out, 3)} Nm/A</span>
              <span>efficiency</span>
              <span>{kt.result.efficiency ? (kt.result.efficiency * 100).toFixed(1) + ' %' : '--'}</span>
              <span>fit r2</span>
              <span>{fmt(kt.result.r2, 4)}</span>
            </div>
          )}
        </Panel>

        <Panel index="03" title="LOST MOTION (30:1 BACKLASH + COMPLIANCE)">
          <F label="test torque" unit="Nm">
            <NumInput value={blT} onCommit={setBlT} />
          </F>
          <div className="row" style={{ marginTop: 4 }}>
            <Button
              kind="primary"
              disabled={bl.busy}
              onClick={() => {
                setSimMode('backlash')
                bl.run('backlash', { axis: ax, torque_nm: blT, cycles: 3 })
              }}
            >
              {bl.busy ? 'cycling...' : 'run lost-motion test'}
            </Button>
          </div>
          <span className="muted" style={{ fontSize: 'var(--fs-tick)', marginTop: 4 }}>
            Measures motor-side motion across the 6:1 × 5:1 planetary stages with the output locked.
          </span>
          {bl.result && (
            <div className="kv num" style={{ marginTop: 8 }}>
              <span>at 30:1 joint</span>
              <span>
                {fmt(bl.result.joint_deg, 3)} deg ({fmt(bl.result.joint_arcmin, 1)} arcmin)
              </span>
              <span>motor side</span>
              <span>{fmt(bl.result.motor_turns, 4)} turn</span>
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}

export function Tests() {
  const ax = useApp((s) => s.axis)
  const [tab, setTab] = useState('tuning')
  return (
    <div>
      <div className="view-head">
        <h1>AUTOMATED TEST RUNNERS</h1>
        <span className="sub">AXIS {ax} · 30:1 (6:1 × 5:1 PLANETARY) · EVERY TEST ENDS IN IDLE</span>
        <div className="row" style={{ marginLeft: 'auto' }}>
          <Segmented
            options={[
              [0, 'axis0'],
              [1, 'axis1'],
            ]}
            value={ax}
            onChange={(a) => useApp.setState({ axis: a })}
          />
        </div>
      </div>
      <Tabs
        tabs={[
          ['tuning', 'tuning & bode'],
          ['thermal', 'thermal hold'],
          ['char', '30:1 characterization'],
        ]}
        value={tab}
        onChange={setTab}
      />
      <div style={{ marginTop: 6 }}>
        {tab === 'tuning' && <Tuning ax={ax} />}
        {tab === 'thermal' && <Thermal ax={ax} />}
        {tab === 'char' && <Characterize ax={ax} />}
      </div>
    </div>
  )
}
