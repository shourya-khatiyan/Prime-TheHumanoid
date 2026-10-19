import { useEffect, useRef, useState } from 'react'
import { Button, NumInput, Panel, PropInput, Segmented, Tabs, Tag, Value } from '../primitives'
import { ControlTwin } from '../components/SimTwins'
import { act, P, startJob, useAliasLatest, useApp, useJobRunner, useLatest } from '../lib/store'
import { AXIS_STATES, enumDef } from '../lib/meta'
import { fmt, num } from '../lib/format'
import { CurrentPlot, MotionPlot } from './panels'
import { AnglePanel, PushPanel } from './AnglePush'

const KIND = { 1: 'torque', 2: 'vel', 3: 'pos' } as const

/** live-editable property row */
function PropRow({ path, label }: { path: string; label?: string }) {
  const meta = useApp((s) => s.meta)
  const tree = useApp((s) => s.tree)
  const [v] = useLatest([path], 4)
  if (!path || !tree[path]) return null
  return (
    <div className="field">
      <label title={path}>{label ?? path.split('.').slice(-1)[0]}</label>
      <PropInput meta={meta} path={path} type={tree[path].type} value={v} onCommit={(nv) => act('write', { path, value: nv }).catch(() => undefined)} />
      <span className="unit">{meta?.props[path]?.unit ?? ''}</span>
    </div>
  )
}

/**
 * setpoint slider + number, limited by the profile envelope.
 * converts between motor shaft turns/torque and 30:1 (6:1 x 5:1) output joint degrees/torque.
 */
