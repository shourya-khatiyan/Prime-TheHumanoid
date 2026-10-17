import { useEffect, useRef, useState } from 'react'
import { Button, Segmented } from '../primitives'
import { useAliasLatest, useApp } from '../lib/store'
import { fmt, num } from '../lib/format'

type SubId = 'vbus' | 'mcu' | 'brake' | 'm0_stage' | 'spi' | 'motor' | 'pcb'
type CamPreset = 'orbit' | 'top' | 'side' | 'motor'

type Vec3 = [number, number, number]
type Line3D = { a: Vec3; b: Vec3; group: SubId; weight?: number; dashed?: boolean }
type Dot3D = { p: Vec3; group: SubId; size?: number }

/** build a 3D wireframe box from center (cx,cy,cz) and half-extents (hx,hy,hz) */
function addBox(lines: Line3D[], cx: number, cy: number, cz: number, hx: number, hy: number, hz: number, group: SubId, weight = 1) {
  const c: Vec3[] = [
    [cx - hx, cy - hy, cz - hz],
    [cx + hx, cy - hy, cz - hz],
    [cx + hx, cy - hy, cz + hz],
    [cx - hx, cy - hy, cz + hz],
    [cx - hx, cy + hy, cz - hz],
    [cx + hx, cy + hy, cz - hz],
    [cx + hx, cy + hy, cz + hz],
    [cx - hx, cy + hy, cz + hz],
  ]
  const edges: [number, number][] = [
    [0, 1], [1, 2], [2, 3], [3, 0],
    [4, 5], [5, 6], [6, 7], [7, 4],
    [0, 4], [1, 5], [2, 6], [3, 7],
  ]
  for (const [i, j] of edges) lines.push({ a: c[i], b: c[j], group, weight })
}

/** build a vertical cylinder along the Y axis */
function addCylinderY(lines: Line3D[], cx: number, y0: number, y1: number, cz: number, r: number, segs: number, group: SubId, weight = 1) {
  for (let i = 0; i < segs; i++) {
    const a0 = (i / segs) * Math.PI * 2
    const a1 = ((i + 1) / segs) * Math.PI * 2
    const x0 = cx + Math.cos(a0) * r
    const z0 = cz + Math.sin(a0) * r
    const x1 = cx + Math.cos(a1) * r
    const z1 = cz + Math.sin(a1) * r
    lines.push({ a: [x0, y0, z0], b: [x1, y0, z1], group, weight })
    lines.push({ a: [x0, y1, z0], b: [x1, y1, z1], group, weight })
    if (i % 2 === 0) lines.push({ a: [x0, y0, z0], b: [x0, y1, z0], group, weight: weight * 0.75 })
  }
}

