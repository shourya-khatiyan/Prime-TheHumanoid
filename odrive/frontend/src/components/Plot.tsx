import { useEffect, useRef, useState } from 'react'
import uPlot, { type AlignedData, type Options } from 'uplot'
import 'uplot/dist/uPlot.min.css'
import { m4, telemetry } from '../lib/telemetry'
import { useStream } from '../lib/store'
import './plot.css'

export type SeriesDef = { path: string; label: string; scale?: string; color?: number; transform?: (v: number) => number }

const SERIES_VARS = ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6']
const DASHES: number[][] = [[], [6, 3], [2, 3], [10, 3, 2, 3], [4, 4], [1, 2]]

// minimum vertical span per unit so idle ADC noise never auto-zooms to 100% chart height
const MIN_SPAN: Record<string, number> = {
  turn: 0.2,
  'turn/s': 0.5,
  A: 1.0,
  V: 1.0,
  C: 4.0,
}

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

/** short tick labels: at most ~6 characters, clean zero, exponent only for huge values */
function ticks(_u: uPlot, splits: number[]): string[] {
  const span = Math.abs((splits[splits.length - 1] ?? 0) - (splits[0] ?? 0))
  return splits.map((v) => {
    const a = Math.abs(v)
    if (a < 1e-6) return '0'
    if (a >= 1e5 || a < 1e-3) return v.toExponential(1)
    const digits = span > 0 ? Math.max(0, Math.min(3, Math.ceil(-Math.log10(span)) + 1)) : 2
    return v.toFixed(digits)
  })
}

/** compute y-axis range with a deadband floor so steady signals stay calm */
function yScaleRange(unit: string): uPlot.Range.Function {
  const minSpan = MIN_SPAN[unit] ?? 0.2
  return (_u, dataMin, dataMax) => {
    if (!Number.isFinite(dataMin) || !Number.isFinite(dataMax)) return [-minSpan / 2, minSpan / 2]
    const span = dataMax - dataMin
    if (span < minSpan) {
      const mid = Math.abs(dataMin + dataMax) * 0.5 < minSpan * 0.15 ? 0 : (dataMin + dataMax) * 0.5
      return [mid - minSpan * 0.5, mid + minSpan * 0.5]
    }
    const pad = span * 0.08
    return [dataMin - pad, dataMax + pad]
  }
}

/** shared dark terminal look for every chart */
function baseOpts(
  width: number,
  height: number,
  series: { label: string; scale?: string; color?: number }[],
  scales: string[],
  xLabel: string,
  legend = true,
  windowS?: number,
): Options {
  const grid = { stroke: cssVar('--grid-major'), width: 1 }
  const tickStyle = { stroke: cssVar('--border'), width: 1 }
  const axisFont = `10px ${cssVar('--font')}`
  const axes: uPlot.Axis[] = [
    { stroke: cssVar('--muted'), grid, ticks: tickStyle, font: axisFont, size: 22 },
  ]
  scales.forEach((sc, i) => {
    axes.push({
      scale: sc,
      side: i === 0 ? 3 : 1,
      stroke: cssVar('--muted'),
      grid: i === 0 ? grid : { show: false },
      ticks: tickStyle,
      values: ticks,
      font: axisFont,
      size: 46,
    })
  })
  return {
    width,
    height,
    legend: { show: legend, live: true },
    cursor: { drag: { x: true, y: false }, points: { size: 4 } },
    scales: {
      x: windowS ? { time: false, range: () => [-windowS, 0] } : { time: false },
      ...Object.fromEntries(scales.map((s) => [s, { auto: true, range: yScaleRange(s) }])),
    },
    axes,
    series: [
      { label: xLabel },
      ...series.map((s, i) => {
        const c = s.color ?? i
        return {
          label: s.label,
          scale: s.scale ?? scales[0],
          stroke: cssVar(SERIES_VARS[c % SERIES_VARS.length]),
          width: 1.35,
          dash: DASHES[c % DASHES.length],
          points: { show: false },
          spanGaps: false,
        }
      }),
    ],
  }
}

