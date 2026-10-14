import { useEffect, useMemo, useState } from 'react'
import { Button, NumInput, Panel, PropInput, Tabs, Tag } from '../primitives'
import { act, say, startJob, useApp, waitJob } from '../lib/store'
import { rpc } from '../lib/rpc'
import { date, fmt } from '../lib/format'

type Snapshot = Record<string, unknown>

const GROUPS: [string, string, (p: string, a: string) => boolean][] = [
  ['power', 'power / brake', (p) => /^config\.(dc_|brake|enable_brake|max_regen|enable_dc_bus)/.test(p)],
  ['motor', 'motor', (p, a) => p.startsWith(`${a}.motor.config.`) && !p.includes('acim')],
  ['encoder', 'encoder', (p, a) => p.startsWith(`${a}.encoder.config.`)],
  ['controller', 'controller', (p, a) => p.startsWith(`${a}.controller.config.`) && !p.includes('anticogging')],
  ['trap', 'trap trajectory', (p, a) => p.startsWith(`${a}.trap_traj.`)],
  ['axis', 'axis / watchdog / startup', (p, a) => p.startsWith(`${a}.config.`) && !p.includes('lockin') && !p.includes('can')],
  ['can', 'can', (p, a) => p.startsWith('can.') || (p.startsWith(`${a}.config.`) && p.includes('can'))],
  ['thermistors', 'thermistors', (p, a) => p.startsWith(a) && p.includes('thermistor.config')],
  ['endstops', 'endstops / homing', (p, a) => p.startsWith(`${a}.min_endstop`) || p.startsWith(`${a}.max_endstop`) || p === `${a}.controller.config.homing_speed`],
  ['anticogging', 'anticogging', (p, a) => p.startsWith(`${a}.controller.config.anticogging`)],
  ['lockin', 'lock-in / sensorless', (p, a) => (p.startsWith(`${a}.config.`) && p.includes('lockin')) || p.startsWith(`${a}.sensorless_estimator`)],
  ['io', 'interfaces / gpio', (p) => /^config\.(enable_uart|uart|gpio|enable_i2c|enable_can|usb_cdc|enable_ascii)/.test(p)],
  ['acim', 'acim (induction motors)', (p, a) => p.startsWith(a) && p.includes('acim')],
]

function same(a: unknown, b: unknown): boolean {
  if (typeof a === 'number' && typeof b === 'number') return a === b || Math.abs(a - b) <= 1e-6 * Math.max(1, Math.abs(a)) || (Number.isNaN(a) && Number.isNaN(b))
  return String(a) === String(b)
}

