import { useMemo, useState, type ReactNode } from 'react'
import GridLayout, { WidthProvider, type Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import { Button, Panel } from '../primitives'
import { useApp } from '../lib/store'
import { AxisCard, CurrentPlot, EncoderCard, ErrorsPanel, EventsPanel, JointCard, MotionPlot, PowerCard, PowerPlot, ThermalPlot } from './panels'
import './dashboard.css'

const Grid = WidthProvider(GridLayout)
const STORE = 'odrv.layouts.v1'

type PanelId = 'motion' | 'current' | 'power' | 'thermal' | 'axis' | 'joint' | 'errors' | 'encoder' | 'powercard' | 'events'

// panel size follows how much the data matters for decisions: one anchor, the rest smaller
const PRESETS: Record<string, Layout[]> = {
  bench: [
    { i: 'motion', x: 0, y: 0, w: 8, h: 9 },
    { i: 'axis', x: 8, y: 0, w: 4, h: 9 },
    { i: 'current', x: 0, y: 9, w: 5, h: 7 },
    { i: 'errors', x: 5, y: 9, w: 3, h: 7 },
    { i: 'encoder', x: 8, y: 9, w: 4, h: 7 },
    { i: 'joint', x: 0, y: 16, w: 5, h: 5 },
    { i: 'powercard', x: 5, y: 16, w: 3, h: 5 },
    { i: 'power', x: 8, y: 16, w: 4, h: 5 },
    { i: 'thermal', x: 0, y: 21, w: 6, h: 6 },
    { i: 'events', x: 6, y: 21, w: 6, h: 6 },
  ],
  tuning: [
    { i: 'motion', x: 0, y: 0, w: 9, h: 11 },
    { i: 'axis', x: 9, y: 0, w: 3, h: 11 },
    { i: 'current', x: 0, y: 11, w: 9, h: 8 },
    { i: 'errors', x: 9, y: 11, w: 3, h: 8 },
    { i: 'joint', x: 0, y: 19, w: 6, h: 5 },
    { i: 'encoder', x: 6, y: 19, w: 6, h: 5 },
  ],
  thermal: [
    { i: 'thermal', x: 0, y: 0, w: 8, h: 11 },
    { i: 'powercard', x: 8, y: 0, w: 4, h: 5 },
    { i: 'axis', x: 8, y: 5, w: 4, h: 6 },
    { i: 'current', x: 0, y: 11, w: 6, h: 7 },
    { i: 'power', x: 6, y: 11, w: 6, h: 7 },
    { i: 'errors', x: 0, y: 18, w: 6, h: 5 },
    { i: 'events', x: 6, y: 18, w: 6, h: 5 },
  ],
}

const TITLES: Record<PanelId, string> = {
  motion: 'motion . pos / vel',
  current: 'current . Iq setpoint vs measured',
  power: 'dc bus',
  thermal: 'temperature',
  axis: 'axis',
  joint: 'joint space (via gear ratio)',
  errors: 'errors . first-out',
  encoder: 'encoder . AS5047P',
  powercard: 'power',
  events: 'events',
}

function loadLayouts(): Record<string, Layout[]> {
  try {
    return { ...PRESETS, ...JSON.parse(localStorage.getItem(STORE) ?? '{}') }
  } catch {
    return { ...PRESETS }
  }
}

/** bento dashboard: locked in operate mode, draggable/resizable in edit mode, layouts saved per task */
export function Dashboard() {
  const ax = useApp((s) => s.axis)
  const alarms = useApp((s) => s.status?.safety.alarms.length ?? 0)
  const [layouts, setLayouts] = useState(loadLayouts)
  const [preset, setPreset] = useState<string>(() => localStorage.getItem(STORE + '.active') ?? 'bench')
  const [edit, setEdit] = useState(false)
  const [windowS, setWindowS] = useState(10)
  const layout = layouts[preset] ?? PRESETS.bench

  const body = (id: PanelId): ReactNode => {
    switch (id) {
      case 'motion':
        return <MotionPlot ax={ax} windowS={windowS} />
      case 'current':
        return <CurrentPlot ax={ax} windowS={windowS} />
      case 'power':
        return <PowerPlot windowS={windowS} />
      case 'thermal':
        return <ThermalPlot ax={ax} windowS={Math.max(windowS, 60)} />
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
    <div>
      <div className="view-head">
        <h1>dashboard</h1>
        <span className="sub">axis{ax}</span>
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
              axis{a}
            </Button>
          ))}
          <span className="muted">|</span>
          {[5, 10, 30, 60].map((w) => (
            <Button key={w} small kind={w === windowS ? 'on' : ''} onClick={() => setWindowS(w)}>
              {w}s
            </Button>
          ))}
          <span className="muted">|</span>
          <Button small kind={edit ? 'primary' : ''} onClick={() => setEdit(!edit)}>
            {edit ? 'done editing' : 'edit layout'}
          </Button>
          {edit && (
            <Button small onClick={() => save(PRESETS[preset])}>
              reset
            </Button>
          )}
        </div>
      </div>
      <Grid
        className={`bento ${edit ? 'editing' : ''}`}
        layout={layout}
        cols={12}
        rowHeight={30}
        margin={[6, 6]}
        containerPadding={[0, 0]}
        isDraggable={edit}
        isResizable={edit}
        draggableHandle=".panel-head"
        onLayoutChange={(l) => edit && save(l)}
      >
        {items.map((id) => (
          <div key={id}>
            <Panel title={TITLES[id]} alarm={id === 'errors' && alarms > 0} flush={['motion', 'current', 'power', 'thermal'].includes(id)}>
              {body(id)}
            </Panel>
          </div>
        ))}
      </Grid>
    </div>
  )
}
