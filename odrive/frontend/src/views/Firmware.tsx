import { useEffect, useState } from 'react'
import { Button, Panel, Tag } from '../primitives'
import { act, startJob, useApp, useLatest } from '../lib/store'
import { date } from '../lib/format'

/** device identity, config backup and the guarded update to official 0.5.6 */
export function Firmware() {
  const status = useApp((s) => s.status)
  const info = status?.device.info
  const [backups, setBackups] = useState<any[]>([])
  const [unreleased, userCfg] = useLatest(['fw_version_unreleased', 'user_config_loaded'], 1)
  const refresh = () => act<any[]>('backup_list', {}, true).then(setBackups).catch(() => undefined)
  useEffect(() => {
    refresh()
  }, [])
  const mine = backups.filter((b) => b.device?.serial === info?.serial)
  const latest = info?.fw === '0.5.6'
  return (
    <div>
      <div className="view-head">
        <h1>firmware</h1>
        <span className="sub">0.5.6 is the last release for v3.x hardware</span>
      </div>
      <div className="grid2">
        <Panel title="device">
          <div className="kv num">
            <span>serial</span>
            <span>{info?.serial ?? '--'}</span>
            <span>firmware</span>
            <span>
              {info?.fw ?? '--'} {latest ? '' : <Tag level="warn">update available: 0.5.6</Tag>}
            </span>
            <span>official release</span>
            <span>{unreleased === undefined ? '--' : unreleased ? 'no (custom/dev build)' : 'yes'}</span>
            <span>hardware</span>
            <span>{info?.hw ?? '--'}</span>
            <span>user config loaded</span>
            <span>{String(userCfg ?? '--')}</span>
            <span>transport</span>
            <span>
              {status?.device.transport ?? '--'} {info?.port ?? ''}
            </span>
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <Button
              kind="primary"
              onClick={async () => {
                await act('backup_save', { name: `pre-flash-${info?.fw}` })
                refresh()
              }}
            >
              backup config now
            </Button>
            <Button onClick={() => act('connect', { mode: 'auto' })}>reconnect</Button>
          </div>
          <div className="muted" style={{ marginTop: 6 }}>
            {mine.length ? `latest backup of this board: ${mine[0].id} (${date(mine[0].created)})` : 'no backup of this board yet'}
          </div>
        </Panel>
        <Panel title="update to 0.5.6 (v3.6-56V)" alarm={false}>
          <div className="col">
            <span>why: fixes the CAN baud setting (0.5.2), adds cyclic CAN telemetry (0.5.6), ascii protocol fixes.</span>
            <span className="warn-text">risk: this is a Flipsky clone. ODrive staff report Flipsky changed hardware without publishing firmware, so official firmware is not guaranteed to work.</span>
            <ol className="dim" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
              <li>dump the whole flash and the OTP area (0x1FFF7800) with an ST-Link + STM32CubeProgrammer. this is the only way back.</li>
              <li>back up the config here (button on the left).</li>
              <li>install WinUSB (Zadig) for "STM32 BOOTLOADER" (0483:DF11), otherwise DFU stalls on windows.</li>
              <li>the job downloads the official .elf, converts it to .hex, releases usb, runs odrivetool dfu, reconnects.</li>
              <li>it then asks for a multimeter bus-voltage reading: a mismatch means the wrong board variant.</li>
              <li>restore settings from the backup (paths changed in 0.5.2+, the restore skips missing ones).</li>
            </ol>
            <div className="row">
              <Button kind="danger" disabled={!info || !mine.length || latest} onClick={() => startJob('firmware_flash', {}).catch(() => undefined)}>
                flash official 0.5.6
              </Button>
              {!mine.length && <span className="muted">needs a backup of this board first</span>}
            </div>
          </div>
        </Panel>
      </div>
    </div>
  )
}