/** grouped property editor with staged changes: apply writes them live, save stores them in flash */
function Editor({ snap, reload }: { snap: Snapshot; reload: () => void }) {
  const ax = useApp((s) => s.axis)
  const meta = useApp((s) => s.meta)
  const tree = useApp((s) => s.tree)
  const [group, setGroup] = useState('motor')
  const [staged, setStaged] = useState<Record<string, unknown>>({})
  const [filter, setFilter] = useState('')
  const a = `axis${ax}`
  const paths = useMemo(() => {
    const def = GROUPS.find((g) => g[0] === group)!
    return Object.keys(snap)
      .filter((p) => def[2](p, a))
      .filter((p) => !filter || p.includes(filter))
      .sort()
  }, [snap, group, a, filter])
  const nStaged = Object.keys(staged).length
  const apply = async () => {
    try {
      const j = await waitJob(await startJob('config_apply', { changes: Object.entries(staged).map(([path, value]) => ({ path, value })) }))
      if (j.state === 'done') {
        setStaged({})
        say(`${j.result.written.length} written, ${j.result.failed.length} failed; not saved yet`)
      }
    } catch {
      // cancelled
    }
    reload()
  }
  return (
    <div className="grid2" style={{ gridTemplateColumns: '220px 1fr' }}>
      <Panel title="groups">
        <div className="col">
          {GROUPS.map(([id, label]) => (
            <Button key={id} small kind={id === group ? 'on' : ''} onClick={() => setGroup(id)}>
              {label}
            </Button>
          ))}
          <div className="row" style={{ marginTop: 8 }}>
            {[0, 1].map((x) => (
              <Button key={x} small kind={x === ax ? 'on' : ''} onClick={() => useApp.setState({ axis: x })}>
                axis{x}
              </Button>
            ))}
          </div>
        </div>
      </Panel>
      <Panel
        title={`${GROUPS.find((g) => g[0] === group)![1]} . ${paths.length} settings`}
        tools={
          <>
            <input placeholder="filter" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ width: 140 }} />
            <Button small onClick={reload}>
              pull from device
            </Button>
          </>
        }
      >
        {paths.map((p) => {
          const dev = snap[p]
          const val = p in staged ? staged[p] : dev
          const m = meta?.props[p]
          return (
            <div key={p} className={`field ${p in staged ? 'changed' : ''}`} title={[p, m?.brief, m?.doc].filter(Boolean).join('\n\n')}>
              <label>{p.replace(/^axis\d\./, '').replace(/^(motor|encoder|controller|trap_traj)\.config\./, '').replace(/^config\./, '')}</label>
              <PropInput
                meta={meta}
                path={p}
                type={tree[p]?.type}
                value={val}
                onCommit={(v) =>
                  setStaged((s) => {
                    const n = { ...s }
                    if (same(v, dev)) delete n[p]
                    else n[p] = v
                    return n
                  })
                }
              />
              <span className="unit">
                {m?.unit ?? ''}
                {p in staged && <span className="muted"> was {fmt(dev)}</span>}
              </span>
            </div>
          )
        })}
        <div className="row" style={{ position: 'sticky', bottom: -8, background: 'var(--surface)', padding: '8px 0', borderTop: '1px solid var(--border)', marginTop: 8 }}>
          <span className="dim">{nStaged} staged</span>
          <Button kind="primary" disabled={!nStaged} onClick={apply}>
            apply live
          </Button>
          <Button disabled={!nStaged} onClick={() => setStaged({})}>
            discard
          </Button>
          <Button onClick={() => act('call', { path: 'save_configuration', args: [] }).catch(() => undefined)}>save to flash</Button>
          <Button kind="danger" onClick={() => act('call', { path: 'erase_configuration', args: [] }).catch(() => undefined)}>
            erase config
          </Button>
          <Button onClick={() => act('call', { path: 'reboot', args: [] }).catch(() => undefined)}>reboot</Button>
        </div>
      </Panel>
    </div>
  )
}

