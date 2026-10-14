import { useEffect } from 'react'
import { StatusBar } from './components/StatusBar'
import { CommandPalette, ConfirmDialog, JobDock, MessageLine } from './components/Overlays'
import { act, useApp } from './lib/store'
import { VIEWS } from './views/registry'
import './components/shell.css'

function typing(e: KeyboardEvent): boolean {
  const el = e.target as HTMLElement
  return el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable
}

/** global keys: esc = disarm all (always), ':' or ctrl+k = palette, alt+key = switch view */
function useHotkeys() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const s = useApp.getState()
      if (e.key === 'Escape' && !s.confirm && !s.palette) {
        act('disarm', { reason: 'esc key' }).catch(() => undefined)
        return
      }
      if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === ':' && !typing(e))) {
        e.preventDefault()
        useApp.setState({ palette: true })
        return
      }
      // view switching needs alt so stray typing never changes the screen mid-test
      if (!e.altKey || e.ctrlKey || e.metaKey || s.confirm || s.palette) return
      const key = e.code.startsWith('Digit') ? e.code.slice(5) : e.code.startsWith('Key') ? e.code.slice(3).toLowerCase() : e.key
      const v = VIEWS.find((x) => x.key === key)
      if (v) {
        e.preventDefault()
        useApp.setState({ view: v.id })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
}

export function App() {
  useHotkeys()
  // re-render the whole tree once the device's alias table arrives (or changes after a reflash)
  useApp((s) => s.alias)
  const view = useApp((s) => s.view)
  const link = useApp((s) => s.link)
  const connected = useApp((s) => s.status?.device.connected)
  const lastError = useApp((s) => s.status?.device.last_error)
  const View = (VIEWS.find((v) => v.id === view) ?? VIEWS[0]).component
  return (
    <div className="app">
      <StatusBar />
      <nav className="nav">
        {VIEWS.map((v) => (
          <button key={v.id} className={v.id === view ? 'active' : ''} onClick={() => useApp.setState({ view: v.id })}>
            <span className="key">{v.key}</span>
            {v.label}
          </button>
        ))}
        <div className="sep" />
        <div className="note">
          the gui is a commissioning and test tool. it is not a safety device: keep a hardware e-stop on the dc bus.
        </div>
      </nav>
      <main className="main">
        {link !== 'open' && (
          <div className="warn-text" style={{ marginBottom: 6 }}>
            backend {link}. start it with `python run.py` in odrive/backend.
          </div>
        )}
        {link === 'open' && !connected && (
          <div className="warn-text" style={{ marginBottom: 6 }}>
            no device: {lastError || 'searching...'}. plug in the ODrive over usb, or use the palette (:) to switch to the simulated device.
          </div>
        )}
        <View />
      </main>
      <MessageLine />
      <JobDock />
      <ConfirmDialog />
      <CommandPalette />
    </div>
  )
}