function Setpoint({ ax, kind, active }: { ax: number; kind: 'pos' | 'vel' | 'torque'; active: boolean }) {
  const profile = useApp((s) => s.profile)!
  const [cur, iqSet, iqMeas, curLim, ktDev, posMeas, velMeas] = useAliasLatest(
    [`input_${kind}.${ax}`, `iq_set.${ax}`, `iq.${ax}`, `current_lim.${ax}`, `kt.${ax}`, `pos.${ax}`, `vel.${ax}`],
    8,
  )
  const origin = useApp((s) => s.status?.safety.origin?.[ax] ?? 0)
  const kt = Number.isFinite(num(ktDev)) && num(ktDev) > 0 ? num(ktDev) : profile.derived.kt_nm_per_a
  const ratio = Number(profile.gear.ratio ?? 30)
  const eff = Number(profile.gear.efficiency ?? 0.87)
  const maxCurA = Number.isFinite(num(curLim)) && num(curLim) > 0 ? Math.min(num(curLim), profile.motor.current_peak_a) : profile.motor.current_continuous_a

  const lo = kind === 'pos' ? origin + profile.limits.pos_min_turns : kind === 'vel' ? -profile.limits.vel_max_turns_s : -(maxCurA * kt)
  const hi = kind === 'pos' ? origin + profile.limits.pos_max_turns : kind === 'vel' ? profile.limits.vel_max_turns_s : maxCurA * kt
  const [slider, setSlider] = useState(0)
  useEffect(() => setSlider(num(cur) || 0), [cur])
  const send = (v: number) => act('setpoint', { axis: ax, kind, value: v }).catch(() => undefined)
  const sendCurrentA = (amps: number) => send(amps * kt)

  if (kind === 'torque') {
    const cmdTorque = Number.isFinite(num(cur)) ? num(cur) : 0
    const cmdAmps = kt > 0 ? cmdTorque / kt : 0
    const cmdJointNm = cmdTorque * ratio * eff
    const measAmps = Number.isFinite(num(iqMeas)) ? num(iqMeas) : 0
    const measTorque = measAmps * kt
    const measJointNm = measTorque * ratio * eff

    return (
      <div className="col">
        <div className="field">
          <label>desired current (Iq)</label>
          <div className="row" style={{ gap: 6 }}>
            <NumInput value={cmdAmps} onCommit={sendCurrentA} disabled={!active} width={96} />
            <Button small disabled={!active} onClick={() => send(0)}>
              zero (0 A)
            </Button>
          </div>
          <span className="unit">A (±{fmt(maxCurA, 0)}A)</span>
        </div>

        <div className="field">
          <label>desired motor torque (Iq × Kt)</label>
          <NumInput value={cmdTorque} onCommit={send} disabled={!active} width={96} />
          <span className="unit">Nm (Kt={fmt(kt, 4)})</span>
        </div>

        <PropRow path={P(`vel_limit.${ax}`)} label="speed cap (vel_limit)" />
        <span className="muted" style={{ fontSize: 'var(--fs-tick)' }}>
          With no load, any torque above friction accelerates the rotor until this speed cap. Under load (stick on the scale) the torque presses instead of
          spinning. Keep the cap low (1-2 turn/s) for torque tests.
        </span>

        <input
          type="range"
          min={-maxCurA}
          max={maxCurA}
          step={maxCurA / 500}
          value={kt > 0 ? slider / kt : 0}
          disabled={!active}
          onChange={(e) => setSlider(Number(e.target.value) * kt)}
          onPointerUp={() => send(slider)}
          onKeyUp={() => send(slider)}
          style={{ width: '100%' }}
        />

        <div className="row" style={{ gap: 5 }}>
          <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>PRESETS:</span>
          {[-12, -6, -3, -1, 0, 1, 3, 6, 12].map((a) => (
            <Button key={a} small disabled={!active || Math.abs(a) > maxCurA} kind={Math.abs(cmdAmps - a) < 0.05 && a !== 0 ? 'on' : 'chip'} onClick={() => sendCurrentA(a)}>
              {a > 0 ? `+${a}A` : `${a}A`}
            </Button>
          ))}
        </div>

        <div className="stat-strip num" style={{ marginTop: 4 }}>
          <div className="cell">
            <span className="k">cmd Iq / trq</span>
            <span className="v">
              {fmt(cmdAmps, 2)}A · {fmt(cmdTorque, 2)}Nm
            </span>
          </div>
          <div className="cell">
            <span className="k">cmd joint ({ratio}:1)</span>
            <span className="v">{fmt(cmdJointNm, 2)} Nm</span>
          </div>
          <div className="cell">
            <span className="k">meas Iq ({fmt(iqSet, 1)}A)</span>
            <span className="v">{fmt(measAmps, 2)} A</span>
          </div>
          <div className="cell">
            <span className="k">meas joint trq</span>
            <span className="v">{fmt(measJointNm, 2)} Nm</span>
          </div>
        </div>
      </div>
    )
  }

  // joint angles are measured from the zero set with "set zero here"; speeds need no offset
  const zero = kind === 'pos' ? origin : 0
  const cmdVal = Number.isFinite(num(cur)) ? num(cur) : 0
  const cmdJoint = ((cmdVal - zero) * 360) / ratio
  const measVal = kind === 'pos' ? num(posMeas) : num(velMeas)
  const measJoint = Number.isFinite(measVal) ? ((measVal - zero) * 360) / ratio : undefined

  return (
    <div className="col">
      <div className="field">
        <label>{kind === 'pos' ? 'motor target (input_pos)' : 'motor speed (input_vel)'}</label>
        <div className="row" style={{ gap: 6 }}>
          <NumInput value={cmdVal} onCommit={send} disabled={!active} width={96} />
          <Button small disabled={!active} onClick={() => send(kind === 'pos' ? num(posMeas) || 0 : 0)}>
            {kind === 'pos' ? 'hold here' : 'zero'}
          </Button>
        </div>
        <span className="unit">{kind === 'pos' ? 'turn' : 'turn/s'}</span>
      </div>

      <div className="field">
        <label>{kind === 'pos' ? `joint target (${ratio}:1)` : `joint speed (${ratio}:1)`}</label>
        <NumInput value={cmdJoint} onCommit={(deg) => send(zero + (deg / 360) * ratio)} disabled={!active} width={96} />
        <span className="unit">{kind === 'pos' ? 'deg' : 'deg/s'}</span>
      </div>

      <input
        type="range"
        min={lo}
        max={hi}
        step={(hi - lo) / 2000}
        value={slider}
        disabled={!active}
        onChange={(e) => setSlider(Number(e.target.value))}
        onPointerUp={() => send(slider)}
        onKeyUp={() => send(slider)}
        style={{ width: '100%' }}
      />

      <div className="stat-strip num" style={{ marginTop: 2 }}>
        <div className="cell">
          <span className="k">cmd motor</span>
          <span className="v">
            {fmt(cmdVal, 3)} {kind === 'pos' ? 'trn' : 't/s'}
          </span>
        </div>
        <div className="cell">
          <span className="k">meas motor</span>
          <span className="v">
            {fmt(measVal, 3)} {kind === 'pos' ? 'trn' : 't/s'}
          </span>
        </div>
        <div className="cell">
          <span className="k">cmd joint</span>
          <span className="v">
            {fmt(cmdJoint, 1)} {kind === 'pos' ? '°' : '°/s'}
          </span>
        </div>
        <div className="cell">
          <span className="k">meas joint</span>
          <span className="v">
            {fmt(measJoint, 1)} {kind === 'pos' ? '°' : '°/s'}
          </span>
        </div>
      </div>
    </div>
  )
}