/** named backups double as presets: save, compare against the device, restore */
function Backups({ snap, reload }: { snap: Snapshot; reload: () => void }) {
  const [list, setList] = useState<any[]>([])
  const [name, setName] = useState('')
  const [cmp, setCmp] = useState<{ id: string; rows: { path: string; dev: unknown; bak: unknown }[] } | null>(null)
  const refresh = () => act<any[]>('backup_list', {}, true).then(setList).catch(() => undefined)
  useEffect(() => {
    refresh()
  }, [])
  const compare = async (id: string) => {
    const doc = await act<any>('backup_load', { id })
    const rows = Object.entries(doc.values as Record<string, unknown>)
      .filter(([p, v]) => p in snap && !same(snap[p], v))
      .map(([path, bak]) => ({ path, dev: snap[path], bak }))
    setCmp({ id, rows })
  }
  const restore = async () => {
    if (!cmp) return
    try {
      await waitJob(await startJob('config_apply', { changes: cmp.rows.map((r) => ({ path: r.path, value: r.bak })) }))
    } catch {
      // cancelled
    }
    reload()
    setCmp(null)
  }
  return (
    <div className="grid2">
      <Panel title="backups / presets">
        <div className="row" style={{ marginBottom: 6 }}>
          <input placeholder="name, e.g. shoulder-tuned-v1" value={name} onChange={(e) => setName(e.target.value)} />
          <Button
            kind="primary"
            onClick={async () => {
              await act('backup_save', { name: name || 'backup' })
              setName('')
              refresh()
            }}
          >
            save backup of device
          </Button>
        </div>
        <table>
          <thead>
            <tr>
              <th>name</th>
              <th>device</th>
              <th>created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {list.map((b) => (
              <tr key={b.id}>
                <td>{b.name}</td>
                <td className="muted">
                  {b.device?.serial} fw {b.device?.fw}
                </td>
                <td className="muted num">{date(b.created)}</td>
                <td className="row">
                  <Button small onClick={() => compare(b.id)}>
                    compare
                  </Button>
                  <a href={`/api/backup/${b.id}.json?token=${rpc.token}`} target="_blank" rel="noreferrer">
                    json
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
      <Panel title={cmp ? `diff . ${cmp.id}` : 'diff'} tools={cmp && cmp.rows.length > 0 && <Button kind="primary" small onClick={restore}>restore {cmp.rows.length} values</Button>}>
        {!cmp && <span className="muted">compare a backup to see what differs from the device</span>}
        {cmp && cmp.rows.length === 0 && <span className="ok-text">device matches this backup</span>}
        {cmp && cmp.rows.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>path</th>
                <th>device</th>
                <th>backup</th>
              </tr>
            </thead>
            <tbody>
              {cmp.rows.map((r) => (
                <tr key={r.path}>
                  <td>{r.path}</td>
                  <td className="num">{fmt(r.dev)}</td>
                  <td className="num dim">{fmt(r.bak)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  )
}

/** editable actuator profile: the limits the backend enforces */
function ProfileEditor() {
  const profile = useApp((s) => s.profile)
  const [draft, setDraft] = useState<any>(null)
  useEffect(() => {
    if (profile) setDraft(structuredClone(profile))
  }, [profile])
  if (!draft) return <span className="muted">no profile</span>
  const sections = Object.entries(draft).filter(([k, v]) => k !== 'derived' && typeof v === 'object')
  const set = (sec: string, key: string, v: unknown) => setDraft({ ...draft, [sec]: { ...draft[sec], [key]: v } })
  return (
    <div>
      <div className="row" style={{ marginBottom: 6 }}>
        <span className="dim">name</span>
        <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} style={{ width: 300 }} />
        <span className="dim">axis</span>
        <NumInput value={draft.axis} onCommit={(v) => setDraft({ ...draft, axis: Math.trunc(v) })} width={50} />
        <Button
          kind="primary"
          onClick={async () => {
            const saved = await act('profile_set', { data: draft })
            useApp.setState({ profile: saved })
            say('profile saved; new limits apply immediately')
          }}
        >
          save profile
        </Button>
        <span className="muted">
          Kt {fmt(profile!.derived.kt_nm_per_a, 4)} Nm/A . torque max {fmt(profile!.derived.torque_max_nm, 3)} Nm . joint peak {fmt(profile!.derived.joint_torque_peak_nm, 1)} Nm
        </span>
      </div>
      <div className="grid3">
        {sections.map(([sec, obj]) => (
          <Panel key={sec} title={sec}>
            {Object.entries(obj as Record<string, unknown>).map(([k, v]) => (
              <div className="field" key={k}>
                <label>{k}</label>
                {typeof v === 'number' ? (
                  <NumInput value={v} onCommit={(nv) => set(sec, k, nv)} />
                ) : typeof v === 'boolean' ? (
                  <input type="checkbox" checked={v} onChange={(e) => set(sec, k, e.target.checked)} />
                ) : sec === 'encoder' && k === 'mode' ? (
                  <select value={String(v)} onChange={(e) => set(sec, k, e.target.value)}>
                    <option value="SPI_ABS_AMS">SPI_ABS_AMS (absolute, AS5047P over SPI)</option>
                    <option value="INCREMENTAL">INCREMENTAL (A/B/Z quadrature)</option>
                  </select>
                ) : (
                  <input value={String(v)} onChange={(e) => set(sec, k, e.target.value)} />
                )}
                <span />
              </div>
            ))}
          </Panel>
        ))}
      </div>
    </div>
  )
}

export function Config() {
  const [tab, setTab] = useState('edit')
  const [snap, setSnap] = useState<Snapshot>({})
  const connected = useApp((s) => s.status?.device.connected)
  const gen = useApp((s) => s.status?.device.generation)
  const reload = () => act<Snapshot>('config_snapshot', {}, true).then(setSnap).catch(() => undefined)
  useEffect(() => {
    if (connected) reload()
  }, [connected, gen])
  return (
    <div>
      <div className="view-head">
        <h1>configuration</h1>
        <span className="sub">{Object.keys(snap).length} writable settings . changes are staged, then applied live, then saved to flash</span>
        {!connected && <Tag level="warn">no device</Tag>}
      </div>
      <Tabs
        tabs={[
          ['edit', 'editor'],
          ['backups', 'backups / presets'],
          ['profile', 'actuator profile'],
        ]}
        value={tab}
        onChange={setTab}
      />
      <div style={{ marginTop: 6 }}>
        {tab === 'edit' && <Editor snap={snap} reload={reload} />}
        {tab === 'backups' && <Backups snap={snap} reload={reload} />}
        {tab === 'profile' && <ProfileEditor />}
      </div>
    </div>
  )
}