/** build static ODESC 3.6 56V PCB geometry and onboard components in millimeter-scale coordinates */
function buildStaticMesh(): { lines: Line3D[]; dots: Dot3D[] } {
  const lines: Line3D[] = []
  const dots: Dot3D[] = []

  // 1. 4-layer ODESC 3.6 PCB substrate (-74..+34 X, -2.4..0 Y, -25..+25 Z)
  addBox(lines, -20, -1.2, 0, 54, 1.2, 25, 'pcb', 1.35)

  for (let ix = -68; ix <= 28; ix += 6) {
    for (let iz = -21; iz <= 21; iz += 5.25) {
      dots.push({ p: [ix, 0.1, iz], group: 'pcb', size: 1.2 })
    }
  }
  const holes: [number, number][] = [[-69, -20], [-69, 20], [29, -20], [29, 20]]
  for (const [hx, hz] of holes) {
    addCylinderY(lines, hx, -2.4, 0.5, hz, 2.8, 10, 'pcb', 0.95)
  }

  // 2. 6x 56V 470uF electrolytic DC bus capacitors along central spine
  for (let i = 0; i < 6; i++) {
    const cx = -52 + i * 12
    addCylinderY(lines, cx, 0, 14.5, 0, 4.8, 12, 'vbus', 1.2)
    lines.push({ a: [cx - 3, 14.6, 0], b: [cx + 3, 14.6, 0], group: 'vbus', weight: 0.85 })
    lines.push({ a: [cx, 14.6, -3], b: [cx, 14.6, 3], group: 'vbus', weight: 0.85 })
  }

  // 3. XT60 DC bus input connector (-74 X) + heavy supply leads
  addBox(lines, -71, 4.2, 0, 5, 4.2, 7.5, 'vbus', 1.35)
  lines.push({ a: [-82, 4.5, -3.2], b: [-76, 4.5, -3.2], group: 'vbus', weight: 1.6 })
  lines.push({ a: [-82, 4.5, 3.2], b: [-76, 4.5, 3.2], group: 'vbus', weight: 1.6 })

  // 4. AUX 2.0 ohm ceramic brake resistor module (-58 X, -32 Z)
  addBox(lines, -58, 2.8, -18, 6.5, 2.8, 3.5, 'brake', 1.15)
  addBox(lines, -58, 8, -32, 13, 3.2, 4, 'brake', 1.2)
  lines.push({ a: [-62, 2.8, -21.5], b: [-64, 8, -28], group: 'brake', weight: 1, dashed: true })
  lines.push({ a: [-54, 2.8, -21.5], b: [-52, 8, -28], group: 'brake', weight: 1, dashed: true })

  // 5. M0 Power Stage (+Z side: 6x D2PAK MOSFETs + DRV8301 gate driver + phase pads A/B/C)
  for (let i = 0; i < 6; i++) {
    const fx = -46 + i * 10.5
    addBox(lines, fx, 1.8, 15, 3.6, 1.8, 4, 'm0_stage', 1.2)
    dots.push({ p: [fx, 3.8, 15], group: 'm0_stage', size: 1.7 })
  }
  addBox(lines, 15, 1.5, 12.5, 4.2, 1.5, 3.4, 'm0_stage', 1.15)
  for (let p = 0; p < 3; p++) {
    const px = -16 + p * 11
    addBox(lines, px, 2.6, 22.5, 3.2, 2.6, 2.4, 'm0_stage', 1.3)
  }

  // 6. M1 Power Stage (-Z side)
  for (let i = 0; i < 6; i++) {
    const fx = -46 + i * 10.5
    addBox(lines, fx, 1.8, -15, 3.6, 1.8, 4, 'pcb', 0.8)
  }
  addBox(lines, 15, 1.5, -12.5, 4.2, 1.5, 3.4, 'pcb', 0.8)

  // 7. STM32F405RGT6 LQFP-64 MCU + USB-C port
  addBox(lines, 22, 1.6, -1, 5.2, 1.6, 5.2, 'mcu', 1.4)
  for (let p = -4; p <= 4; p += 2) {
    lines.push({ a: [22 + p, 0.5, -6.2], b: [22 + p, 0.5, -8], group: 'mcu', weight: 0.85 })
    lines.push({ a: [22 + p, 0.5, 4.2], b: [22 + p, 0.5, 6], group: 'mcu', weight: 0.85 })
    lines.push({ a: [16.8, 0.5, -1 + p], b: [15, 0.5, -1 + p], group: 'mcu', weight: 0.85 })
    lines.push({ a: [27.2, 0.5, -1 + p], b: [29, 0.5, -1 + p], group: 'mcu', weight: 0.85 })
  }
  addBox(lines, 32, 2.2, -9.5, 3.8, 2.2, 4.2, 'mcu', 1.25)

  // 8. J4 GPIO / SPI / CAN header + SPI harness to AS5047P encoder
  addBox(lines, 26, 3, 17.5, 5, 3, 3, 'spi', 1.35)
  for (let pin = 0; pin < 6; pin++) {
    const px = 22 + pin * 1.6
    lines.push({ a: [px, 0, 16.5], b: [px, 7, 16.5], group: 'spi', weight: 1.1 })
    lines.push({ a: [px, 0, 18.8], b: [px, 7, 18.8], group: 'spi', weight: 1.1 })
  }
  lines.push({ a: [31, 5.5, 17.5], b: [82, 10, 8], group: 'spi', weight: 1.15, dashed: true })
  lines.push({ a: [31, 5.5, 19], b: [82, 7, 8], group: 'spi', weight: 0.95, dashed: true })

  // 9. 3-phase heavy motor leads from M0 pads to BLDC stator at X=+50
  lines.push({ a: [-16, 3.8, 24.5], b: [50, 5, 14], group: 'm0_stage', weight: 1.25 })
  lines.push({ a: [-5, 3.8, 24.5], b: [50, 5, 8], group: 'm0_stage', weight: 1.25 })
  lines.push({ a: [6, 3.8, 24.5], b: [50, 5, 2], group: 'm0_stage', weight: 1.25 })

  return { lines, dots }
}