function Jog({ ax, kind, active }: { ax: number; kind: 'pos' | 'vel' | 'torque'; active: boolean }) {
  const [posSet] = useAliasLatest([`input_pos.${ax}`], 8)
  const [jogV, setJogV] = useState(0.5)
  const send = (v: number) => act('setpoint', { axis: ax, kind, value: v }).catch(() => undefined)
  if (kind === 'pos')
    return (
      <div className="row" style={{ gap: 5 }}>
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>JOG STEP (TURN):</span>
        {[-1, -0.1, -0.01, 0.01, 0.1, 1].map((d) => (
          <Button key={d} small kind="chip" disabled={!active} onClick={() => send((num(posSet) || 0) + d)}>
            {d > 0 ? `+${d}` : d}
          </Button>
        ))}
      </div>
    )
  if (kind === 'vel')
    return (
      <div className="row" style={{ gap: 6 }}>
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>HOLD TO JOG:</span>
        {[-1, 1].map((s) => (
          <button key={s} className="btn small" disabled={!active} onPointerDown={() => send(s * jogV)} onPointerUp={() => send(0)} onPointerLeave={() => send(0)}>
            {s < 0 ? '<< rev' : 'fwd >>'}
          </button>
        ))}
        <NumInput value={jogV} onCommit={setJogV} width={70} />
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>turn/s</span>
      </div>
    )
  return null
}

/** client-side square/sine generator on the active setpoint (backend still clamps every value) */
function Generator({ ax, kind, active }: { ax: number; kind: 'pos' | 'vel' | 'torque'; active: boolean }) {
  const [shape, setShape] = useState<'square' | 'sine'>('square')
  const [amp, setAmp] = useState(kind === 'pos' ? 0.1 : kind === 'vel' ? 0.5 : 0.02)
  const [freq, setFreq] = useState(0.5)
  const [offset, setOffset] = useState(0)
  const [running, setRunning] = useState(false)
  const timer = useRef(0)
  const inFlight = useRef(false)
  const [posNow] = useAliasLatest([`pos.${ax}`], 2)
  useEffect(() => {
    if (!running) return
    const t0 = performance.now()
    const base = kind === 'pos' ? (num(posNow) || 0) + offset : offset
    timer.current = window.setInterval(() => {
      // skip this tick while the last setpoint is unanswered, so a slow link never builds a queue of stale setpoints
      if (inFlight.current) return
      const t = (performance.now() - t0) / 1000
      const ph = 2 * Math.PI * freq * t
      const v = base + (shape === 'sine' ? amp * Math.sin(ph) : Math.sin(ph) >= 0 ? amp : -amp)
      inFlight.current = true
      act('setpoint', { axis: ax, kind, value: v }, true)
        .catch(() => setRunning(false))
        .finally(() => (inFlight.current = false))
    }, 20)
    return () => clearInterval(timer.current)
  }, [running])
  useEffect(() => {
    if (!active) setRunning(false)
  }, [active])
  return (
    <div className="col" style={{ borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 4 }}>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>WAVEFORM GENERATOR (UP TO 50 HZ STREAM)</span>
        <Button small kind={running ? 'on' : 'primary'} disabled={!active} onClick={() => setRunning(!running)}>
          {running ? 'stop wave' : 'start wave'}
        </Button>
      </div>
      <div className="row" style={{ gap: 8 }}>
        <Segmented
          disabled={running}
          options={[
            ['square', 'square'],
            ['sine', 'sine'],
          ]}
          value={shape}
          onChange={setShape}
        />
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>AMP</span>
        <NumInput value={amp} onCommit={setAmp} width={64} disabled={running} />
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>FREQ</span>
        <NumInput value={freq} onCommit={(v) => setFreq(Math.min(10, Math.max(0.05, v)))} width={56} disabled={running} />
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>HZ · OFFSET</span>
        <NumInput value={offset} onCommit={setOffset} width={56} disabled={running} />
      </div>
    </div>
  )
}

