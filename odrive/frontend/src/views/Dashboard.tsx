import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import GridLayout, { type Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import { Button, Panel } from '../primitives'
import { useApp } from '../lib/store'
import { OdriveHologram } from '../components/OdriveHologram'
import { AxisCard, CurrentPlot, EncoderCard, ErrorsPanel, EventsPanel, JointCard, MotionPlot, PowerCard, PowerPlot, ThermalPlot } from './panels'
import './dashboard.css'

const STORE = 'odrv.layouts.v3'

type PanelId = 'hologram' | 'axis' | 'joint' | 'encoder' | 'powercard' | 'motion' | 'current' | 'errors' | 'power' | 'thermal' | 'events'

const PRESETS: Record<string, Layout[]> = {
  bench: [
    { i: 'axis', x: 0, y: 0, w: 3, h: 7 },
    { i: 'joint', x: 0, y: 7, w: 3, h: 6 },
    { i: 'hologram', x: 3, y: 0, w: 6, h: 13 },
    { i: 'encoder', x: 9, y: 0, w: 3, h: 7 },
    { i: 'powercard', x: 9, y: 7, w: 3, h: 6 },
    { i: 'motion', x: 0, y: 13, w: 6, h: 7 },
    { i: 'current', x: 6, y: 13, w: 6, h: 7 },
    { i: 'errors', x: 0, y: 20, w: 4, h: 6 },
    { i: 'power', x: 4, y: 20, w: 4, h: 6 },
    { i: 'thermal', x: 8, y: 20, w: 4, h: 6 },
  ],
  tuning: [
    { i: 'motion', x: 0, y: 0, w: 7, h: 8 },
    { i: 'hologram', x: 7, y: 0, w: 5, h: 11 },
    { i: 'current', x: 0, y: 8, w: 7, h: 8 },
    { i: 'axis', x: 7, y: 11, w: 5, h: 5 },
    { i: 'joint', x: 0, y: 16, w: 4, h: 6 },
    { i: 'encoder', x: 4, y: 16, w: 4, h: 6 },
    { i: 'errors', x: 8, y: 16, w: 4, h: 6 },
  ],
  thermal: [
    { i: 'thermal', x: 0, y: 0, w: 7, h: 10 },
    { i: 'hologram', x: 7, y: 0, w: 5, h: 10 },
    { i: 'powercard', x: 0, y: 10, w: 4, h: 6 },
    { i: 'power', x: 4, y: 10, w: 4, h: 6 },
    { i: 'current', x: 8, y: 10, w: 4, h: 6 },
    { i: 'axis', x: 0, y: 16, w: 4, h: 6 },
    { i: 'errors', x: 4, y: 16, w: 4, h: 6 },
    { i: 'events', x: 8, y: 16, w: 4, h: 6 },
  ],
}

const META: Record<PanelId, { idx: string; title: string }> = {
  axis: { idx: '01', title: 'AXIS' },
  joint: { idx: '02', title: 'JOINT' },
  hologram: { idx: '03', title: 'ODESC 3.6 HOLOGRAM' },
  encoder: { idx: '04', title: 'ENCODER' },
  powercard: { idx: '05', title: 'POWER' },
  motion: { idx: '06', title: 'MOTION' },
  current: { idx: '07', title: 'CURRENT' },
  errors: { idx: '08', title: 'FAULTS' },
  power: { idx: '09', title: 'DC BUS' },
  thermal: { idx: '10', title: 'THERMAL' },
  events: { idx: '11', title: 'EVENTS' },
}

/** load user-customized dashboard layouts from localStorage with preset fallbacks */
function loadLayouts(): Record<string, Layout[]> {
  try {
    return { ...PRESETS, ...JSON.parse(localStorage.getItem(STORE) ?? '{}') }
  } catch {
    return { ...PRESETS }
  }
}

/** bento dashboard: locked in operate mode, draggable/resizable in edit mode, layouts saved per task */
export function Dashboard() {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [gridW, setGridW] = useState(1200)
  const ax = useApp((s) => s.axis)
  const alarms = useApp((s) => s.status?.safety.alarms.length ?? 0)
  const [layouts, setLayouts] = useState(loadLayouts)
  const [preset, setPreset] = useState<string>(() => localStorage.getItem(STORE + '.active') ?? 'bench')
  const [edit, setEdit] = useState(false)
  const [paused, setPaused] = useState(false)
  const [windowS, setWindowS] = useState(10)
  const layout = layouts[preset] ?? PRESETS.bench

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const update = () => setGridW(Math.max(640, el.clientWidth))
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const body = (id: PanelId): ReactNode => {
    switch (id) {
      case 'hologram':
        return <OdriveHologram ax={ax} />
      case 'motion':
        return <MotionPlot ax={ax} windowS={windowS} paused={paused} />
      case 'current':
        return <CurrentPlot ax={ax} windowS={windowS} paused={paused} />
      case 'power':
        return <PowerPlot windowS={windowS} paused={paused} />
      case 'thermal':
        return <ThermalPlot ax={ax} windowS={Math.max(windowS, 60)} paused={paused} />
      case 'axis':
        return <AxisCard ax={ax} />
      case 'joint':
        return <JointCard ax={ax} />
      case 'errors':
        return <ErrorsPanel ax={ax} />
      case 'encoder':
        return <EncoderCard ax={ax} />
      case 'powercard':
        return <PowerCard />
      case 'events':
        return <EventsPanel />
      default: {
        const never: never = id
        return never
      }
    }
  }

  const save = (next: Layout[]) => {
    const all = { ...layouts, [preset]: next }
    setLayouts(all)
    localStorage.setItem(STORE, JSON.stringify(all))
  }
  const items = useMemo(() => layout.map((l) => l.i as PanelId), [layout])

  return (
    <div ref={wrapRef}>
      <div className="view-head">
        <h1>DASHBOARD</h1>
        <div className="row" style={{ marginLeft: 'auto' }}>
          {Object.keys(PRESETS).map((p) => (
            <Button
              key={p}
              small
              kind={p === preset ? 'on' : ''}
              onClick={() => {
                setPreset(p)
                localStorage.setItem(STORE + '.active', p)
              }}
            >
              {p}
            </Button>
          ))}
          <span className="muted">|</span>
          {[0, 1].map((a) => (
            <Button key={a} small kind={a === ax ? 'on' : ''} onClick={() => useApp.setState({ axis: a })}>
              ax{a}
            </Button>
          ))}
          <span className="muted">|</span>
          {[5, 10, 30, 60].map((w) => (
            <Button key={w} small kind={w === windowS ? 'on' : ''} onClick={() => setWindowS(w)}>
              {w}s
            </Button>
          ))}
          <Button small kind={paused ? 'danger' : ''} onClick={() => setPaused(!paused)}>
            {paused ? 'paused' : 'pause'}
          </Button>
          <span className="muted">|</span>
          <Button small kind={edit ? 'primary' : ''} onClick={() => setEdit(!edit)}>
            {edit ? 'lock' : 'edit'}
          </Button>
          {edit && (
            <Button small onClick={() => save(PRESETS[preset])}>
              reset
            </Button>
          )}
        </div>
      </div>
      <GridLayout
        className={`bento ${edit ? 'editing' : ''}`}
        layout={layout}
        width={gridW}
        cols={12}
        rowHeight={22}
        margin={[8, 8]}
        containerPadding={[0, 0]}
        isDraggable={edit}
        isResizable={edit}
        draggableHandle=".panel-head"
        onLayoutChange={(l) => edit && save(l)}
      >
        {items.map((id) => {
          const m = META[id]
          const isAlarm = id === 'errors' && alarms > 0
          return (
            <div key={id}>
              <Panel
                index={m.idx}
                title={m.title}
                status={isAlarm ? 'alarm' : 'live'}
                alarm={isAlarm}
                flush={['hologram', 'motion', 'current', 'power', 'thermal'].includes(id)}
              >
                {body(id)}
              </Panel>
            </div>
          )
        })}
      </GridLayout>
    </div>
  )
}
