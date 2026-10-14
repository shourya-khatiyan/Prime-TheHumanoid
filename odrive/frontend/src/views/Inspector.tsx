import { useEffect, useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Button, Panel, PropInput } from '../primitives'
import { LivePlot } from '../components/Plot'
import { act, useApp } from '../lib/store'
import { decodeFlags, enumName } from '../lib/meta'
import { fmt, hex } from '../lib/format'
import './inspector.css'

const FAV_KEY = 'odrv.favourites.v1'

/** full device property tree: search, favourites, live values for visible rows, edit, call, chart */
export function Inspector() {
  const tree = useApp((s) => s.tree)
  const meta = useApp((s) => s.meta)
  const [q, setQ] = useState('')
  const [favs, setFavs] = useState<string[]>(() => JSON.parse(localStorage.getItem(FAV_KEY) ?? '[]'))
  const [onlyFav, setOnlyFav] = useState(false)
  const [charted, setCharted] = useState<string[]>([])
  const [values, setValues] = useState<Record<string, unknown>>({})
  const [editing, setEditing] = useState<string | null>(null)
  const [args, setArgs] = useState<Record<string, string>>({})
  const scroller = useRef<HTMLDivElement>(null)

  const rows = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean)
    const all = Object.keys(tree)
      .filter((p) => words.every((w) => p.toLowerCase().includes(w) || (meta?.props[p]?.brief ?? '').toLowerCase().includes(w)))
      .filter((p) => !onlyFav || favs.includes(p))
      .sort()
    return [...all.filter((p) => favs.includes(p)), ...all.filter((p) => !favs.includes(p))]
  }, [tree, q, favs, onlyFav, meta])

  const virt = useVirtualizer({ count: rows.length, getScrollElement: () => scroller.current, estimateSize: () => 26, overscan: 10 })
  const visible = virt.getVirtualItems().map((v) => rows[v.index])
  const visibleKey = visible.join('|')

  // poll only what is on screen, once a second
  useEffect(() => {
    let stop = false
    const props = visible.filter((p) => tree[p]?.kind === 'prop')
    const tick = () =>
      props.length &&
      act<Record<string, unknown>>('read', { paths: props }, true)
        .then((v) => !stop && setValues((old) => ({ ...old, ...v })))
        .catch(() => undefined)
    tick()
    const id = setInterval(tick, 1000)
    return () => {
      stop = true
      clearInterval(id)
    }
  }, [visibleKey, tree])

  const toggleFav = (p: string) => {
    const next = favs.includes(p) ? favs.filter((x) => x !== p) : [...favs, p]
    setFavs(next)
    localStorage.setItem(FAV_KEY, JSON.stringify(next))
  }

  const render = (p: string) => {
    const node = tree[p]
    const m = meta?.props[p]
    const v = values[p]
    if (node.kind === 'func') {
      return (
        <>
          <span className="cell-type muted">fn({(node.args ?? []).join(', ')})</span>
          <span className="cell-val">
            {(node.args?.length ?? 0) > 0 && <input value={args[p] ?? ''} placeholder={node.args!.join(', ')} onChange={(e) => setArgs({ ...args, [p]: e.target.value })} style={{ width: 160 }} />}
          </span>
          <Button
            small
            onClick={() =>
              act('call', {
                path: p,
                args: (args[p] ?? '')
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean)
                  .map(Number),
              }).then((r) => setValues({ ...values, [p]: r }))
            }
          >
            call
          </Button>
          <span className="muted">{v !== undefined ? `-> ${fmt(v)}` : ''}</span>
        </>
      )
    }
    const flags = m?.enum && meta?.enums[m.enum]?.kind === 'flags' ? decodeFlags(meta, p, v) : null
    const en = enumName(meta, p, v)
    return (
      <>
        <span className="cell-type muted">
          {node.writable ? 'rw' : 'r '} {node.type}
        </span>
        <span className="cell-val num" onDoubleClick={() => node.writable && setEditing(p)}>
          {editing === p ? (
            <PropInput
              meta={meta}
              path={p}
              type={node.type}
              value={v}
              onCommit={(nv) => {
                setEditing(null)
                act('write', { path: p, value: nv })
                  .then(() => act<Record<string, unknown>>('read', { paths: [p] }, true))
                  .then((r) => setValues((o) => ({ ...o, ...r })))
                  .catch(() => undefined)
              }}
            />
          ) : flags ? (
            <span className={flags.length ? 'error-text' : ''}>
              {hex(v)} {flags.join(' | ')}
            </span>
          ) : (
            <>
              {fmt(v, 5)}
              {en && <span className="dim"> {en}</span>}
              <span className="muted"> {m?.unit ?? ''}</span>
            </>
          )}
        </span>
        {node.writable && editing !== p && (
          <Button small onClick={() => setEditing(p)}>
            edit
          </Button>
        )}
        <label className="muted" title="chart this property">
          <input type="checkbox" checked={charted.includes(p)} onChange={(e) => setCharted(e.target.checked ? [...charted, p].slice(-6) : charted.filter((x) => x !== p))} /> plot
        </label>
      </>
    )
  }

  return (
    <div>
      <div className="view-head">
        <h1>inspector</h1>
        <span className="sub">{rows.length} of {Object.keys(tree).length} entries . double-click a value to edit</span>
        <div className="row" style={{ marginLeft: 'auto' }}>
          <input placeholder="search path or doc (space = and)" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 320 }} autoFocus />
          <Button small kind={onlyFav ? 'on' : ''} onClick={() => setOnlyFav(!onlyFav)}>
            favourites
          </Button>
        </div>
      </div>
      {charted.length > 0 && (
        <Panel title={`plot . ${charted.length} signals (max 6)`} tools={<Button small onClick={() => setCharted([])}>clear</Button>} flush>
          <div className="h-plot">
            <LivePlot series={charted.map((p, i) => ({ path: p, label: p.split('.').slice(-2).join('.'), scale: meta?.props[p]?.unit ?? `y${i}` }))} windowS={20} />
          </div>
        </Panel>
      )}
      <div className="insp" ref={scroller}>
        <div style={{ height: virt.getTotalSize(), position: 'relative' }}>
          {virt.getVirtualItems().map((vi) => {
            const p = rows[vi.index]
            const parts = p.split('.')
            return (
              <div key={p} className="insp-row" style={{ transform: `translateY(${vi.start}px)` }} title={[meta?.props[p]?.brief, meta?.props[p]?.doc, meta?.funcs[p]?.doc].filter(Boolean).join('\n\n')}>
                <button className={`star ${favs.includes(p) ? 'on' : ''}`} onClick={() => toggleFav(p)} aria-label="favourite">
                  {favs.includes(p) ? '*' : '.'}
                </button>
                <span className="cell-path">
                  <span className="muted">{parts.slice(0, -1).join('.')}.</span>
                  {parts[parts.length - 1]}
                </span>
                {render(p)}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
