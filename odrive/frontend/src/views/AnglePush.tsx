import { useState, type ReactNode } from 'react'
import { Button, NumInput, Segmented, Tag } from '../primitives'
import { act, P, useAliasLatest, useApp, useJobRunner } from '../lib/store'
import { fmt, num } from '../lib/format'

type PathMode = 'short' | 'cw' | 'ccw' | 'abs'

/** joint-degree change needed to reach `target` from `current` with the chosen path rule */
export function angleDelta(current: number, target: number, mode: PathMode): number {
  const wrap = (x: number) => ((x % 360) + 360) % 360
  switch (mode) {
    case 'short':
      return wrap(target - current + 180) - 180
    case 'cw':
      return wrap(target - current)
    case 'ccw':
      return -wrap(current - target)
    case 'abs':
      return target - current
    default: {
      const never: never = mode
      return never
    }
  }
}

const field = (label: string, input: ReactNode, unit: string) => (
  <div className="field">
    <label>{label}</label>
    {input}
    <span className="unit">{unit}</span>
  </div>
)

/**
 * move the joint to an angle (degrees at the 30:1 output) with a trapezoidal trajectory.
 * angles are measured from the zero set with "set zero here".
 */
export function AnglePanel({ ax, active }: { ax: number; active: boolean }) {
  const profile = useApp((s) => s.profile)!
  const origin = useApp((s) => s.status?.safety.origin?.[ax] ?? 0)
  const [pos, iq, kt, velLim, cm, im] = useAliasLatest([`pos.${ax}`, `iq.${ax}`, `kt.${ax}`, `vel_limit.${ax}`, `ctrl_mode.${ax}`, `input_mode.${ax}`], 8)
  const ratio = Number(profile.gear.ratio ?? 30)
  const eff = Number(profile.gear.efficiency ?? 0.87)
  const [target, setTarget] = useState(0)
  const [path, setPath] = useState<PathMode>('short')
  const [speed, setSpeed] = useState(30)
  const [accel, setAccel] = useState(60)
  const [curA, setCurA] = useState(Math.min(6, profile.motor.current_continuous_a))
  const [busy, setBusy] = useState(false)

  const joint = ((num(pos) - origin) * 360) / ratio
  const delta = Number.isFinite(joint) ? angleDelta(joint, target, path) : NaN
  const winLo = (profile.limits.pos_min_turns * 360) / ratio
  const winHi = (profile.limits.pos_max_turns * 360) / ratio
  const ktv = num(kt) > 0 ? num(kt) : profile.derived.kt_nm_per_a
  const toMotor = (deg: number) => (deg * ratio) / 360

  const go = async () => {
    setBusy(true)
    try {
      const vel = toMotor(speed)
      const acc = toMotor(accel)
      await act('write', { path: `axis${ax}.trap_traj.config.vel_limit`, value: vel })
      // equal accel and decel: fw 0.5.x trajectories oscillate when accel < decel
      await act('write', { path: `axis${ax}.trap_traj.config.accel_limit`, value: acc })
      await act('write', { path: `axis${ax}.trap_traj.config.decel_limit`, value: acc })
      if (num(velLim) < vel * 1.2) await act('write', { path: P(`vel_limit.${ax}`), value: vel * 1.2 })
      await act('write', { path: P(`current_lim.${ax}`), value: curA })
      if (num(cm) !== 3) await act('write', { path: P(`ctrl_mode.${ax}`), value: 3 })
      if (num(im) !== 5) await act('write', { path: P(`input_mode.${ax}`), value: 5 })
      await act('setpoint', { axis: ax, kind: 'pos', value: num(pos) + toMotor(delta) })
    } catch {
      // the message bar shows why (limits, confirmation cancelled, outside window)
    } finally {
      setBusy(false)
    }
  }
  const stop = () => act('setpoint', { axis: ax, kind: 'pos', value: num(pos) }).catch(() => undefined)

  return (
    <div className="col">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>
          JOINT DEGREES AT THE {ratio}:1 OUTPUT · MEASURED FROM YOUR ZERO · WINDOW {fmt(winLo, 0)}° … {fmt(winHi, 0)}°
        </span>
        <Button small onClick={() => act('set_origin', { axis: ax }).catch(() => undefined)} title="Make the current rotor position 0° (resets when the board reconnects)">
          set zero here
        </Button>
      </div>

      {field(
        'target angle',
        <div className="row" style={{ gap: 6 }}>
          <NumInput value={target} onCommit={setTarget} width={80} />
          {[-90, -45, -15, 0, 15, 45, 90].map((d) => (
            <Button key={d} small kind={target === d ? 'on' : 'chip'} onClick={() => setTarget(d)}>
              {d > 0 ? `+${d}` : d}
            </Button>
          ))}
        </div>,
        'deg',
      )}
      {field(
        'path',
        <Segmented
          options={[
            ['short', 'shortest'],
            ['cw', '+ only (cw)'],
            ['ccw', '− only (ccw)'],
            ['abs', 'absolute'],
          ]}
          value={path}
          onChange={(v) => setPath(v as PathMode)}
        />,
        '',
      )}
      {field('speed', <NumInput value={speed} onCommit={(v) => setSpeed(Math.max(1, Math.min((profile.limits.vel_max_turns_s * 360) / ratio, v)))} width={80} />, 'deg/s (joint)')}
      {field('acceleration', <NumInput value={accel} onCommit={(v) => setAccel(Math.max(1, v))} width={80} />, 'deg/s² (joint)')}
      {field(
        'current limit',
        <NumInput value={curA} onCommit={(v) => setCurA(Math.max(0.5, Math.min(profile.motor.current_peak_a, v)))} width={80} />,
        `A ≈ ${fmt(curA * ktv * ratio * eff, 1)} Nm joint`,
      )}

      <div className="row" style={{ marginTop: 4 }}>
        <Button kind="primary" disabled={!active || busy || !Number.isFinite(delta)} onClick={go}>
          go to {fmt(target, 1)}°
        </Button>
        <Button disabled={!active} onClick={stop}>
          stop here
        </Button>
        {!active && <Tag level="warn">enter closed loop first</Tag>}
      </div>

      <div className="stat-strip num" style={{ marginTop: 6 }}>
        <div className="cell">
          <span className="k">joint now</span>
          <span className="v">{fmt(joint, 2)}°</span>
        </div>
        <div className="cell">
          <span className="k">move</span>
          <span className="v">{fmt(delta, 2)}°</span>
        </div>
        <div className="cell">
          <span className="k">motor turns</span>
          <span className="v">{fmt(num(pos) - origin, 3)}</span>
        </div>
        <div className="cell">
          <span className="k">Iq · joint torque</span>
          <span className="v">
            {fmt(iq, 2)} A · {fmt(num(iq) * ktv * ratio * eff, 2)} Nm
          </span>
        </div>
      </div>
    </div>
  )
}