const STATIC_MESH = buildStaticMesh()

const ANCHORS: Record<Exclude<SubId, 'pcb'>, Vec3> = {
  vbus: [-40, 14, 0],
  mcu: [22, 3, -1],
  brake: [-58, 8, -30],
  m0_stage: [-16, 4, 16],
  spi: [82, 5, 6],
  motor: [62, 5, 6],
}

/**
 * Interactive 3D CAD / Point-Cloud Hologram of the ODESC 3.6 56V controller,
 * coupled 90KV BLDC actuator (30:1 two-stage planetary 6:1 x 5:1), and AS5047P SPI absolute encoder.
 */
export function OdriveHologram({ ax }: { ax: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)
  const leftRefs = useRef<(HTMLDivElement | null)[]>([])
  const rightRefs = useRef<(HTMLDivElement | null)[]>([])

  const status = useApp((s) => s.status)
  const profile = useApp((s) => s.profile)
  const [vbus, ibus, brakeArmed, state, err, motErr, encErr, pos, vel, iq, iqSet, fet0, spiErr, posAbs, shadow, encMode, encCs, encCpr] =
    useAliasLatest(
      [
        'vbus',
        'ibus',
        'brake_armed',
        `state.${ax}`,
        `error.${ax}`,
        `motor_error.${ax}`,
        `enc_error.${ax}`,
        `pos.${ax}`,
        `vel.${ax}`,
        `iq.${ax}`,
        `iq_set.${ax}`,
        `fet_temp.${ax}`,
        `spi_err.${ax}`,
        `pos_abs.${ax}`,
        `shadow.${ax}`,
        `enc_mode.${ax}`,
        `enc_cs.${ax}`,
        `enc_cpr.${ax}`,
      ],
      15,
    )

  const [cam, setCam] = useState<CamPreset>('orbit')
  const [autoSpin, setAutoSpin] = useState(true)
  const [selected, setSelected] = useState<SubId | null>(null)
  const rotRef = useRef({ yaw: -0.48, pitch: 0.46, dragging: false, lx: 0, ly: 0 })
  const liveRef = useRef({
    vbus: 0,
    ibus: 0,
    pos: 0,
    vel: 0,
    iq: 0,
    fet0: 25,
    spiErr: 0,
    posAbs: 0,
    busFault: false,
    motFault: false,
    encFault: false,
    active: false,
    selected: null as SubId | null,
  })

  const busV = num(vbus)
  const busBad = !!profile && Number.isFinite(busV) && (busV < profile.power.bus_min_v || busV > profile.power.bus_max_v)
  const isSpi = num(encMode) >= 256
  const encBad = (num(encErr) !== 0 && encErr !== undefined) || (isSpi && (num(spiErr) > 0.05 || num(posAbs) === 16383))
  const motBad = (num(motErr) !== 0 && motErr !== undefined) || (num(err) !== 0 && err !== undefined && !encBad)
  const isClosedLoop = num(state) === 8
  const ratio = Number(profile?.gear.ratio ?? 30)
  const eff = Number(profile?.gear.efficiency ?? 0.87)
  const kt = Number(profile?.derived.kt_nm_per_a ?? 0.0919)
  const jointDeg = Number.isFinite(num(pos)) ? (num(pos) * 360) / ratio : undefined
  const jointTorque = Number.isFinite(num(iq)) ? num(iq) * kt * ratio * eff : undefined
  const busPwr = Number.isFinite(busV * num(ibus)) ? busV * num(ibus) : undefined

  liveRef.current = {
    vbus: Number.isFinite(busV) ? busV : 0,
    ibus: Number.isFinite(num(ibus)) ? num(ibus) : 0,
    pos: Number.isFinite(num(pos)) ? num(pos) : 0,
    vel: Number.isFinite(num(vel)) ? num(vel) : 0,
    iq: Number.isFinite(num(iq)) ? num(iq) : 0,
    fet0: Number.isFinite(num(fet0)) ? num(fet0) : 25,
    spiErr: Number.isFinite(num(spiErr)) ? num(spiErr) : 0,
    posAbs: Number.isFinite(num(posAbs)) ? num(posAbs) : 0,
    busFault: busBad,
    motFault: motBad,
    encFault: encBad,
    active: isClosedLoop,
    selected,
  }

  const applyPreset = (p: CamPreset) => {
    setCam(p)
    if (p === 'orbit') {
      rotRef.current.yaw = -0.48
      rotRef.current.pitch = 0.46
      setAutoSpin(true)
    } else if (p === 'top') {
      rotRef.current.yaw = 0
      rotRef.current.pitch = 1.35
      setAutoSpin(false)
    } else if (p === 'side') {
      rotRef.current.yaw = 0
      rotRef.current.pitch = 0.14
      setAutoSpin(false)
    } else if (p === 'motor') {
      rotRef.current.yaw = -1.1
      rotRef.current.pitch = 0.36
      setAutoSpin(false)
    }
  }

  useEffect(() => {
    const canvas = canvasRef.current
    const stage = stageRef.current
    if (!canvas || !stage) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let lastT = performance.now()
    let phaseFlow = 0

    const render = (now: number) => {
      raf = requestAnimationFrame(render)
      const dt = Math.min(0.05, (now - lastT) / 1000)
      lastT = now

      const dpr = window.devicePixelRatio || 1
      const w = stage.clientWidth
      const h = stage.clientHeight
      if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
        canvas.width = Math.floor(w * dpr)
        canvas.height = Math.floor(h * dpr)
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)

      const rot = rotRef.current
      if (autoSpin && !rot.dragging) {
        rot.yaw += dt * 0.22
      }
      const lv = liveRef.current
      phaseFlow = (phaseFlow + dt * (0.9 + Math.min(8, Math.abs(lv.iq) * 0.8))) % 1

      const cy = Math.cos(rot.yaw)
      const sy = Math.sin(rot.yaw)
      const cp = Math.cos(rot.pitch)
      const sp = Math.sin(rot.pitch)

      const padSide = leftRefs.current[0]?.clientWidth ?? 102
      const clearW = Math.max(180, w - padSide * 2 - 20)
      const clearH = Math.max(160, h - 56)
      const unitPx = Math.min((clearW * 0.5) / 86, (clearH * 0.5) / 46)
      const cxScreen = w * 0.5
      const cyScreen = h * 0.49

      const project = (p: Vec3): { x: number; y: number; z: number; s: number } => {
        const x0 = p[0] - 4
        const y0 = p[1] - 4
        const z0 = p[2]
        const rx = x0 * cy - z0 * sy
        const rz0 = x0 * sy + z0 * cy
        const ry = y0 * cp - rz0 * sp
        const rz = y0 * sp + rz0 * cp
        const fov = 340 / (340 + rz * 0.55)
        return {
          x: cxScreen + rx * unitPx * fov,
          y: cyScreen - ry * unitPx * fov,
          z: rz,
          s: fov,
        }
      }

      const colorFor = (group: SubId, alpha = 0.85): string => {
        const boost = lv.selected === group ? 0.25 : lv.selected && lv.selected !== group ? -0.35 : 0
        const a = Math.max(0.14, Math.min(1, alpha + boost))
        if (group === 'spi' && lv.encFault) return `rgba(255, 90, 79, ${a})`
        if (group === 'vbus' && lv.busFault) return `rgba(255, 176, 0, ${a})`
        if (group === 'm0_stage' && lv.motFault) return `rgba(255, 90, 79, ${a})`
        if (group === 'm0_stage' && lv.fet0 > 60) return `rgba(255, 176, 0, ${a})`
        if (group === 'motor' && lv.active) return `rgba(89, 200, 255, ${a})`
        if (group === 'pcb') return `rgba(94, 168, 122, ${a * 0.68})`
        return `rgba(61, 245, 122, ${a})`
      }

      // 1. Concentric dotted hologram base radar rings
      for (const ringR of [86, 62]) {
        const segs = ringR === 86 ? 64 : 40
        for (let i = 0; i < segs; i++) {
          const ang = (i / segs) * Math.PI * 2
          const pt = project([Math.cos(ang) * ringR + 4, -10, Math.sin(ang) * ringR * 0.62])
          const major = i % 8 === 0
          ctx.fillStyle = major ? 'rgba(61, 245, 122, 0.65)' : 'rgba(61, 245, 122, 0.22)'
          const sz = major ? 2.2 : 1.2
          ctx.fillRect(pt.x - sz * 0.5, pt.y - sz * 0.5, sz, sz)
        }
      }

      // 2. PCB point-cloud matrix
      for (const d of STATIC_MESH.dots) {
        const pt = project(d.p)
        ctx.fillStyle = colorFor(d.group, 0.52)
        const sz = (d.size ?? 1.3) * pt.s
        ctx.fillRect(pt.x - sz * 0.5, pt.y - sz * 0.5, sz, sz)
      }

      // 3. Dynamic rotating 90KV BLDC rotor + AS5047P encoder disc
      const dynLines: Line3D[] = []
      const mechAngle = lv.pos * Math.PI * 2
      const encAngle = (lv.posAbs / 16384) * Math.PI * 2
      const my = 5
      const mz = 6
      const mR = 18
      const mSegs = 20

      for (let i = 0; i < mSegs; i++) {
        const a0 = mechAngle + (i / mSegs) * Math.PI * 2
        const a1 = mechAngle + ((i + 1) / mSegs) * Math.PI * 2
        const y0 = my + Math.cos(a0) * mR
        const z0 = mz + Math.sin(a0) * mR
        const y1 = my + Math.cos(a1) * mR
        const z1 = mz + Math.sin(a1) * mR
        dynLines.push({ a: [50, y0, z0], b: [50, y1, z1], group: 'motor', weight: 1.25 })
        dynLines.push({ a: [72, y0, z0], b: [72, y1, z1], group: 'motor', weight: 1.35 })
        if (i % 2 === 0) {
          dynLines.push({ a: [50, y0, z0], b: [72, y0, z0], group: 'motor', weight: 0.95 })
        }
        if (i % 4 === 0) {
          dynLines.push({ a: [72, my, mz], b: [72, y0, z0], group: 'motor', weight: 1.1 })
        }
      }

      const eSegs = 16
      const eR = 10.5
      for (let i = 0; i < eSegs; i++) {
        const a0 = (i / eSegs) * Math.PI * 2
        const a1 = ((i + 1) / eSegs) * Math.PI * 2
        dynLines.push({
          a: [82, my + Math.cos(a0) * eR, mz + Math.sin(a0) * eR],
          b: [82, my + Math.cos(a1) * eR, mz + Math.sin(a1) * eR],
          group: 'spi',
          weight: 1.3,
        })
      }
      dynLines.push({ a: [46, my, mz], b: [85, my, mz], group: 'motor', weight: 1.45 })
      dynLines.push({
        a: [82, my, mz],
        b: [82, my + Math.cos(encAngle) * eR, mz + Math.sin(encAngle) * eR],
        group: 'spi',
        weight: 1.9,
      })

      // 4. Draw all 3D wireframe edges
      const allLines = [...STATIC_MESH.lines, ...dynLines]
      for (const ln of allLines) {
        const pa = project(ln.a)
        const pb = project(ln.b)
        const depthAlpha = Math.max(0.28, Math.min(0.96, 0.72 - ((pa.z + pb.z) * 0.5) / 240))
        ctx.beginPath()
        ctx.strokeStyle = colorFor(ln.group, depthAlpha)
        ctx.lineWidth = (ln.weight ?? 1) * ((pa.s + pb.s) * 0.5)
        if (ln.dashed) ctx.setLineDash([3, 3])
        else ctx.setLineDash([])
        ctx.moveTo(pa.x, pa.y)
        ctx.lineTo(pb.x, pb.y)
        ctx.stroke()
      }
      ctx.setLineDash([])

      // 5. Animated 3-phase current particles along M0 -> Motor leads
      const phaseStarts: Vec3[] = [[-16, 3.8, 24.5], [-5, 3.8, 24.5], [6, 3.8, 24.5]]
      const phaseEnds: Vec3[] = [[50, 5, 14], [50, 5, 8], [50, 5, 2]]
      for (let p = 0; p < 3; p++) {
        const t = (phaseFlow + p * 0.33) % 1
        const s = phaseStarts[p]
        const e = phaseEnds[p]
        const pt = project([s[0] + (e[0] - s[0]) * t, s[1] + (e[1] - s[1]) * t, s[2] + (e[2] - s[2]) * t])
        ctx.fillStyle = lv.motFault ? '#ff5a4f' : '#3df57a'
        ctx.fillRect(pt.x - 2, pt.y - 2, 4, 4)
      }

      // 6. Draw 3D leader lines from each subsystem anchor to its left/right HUD callout box
      const stageRect = stage.getBoundingClientRect()
      const leftKeys: Exclude<SubId, 'pcb'>[] = ['vbus', 'mcu', 'brake']
      const rightKeys: Exclude<SubId, 'pcb'>[] = ['m0_stage', 'spi', 'motor']

      const drawLeader = (sub: Exclude<SubId, 'pcb'>, el: HTMLDivElement | null, side: 'left' | 'right') => {
        if (!el) return
        const r = el.getBoundingClientRect()
        const boxX = side === 'left' ? r.right - stageRect.left : r.left - stageRect.left
        const boxY = r.top + r.height * 0.5 - stageRect.top
        const anc = project(ANCHORS[sub])
        const elbowX = side === 'left' ? boxX + 10 : boxX - 10

        const isFault = (sub === 'spi' && lv.encFault) || (sub === 'vbus' && lv.busFault) || (sub === 'm0_stage' && lv.motFault)
        const isSel = lv.selected === sub
        const stroke = isFault
          ? 'rgba(255, 90, 79, 0.85)'
          : isSel
            ? 'rgba(61, 245, 122, 0.95)'
            : 'rgba(94, 158, 118, 0.4)'

        ctx.beginPath()
        ctx.strokeStyle = stroke
        ctx.lineWidth = isSel || isFault ? 1.3 : 0.9
        ctx.moveTo(boxX, boxY)
        ctx.lineTo(elbowX, boxY)
        ctx.lineTo(anc.x, anc.y)
        ctx.stroke()

        ctx.fillStyle = isFault ? '#ff5a4f' : '#3df57a'
        ctx.fillRect(anc.x - 2, anc.y - 2, 4, 4)
      }

      leftKeys.forEach((k, i) => drawLeader(k, leftRefs.current[i] ?? null, 'left'))
      rightKeys.forEach((k, i) => drawLeader(k, rightRefs.current[i] ?? null, 'right'))
    }

    raf = requestAnimationFrame(render)
    return () => cancelAnimationFrame(raf)
  }, [autoSpin])

  const dev = status?.device

  const leftNodes: { id: Exclude<SubId, 'pcb'>; label: string; val: string; tip: string; state?: 'warn' | 'alarm' }[] = [
    {
      id: 'vbus',
      label: 'DC BUS',
      val: `${fmt(vbus, 2)} V`,
      tip: `${fmt(ibus, 2)} A · ${fmt(busPwr, 1)} W`,
      state: busBad ? 'alarm' : undefined,
    },
    {
      id: 'mcu',
      label: 'STM32',
      val: dev?.connected ? `${dev.rate_achieved.toFixed(0)} Hz` : 'OFFLINE',
      tip: `FW ${dev?.info?.fw ?? '--'} · ${dev?.cols ?? 0} ch`,
      state: !dev?.connected ? 'warn' : undefined,
    },
    {
      id: 'brake',
      label: 'BRAKE',
      val: brakeArmed ? '2.0 Ω OK' : 'OFF',
      tip: `Max regen ${profile?.power.dc_max_negative_current_a ?? -0.01} A`,
      state: brakeArmed === false ? 'warn' : undefined,
    },
  ]

  const rightNodes: { id: Exclude<SubId, 'pcb'>; label: string; val: string; tip: string; state?: 'warn' | 'alarm' }[] = [
    {
      id: 'm0_stage',
      label: `M${ax} FET`,
      val: `${fmt(fet0, 1)} °C`,
      tip: `Iq ${fmt(iq, 2)} A / Set ${fmt(iqSet, 2)} A`,
      state: motBad ? 'alarm' : num(fet0) > 65 ? 'warn' : undefined,
    },
    {
      id: 'spi',
      label: isSpi ? 'AS5047P' : 'ABZ ENC',
      val: isSpi ? `${fmt(posAbs, 0)}` : `${fmt(shadow, 0)}`,
      tip: isSpi ? `CS GPIO${fmt(encCs, 0)} · CPR ${fmt(encCpr, 0)}` : `J4 M0 A/B/Z · CPR ${fmt(encCpr, 0)}`,
      state: encBad ? 'alarm' : undefined,
    },
    {
      id: 'motor',
      label: 'JOINT',
      val: `${fmt(jointDeg, 1)}°`,
      tip: `${fmt(jointTorque, 2)} Nm · ${fmt(vel, 2)} t/s`,
    },
  ]

  return (
    <div className="holo-stage" ref={stageRef}>
      <div className="holo-bracket tl" />
      <div className="holo-bracket tr" />
      <div className="holo-bracket bl" />
      <div className="holo-bracket br" />

      <div className="holo-callouts left">
        {leftNodes.map((n, i) => (
          <div
            key={n.id}
            ref={(el) => {
              leftRefs.current[i] = el
            }}
            title={n.tip}
            className={`holo-node num ${n.state ?? ''} ${selected === n.id ? 'active' : ''}`}
            onClick={() => setSelected(selected === n.id ? null : n.id)}
          >
            <div className="n-head">
              <span>{n.label}</span>
              <span>{n.state === 'alarm' ? '■' : n.state === 'warn' ? '▲' : '●'}</span>
            </div>
            <div className="n-val">{n.val}</div>
          </div>
        ))}
      </div>

      <div className="holo-callouts right">
        {rightNodes.map((n, i) => (
          <div
            key={n.id}
            ref={(el) => {
              rightRefs.current[i] = el
            }}
            title={n.tip}
            className={`holo-node num ${n.state ?? ''} ${selected === n.id ? 'active' : ''}`}
            onClick={() => setSelected(selected === n.id ? null : n.id)}
          >
            <div className="n-head">
              <span>{n.label}</span>
              <span>{n.state === 'alarm' ? '■' : n.state === 'warn' ? '▲' : '●'}</span>
            </div>
            <div className="n-val">{n.val}</div>
          </div>
        ))}
      </div>

      <canvas
        ref={canvasRef}
        className="holo-canvas"
        onPointerDown={(e) => {
          rotRef.current.dragging = true
          rotRef.current.lx = e.clientX
          rotRef.current.ly = e.clientY
          e.currentTarget.setPointerCapture(e.pointerId)
        }}
        onPointerMove={(e) => {
          if (!rotRef.current.dragging) return
          const dx = e.clientX - rotRef.current.lx
          const dy = e.clientY - rotRef.current.ly
          rotRef.current.lx = e.clientX
          rotRef.current.ly = e.clientY
          rotRef.current.yaw += dx * 0.008
          rotRef.current.pitch = Math.max(-0.4, Math.min(1.45, rotRef.current.pitch + dy * 0.008))
        }}
        onPointerUp={() => {
          rotRef.current.dragging = false
        }}
      />

      <div className="holo-hud-bottom num">
        <div className="holo-controls" style={{ marginLeft: 'auto', gap: 6 }}>
          <Segmented
            options={[
              ['orbit', 'orbit'],
              ['top', 'top'],
              ['side', 'side'],
              ['motor', 'motor'],
            ]}
            value={cam}
            onChange={applyPreset}
          />
          <Button small kind={autoSpin ? 'on' : 'chip'} onClick={() => setAutoSpin(!autoSpin)}>
            {autoSpin ? 'spin: on' : 'spin: off'}
          </Button>
        </div>
      </div>
    </div>
  )
}