/** sensorless open-loop spin (LOCKIN_SPIN, state 9) that works without an encoder */
function OpenLoopPanel({ ax }: { ax: number }) {
  const profile = useApp((s) => s.profile)!
  const runner = useJobRunner(`control.openloop.${ax}`)
  const [encMode, spiErr, state, iq] = useAliasLatest([`enc_mode.${ax}`, `spi_err.${ax}`, `state.${ax}`, `iq.${ax}`], 8)
  const [vel, setVel] = useState(0.5)
  const [cur, setCur] = useState(3.0)
  const [turns, setTurns] = useState(2.0)
  const [dur, setDur] = useState(4.0)
  const maxCur = profile.motor.current_continuous_a ?? 12
  const maxVel = profile.limits.vel_max_turns_s ?? 30
  // mode 0 only means "spi bypassed" when the profile expects an spi encoder; for abz wiring it is the normal mode
  const bypassed = num(encMode) === 0 && String(profile.encoder?.mode ?? '').startsWith('SPI')
  const spiBad = num(encMode) >= 256 && num(spiErr) > 0.01
  const spinning = num(state) === 9 || runner.busy

  const restoreSpi = async () => {
    await act('write', { path: P(`enc_mode.${ax}`), value: 257 })
    await act('call', { path: 'save_configuration', args: [] })
    await act('call', { path: 'reboot', args: [] }).catch(() => undefined)
  }

  return (
    <div className="col">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>
          DRIVES ROTATING CURRENT VECTOR DIRECTLY (NO ENCODER REQUIRED)
        </span>
        {num(encMode) === 0 ? (
          <Tag level="info">enc mode 0 (ABZ)</Tag>
        ) : spiBad ? (
          <Tag level="warn">spi fault (auto-bypass)</Tag>
        ) : (
          <Tag level="quiet">spi mode {fmt(encMode, 0)}</Tag>
        )}
      </div>

      <div className="field">
        <label>speed (+fwd / -rev)</label>
        <div className="row" style={{ gap: 6 }}>
          <NumInput value={vel} onCommit={(v) => setVel(Math.max(-maxVel, Math.min(maxVel, v)))} width={70} disabled={spinning} />
          <Segmented
            disabled={spinning}
            options={[
              [-1, '-1'],
              [-0.5, '-0.5'],
              [0.5, '+0.5'],
              [1, '+1'],
            ]}
            value={vel}
            onChange={setVel}
          />
        </div>
        <span className="unit">turn/s</span>
      </div>

      <div className="field">
        <label>phase current</label>
        <div className="row" style={{ gap: 6 }}>
          <NumInput value={cur} onCommit={(v) => setCur(Math.max(0.5, Math.min(maxCur, v)))} width={70} disabled={spinning} />
          <Segmented
            disabled={spinning}
            options={[
              [3, '3A'],
              [6, '6A'],
              [9, '9A'],
              [12, '12A'],
            ]}
            value={cur}
            onChange={setCur}
          />
        </div>
        <span className="unit">A (max {maxCur})</span>
      </div>

      <div className="field">
        <label>target distance (0 = timed)</label>
        <div className="row" style={{ gap: 6 }}>
          <NumInput value={turns} onCommit={(v) => setTurns(Math.max(0, Math.min(50, v)))} width={70} disabled={spinning} />
          <Segmented
            disabled={spinning}
            options={[
              [1, '1 trn'],
              [2, '2 trn'],
              [5, '5 trn'],
              [0, 'timed'],
            ]}
            value={turns}
            onChange={setTurns}
          />
          {turns === 0 && <NumInput value={dur} onCommit={(v) => setDur(Math.max(0.5, Math.min(30, v)))} width={56} disabled={spinning} />}
        </div>
        <span className="unit">{turns === 0 ? 's' : 'turns'}</span>
      </div>

      <div className="row" style={{ marginTop: 4 }}>
        <Button
          kind="primary"
          disabled={spinning}
          onClick={() => runner.run('open_loop', { axis: ax, current_a: cur, vel_turns_s: vel, turns, duration_s: dur })}
        >
          {spinning ? 'spinning...' : 'spin open loop'}
        </Button>
        <Button kind="danger" onClick={() => act('disarm', { reason: 'open-loop stop' })}>
          stop (idle)
        </Button>
        {bypassed && (
          <Button small onClick={() => restoreSpi().catch(() => undefined)} title="Switch axis encoder back to SPI_ABS_AMS (257), save and reboot">
            restore spi encoder
          </Button>
        )}
      </div>

      <div className="stat-strip num" style={{ marginTop: 6 }}>
        <div className="cell">
          <span className="k">live Iq</span>
          <span className="v">{fmt(iq, 2)} A</span>
        </div>
        <div className="cell">
          <span className="k">last avg Iq</span>
          <span className="v">{runner.result ? `${fmt(runner.result.iq_avg, 2)} A` : '--'}</span>
        </div>
        <div className="cell">
          <span className="k">peak Iq</span>
          <span className="v">{runner.result ? `${fmt(runner.result.iq_peak, 2)} A` : '--'}</span>
        </div>
        <div className="cell">
          <span className="k">counts / turn</span>
          <span className="v">{runner.result?.counts_per_turn != null ? fmt(runner.result.counts_per_turn, 0) : '--'}</span>
        </div>
        <div className="cell">
          <span className="k">status</span>
          <span className="v">{runner.result ? (runner.result.ok ? 'PASS' : 'FAULT') : 'READY'}</span>
        </div>
      </div>
    </div>
  )
}