/** push mode for torque tests: approach the load slowly, push with set currents, enter the scale reading */
export function PushPanel({ ax }: { ax: number }) {
  const profile = useApp((s) => s.profile)!
  const runner = useJobRunner(`control.push.${ax}`)
  const [kt] = useAliasLatest([`kt.${ax}`], 2)
  const ratio = Number(profile.gear.ratio ?? 30)
  const eff = Number(profile.gear.efficiency ?? 0.87)
  const ktv = num(kt) > 0 ? num(kt) : profile.derived.kt_nm_per_a
  const [dir, setDir] = useState(1)
  const [approach, setApproach] = useState(10)
  const [currents, setCurrents] = useState('2, 4, 6')
  const [ramp, setRamp] = useState(1)
  const [maxTravel, setMaxTravel] = useState(30)
  const [arm, setArm] = useState(0.2)
  const [ret, setRet] = useState(1)
  const list = currents
    .split(/[ ,;]+/)
    .map(Number)
    .filter((x) => Number.isFinite(x) && x > 0)
  const maxI = list.length ? Math.max(...list) : 0
  const points: any[] = runner.result?.points ?? []

  return (
    <div className="col">
      <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>
        TORQUE MODE WITH A SPEED CAP: TRAVELS AT THE APPROACH SPEED UNTIL IT MEETS THE LOAD, THEN PRESSES WITH THE SET CURRENT
      </span>
      {field(
        'push direction',
        <Segmented
          options={[
            [1, '+ (cw)'],
            [-1, '− (ccw)'],
          ]}
          value={dir}
          onChange={setDir}
        />,
        '',
      )}
      {field('approach speed', <NumInput value={approach} onCommit={(v) => setApproach(Math.max(0.5, Math.min(60, v)))} width={80} />, 'deg/s (joint)')}
      {field('push currents', <input value={currents} onChange={(e) => setCurrents(e.target.value)} />, `A (max ${profile.motor.current_continuous_a})`)}
      {field('force ramp', <NumInput value={ramp} onCommit={(v) => setRamp(Math.max(0.1, Math.min(10, v)))} width={80} />, 's per step')}
      {field('max travel before contact', <NumInput value={maxTravel} onCommit={(v) => setMaxTravel(Math.max(1, Math.min(360, v)))} width={80} />, 'deg (joint)')}
      {field('lever arm', <NumInput value={arm} onCommit={(v) => setArm(Math.max(0, v))} width={80} />, 'm (joint axis → scale contact)')}
      {field(
        'after the test',
        <Segmented
          options={[
            [1, 'return to start'],
            [0, 'stay (idle)'],
          ]}
          value={ret}
          onChange={setRet}
        />,
        '',
      )}
      <span className="muted" style={{ fontSize: 'var(--fs-tick)' }}>
        Highest step: {fmt(maxI, 1)} A ≈ {fmt(maxI * ktv * ratio * eff, 2)} Nm at the joint
        {arm > 0 ? ` ≈ ${fmt((maxI * ktv * ratio * eff) / (arm * 9.81), 2)} kg on the scale` : ''} (estimate with {fmt(eff * 100, 0)} % gear efficiency). Enter
        each scale reading in the job prompt.
      </span>
      <div className="row" style={{ marginTop: 4 }}>
        <Button
          kind="primary"
          disabled={runner.busy || !list.length}
          onClick={() =>
            runner.run('push_test', {
              axis: ax,
              direction: dir,
              approach_deg_s: approach,
              currents: list,
              ramp_s: ramp,
              max_travel_deg: maxTravel,
              arm_length_m: arm,
              return_to_start: Boolean(ret),
            })
          }
        >
          {runner.busy ? 'pushing...' : 'run push test'}
        </Button>
        <Button kind="danger" onClick={() => act('disarm', { reason: 'push test stop' })}>
          stop (idle)
        </Button>
      </div>
      {points.length > 0 && (
        <table className="num" style={{ marginTop: 6 }}>
          <thead>
            <tr>
              <th>cmd A</th>
              <th>Iq A</th>
              <th>travel °</th>
              <th>joint est Nm</th>
              <th>scale kg</th>
              <th>joint meas Nm</th>
              <th>gear eff</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.current_cmd}>
                <td>{fmt(p.current_cmd, 1)}</td>
                <td>{fmt(p.iq, 2)}</td>
                <td>{fmt(p.travel_deg, 1)}</td>
                <td>{fmt(p.joint_torque_est_nm, 2)}</td>
                <td>{p.scale_kg != null ? fmt(p.scale_kg, 2) : '--'}</td>
                <td>{p.joint_torque_meas_nm != null ? fmt(p.joint_torque_meas_nm, 2) : '--'}</td>
                <td>{p.efficiency != null ? `${fmt(p.efficiency * 100, 1)} %` : '--'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {runner.result?.kt_out_nm_per_a != null && (
        <span className="num" style={{ marginTop: 4 }}>
          output Kt {fmt(runner.result.kt_out_nm_per_a, 3)} Nm/A (ideal {fmt(runner.result.kt_ideal_out, 3)}) · efficiency{' '}
          {fmt(runner.result.efficiency * 100, 1)} % · r² {fmt(runner.result.r2, 3)}
        </span>
      )}
    </div>
  )
}
