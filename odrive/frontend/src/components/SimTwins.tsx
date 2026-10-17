import { useEffect, useRef, useState } from 'react'
import { Panel, Segmented, Tag } from '../primitives'
import { act, useAliasLatest, useApp } from '../lib/store'
import { AXIS_STATES } from '../lib/meta'
import { fmt, num } from '../lib/format'

/** map temperature (25..90 C) to an infrared RGB string */
function tempColor(c: number, alpha = 1): string {
  const t = Math.max(0, Math.min(1, (c - 25) / 60))
  let r = 61
  let g = 245
  let b = 122
  if (t < 0.5) {
    const k = t / 0.5
    r = Math.round(45 + k * 210)
    g = Math.round(210 - k * 34)
    b = Math.round(130 - k * 110)
  } else {
    const k = (t - 0.5) / 0.5
    r = 255
    g = Math.round(176 - k * 110)
    b = Math.round(20 + k * 45)
  }
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/**
 * Interactive 30:1 (6:1 x 5:1 two-stage planetary) Humanoid Shoulder & FOC Vector Twin for the Control tab.
 * Left: LA8308 3-phase stator field, 20-pole-pair rotor, Iq vector, and Stage-1 (6:1) + Stage-2 (5:1) planetary carriers.
 * Right: Ø100 mm shoulder output arm with Ghost Target vs Measured Arm, torque arc, DRV5033 Hall homing sensor at 270 deg,
 * and click/drag target angle commanding.
 */
export function ControlTwin({ ax }: { ax: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const profile = useApp((s) => s.profile)
  const active = useApp((s) => !!s.status?.safety.active_axes.includes(ax))
  const [state, cm, pos, posSet, vel, iq, iqSet, fet, encReady] = useAliasLatest(
    [
      `state.${ax}`,
      `ctrl_mode.${ax}`,
      `pos.${ax}`,
      `input_pos.${ax}`,
      `vel.${ax}`,
      `iq.${ax}`,
      `iq_set.${ax}`,
      `fet_temp.${ax}`,
      `enc_ready.${ax}`,
    ],
    20,
  )
  const [dragCmd, setDragCmd] = useState(true)
  const [previewDeg, setPreviewDeg] = useState<number | null>(null)
  const draggingRef = useRef(false)

  const ratio = Number(profile?.gear.ratio ?? 30)
  const eff = Number(profile?.gear.efficiency ?? 0.87)
  const kt = Number(profile?.derived.kt_nm_per_a ?? 0.0919)
  const posTurns = Number.isFinite(num(pos)) ? num(pos) : 0
  const setTurns = Number.isFinite(num(posSet)) ? num(posSet) : 0
  const velTurns = Number.isFinite(num(vel)) ? num(vel) : 0
  const iqVal = Number.isFinite(num(iq)) ? num(iq) : 0
  const iqSetVal = Number.isFinite(num(iqSet)) ? num(iqSet) : 0
  const fetVal = Number.isFinite(num(fet)) ? num(fet) : 28
  const jointDeg = (posTurns * 360) / ratio
  const targetDeg = previewDeg !== null ? previewDeg : (setTurns * 360) / ratio
  const jointVelDeg = (velTurns * 360) / ratio
  const jointTorqueNm = iqVal * kt * ratio * eff

  const liveRef = useRef({
    posTurns,
    setTurns,
    velTurns,
    iqVal,
    iqSetVal,
    fetVal,
    jointDeg,
    targetDeg,
    jointVelDeg,
    jointTorqueNm,
    ratio,
    state: num(state),
    cm: num(cm),
    active,
  })
  liveRef.current = {
    posTurns,
    setTurns,
    velTurns,
    iqVal,
    iqSetVal,
    fetVal,
    jointDeg,
    targetDeg,
    jointVelDeg,
    jointTorqueNm,
    ratio,
    state: num(state),
    cm: num(cm),
    active,
  }

  const commandFromPointer = (clientX: number, clientY: number, commit: boolean) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const w = rect.width
    const h = rect.height
    const cx = w * 0.73
    const cy = h * 0.52
    const dx = clientX - rect.left - cx
    const dy = clientY - rect.top - cy
    const dist = Math.hypot(dx, dy)
    if (dist < 14 || dist > Math.min(w, h) * 0.48) return
    // 0 deg is straight up (-90 deg screen), clockwise positive
    const deg = ((Math.atan2(dy, dx) * 180) / Math.PI + 90 + 540) % 360 - 180
    setPreviewDeg(deg)
    if (commit) {
      setPreviewDeg(null)
      if (dragCmd && liveRef.current.active && liveRef.current.cm === 3) {
        const turns = (deg / 360) * ratio
        act('setpoint', { axis: ax, kind: 'pos', value: Number(turns.toFixed(4)) }).catch(() => undefined)
      }
    }
  }

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let spinPhase = 0
    let last = performance.now()

    const draw = (now: number) => {
      raf = requestAnimationFrame(draw)
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      const lv = liveRef.current
      if (lv.state === 9) {
        spinPhase += dt * 3.0
      }

      const dpr = window.devicePixelRatio || 1
      const w = wrap.clientWidth
      const h = wrap.clientHeight
      if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
        canvas.width = Math.floor(w * dpr)
        canvas.height = Math.floor(h * dpr)
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)

      const R = Math.min(w * 0.21, h * 0.37)
      const lx = w * 0.27
      const ly = h * 0.53
      const rx = w * 0.73
      const ry = h * 0.53

      const motorRad = lv.state === 9 ? spinPhase : lv.posTurns * Math.PI * 2
      const elecRad = motorRad * 20
      const carrier1Rad = motorRad / 6
      const carrier2Rad = motorRad / lv.ratio

      // ─── LEFT: LA8308 FOC STATOR + 2-STAGE PLANETARY (6:1 x 5:1 = 30:1) ───
      ctx.save()
      // Outer 90T Ring-1 housing circle
      ctx.strokeStyle = '#243a2d'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.arc(lx, ly, R * 1.04, 0, Math.PI * 2)
      ctx.stroke()

      // 12 Stator coils energized by 3-phase currents Ia, Ib, Ic
      const iqNorm = Math.min(1, Math.abs(lv.iqVal) / 12)
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2 - Math.PI * 0.5
        const phaseIdx = i % 3
        const phaseVal = Math.sin(elecRad - (phaseIdx * Math.PI * 2) / 3) * iqNorm
        const sx = lx + Math.cos(a) * (R * 0.92)
        const sy = ly + Math.sin(a) * (R * 0.92)
        ctx.fillStyle =
          phaseVal > 0.08
            ? `rgba(61, 245, 122, ${0.25 + Math.abs(phaseVal) * 0.7})`
            : phaseVal < -0.08
              ? `rgba(89, 200, 255, ${0.25 + Math.abs(phaseVal) * 0.7})`
              : 'rgba(36, 58, 45, 0.55)'
        ctx.beginPath()
        ctx.arc(sx, sy, R * 0.065, 0, Math.PI * 2)
        ctx.fill()
      }

      // Stage-1 Planetary (6:1): 3x 36T planets orbiting at carrier1Rad
      const rOrbit1 = R * 0.62
      const rPlanet1 = R * 0.17
      ctx.strokeStyle = 'rgba(142, 198, 157, 0.25)'
      ctx.setLineDash([2, 3])
      ctx.beginPath()
      ctx.arc(lx, ly, rOrbit1, 0, Math.PI * 2)
      ctx.stroke()
      ctx.setLineDash([])

      for (let p = 0; p < 3; p++) {
        const pa = carrier1Rad + (p * Math.PI * 2) / 3 - Math.PI * 0.5
        const px = lx + Math.cos(pa) * rOrbit1
        const py = ly + Math.sin(pa) * rOrbit1
        ctx.strokeStyle = '#588265'
        ctx.lineWidth = 1.2
        ctx.beginPath()
        ctx.arc(px, py, rPlanet1, 0, Math.PI * 2)
        ctx.stroke()
        // planet spin marker
        const pSpin = -motorRad * 0.5 + pa
        ctx.beginPath()
        ctx.moveTo(px, py)
        ctx.lineTo(px + Math.cos(pSpin) * rPlanet1, py + Math.sin(pSpin) * rPlanet1)
        ctx.stroke()
      }

      // Stage-2 Planetary (5:1): 3x 27T planets orbiting at carrier2Rad
      const rOrbit2 = R * 0.36
      const rPlanet2 = R * 0.1
      for (let p = 0; p < 3; p++) {
        const pa = carrier2Rad + (p * Math.PI * 2) / 3
        const px = lx + Math.cos(pa) * rOrbit2
        const py = ly + Math.sin(pa) * rOrbit2
        ctx.strokeStyle = '#3df57a'
        ctx.lineWidth = 1.2
        ctx.beginPath()
        ctx.arc(px, py, rPlanet2, 0, Math.PI * 2)
        ctx.stroke()
      }

      // Center 18T Sun-1 + motor shaft needle
      ctx.strokeStyle = '#d4f7dc'
      ctx.lineWidth = 1.8
      ctx.beginPath()
      ctx.arc(lx, ly, R * 0.16, 0, Math.PI * 2)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(lx, ly)
      ctx.lineTo(lx + Math.cos(motorRad - Math.PI * 0.5) * (R * 0.82), ly + Math.sin(motorRad - Math.PI * 0.5) * (R * 0.82))
      ctx.stroke()

      // Live Iq Quadrature Torque Vector arrow (perpendicular to rotor)
      if (Math.abs(lv.iqVal) > 0.05) {
        const iqAng = motorRad - Math.PI * 0.5 + (lv.iqVal >= 0 ? Math.PI * 0.5 : -Math.PI * 0.5)
        const iqLen = Math.min(R * 0.85, (Math.abs(lv.iqVal) / 12) * R * 0.85 + 12)
        const ix = lx + Math.cos(iqAng) * iqLen
        const iy = ly + Math.sin(iqAng) * iqLen
        ctx.strokeStyle = '#59c8ff'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(lx, ly)
        ctx.lineTo(ix, iy)
        ctx.stroke()
        ctx.fillStyle = '#59c8ff'
        ctx.beginPath()
        ctx.arc(ix, iy, 3, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.restore()

      // Center transmission link arrow (6:1 -> 5:1 = 30:1)
      ctx.strokeStyle = '#243a2d'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(lx + R * 1.15, ly)
      ctx.lineTo(rx - R * 1.15, ly)
      ctx.stroke()
      ctx.fillStyle = '#8ec69d'
      ctx.font = '600 9px "JetBrains Mono", monospace'
      ctx.textAlign = 'center'
      ctx.fillText('6:1 × 5:1', w * 0.5, ly - 6)
      ctx.fillStyle = '#588265'
      ctx.fillText('30:1 PLANETARY', w * 0.5, ly + 10)

      // ─── RIGHT: 30:1 HUMANOID SHOULDER OUTPUT ARM & TARGET DIAL ───
      ctx.save()
      // Protractor tick ring (-180..+180 deg)
      for (let d = 0; d < 360; d += 10) {
        const a = ((d - 90) * Math.PI) / 180
        const major = d % 30 === 0
        const r0 = R * (major ? 0.92 : 0.97)
        const r1 = R * 1.04
        ctx.strokeStyle = major ? '#3e634c' : '#1d2d23'
        ctx.lineWidth = major ? 1.4 : 1
        ctx.beginPath()
        ctx.moveTo(rx + Math.cos(a) * r0, ry + Math.sin(a) * r0)
        ctx.lineTo(rx + Math.cos(a) * r1, ry + Math.sin(a) * r1)
        ctx.stroke()
      }

      // DRV5033 Hall homing sensor marker at 270 deg (left side of flange)
      const hallAng = Math.PI
      const hx = rx + Math.cos(hallAng) * (R * 1.06)
      const hy = ry + Math.sin(hallAng) * (R * 1.06)
      const normJoint = ((lv.jointDeg % 360) + 360) % 360
      const hallTriggered = Math.abs(normJoint - 270) < 6
      ctx.fillStyle = hallTriggered ? '#3df57a' : '#588265'
      ctx.fillRect(hx - 4, hy - 4, 8, 8)

      // Torque envelope arc around output joint
      if (Math.abs(lv.jointTorqueNm) > 0.1) {
        const jRad = ((lv.jointDeg - 90) * Math.PI) / 180
        const span = Math.max(-Math.PI * 0.85, Math.min(Math.PI * 0.85, (lv.jointTorqueNm / 30) * Math.PI * 0.75))
        ctx.strokeStyle = Math.abs(lv.jointTorqueNm) > 30 ? '#ffb000' : '#59c8ff'
        ctx.lineWidth = 3.5
        ctx.beginPath()
        ctx.arc(rx, ry, R * 0.78, jRad, jRad + span, span < 0)
        ctx.stroke()
      }

      // Ghost Target Arm (commanded pos_set)
      const tRad = ((lv.targetDeg - 90) * Math.PI) / 180
      ctx.strokeStyle = 'rgba(89, 200, 255, 0.75)'
      ctx.lineWidth = 2
      ctx.setLineDash([4, 4])
      ctx.beginPath()
      ctx.moveTo(rx, ry)
      ctx.lineTo(rx + Math.cos(tRad) * (R * 0.94), ry + Math.sin(tRad) * (R * 0.94))
      ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = '#59c8ff'
      ctx.beginPath()
      ctx.arc(rx + Math.cos(tRad) * (R * 0.94), ry + Math.sin(tRad) * (R * 0.94), 3.5, 0, Math.PI * 2)
      ctx.fill()

      // Measured 30:1 Shoulder Output Arm
      const jRad = ((lv.jointDeg - 90) * Math.PI) / 180
      const ex = rx + Math.cos(jRad) * (R * 0.9)
      const ey = ry + Math.sin(jRad) * (R * 0.9)
      ctx.strokeStyle = '#3df57a'
      ctx.lineWidth = 4
      ctx.beginPath()
      ctx.moveTo(rx, ry)
      ctx.lineTo(ex, ey)
      ctx.stroke()

      // End-effector joint wrist circle + hub
      ctx.fillStyle = '#0b110e'
      ctx.strokeStyle = '#3df57a'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(rx, ry, R * 0.2, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
      ctx.fillStyle = '#3df57a'
      ctx.beginPath()
      ctx.arc(ex, ey, 5, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()

      // Captions under both dials
      ctx.font = '600 9.5px "JetBrains Mono", monospace'
      ctx.fillStyle = '#8ec69d'
      ctx.textAlign = 'center'
      ctx.fillText(`LA8308 + STG1 (6:1) + STG2 (5:1)`, lx, h - 22)
      ctx.fillStyle = '#588265'
      ctx.fillText(`MOTOR ${fmt(lv.posTurns, 2)} TRN · ${fmt(lv.velTurns, 2)} T/S · IQ ${fmt(lv.iqVal, 2)}A`, lx, h - 9)

      ctx.fillStyle = '#8ec69d'
      ctx.fillText(`SHOULDER OUTPUT (30:1) · ${fmt(lv.jointDeg, 1)}°`, rx, h - 22)
      ctx.fillStyle = '#588265'
      ctx.fillText(`TARGET ${fmt(lv.targetDeg, 1)}° · TRQ ${fmt(lv.jointTorqueNm, 2)} Nm`, rx, h - 9)
    }

    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [])

  const stateName = AXIS_STATES[num(state)] ?? 'IDLE'

  return (
    <div className="col" style={{ gap: 6 }}>
      <div className="row" style={{ justifyContent: 'space-between', padding: '0 4px' }}>
        <div className="row" style={{ gap: 6 }}>
          <Tag level={num(state) === 8 ? 'info' : num(state) === 9 ? 'warn' : 'quiet'}>{stateName}</Tag>
          <span className="muted num" style={{ fontSize: 'var(--fs-micro)' }}>
            {encReady ? 'ENC READY' : 'ENC UNREADY'} · FET {fmt(fetVal, 1)}°C
          </span>
        </div>
        <label className="muted" style={{ fontSize: 'var(--fs-micro)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}>
          <input type="checkbox" checked={dragCmd} onChange={(e) => setDragCmd(e.target.checked)} />
          CLICK/DRAG OUTPUT DIAL TO COMMAND POS
        </label>
      </div>
      <div
        ref={wrapRef}
        style={{
          position: 'relative',
          height: 230,
          background: 'radial-gradient(rgba(61, 245, 122, 0.06) 1px, transparent 1px) 0 0 / 16px 16px, #060a08',
          border: '1px solid var(--border)',
          cursor: dragCmd && active && num(cm) === 3 ? 'crosshair' : 'default',
          userSelect: 'none',
        }}
      >
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%', display: 'block' }}
          onPointerDown={(e) => {
            draggingRef.current = true
            e.currentTarget.setPointerCapture(e.pointerId)
            commandFromPointer(e.clientX, e.clientY, false)
          }}
          onPointerMove={(e) => {
            if (!draggingRef.current) return
            commandFromPointer(e.clientX, e.clientY, false)
          }}
          onPointerUp={(e) => {
            if (!draggingRef.current) return
            draggingRef.current = false
            commandFromPointer(e.clientX, e.clientY, true)
          }}
        />
      </div>
    </div>
  )
}

/**
 * Contextual Twin 1 (Tests > Tuning):
 * Real-time + Replay Dual-Needle Ghost-Target vs Measured Actuator Twin + Phase-Plane (Error vs Rate) Scope.
 */
export function TuningTwin({
  ax,
  trace,
  metrics,
  mode,
}: {
  ax: number
  trace?: { t: number[]; target: number[]; y: number[]; iq?: number[] }
  metrics?: any
  mode: string
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const profile = useApp((s) => s.profile)
  const [pos, posSet, vel, velSet, iq] = useAliasLatest(
    [`pos.${ax}`, `input_pos.${ax}`, `vel.${ax}`, `vel_set.${ax}`, `iq.${ax}`],
    20,
  )
  const [replay, setReplay] = useState(false)
  const [idx, setIdx] = useState(0)

  const ratio = Number(profile?.gear.ratio ?? 30)
  const hasTrace = !!trace && Array.isArray(trace.t) && trace.t.length > 1

  useEffect(() => {
    if (hasTrace) {
      setReplay(true)
      setIdx(0)
    }
  }, [trace, hasTrace])

  useEffect(() => {
    if (!replay || !hasTrace || !trace) return
    const timer = window.setInterval(() => {
      setIdx((i) => (i + 1) % trace.t.length)
    }, 35)
    return () => clearInterval(timer)
  }, [replay, hasTrace, trace])

  const liveRef = useRef({
    target: 0,
    measured: 0,
    iqVal: 0,
    tCur: 0,
    ratio,
    mode,
    trace,
    metrics,
    replay,
    idx,
  })

  const liveTarget = mode === 'position' ? (Number.isFinite(num(posSet)) ? num(posSet) : 0) : Number.isFinite(num(velSet)) ? num(velSet) : 0
  const liveMeas = mode === 'position' ? (Number.isFinite(num(pos)) ? num(pos) : 0) : Number.isFinite(num(vel)) ? num(vel) : 0
  const useTrace = replay && hasTrace && trace
  const curTarget = useTrace ? Number(trace.target[idx] ?? 0) : liveTarget
  const curMeas = useTrace ? Number(trace.y[idx] ?? 0) : liveMeas
  const curIq = useTrace && trace.iq ? Number(trace.iq[idx] ?? 0) : Number.isFinite(num(iq)) ? num(iq) : 0
  const curT = useTrace ? Number(trace.t[idx] ?? 0) : 0

  liveRef.current = {
    target: curTarget,
    measured: curMeas,
    iqVal: curIq,
    tCur: curT,
    ratio,
    mode,
    trace,
    metrics,
    replay: !!useTrace,
    idx,
  }

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    const render = () => {
      raf = requestAnimationFrame(render)
      const dpr = window.devicePixelRatio || 1
      const w = wrap.clientWidth
      const h = wrap.clientHeight
      if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
        canvas.width = Math.floor(w * dpr)
        canvas.height = Math.floor(h * dpr)
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)

      const lv = liveRef.current
      const cx = w * 0.25
      const cy = h * 0.52
      const R = Math.min(w * 0.18, h * 0.38)

      // ─── LEFT: GHOST TARGET vs MEASURED ARM + OVERSHOOT / SETTLING BAND ───
      ctx.strokeStyle = '#243a2d'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.arc(cx, cy, R, 0, Math.PI * 2)
      ctx.stroke()

      // Scale factor so small steps (e.g. 0.1 turn) sweep a clearly visible 120 deg arc
      const baseVal = lv.trace?.target?.[0] ?? 0
      const stepSpan = lv.trace ? Math.max(0.05, Math.max(...lv.trace.target.map((x) => Math.abs(x - baseVal)))) : 0.2
      const toAng = (v: number) => -Math.PI * 0.5 + ((v - baseVal) / stepSpan) * (Math.PI * 0.65)

      const angTarget = toAng(lv.target)
      const angMeas = toAng(lv.measured)

      // +-2% settling band wedge around target
      ctx.fillStyle = 'rgba(61, 245, 122, 0.09)'
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.arc(cx, cy, R * 0.96, angTarget - 0.05, angTarget + 0.05)
      ctx.closePath()
      ctx.fill()

      // Error arc between target and measured
      ctx.strokeStyle = Math.abs(angMeas - angTarget) > 0.08 ? '#ffb000' : '#3df57a'
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.arc(cx, cy, R * 0.72, angTarget, angMeas, angMeas < angTarget)
      ctx.stroke()

      // Ghost Target Needle (dashed cyan)
      ctx.strokeStyle = '#59c8ff'
      ctx.lineWidth = 2
      ctx.setLineDash([4, 4])
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(cx + Math.cos(angTarget) * (R * 0.92), cy + Math.sin(angTarget) * (R * 0.92))
      ctx.stroke()
      ctx.setLineDash([])

      // Measured Rotor / Joint Arm (solid emerald)
      ctx.strokeStyle = '#3df57a'
      ctx.lineWidth = 3.5
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(cx + Math.cos(angMeas) * (R * 0.88), cy + Math.sin(angMeas) * (R * 0.88))
      ctx.stroke()
      ctx.fillStyle = '#3df57a'
      ctx.beginPath()
      ctx.arc(cx, cy, 4.5, 0, Math.PI * 2)
      ctx.fill()

      ctx.font = '600 9.5px "JetBrains Mono", monospace'
      ctx.textAlign = 'center'
      ctx.fillStyle = '#8ec69d'
      ctx.fillText(`STEP / SINE TRACKING DIAL (${lv.mode.toUpperCase()})`, cx, h - 20)
      ctx.fillStyle = '#588265'
      ctx.fillText(`CMD ${fmt(lv.target, 3)} · MEAS ${fmt(lv.measured, 3)} · ERR ${fmt(lv.target - lv.measured, 4)}`, cx, h - 7)

      // ─── RIGHT: PHASE-PLANE / STEP ENVELOPE VISUALIZER ───
      const px0 = w * 0.5
      const py0 = 16
      const pw = w * 0.47
      const ph = h - 42
      ctx.strokeStyle = '#1d2d23'
      ctx.strokeRect(px0, py0, pw, ph)

      // Horizontal target reference & 2% settling corridor
      const yTarget = py0 + ph * 0.35
      const yZero = py0 + ph * 0.82
      ctx.fillStyle = 'rgba(61, 245, 122, 0.07)'
      ctx.fillRect(px0, yTarget - 5, pw, 10)
      ctx.strokeStyle = 'rgba(89, 200, 255, 0.5)'
      ctx.setLineDash([3, 3])
      ctx.beginPath()
      ctx.moveTo(px0, yTarget)
      ctx.lineTo(px0 + pw, yTarget)
      ctx.stroke()
      ctx.setLineDash([])

      if (lv.trace && lv.trace.t.length > 1) {
        const ts = lv.trace.t
        const ys = lv.trace.y
        const tMin = ts[0]
        const tMax = ts[ts.length - 1] || 1
        const yBase = ys[0] ?? 0
        const yStep = (lv.trace.target.find((v) => Math.abs(v - yBase) > 1e-4) ?? yBase + 0.1) - yBase

        ctx.strokeStyle = '#3df57a'
        ctx.lineWidth = 1.8
        ctx.beginPath()
        const maxDrawIdx = lv.replay ? lv.idx : ts.length - 1
        for (let i = 0; i <= maxDrawIdx; i++) {
          const x = px0 + ((ts[i] - tMin) / Math.max(1e-3, tMax - tMin)) * pw
          const norm = (ys[i] - yBase) / (yStep || 0.1)
          const y = yZero - norm * (yZero - yTarget)
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.stroke()

        // Current replay playhead dot
        const curI = Math.min(maxDrawIdx, ts.length - 1)
        const cxDot = px0 + ((ts[curI] - tMin) / Math.max(1e-3, tMax - tMin)) * pw
        const cyDot = yZero - ((ys[curI] - yBase) / (yStep || 0.1)) * (yZero - yTarget)
        ctx.fillStyle = '#3df57a'
        ctx.beginPath()
        ctx.arc(cxDot, cyDot, 4, 0, Math.PI * 2)
        ctx.fill()
      } else {
        ctx.fillStyle = '#588265'
        ctx.textAlign = 'center'
        ctx.fillText('RUN A STEP, GAIN SWEEP, OR SINE TEST TO CAPTURE & REPLAY ENVELOPE', px0 + pw * 0.5, py0 + ph * 0.5)
      }

      ctx.fillStyle = '#8ec69d'
      ctx.textAlign = 'left'
      ctx.fillText(
        lv.metrics
          ? `RISE ${fmt(lv.metrics.rise_s, 3)}s · OVERSHOOT ${fmt(lv.metrics.overshoot_pct, 1)}% · SETTLE ${fmt(lv.metrics.settle_s, 3)}s · PEAK IQ ${fmt(lv.metrics.iq_peak, 2)}A`
          : `LIVE IQ ${fmt(lv.iqVal, 2)} A`,
        px0 + 6,
        h - 9,
      )
    }
    raf = requestAnimationFrame(render)
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <Panel
      index="SIM"
      title="LIVE STEP / SINE ACTUATOR TWIN & ENVELOPE REPLAY"
      status={hasTrace ? 'live' : 'ok'}
      tools={
        hasTrace && (
          <div className="row" style={{ gap: 6 }}>
            <Segmented
              options={[
                ['replay', 'replay trace'],
                ['live', 'live sensor'],
              ]}
              value={replay ? 'replay' : 'live'}
              onChange={(v) => setReplay(v === 'replay')}
            />
            {replay && trace && (
              <input
                type="range"
                min={0}
                max={Math.max(0, trace.t.length - 1)}
                value={idx}
                onChange={(e) => setIdx(Number(e.target.value))}
                style={{ width: 110 }}
              />
            )}
          </div>
        )
      }
    >
      <div
        ref={wrapRef}
        style={{
          height: 195,
          background: 'radial-gradient(rgba(61, 245, 122, 0.05) 1px, transparent 1px) 0 0 / 16px 16px, #060a08',
          border: '1px solid var(--border)',
        }}
      >
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>
    </Panel>
  )
}

/**
 * Contextual Twin 2 (Tests > Thermal):
 * Live Infrared Cutaway of ODESC 3.6 MOSFET Bridge + LA8308 Stator Windings + Locked Rotor Watchdog & I²R Heat Flow.
 */
export function ThermalTwin({
  ax,
  currentCmd,
  maxMotion,
  fits,
}: {
  ax: number
  currentCmd: number
  maxMotion: number
  fits?: Record<string, any>
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const profile = useApp((s) => s.profile)
  const [fet, mot, iq, pos, state] = useAliasLatest(
    [`fet_temp.${ax}`, `motor_temp.${ax}`, `iq.${ax}`, `pos.${ax}`, `state.${ax}`],
    10,
  )

  const rPhase = Number(profile?.motor.phase_resistance_ohm ?? 0.093)
  const fetWarn = Number(profile?.thermal.fet_warn_c ?? 70)
  const fetAbort = Number(profile?.thermal.fet_abort_c ?? 85)
  const fetC = Number.isFinite(num(fet)) && num(fet) > 0 ? num(fet) : 31.5
  const iqA = Number.isFinite(num(iq)) ? num(iq) : 0
  const activeI = num(state) === 8 ? Math.max(Math.abs(iqA), 0.1) : currentCmd
  const copperWatts = 1.5 * iqA * iqA * rPhase
  const cmdWatts = 1.5 * currentCmd * currentCmd * rPhase
  const motC = Number.isFinite(num(mot)) && num(mot) > 0 ? num(mot) : fetC + Math.abs(iqA) * 0.65

  const liveRef = useRef({ fetC, motC, iqA, activeI, copperWatts, cmdWatts, fetWarn, fetAbort, pos: num(pos) || 0, maxMotion, fits })
  liveRef.current = { fetC, motC, iqA, activeI, copperWatts, cmdWatts, fetWarn, fetAbort, pos: num(pos) || 0, maxMotion, fits }

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let flow = 0
    let last = performance.now()

    const render = (now: number) => {
      raf = requestAnimationFrame(render)
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      const lv = liveRef.current
      flow = (flow + dt * (0.6 + Math.min(4, Math.abs(lv.iqA) * 0.25))) % 1

      const dpr = window.devicePixelRatio || 1
      const w = wrap.clientWidth
      const h = wrap.clientHeight
      if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
        canvas.width = Math.floor(w * dpr)
        canvas.height = Math.floor(h * dpr)
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)

      // ─── LEFT: ODESC 3.6 MOSFET BRIDGE BLOCK ───
      const bx = w * 0.06
      const by = h * 0.22
      const bw = w * 0.22
      const bh = h * 0.54
      ctx.fillStyle = tempColor(lv.fetC, 0.16)
      ctx.strokeStyle = tempColor(lv.fetC, 0.9)
      ctx.lineWidth = 1.5
      ctx.fillRect(bx, by, bw, bh)
      ctx.strokeRect(bx, by, bw, bh)

      // 6x MOSFET dies inside bridge
      for (let i = 0; i < 6; i++) {
        const col = i % 3
        const row = Math.floor(i / 3)
        const fx = bx + 12 + col * ((bw - 24) / 3)
        const fy = by + 16 + row * ((bh - 32) / 2)
        ctx.fillStyle = tempColor(lv.fetC + (i % 2) * 1.5, 0.78)
        ctx.fillRect(fx, fy, (bw - 36) / 3, (bh - 44) / 2)
      }

      // ─── CENTER: LA8308 STATOR WINDINGS + LOCKED ROTOR CUTAWAY ───
      const mx = w * 0.52
      const my = h * 0.49
      const mr = Math.min(w * 0.14, h * 0.36)

      // 7075-T6 Housing outer shell with cooling slots
      ctx.strokeStyle = '#335040'
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.arc(mx, my, mr * 1.08, 0, Math.PI * 2)
      ctx.stroke()

      // 12 Stator copper windings colored by motor temperature
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2
        const wx = mx + Math.cos(a) * (mr * 0.78)
        const wy = my + Math.sin(a) * (mr * 0.78)
        ctx.fillStyle = tempColor(lv.motC, 0.82)
        ctx.beginPath()
        ctx.arc(wx, wy, mr * 0.14, 0, Math.PI * 2)
        ctx.fill()
      }

      // Locked Rotor hub + lock clamp indicator
      ctx.fillStyle = '#0b110e'
      ctx.strokeStyle = '#3df57a'
      ctx.lineWidth = 1.8
      ctx.beginPath()
      ctx.arc(mx, my, mr * 0.45, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()

      // 3-phase thermal current particles from MOSFET block to Stator
      for (let p = 0; p < 3; p++) {
        const sy = by + bh * (0.28 + p * 0.22)
        const ey = my + (p - 1) * (mr * 0.35)
        ctx.strokeStyle = tempColor(lv.fetC, 0.45)
        ctx.lineWidth = 1.4
        ctx.beginPath()
        ctx.moveTo(bx + bw, sy)
        ctx.lineTo(mx - mr * 1.08, ey)
        ctx.stroke()

        const t = (flow + p * 0.33) % 1
        const px = bx + bw + (mx - mr * 1.08 - (bx + bw)) * t
        const py = sy + (ey - sy) * t
        ctx.fillStyle = tempColor(Math.max(lv.fetC, lv.motC), 0.95)
        ctx.fillRect(px - 2.5, py - 2.5, 5, 5)
      }

      // ─── RIGHT: THERMAL ENVELOPE BARS & STEADY-STATE PROJECTION ───
      const rx = w * 0.72
      const rw = w * 0.24
      ctx.font = '600 9.5px "JetBrains Mono", monospace'
      ctx.textAlign = 'left'

      const drawBar = (y: number, label: string, valC: number, warnC: number, abortC: number) => {
        ctx.fillStyle = '#8ec69d'
        ctx.fillText(`${label}: ${fmt(valC, 1)} °C`, rx, y)
        ctx.fillStyle = '#588265'
        ctx.fillText(`WARN ${warnC}° / ABORT ${abortC}°`, rx + rw - 115, y)
        ctx.fillStyle = '#131f18'
        ctx.fillRect(rx, y + 5, rw, 9)
        const pct = Math.max(0, Math.min(1, valC / abortC))
        ctx.fillStyle = tempColor(valC, 0.92)
        ctx.fillRect(rx, y + 5, rw * pct, 9)
        // warn tick
        const wx = rx + rw * (warnC / abortC)
        ctx.fillStyle = '#ffb000'
        ctx.fillRect(wx, y + 3, 1.5, 13)
      }

      drawBar(h * 0.25, 'ODESC FET', lv.fetC, lv.fetWarn, lv.fetAbort)
      drawBar(h * 0.52, 'LA8308 STATOR', lv.motC, 80, 100)

      ctx.fillStyle = '#8ec69d'
      ctx.fillText(
        `I²R LOSS: ${fmt(lv.copperWatts, 2)} W LIVE (${fmt(lv.cmdWatts, 1)} W @ ${currentCmd}A)`,
        rx,
        h * 0.78,
      )
      const fetFit = lv.fits?.fet
      ctx.fillStyle = '#588265'
      ctx.fillText(
        fetFit ? `FIT: T∞ = ${fmt(fetFit.t_inf, 1)} °C · τ = ${fmt(fetFit.tau_s, 0)} s` : `ROTOR LOCK WATCHDOG: ±${lv.maxMotion} TURN MAX`,
        rx,
        h * 0.9,
      )

      // Bottom labels for left & center blocks
      ctx.textAlign = 'center'
      ctx.fillStyle = '#8ec69d'
      ctx.fillText(`DRV8301 MOSFET BRIDGE (${fmt(lv.fetC, 1)}°C)`, bx + bw * 0.5, h - 9)
      ctx.fillText(`LA8308 90KV STATOR (${fmt(lv.motC, 1)}°C)`, mx, h - 9)
    }

    raf = requestAnimationFrame(render)
    return () => cancelAnimationFrame(raf)
  }, [currentCmd])

  return (
    <Panel index="SIM" title="LIVE INFRARED THERMAL CUTAWAY & I²R DISSIPATION TWIN" status="live">
      <div
        ref={wrapRef}
        style={{
          height: 185,
          background: 'radial-gradient(rgba(61, 245, 122, 0.05) 1px, transparent 1px) 0 0 / 16px 16px, #060a08',
          border: '1px solid var(--border)',
        }}
      >
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>
    </Panel>
  )
}

/**
 * Contextual Twin 3 (Tests > Characterization):
 * 3-Mode Dynamometer & 30:1 (6:1 x 5:1) Planetary Gear Twin:
 *   - 'friction': Breakaway Stiction & Coulomb/Viscous Stribeck Curve
 *   - 'kt': 30:1 Torque Arm (L) pressing on Digital Scale Load Cell
 *   - 'backlash': 2-Stage (6:1 x 5:1 = 30:1) Planetary Gear Tooth Backlash & Compliance Visualizer
 */
export function CharacterizationTwin({
  ax,
  mode,
  onModeChange,
  frResult,
  ktResult,
  blResult,
  armLengthM,
  testTorqueNm,
}: {
  ax: number
  mode: 'friction' | 'kt' | 'backlash'
  onModeChange: (m: 'friction' | 'kt' | 'backlash') => void
  frResult?: any
  ktResult?: any
  blResult?: any
  armLengthM: number
  testTorqueNm: number
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const profile = useApp((s) => s.profile)
  const [pos, vel, iq] = useAliasLatest([`pos.${ax}`, `vel.${ax}`, `iq.${ax}`], 20)

  const ratio = Number(profile?.gear.ratio ?? 30)
  const kt = Number(profile?.derived.kt_nm_per_a ?? 0.0919)
  const iqVal = Number.isFinite(num(iq)) ? num(iq) : 0
  const velVal = Number.isFinite(num(vel)) ? num(vel) : 0
  const posVal = Number.isFinite(num(pos)) ? num(pos) : 0

  const liveRef = useRef({ mode, iqVal, velVal, posVal, ratio, kt, frResult, ktResult, blResult, armLengthM, testTorqueNm })
  liveRef.current = { mode, iqVal, velVal, posVal, ratio, kt, frResult, ktResult, blResult, armLengthM, testTorqueNm }

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    const render = (now: number) => {
      raf = requestAnimationFrame(render)
      const dpr = window.devicePixelRatio || 1
      const w = wrap.clientWidth
      const h = wrap.clientHeight
      if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
        canvas.width = Math.floor(w * dpr)
        canvas.height = Math.floor(h * dpr)
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)

      const lv = liveRef.current
      const tSec = now / 1000

      if (lv.mode === 'friction') {
        // Left: Rotating Stiction/Slip Drum; Right: Torque vs Speed Stribeck curve
        const cx = w * 0.24
        const cy = h * 0.5
        const R = Math.min(w * 0.16, h * 0.36)
        ctx.strokeStyle = '#2c4536'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(cx, cy, R, 0, Math.PI * 2)
        ctx.stroke()

        const ang = lv.posVal * Math.PI * 2
        ctx.strokeStyle = '#3df57a'
        ctx.lineWidth = 2.5
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(cx + Math.cos(ang) * R * 0.88, cy + Math.sin(ang) * R * 0.88)
        ctx.stroke()

        // Stribeck / Coulomb + Viscous plot on right
        const gx = w * 0.48
        const gy = 18
        const gw = w * 0.48
        const gh = h - 42
        ctx.strokeStyle = '#1d2d23'
        ctx.strokeRect(gx, gy, gw, gh)
        const midY = gy + gh * 0.5
        ctx.strokeStyle = '#243a2d'
        ctx.beginPath()
        ctx.moveTo(gx, midY)
        ctx.lineTo(gx + gw, midY)
        ctx.stroke()

        const coulomb = lv.frResult?.coulomb_nm ?? 0.015
        const visc = lv.frResult?.viscous_nm_per_turn_s ?? 0.002
        const brkP = lv.frResult?.breakaway?.positive ?? coulomb * 1.25
        ctx.strokeStyle = '#3df57a'
        ctx.lineWidth = 1.8
        ctx.beginPath()
        ctx.moveTo(gx + 12, midY - (brkP / 0.1) * (gh * 0.35))
        ctx.lineTo(gx + 28, midY - (coulomb / 0.1) * (gh * 0.35))
        ctx.lineTo(gx + gw - 12, midY - ((coulomb + visc * 2) / 0.1) * (gh * 0.35))
        ctx.stroke()

        ctx.font = '600 9.5px "JetBrains Mono", monospace'
        ctx.fillStyle = '#8ec69d'
        ctx.textAlign = 'center'
        ctx.fillText(`STICTION / BREAKAWAY RIG`, cx, h - 9)
        ctx.fillText(
          lv.frResult
            ? `BREAKAWAY +${fmt(lv.frResult.breakaway?.positive, 4)} / ${fmt(lv.frResult.breakaway?.negative, 4)} Nm · COULOMB ${fmt(coulomb, 4)} Nm`
            : `LIVE TORQUE ${fmt(lv.iqVal * lv.kt, 3)} Nm · SPEED ${fmt(lv.velVal, 2)} T/S`,
          gx + gw * 0.5,
          h - 9,
        )
      } else if (lv.mode === 'kt') {
        // Torque-Arm (L) pressing on a Digital Scale Load Cell
        const jx = w * 0.28
        const jy = h * 0.48
        const R = Math.min(w * 0.12, h * 0.28)
        const armPx = w * 0.36
        const loadX = jx + armPx

        // 30:1 Actuator body
        ctx.strokeStyle = '#3df57a'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(jx, jy, R, 0, Math.PI * 2)
        ctx.stroke()

        // Rigid Torque Arm of length L extending horizontally to load cell
        ctx.strokeStyle = '#d4f7dc'
        ctx.lineWidth = 4
        ctx.beginPath()
        ctx.moveTo(jx, jy)
        ctx.lineTo(loadX, jy)
        ctx.stroke()

        // Downward force vector on scale
        ctx.strokeStyle = '#ffb000'
        ctx.lineWidth = 2.5
        ctx.beginPath()
        ctx.moveTo(loadX, jy)
        ctx.lineTo(loadX, jy + 36)
        ctx.stroke()

        // Digital scale platform
        ctx.fillStyle = '#111a15'
        ctx.strokeStyle = '#59c8ff'
        ctx.lineWidth = 1.5
        ctx.fillRect(loadX - 48, jy + 36, 96, 26)
        ctx.strokeRect(loadX - 48, jy + 36, 96, 26)

        const idealOutKt = lv.kt * lv.ratio
        const measOutKt = lv.ktResult?.kt_out_nm_per_a ?? idealOutKt * 0.87
        const forceN = (Math.abs(lv.iqVal) * measOutKt) / Math.max(0.05, lv.armLengthM)

        ctx.font = '600 10px "JetBrains Mono", monospace'
        ctx.fillStyle = '#59c8ff'
        ctx.textAlign = 'center'
        ctx.fillText(`${fmt(forceN, 1)} N (${fmt(forceN / 9.81, 2)} kg)`, loadX, jy + 53)
        ctx.fillStyle = '#8ec69d'
        ctx.fillText(`ARM L = ${lv.armLengthM} m`, jx + armPx * 0.5, jy - 10)
        ctx.fillText(
          lv.ktResult
            ? `MEASURED KT_OUT ${fmt(lv.ktResult.kt_out_nm_per_a, 3)} Nm/A vs IDEAL ${fmt(lv.ktResult.kt_ideal_out, 3)} Nm/A (EFF ${((lv.ktResult.efficiency ?? 0) * 100).toFixed(1)}%)`
            : `30:1 (6:1 × 5:1) TORQUE ARM DYNAMOMETER · IDEAL KT_OUT = ${fmt(idealOutKt, 3)} Nm/A`,
          w * 0.5,
          h - 9,
        )
      } else {
        // Lost motion (backlash + compliance) in 2-stage 6:1 x 5:1 = 30:1 planetary mesh
        const cx = w * 0.34
        const cy = h * 0.48
        const R = Math.min(w * 0.16, h * 0.35)
        const osc = Math.sin(tSec * 3.2)
        const playDeg = lv.blResult?.joint_deg ?? 0.18
        const playArcmin = lv.blResult?.joint_arcmin ?? playDeg * 60

        // Locked Outer Ring-2 (ground marks)
        ctx.strokeStyle = '#ff5a4f'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(cx, cy, R * 1.05, 0, Math.PI * 2)
        ctx.stroke()

        // Rocking Sun/Planet mesh showing exaggerated angular play
        const rockAng = osc * 0.18
        ctx.strokeStyle = '#3df57a'
        ctx.lineWidth = 2.5
        ctx.beginPath()
        ctx.arc(cx, cy, R * 0.55, 0, Math.PI * 2)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(cx + Math.cos(rockAng - Math.PI * 0.5) * (R * 0.9), cy + Math.sin(rockAng - Math.PI * 0.5) * (R * 0.9))
        ctx.stroke()

        // Right side: Hysteresis / Backlash gap diagram
        const rx = w * 0.6
        const rw = w * 0.34
        ctx.font = '600 10px "JetBrains Mono", monospace'
        ctx.textAlign = 'left'
        ctx.fillStyle = '#8ec69d'
        ctx.fillText(`2-STAGE PLANETARY (6:1 × 5:1 = 30:1)`, rx, h * 0.3)
        ctx.fillStyle = '#d4f7dc'
        ctx.fillText(`LOST MOTION: ${fmt(playDeg, 3)}° (${fmt(playArcmin, 1)} arcmin)`, rx, h * 0.48)
        ctx.fillStyle = '#588265'
        ctx.fillText(`TEST TORQUE: ±${lv.testTorqueNm} Nm · OUTPUT LOCKED`, rx, h * 0.64)
        ctx.fillStyle = '#131f18'
        ctx.fillRect(rx, h * 0.72, rw, 10)
        ctx.fillStyle = '#3df57a'
        ctx.fillRect(rx + rw * 0.5 + osc * (rw * 0.35) - 6, h * 0.72, 12, 10)
      }
    }

    raf = requestAnimationFrame(render)
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <Panel
      index="SIM"
      title="LIVE ACTUATOR CHARACTERIZATION DYNAMOMETER & 30:1 GEAR TWIN"
      status="live"
      tools={
        <Segmented
          options={[
            ['friction', '01 stiction / friction'],
            ['kt', '02 torque arm (Kt / eff)'],
            ['backlash', '03 30:1 gear backlash'],
          ]}
          value={mode}
          onChange={onModeChange}
        />
      }
    >
      <div
        ref={wrapRef}
        style={{
          height: 175,
          background: 'radial-gradient(rgba(61, 245, 122, 0.05) 1px, transparent 1px) 0 0 / 16px 16px, #060a08',
          border: '1px solid var(--border)',
        }}
      >
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>
    </Panel>
  )
}