/** interactive encoder setup panel: switch between INCREMENTAL (J4 M0 A/B/Z) and SPI_ABS_AMS (J3 SPI), edit CPR / CS pin, and watch live A/B/Z pins */
function EncoderSetupPanel({ ax }: { ax: number }) {
  const runner = useJobRunner(`control.encsetup.${ax}`)
  const [devMode, devCpr, devCs, devIdx, shadow, inCpr, posAbs, hall, encReady] = useAliasLatest(
    [`enc_mode.${ax}`, `enc_cpr.${ax}`, `enc_cs.${ax}`, `enc_use_index.${ax}`, `shadow.${ax}`, `count_in_cpr.${ax}`, `pos_abs.${ax}`, `hall_state.${ax}`, `enc_ready.${ax}`],
    10,
  )
  const [mode, setMode] = useState<'INCREMENTAL' | 'SPI_ABS_AMS'>('INCREMENTAL')
  const [cpr, setCpr] = useState(4000)
  const [useIdx, setUseIdx] = useState(false)
  const [csPin, setCsPin] = useState(4)
  const syncedRef = useRef(false)

  useEffect(() => {
    if (!syncedRef.current && devMode !== undefined) {
      syncedRef.current = true
      const m = num(devMode) >= 256 ? 'SPI_ABS_AMS' : 'INCREMENTAL'
      setMode(m)
      if (num(devCpr) > 0) setCpr(num(devCpr))
      if (devIdx !== undefined) setUseIdx(Boolean(devIdx))
      if (num(devCs) > 0) setCsPin(num(devCs))
    }
  }, [devMode, devCpr, devCs, devIdx])

  const switchMode = (m: 'INCREMENTAL' | 'SPI_ABS_AMS') => {
    setMode(m)
    if (m === 'INCREMENTAL' && cpr === 16384) setCpr(4000)
    if (m === 'SPI_ABS_AMS' && cpr !== 16384) setCpr(16384)
  }

  const h = Number.isFinite(num(hall)) ? Math.trunc(num(hall)) : 0
  const pinA = h & 1
  const pinB = (h >> 1) & 1
  const pinZ = (h >> 2) & 1

  return (
    <div className="col">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>
          {mode === 'INCREMENTAL'
            ? 'ABZ USES DEDICATED J4 M0 (A / B / Z) PINS — GPIO 4 IS NOT USED'
            : 'SPI USES J3 (SCK / MISO / MOSI) + CS ON GPIO PIN'}
        </span>
        <Tag level={encReady ? 'info' : 'quiet'}>{encReady ? 'enc ready' : `mode ${fmt(devMode, 0)}`}</Tag>
      </div>

      <div className="field">
        <label>encoder interface</label>
        <Segmented
          disabled={runner.busy}
          options={[
            ['INCREMENTAL', 'incremental (J4 A/B/Z)'],
            ['SPI_ABS_AMS', 'spi abs (J3 + CS GPIO)'],
          ]}
          value={mode}
          onChange={switchMode}
        />
        <span />
      </div>

      <div className="field">
        <label>cpr (counts / rev)</label>
        <div className="row" style={{ gap: 6 }}>
          <NumInput value={cpr} onCommit={(v) => setCpr(Math.max(16, Math.trunc(v)))} width={80} disabled={runner.busy} />
          {(mode === 'INCREMENTAL' ? [4000, 4096, 2000] : [16384, 4096]).map((v) => (
            <Button key={v} small kind={cpr === v ? 'on' : 'chip'} disabled={runner.busy} onClick={() => setCpr(v)}>
              {v}
            </Button>
          ))}
        </div>
        <span className="unit">{mode === 'INCREMENTAL' ? '4×PPR' : '14-bit'}</span>
      </div>

      {mode === 'INCREMENTAL' ? (
        <div className="field">
          <label>use_index (Z pulse)</label>
          <Segmented
            disabled={runner.busy}
            options={[
              [0, 'off (A/B only)'],
              [1, 'on (requires Z search)'],
            ]}
            value={useIdx ? 1 : 0}
            onChange={(v) => setUseIdx(Boolean(v))}
          />
          <span className="unit">J4 M0 Z</span>
        </div>
      ) : (
        <div className="field">
          <label>abs_spi_cs_gpio_pin</label>
          <div className="row" style={{ gap: 6 }}>
            <NumInput value={csPin} onCommit={(v) => setCsPin(Math.max(1, Math.min(8, Math.trunc(v))))} width={56} disabled={runner.busy} />
            <Segmented
              disabled={runner.busy}
              options={[
                [3, 'gpio3'],
                [4, 'gpio4'],
                [5, 'gpio5'],
                [6, 'gpio6'],
                [7, 'gpio7'],
                [8, 'gpio8'],
              ]}
              value={csPin}
              onChange={setCsPin}
            />
          </div>
          <span className="unit">J3 GPIO</span>
        </div>
      )}

      <div className="row" style={{ marginTop: 4 }}>
        <Button
          kind="primary"
          disabled={runner.busy}
          onClick={async () => {
            await runner.run('encoder_setup', { axis: ax, mode, cpr, use_index: useIdx, cs_gpio: csPin })
            const p = await act('profile_get', {}, true).catch(() => null)
            if (p) useApp.setState({ profile: p })
          }}
        >
          {runner.busy ? 'saving & rebooting...' : 'apply & save encoder'}
        </Button>
        <Button
          kind="primary"
          small
          disabled={runner.busy}
          onClick={() => startJob('calibrate', { axis: ax, kind: 'encoder', mark_precalibrated: true }).catch(() => undefined)}
        >
          calibrate offset
        </Button>
      </div>

      <div className="stat-strip num" style={{ marginTop: 6 }}>
        <div className="cell">
          <span className="k">shadow_count</span>
          <span className="v">{fmt(shadow, 0)}</span>
        </div>
        <div className="cell">
          <span className="k">count_in_cpr</span>
          <span className="v">{fmt(inCpr, 0)}</span>
        </div>
        <div className="cell">
          <span className="k">J4 M0 A / B / Z</span>
          <span className="v">
            A:{pinA} · B:{pinB} · Z:{pinZ}
          </span>
        </div>
        <div className="cell">
          <span className="k">spi pos_abs</span>
          <span className="v">{fmt(posAbs, 0)}</span>
        </div>
      </div>
    </div>
  )
}

