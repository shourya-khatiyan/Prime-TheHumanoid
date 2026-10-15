import { Component, useEffect, type ErrorInfo, type ReactNode } from 'react'
import { StatusBar } from './components/StatusBar'
import { CommandPalette, ConfirmDialog, JobDock, MessageLine } from './components/Overlays'
import { Button } from './primitives'
import { act, useApp } from './lib/store'
import { VIEWS } from './views/registry'
import './components/shell.css'

/** catches view render or HMR state errors so the shell never unmounts to a black screen */
class ViewBoundary extends Component<{ view: string; children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidUpdate(prev: { view: string }) {
    if (prev.view !== this.props.view && this.state.error) {
      this.setState({ error: null })
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('View render error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="panel" style={{ padding: 16, height: 'auto' }}>
          <div className="error-text" style={{ marginBottom: 8 }}>
            ■ VIEW RENDER ERROR: {this.state.error.message}
          </div>
          <div className="row">
            <Button kind="primary" onClick={() => this.setState({ error: null })}>
              retry view
            </Button>
            <Button onClick={() => location.reload()}>reload page</Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

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
        <div className="note" title="Keep a physical DC bus emergency stop switch wired at all times">
          HW E-STOP REQUIRED
        </div>
      </nav>
      <main className="main">
        {link !== 'open' && (
          <div className="warn-text" style={{ marginBottom: 6 }}>
            backend {link}. start it with `python run.py` in odrive/backend.
          </div>
        )}
        {link === 'open' && !connected && (
          <div className="row warn-text" style={{ marginBottom: 6 }}>
            <span>no device: {lastError || 'searching...'}.</span>
            <Button small kind="primary" onClick={() => act('connect', { mode: 'mock' })}>
              use simulated device
            </Button>
          </div>
        )}
        <ViewBoundary view={view}>
          <View />
        </ViewBoundary>
      </main>
      <MessageLine />
      <JobDock />
      <ConfirmDialog />
      <CommandPalette />
    </div>
  )
}
