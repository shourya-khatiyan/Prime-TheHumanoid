import { useState, type ReactNode } from 'react'
import { Button, NumInput, Panel, Tabs, Value } from '../primitives'
import { StaticPlot } from '../components/Plot'
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
  return (
    <div className="grid2">
      <Panel title="step response">
        <F label="mode">
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="position">position</option>
            <option value="velocity">velocity</option>
          </select>
        </F>
        <F label="amplitude" unit={mode === 'position' ? 'turn' : 'turn/s'}>
          <NumInput value={amp} onCommit={setAmp} />
        </F>
        <F label="hold" unit="s">
          <NumInput value={hold} onCommit={setHold} />
        </F>
        <div className="row">
          <Button kind="primary" disabled={step.busy} onClick={() => step.run('step_response', { axis: ax, mode, amplitude: amp, hold_s: hold })}>
            run step
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
      <Panel title="gain sweep">
        <F label="gain">
          <select value={gain} onChange={(e) => setGain(e.target.value)}>
            <option value="pos_gain">pos_gain</option>
            <option value="vel_gain">vel_gain</option>
            <option value="vel_integrator_gain">vel_integrator_gain</option>
          </select>
        </F>
        <F label="values">
          <input value={values} onChange={(e) => setValues(e.target.value)} />
        </F>
        <div className="row">
          <Button kind="primary" disabled={sweep.busy} onClick={() => sweep.run('gain_sweep', { axis: ax, mode, gain, values: parseList(values), amplitude: amp, hold_s: Math.min(hold, 1) })}>
            run sweep
          </Button>
          <span className="muted">uses the step mode/amplitude on the left; original gain is restored</span>
        </div>
        {sweepRows.length > 0 && (
          <>
            <table>
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
      <Panel title="sine response (position)">
        <F label="amplitude" unit="turn">
          <NumInput value={sAmp} onCommit={setSAmp} />
        </F>
        <F label="frequencies" unit="Hz">
          <input value={freqs} onChange={(e) => setFreqs(e.target.value)} />
        </F>
        <div className="row">
          <Button kind="primary" disabled={sine.busy} onClick={() => sine.run('sine_response', { axis: ax, amplitude: sAmp, freqs: parseList(freqs) })}>
            run sine sweep
          </Button>
        </div>
        {sine.result && (
          <>
            <table>
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
      <Panel title="tuning procedure (odrive cascaded loops)">
        <ol className="dim" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
          <li>start with pos_gain 20, vel_gain 0.16 x (your Kt / 0.04), vel_integrator_gain 0.</li>
          <li>raise vel_gain 30 % per step until it buzzes or vibrates, then back off 50 %.</li>
          <li>raise pos_gain 30 % per step until position steps overshoot, then back off a little.</li>
          <li>set vel_integrator_gain = 0.5 x bandwidth x vel_gain, bandwidth ~ 1 / settle time.</li>
          <li>repeat with the gearbox and load attached: reflected inertia grows with ratio squared.</li>
        </ol>
      </Panel>
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
    <div className="grid2">
      <Panel title="thermal hold (locked rotor)">
        <F label="current" unit="A">
          <NumInput value={current} onCommit={setCurrent} />
        </F>
        <F label="duration" unit="min">
          <NumInput value={minutes} onCommit={setMinutes} />
        </F>
        <F label="abort if rotor moves" unit="turn">
          <NumInput value={motion} onCommit={setMotion} />
        </F>
        <div className="row">
          {[6, 8, 12].map((a) => (
            <Button key={a} small onClick={() => setCurrent(a)}>
              {a} A
            </Button>
          ))}
          <Button kind="primary" disabled={t.busy} onClick={() => t.run('thermal', { axis: ax, current_a: current, duration_min: minutes, max_motion_turns: motion })}>
            start thermal test
          </Button>
        </div>
        <span className="muted">aborts on rotor motion, FET or motor temperature limits, any error, or a lost gui heartbeat.</span>
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
      <Panel title="live temperature (10 min)" flush>
        <div className="h-plot-lg">
          <ThermalPlot ax={ax} windowS={600} />
        </div>
      </Panel>
      {rows.length > 0 && (
        <Panel title={`result . ${t.result.stop_reason}`} flush>
          <div className="h-plot">
            <StaticPlot x={rows.map((r) => r.t)} ys={[rows.map((r) => r.fet_c), rows.map((r) => r.motor_c), rows.map((r) => r.iq)]} labels={['fet C', 'motor C', 'Iq A']} scales={['C', 'C', 'A']} />
          </div>
        </Panel>
      )}
    </div>
  )
}

function Characterize({ ax }: { ax: number }) {
  const fr = useJobRunner('tests.fr')
  const kt = useJobRunner('tests.kt')
  const bl = useJobRunner('tests.bl')
  const [maxT, setMaxT] = useState(0.3)
  const [currents, setCurrents] = useState('1, 2, 3, 4')
  const [arm, setArm] = useState(0.2)
  const [blT, setBlT] = useState(0.1)
  return (
    <div className="grid3">
      <Panel title="friction / breakaway">
        <F label="max torque" unit="Nm">
          <NumInput value={maxT} onCommit={setMaxT} />
        </F>
        <Button kind="primary" disabled={fr.busy} onClick={() => fr.run('friction', { axis: ax, max_torque_nm: maxT })}>
          run friction test
        </Button>
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
      <Panel title="effective Kt / efficiency">
        <F label="currents" unit="A">
          <input value={currents} onChange={(e) => setCurrents(e.target.value)} />
        </F>
        <F label="torque arm" unit="m">
          <NumInput value={arm} onCommit={setArm} />
        </F>
        <Button kind="primary" disabled={kt.busy} onClick={() => kt.run('kt_efficiency', { axis: ax, currents: parseList(currents), arm_length_m: arm })}>
          run Kt test
        </Button>
        <span className="muted">you enter each scale reading in the job panel.</span>
        {kt.result && (
          <div className="kv num" style={{ marginTop: 8 }}>
            <span>Kt at output</span>
            <span>{fmt(kt.result.kt_out_nm_per_a, 3)} Nm/A</span>
            <span>ideal</span>
            <span>{fmt(kt.result.kt_ideal_out, 3)} Nm/A</span>
            <span>efficiency</span>
            <span>{kt.result.efficiency ? (kt.result.efficiency * 100).toFixed(1) + ' %' : '--'}</span>
            <span>fit r2</span>
            <span>{fmt(kt.result.r2, 4)}</span>
          </div>
        )}
      </Panel>
      <Panel title="lost motion (backlash + compliance)">
        <F label="test torque" unit="Nm">
          <NumInput value={blT} onCommit={setBlT} />
        </F>
        <Button kind="primary" disabled={bl.busy} onClick={() => bl.run('backlash', { axis: ax, torque_nm: blT, cycles: 3 })}>
          run lost-motion test
        </Button>
        <span className="muted">partial until the output encoder exists: measures motor-side motion with the output locked.</span>
        {bl.result && (
          <div className="kv num" style={{ marginTop: 8 }}>
            <span>at joint</span>
            <span>
              {fmt(bl.result.joint_deg, 3)} deg ({fmt(bl.result.joint_arcmin, 1)} arcmin)
            </span>
            <span>motor side</span>
            <span>{fmt(bl.result.motor_turns, 4)} turn</span>
          </div>
        )}
      </Panel>
    </div>
  )
}

export function Tests() {
  const ax = useApp((s) => s.axis)
  const [tab, setTab] = useState('tuning')
  return (
    <div>
      <div className="view-head">
        <h1>tests</h1>
        <span className="sub">axis{ax} . every test ends with the axis in idle</span>
      </div>
      <Tabs
        tabs={[
          ['tuning', 'tuning'],
          ['thermal', 'thermal'],
          ['char', 'characterization'],
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