/** keep a chart sized to its container */
function useSize(ref: React.RefObject<HTMLDivElement | null>) {
  const [size, setSize] = useState({ w: 300, h: 160 })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(() => setSize({ w: Math.max(120, el.clientWidth), h: Math.max(80, el.clientHeight) }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [ref])
  return size
}

/**
 * live telemetry chart.
 * pulls from the shared ring buffers, m4-downsamples to the pixel width and redraws at ~20 fps.
 */
export function LivePlot({ series, windowS = 10, paused = false }: { series: SeriesDef[]; windowS?: number; paused?: boolean }) {
  const wrap = useRef<HTMLDivElement>(null)
  const plotEl = useRef<HTMLDivElement>(null)
  const chart = useRef<uPlot | null>(null)
  const legendEl = useRef<HTMLDivElement>(null)
  const [localPause, setLocalPause] = useState(false)
  const isPaused = paused || localPause
  const size = useSize(wrap)
  const paths = series.map((s) => s.path).filter(Boolean)
  const key = series.map((s) => `${s.path}:${s.scale}:${s.label}`).join('|') + `:${windowS}`
  useStream(paths)

  useEffect(() => {
    if (!plotEl.current) return
    const scales = [...new Set(series.map((s) => s.scale ?? 'y'))]
    const opts = baseOpts(size.w, Math.max(60, size.h - 22), series, scales, 's', false, windowS)
    const empty: AlignedData = [[], ...series.map(() => [])]
    chart.current = new uPlot(opts, empty, plotEl.current)
    return () => {
      chart.current?.destroy()
      chart.current = null
    }
  }, [key])

  useEffect(() => {
    chart.current?.setSize({ width: size.w, height: Math.max(60, size.h - 22) })
  }, [size.w, size.h])

  useEffect(() => {
    let raf = 0
    let seen = -1
    let last = 0
    const draw = (now: number) => {
      raf = requestAnimationFrame(draw)
      if (isPaused || !chart.current || now - last < 50 || telemetry.version === seen) return
      last = now
      seen = telemetry.version
      const { t, ys } = telemetry.window(paths, windowS)
      const ds = m4(t, ys, Math.max(50, Math.floor(size.w / 2)))
      const t0 = telemetry.lastTs
      const x = ds.t.map((v) => v - t0)
      const yy = ds.ys.map((arr, i) => {
        const tr = series[i]?.transform
        return tr ? arr.map(tr) : arr
      })
      chart.current.setData([x, ...yy] as AlignedData, true)
      const spans = legendEl.current?.querySelectorAll<HTMLSpanElement>('.lv')
      spans?.forEach((el, i) => {
        const arr = yy[i]
        const v = arr && arr.length ? arr[arr.length - 1] : NaN
        const clean = Math.abs(v) < 5e-4 ? 0 : v
        el.textContent = Number.isFinite(clean) ? clean.toFixed(2) : '--'
      })
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [key, windowS, isPaused, size.w])

  const missing = paths.length < series.length
  return (
    <div className="plot" ref={wrap} onDoubleClick={() => setLocalPause((p) => !p)} title="Double-click to pause/resume trace">
      {missing && <div className="plot-empty">NO DATA</div>}
      <div ref={plotEl} />
      <div className="plot-legend" ref={legendEl}>
        {series.map((s, i) => (
          <span key={s.label} className="li">
            <i style={{ background: `var(${SERIES_VARS[(s.color ?? i) % SERIES_VARS.length]})` }} />
            {s.label} <span className="lv num">--</span>
            <span className="muted"> {s.scale}</span>
          </span>
        ))}
        {isPaused && <span className="warn-text" style={{ marginLeft: 'auto' }}>PAUSED</span>}
      </div>
    </div>
  )
}

/** chart for static data (recordings, job results). x is the first array. */
export function StaticPlot({ x, ys, labels, scales, xLabel = 's' }: { x: number[]; ys: (number | null)[][]; labels: string[]; scales?: string[]; xLabel?: string }) {
  const wrap = useRef<HTMLDivElement>(null)
  const plotEl = useRef<HTMLDivElement>(null)
  const chart = useRef<uPlot | null>(null)
  const size = useSize(wrap)
  const key = labels.join('|') + (scales ?? []).join('|')

  useEffect(() => {
    if (!plotEl.current) return
    const sc = scales ?? labels.map(() => 'y')
    const uniq = [...new Set(sc)]
    const opts = baseOpts(size.w, Math.max(60, size.h - 22), labels.map((l, i) => ({ label: l, scale: sc[i], color: i })), uniq, xLabel)
    chart.current = new uPlot(opts, [x, ...ys] as AlignedData, plotEl.current)
    return () => {
      chart.current?.destroy()
      chart.current = null
    }
  }, [key, xLabel])

  useEffect(() => {
    chart.current?.setData([x, ...ys] as AlignedData, true)
  }, [x, ys])

  useEffect(() => {
    chart.current?.setSize({ width: size.w, height: Math.max(60, size.h - 22) })
  }, [size.w, size.h])

  return (
    <div className="plot" ref={wrap}>
      {x.length === 0 && <div className="plot-empty">NO DATA</div>}
      <div ref={plotEl} />
    </div>
  )
}
