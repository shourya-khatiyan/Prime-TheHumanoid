import { useEffect, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Button, NumInput, Panel, Tag } from '../primitives'
import { act, onCan, P, useApp, useLatest, type CanFrame } from '../lib/store'
import { time } from '../lib/format'

const CMDS: [number, string, string[]][] = [
  [0x001, 'heartbeat (rtr)', []],
  [0x002, 'estop', []],
  [0x007, 'set_requested_state', ['state']],
  [0x009, 'get_encoder_estimates (rtr)', []],
  [0x00b, 'set_controller_mode', ['control_mode', 'input_mode']],
  [0x00c, 'set_input_pos', ['pos', 'vel_ff', 'torque_ff']],
  [0x00d, 'set_input_vel', ['vel', 'torque_ff']],
  [0x00e, 'set_input_torque', ['torque']],
  [0x00f, 'set_limits', ['vel_limit', 'current_limit']],
  [0x014, 'get_iq (rtr)', []],
  [0x017, 'get_vbus_voltage (rtr)', []],
  [0x018, 'clear_errors', []],
  [0x016, 'reboot', []],
]

/** CAN monitor (CANSimple decode), send console and the usb-side CAN setup of the ODrive */
export function Can() {
  const can = useApp((s) => s.status?.can)
  const tree = useApp((s) => s.tree)
  const ax = useApp((s) => s.axis)
  const [frames, setFrames] = useState<CanFrame[]>([])
  const [paused, setPaused] = useState(false)
  const [iface, setIface] = useState('slcan')
  const [channel, setChannel] = useState('COM8')
  const [bitrate, setBitrate] = useState(1000000)
  const [detected, setDetected] = useState<any[] | null>(null)
  const [node, setNode] = useState(0)
  const [cmd, setCmd] = useState(0x009)
  const [vals, setVals] = useState('')
  const [rawId, setRawId] = useState('0x009')
  const [rawData, setRawData] = useState('')
  const scroller = useRef<HTMLDivElement>(null)
  const pausedRef = useRef(paused)
  pausedRef.current = paused
  useEffect(
    () =>
      onCan((f) => {
        if (!pausedRef.current) setFrames((old) => [...old, ...f].slice(-3000))
      }),
    [],
  )
  const virt = useVirtualizer({ count: frames.length, getScrollElement: () => scroller.current, estimateSize: () => 22, overscan: 12 })
  const nodePath = P(`can_node.${ax}`)
  const [nodeId, baud] = useLatest([nodePath, P('can_baud')], 2)
  const def = CMDS.find((c) => c[0] === cmd)
  const isRtr = def?.[1].includes('(rtr)')
  const send = () =>
    act('can_send', {
      node,
      cmd,
      rtr: isRtr,
      values: vals
        .split(/[ ,]+/)
        .filter(Boolean)
        .map(Number),
    }).catch(() => undefined)

  return (
    <div>
      <div className="view-head">
        <h1>can bus</h1>
        <span className="sub">python-can . ODrive CANSimple decode . motion frames need confirmation (they bypass usb safety)</span>
        {can?.open ? <Tag level="info">open {can.interface}:{can.channel} @ {can.bitrate}</Tag> : <Tag level="quiet">closed</Tag>}
      </div>
      <div className="grid2" style={{ gridTemplateColumns: '1fr 2fr' }}>
        <div className="col">
          <Panel title="adapter">
            <div className="field">
              <label>interface</label>
              <select value={iface} onChange={(e) => setIface(e.target.value)}>
                {['slcan', 'gs_usb', 'pcan', 'kvaser', 'vector', 'ixxat', 'canalystii', 'serial', 'virtual'].map((i) => (
                  <option key={i}>{i}</option>
                ))}
              </select>
              <span />
            </div>
            <div className="field">
              <label>channel</label>
              <input value={channel} onChange={(e) => setChannel(e.target.value)} />
              <span className="unit">COMx, PCAN_USBBUS1, 0</span>
            </div>
            <div className="field">
              <label>bitrate</label>
              <NumInput value={bitrate} onCommit={(v) => setBitrate(Math.trunc(v))} />
              <span className="unit">bit/s</span>
            </div>
            <div className="row">
              {can?.open ? (
                <Button onClick={() => act('can_close')}>close</Button>
              ) : (
                <Button kind="primary" onClick={() => act('can_open', { interface: iface, channel, bitrate }).catch(() => undefined)}>
                  open
                </Button>
              )}
              <Button onClick={() => act<any[]>('can_detect').then(setDetected).catch(() => undefined)}>detect adapters</Button>
            </div>
            {detected && <pre className="mono-pre muted">{detected.length ? detected.map((d) => JSON.stringify(d)).join('\n') : 'no adapters detected'}</pre>}
            {can?.last_error && <div className="warn-text">{can.last_error}</div>}
            <div className="kv num" style={{ marginTop: 6 }}>
              <span>rx / tx / err</span>
              <span>
                {can?.rx ?? 0} / {can?.tx ?? 0} / {can?.errors ?? 0}
              </span>
            </div>
          </Panel>
          <Panel title={`odrive can setup (usb) . axis${ax}`}>
            <div className="kv num">
              <span>node id</span>
              <span>{String(nodeId ?? '--')}</span>
              <span>baud</span>
              <span>{String(baud ?? '--')}</span>
            </div>
            <div className="row" style={{ marginTop: 6 }}>
              <span className="dim">node id</span>
              <NumInput value={nodeId as number} onCommit={(v) => act('write', { path: nodePath, value: Math.trunc(v) }).catch(() => undefined)} width={60} />
              {tree['can.set_baud_rate'] ? (
                <Button onClick={() => act('call', { path: 'can.set_baud_rate', args: [1000000] }).catch(() => undefined)}>set 1 Mbit (fw 0.5.1)</Button>
              ) : (
                <Button onClick={() => act('write', { path: 'can.config.baud_rate', value: 1000000 }).catch(() => undefined)}>set 1 Mbit</Button>
              )}
            </div>
            <span className="muted">fw 0.5.1 has a known bug where the baud setting may not persist; 0.5.6 fixes it.</span>
          </Panel>
          <Panel title="send">
            <div className="field">
              <label>node</label>
              <NumInput value={node} onCommit={(v) => setNode(Math.trunc(v))} />
              <span />
            </div>
            <div className="field">
              <label>command</label>
              <select value={cmd} onChange={(e) => setCmd(Number(e.target.value))}>
                {CMDS.map(([id, n]) => (
                  <option key={id} value={id}>
                    0x{id.toString(16).padStart(3, '0')} {n}
                  </option>
                ))}
              </select>
              <span />
            </div>
            {!!def?.[2].length && (
              <div className="field">
                <label>{def[2].join(', ')}</label>
                <input value={vals} onChange={(e) => setVals(e.target.value)} />
                <span />
              </div>
            )}
            <Button kind="primary" disabled={!can?.open} onClick={send}>
              send
            </Button>
            <div className="row" style={{ marginTop: 8 }}>
              <span className="dim">raw</span>
              <input value={rawId} onChange={(e) => setRawId(e.target.value)} style={{ width: 80 }} />
              <input value={rawData} placeholder="hex bytes" onChange={(e) => setRawData(e.target.value)} style={{ width: 180 }} />
              <Button disabled={!can?.open} onClick={() => act('can_send', { id: rawId, data: rawData }).catch(() => undefined)}>
                send raw
              </Button>
            </div>
          </Panel>
        </div>
        <Panel
          title={`frames . ${frames.length}`}
          tools={
            <>
              <Button small kind={paused ? 'on' : ''} onClick={() => setPaused(!paused)}>
                {paused ? 'resume' : 'pause'}
              </Button>
              <Button small onClick={() => setFrames([])}>
                clear
              </Button>
            </>
          }
          flush
        >
          <div ref={scroller} style={{ height: 'calc(100vh - 160px)', overflow: 'auto' }}>
            <div style={{ height: virt.getTotalSize(), position: 'relative' }}>
              {virt.getVirtualItems().map((vi) => {
                const f = frames[vi.index]
                return (
                  <div key={vi.key} className="num" style={{ position: 'absolute', left: 8, right: 8, transform: `translateY(${vi.start}px)`, height: 22, whiteSpace: 'nowrap', fontSize: 'var(--fs-tick)' }}>
                    <span className="muted">{time(f.ts)} </span>
                    <span className={f.dir === 'tx' ? 'dim' : ''}>{f.dir} </span>
                    <span>0x{f.id.toString(16).padStart(3, '0')} </span>
                    <span className="muted">{f.rtr ? 'RTR ' : ''}</span>
                    <span>{f.data.padEnd(16)} </span>
                    {f.name && (
                      <span className="dim">
                        node{f.node} {f.name} {f.fields ? f.fields.map((x) => (Number.isInteger(x) ? x : x.toFixed(4))).join(', ') : ''}
                      </span>
                    )}
                    {f.err && <span className="error-text"> error frame</span>}
                  </div>
                )
              })}
            </div>
          </div>
        </Panel>
      </div>
    </div>
  )
}