export function Control() {
  const ax = useApp((s) => s.axis)
  const meta = useApp((s) => s.meta)
  const profile = useApp((s) => s.profile)
  const active = useApp((s) => !!s.status?.safety.active_axes.includes(ax))
  const [state, cm, im, err, cal, ready, useIdx, idxFound] = useAliasLatest(
    [`state.${ax}`, `ctrl_mode.${ax}`, `input_mode.${ax}`, `error.${ax}`, `motor_cal.${ax}`, `enc_ready.${ax}`, `enc_use_index.${ax}`, `enc_index.${ax}`],
    8,
  )
  const [subTab, setSubTab] = useState<'drive' | 'angle' | 'openloop' | 'gains' | 'encoder'>('drive')
  const kind = KIND[num(cm) as 1 | 2 | 3] ?? 'pos'
  const imDef = enumDef(meta, P(`input_mode.${ax}`))
  const reqState = (s: number) => act('write', { path: P(`req_state.${ax}`), value: s }).catch(() => undefined)
  if (!profile) return <span className="muted">waiting for device</span>

  return (
    <div className="col" style={{ gap: 10 }}>
      <div className="view-head">
        <h1>CONTROL WORKBENCH</h1>
        <span className="sub">
          AXIS {ax} · {AXIS_STATES[num(state)] ?? '--'} · 30:1 (6:1 × 5:1 PLANETARY)
        </span>
        <div className="row" style={{ marginLeft: 'auto', gap: 8 }}>
          <span className={`tech-chip num ${cal ? 'on' : 'warn'}`}>MOT CAL: {cal ? 'YES' : 'NO'}</span>
          <span className={`tech-chip num ${ready ? 'on' : 'warn'}`}>ENC: {ready ? 'READY' : 'UNREADY'}</span>
          {Boolean(useIdx) && <span className={`tech-chip num ${idxFound ? 'on' : 'warn'}`}>INDEX: {idxFound ? 'FOUND' : 'NOT FOUND'}</span>}
          {num(err) !== 0 && <Tag level="alarm">FAULT</Tag>}
          {active && <Tag level="info">WATCHDOG FED</Tag>}
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

      {/* Unified Top Command & Calibration Bar */}
      <Panel index="00" title="AXIS STATE & CALIBRATION COMMAND BAR">
        <div className="row" style={{ justifyContent: 'space-between', gap: 12 }}>
          <div className="row" style={{ gap: 8 }}>
            <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>OPERATING STATE:</span>
            <Button kind={num(state) === 1 ? 'on' : 'danger'} onClick={() => reqState(1)}>
              idle (disarm)
            </Button>
            <Button kind={num(state) === 8 ? 'on' : 'primary'} onClick={() => reqState(8)}>
              closed loop
            </Button>
            <Button onClick={() => act('clear_errors', { axis: ax }).catch(() => undefined)}>clear errors</Button>
            <Button onClick={() => act('set_origin', { axis: ax }).catch(() => undefined)} title="Make the current rotor position the zero for angles and the position window">
              set zero here
            </Button>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <span className="muted" style={{ fontSize: 'var(--fs-micro)' }}>CALIBRATION:</span>
            <Button kind="primary" small onClick={() => startJob('calibrate', { axis: ax, kind: 'motor' }).catch(() => undefined)}>
              motor R/L
            </Button>
            {Boolean(useIdx) && (
              <Button kind={idxFound ? 'on' : 'primary'} small onClick={() => startJob('calibrate', { axis: ax, kind: 'index' }).catch(() => undefined)}>
                index search
              </Button>
            )}
            <Button kind="primary" small onClick={() => startJob('calibrate', { axis: ax, kind: 'encoder' }).catch(() => undefined)}>
              encoder offset
            </Button>
            <Button kind="primary" small onClick={() => startJob('calibrate', { axis: ax, kind: 'full' }).catch(() => undefined)}>
              full cal
            </Button>
          </div>
        </div>
      </Panel>

      {/* 2-Zone Split Workspace: Left = Focused Mode Deck; Right = Live Interactive 30:1 Twin + Synchronized Plots */}
      <div className="grid2">
        <div className="col" style={{ gap: 8 }}>
          <Tabs
            tabs={[
              ['drive', 'closed-loop drive'],
              ['angle', 'angle & push'],
              ['openloop', 'open-loop spin'],
              ['gains', 'gains & limits'],
              ['encoder', 'encoder setup'],
            ]}
            value={subTab}
            onChange={(v) => setSubTab(v as typeof subTab)}
          />

          {subTab === 'drive' && (
            <Panel
              index="01"
              title={`CLOSED-LOOP DRIVE · ${kind === 'torque' ? 'CURRENT / TORQUE' : kind.toUpperCase()}`}
              status={active ? 'live' : undefined}
            >
              <div className="col" style={{ gap: 10 }}>
                <div className="field">
                  <label>control mode</label>
                  <Segmented
                    options={[
                      [3, 'position'],
                      [2, 'velocity'],
                      [1, 'current / torque'],
                    ]}
                    value={num(cm)}
                    onChange={(v) => act('write', { path: P(`ctrl_mode.${ax}`), value: v })}
                  />
                  <span />
                </div>
                <div className="field">
                  <label>input mode</label>
                  <select value={String(im ?? '')} onChange={(e) => act('write', { path: P(`input_mode.${ax}`), value: Number(e.target.value) })}>
                    {imDef?.kind === 'enum' &&
                      Object.entries(imDef.values).map(([n, v]) => (
                        <option key={n} value={v}>
                          {n}
                        </option>
                      ))}
                  </select>
                  <span />
                </div>
                {!active && (
                  <div className="warn-text" style={{ fontSize: 'var(--fs-tick)', padding: '4px 8px', background: 'rgba(255, 176, 0, 0.08)', border: '1px solid var(--warn)' }}>
                    ▲ Setpoints are locked while IDLE. Click &quot;CLOSED LOOP&quot; above: it starts at rest (holds position, zero speed and torque), so a setpoint that faulted the axis is not re-applied. Use the 02 OPEN-LOOP SPIN tab to test without an encoder.
                  </div>
                )}
                <Setpoint ax={ax} kind={kind} active={active} />
                <Jog ax={ax} kind={kind} active={active} />
                <Generator key={kind} ax={ax} kind={kind} active={active} />
              </div>
            </Panel>
          )}

          {subTab === 'angle' && (
            <>
              <Panel index="05A" title="MOVE TO ANGLE (TRAPEZOIDAL TRAJECTORY)" status={active ? 'live' : undefined}>
                <AnglePanel ax={ax} active={active} />
              </Panel>
              <Panel index="05B" title="PUSH TEST (TORQUE AGAINST A SCALE)">
                <PushPanel ax={ax} />
              </Panel>
            </>
          )}

          {subTab === 'openloop' && (
            <Panel index="02" title="OPEN-LOOP SPIN (NO ENCODER REQUIRED)" status={num(state) === 9 ? 'live' : undefined}>
              <OpenLoopPanel ax={ax} />
            </Panel>
          )}

          {subTab === 'gains' && (
            <div className="col" style={{ gap: 10 }}>
              <Panel index="03A" title="CASCADED LOOP GAINS">
                <PropRow path={P(`pos_gain.${ax}`)} />
                <PropRow path={P(`vel_gain.${ax}`)} />
                <PropRow path={P(`vel_int_gain.${ax}`)} label="vel_integrator_gain" />
                <PropRow path={`axis${ax}.controller.config.input_filter_bandwidth`} />
                <PropRow path={`axis${ax}.controller.config.vel_ramp_rate`} />
                <PropRow path={`axis${ax}.controller.config.torque_ramp_rate`} />
              </Panel>
              <Panel index="03B" title="HARDWARE & TRAJECTORY LIMITS">
                <PropRow path={P(`vel_limit.${ax}`)} label="vel_limit (max speed)" />
                <PropRow path={`axis${ax}.controller.config.vel_limit_tolerance`} label="vel_limit_tolerance" />
                <PropRow path={`axis${ax}.controller.config.enable_overspeed_error`} label="enable_overspeed_error" />
                <PropRow path={P(`current_lim.${ax}`)} label="current_lim (max current)" />
                <PropRow path={`axis${ax}.motor.config.current_lim_margin`} label="current_lim_margin" />
                <PropRow path={P(`torque_mode_vel_limit.${ax}`)} label="torque-mode vel limit" />
                <PropRow path={`axis${ax}.encoder.config.calib_range`} label="encoder calib_range" />
                <PropRow path={`axis${ax}.trap_traj.config.vel_limit`} label="trap vel_limit" />
                <PropRow path={`axis${ax}.trap_traj.config.accel_limit`} label="trap accel_limit" />
                <PropRow path={`axis${ax}.trap_traj.config.decel_limit`} label="trap decel_limit" />
                <div className="row" style={{ marginTop: 8, paddingTop: 6, borderTop: '1px solid var(--border)' }}>
                  <Value k="profile vel max" v={profile.limits.vel_max_turns_s} u="turn/s" />
                  <Value k="profile current cont / peak" v={`${profile.motor.current_continuous_a} / ${profile.motor.current_peak_a}`} u="A" />
                  <Value k="joint peak (30:1)" v={fmt(profile.derived.joint_torque_peak_nm, 1)} u="Nm" />
                </div>
              </Panel>
            </div>
          )}

          {subTab === 'encoder' && (
            <Panel index="04" title="ENCODER INTERFACE SETUP (J4 ABZ / J3 SPI)">
              <EncoderSetupPanel ax={ax} />
            </Panel>
          )}
        </div>

        <div className="col" style={{ gap: 10 }}>
          <Panel index="SIM" title="LIVE 30:1 (6:1 × 5:1) SHOULDER & FOC VECTOR TWIN" status="live">
            <ControlTwin ax={ax} />
          </Panel>
          <div className="grid2">
            <Panel index="PLT" title="MOTION (POS / VEL)" flush>
              <div className="h-plot">
                <MotionPlot ax={ax} windowS={10} />
              </div>
            </Panel>
            <Panel index="PLT" title="CURRENT (IQ SET / MEAS)" flush>
              <div className="h-plot">
                <CurrentPlot ax={ax} windowS={10} />
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  )
}
