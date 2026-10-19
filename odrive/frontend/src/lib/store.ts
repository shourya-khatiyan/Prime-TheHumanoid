import { useEffect, useRef, useState } from 'react'
import { create } from 'zustand'
import type { Metadata } from './meta'
import { rpc, RpcError, type LinkState, type ServerMsg } from './rpc'
import { telemetry, type TelFrame } from './telemetry'

// ---------- server message shapes ----------

export type Alarm = { key: string; level: string; msg: string; flags: string[]; ts: number; acked: boolean; shelved_until: number }
export type Status = {
  device: {
    connected: boolean
    transport: string | null
    mode: string
    info: { serial: string; fw: string; hw: string; port?: string; simulated?: boolean } | null
    rate_target: number
    rate_achieved: number
    cols: number
    generation: number
    last_error: string
  }
  safety: { active_axes: number[]; watchdog_axes: number[]; alarms: Alarm[]; shelved: Alarm[]; first_out: string | null; origin?: Record<string, number> }
  jobs: string[]
  recording: boolean
  can: { open: boolean; interface?: string; channel?: string; bitrate?: number; rx: number; tx: number; errors: number; last_error: string }
  profile: string
  clients: number
}
export type TreeNode = { kind: 'prop' | 'func'; type?: string; writable?: boolean; args?: string[] }
export type Profile = Record<string, any> & {
  name: string
  axis: number
  derived: { kt_nm_per_a: number; torque_max_nm: number; joint_torque_peak_nm: number; joint_vel_max_deg_s: number }
}
export type JobInfo = {
  id: string
  kind: string
  title: string
  state: 'running' | 'done' | 'failed' | 'aborted'
  params: Record<string, unknown>
  started: number
  ended?: number
  result: any
  error: string | null
  progress: number
  logs: { ts: number; level: string; msg: string }[]
  prompt: { text: string; options: string[]; inputs: { key: string; label: string; unit: string }[] } | null
}
export type EventMsg = { ts: number; level: string; src: string; msg: string }

type ConfirmReq = { message: string; action: string; resolve: (ok: boolean) => void }

type AppState = {
  link: LinkState
  status: Status | null
  alias: Record<string, string>
  tree: Record<string, TreeNode>
  profile: Profile | null
  jobDefs: Record<string, { title: string; energizes: boolean; confirm: boolean }>
  meta: Metadata | null
  jobs: Record<string, JobInfo>
  events: EventMsg[]
  message: { text: string; level: string; ts: number } | null
  confirm: ConfirmReq | null
  axis: number
  view: string
  palette: boolean
}

export const useApp = create<AppState>(() => ({
  link: 'closed',
  status: null,
  alias: {},
  tree: {},
  profile: null,
  jobDefs: {},
  meta: null,
  jobs: {},
  events: [],
  message: null,
  confirm: null,
  axis: 0,
  view: 'dashboard',
  palette: false,
}))

// ---------- helpers ----------

/** show a line in the bottom message bar */
export function say(text: string, level = 'info'): void {
  useApp.setState({ message: { text, level, ts: Date.now() / 1000 } })
}

/** resolve an alias like 'fet_temp.0' to the device path ('' if unknown) */
export function P(alias: string): string {
  return useApp.getState().alias[alias] ?? ''
}

export class Cancelled extends Error {}

/** open the confirmation dialog and wait for the user's decision */
export function askConfirm(message: string, action: string): Promise<boolean> {
  return new Promise((resolve) => useApp.setState({ confirm: { message, action, resolve } }))
}

/**
 * run an rpc op; if the backend says it needs confirmation, ask the user,
 * get a one-shot token and retry. errors are shown in the message bar and rethrown.
 */
export async function act<T = any>(op: string, args: Record<string, unknown> = {}, quiet = false): Promise<T> {
  try {
    return await rpc.call<T>(op, args)
  } catch (e) {
    if (e instanceof RpcError && e.code === 'confirm' && e.action) {
      const ok = await askConfirm(e.message, e.action)
      if (!ok) {
        say('cancelled', 'warn')
        throw new Cancelled('cancelled')
      }
      const { token } = await rpc.call<{ token: string }>('arm', { action: e.action })
      try {
        return await rpc.call<T>(op, { ...args, token })
      } catch (e2) {
        if (!quiet) say(String((e2 as Error).message), 'error')
        throw e2
      }
    }
    if (!quiet) say(String((e as Error).message), 'error')
    throw e
  }
}

/** start a job (handles confirmation) and return its id */
export async function startJob(kind: string, params: Record<string, unknown> = {}): Promise<string> {
  const j = await act<JobInfo>('job_start', { kind, params })
  useApp.setState((s) => ({ jobs: { ...s.jobs, [j.id]: { ...(s.jobs[j.id] ?? {}), ...j, logs: [], progress: 0, prompt: null } as JobInfo } }))
  say(`started ${j.title}`)
  return j.id
}

/** wait for a job to finish (resolves with its final state) */
export function waitJob(id: string): Promise<JobInfo> {
  return new Promise((resolve) => {
    const check = () => {
      const j = useApp.getState().jobs[id]
      if (j && j.state !== 'running') {
        unsub()
        resolve(j)
      }
    }
    const unsub = useApp.subscribe(check)
    check()
  })
}

// results survive view switches (the views remount, this map does not)
const lastJobs = new Map<string, JobInfo>()

/**
 * run jobs from a view and keep the last finished one under `key`.
 * returns { job, busy, run, result } where result is set only for a successful job.
 */
export function useJobRunner(key: string) {
  const [job, setJob] = useState<JobInfo | null>(() => lastJobs.get(key) ?? null)
  const [busy, setBusy] = useState(false)
  const run = async (kind: string, params: Record<string, unknown>) => {
    setBusy(true)
    try {
      const done = await waitJob(await startJob(kind, params))
      lastJobs.set(key, done)
      setJob(done)
    } catch {
      // cancelled or refused; the message bar shows why
    } finally {
      setBusy(false)
    }
  }
  return { job, busy, run, result: job?.state === 'done' ? job.result : null }
}

// ---------- telemetry subscription manager ----------

const wanted = new Map<number, string[]>()
let subId = 0
let subTimer = 0
let subRate = 100

function pushSubscription() {
  clearTimeout(subTimer)
  subTimer = window.setTimeout(() => {
    const paths = [...new Set([...wanted.values()].flat().filter(Boolean))]
    rpc.call('subscribe', { paths, rate: subRate }).catch(() => undefined)
  }, 60)
}

/** ask the backend to stream these paths while the calling component is mounted */
export function useStream(paths: string[]): void {
  const key = paths.join('|')
  useEffect(() => {
    const id = ++subId
    wanted.set(id, paths)
    pushSubscription()
    return () => {
      wanted.delete(id)
      pushSubscription()
    }
  }, [key])
}

export function setStreamRate(hz: number): void {
  subRate = hz
  pushSubscription()
}

/** latest telemetry values for paths, re-rendering at most `hz` times per second */
export function useLatest(paths: string[], hz = 10): unknown[] {
  useStream(paths)
  const [, force] = useState(0)
  const seen = useRef(-1)
  useEffect(() => {
    const id = setInterval(() => {
      if (telemetry.version !== seen.current) {
        seen.current = telemetry.version
        force((x) => x + 1)
      }
    }, 1000 / hz)
    return () => clearInterval(id)
  }, [hz])
  return paths.map((p) => telemetry.get(p))
}

/** same as useLatest but by alias names */
export function useAliasLatest(aliases: string[], hz = 10): unknown[] {
  const alias = useApp((s) => s.alias)
  return useLatest(
    aliases.map((a) => alias[a] ?? ''),
    hz,
  )
}

// ---------- wiring ----------

let lastGeneration = -1

async function loadDevice() {
  try {
    const hello = await rpc.call<any>('hello')
    useApp.setState({ alias: hello.alias, tree: hello.tree, profile: hello.profile, jobDefs: hello.jobs, status: hello.status })
    if (hello.meta_fw && useApp.getState().meta?.fw !== hello.meta_fw) {
      const meta = await rpc.call<Metadata>('meta', { fw: hello.meta_fw })
      useApp.setState({ meta })
    }
    const jobs = await rpc.call<JobInfo[]>('jobs')
    useApp.setState({ jobs: Object.fromEntries(jobs.map((j) => [j.id, j])) })
    pushSubscription()
  } catch {
    // retried on the next status update
  }
}

function onMessage(m: ServerMsg) {
  switch (m.t) {
    case 'tel':
      telemetry.push(m as unknown as TelFrame)
      break
    case 'status': {
      const st = m as unknown as Status
      useApp.setState({ status: st })
      const gen = st.device.connected ? st.device.generation : -1
      if (gen !== lastGeneration) {
        lastGeneration = gen
        if (gen >= 0) loadDevice()
      }
      break
    }
    case 'event': {
      const ev = { ts: Date.now() / 1000, level: String(m.level), src: String(m.src), msg: String(m.msg) }
      useApp.setState((s) => ({ events: [...s.events.slice(-499), ev] }))
      if (ev.level === 'alarm' || ev.level === 'warn') say(ev.msg, ev.level === 'alarm' ? 'error' : 'warn')
      break
    }
    case 'job': {
      const j = m as unknown as JobInfo
      useApp.setState((s) => ({ jobs: { ...s.jobs, [j.id]: j } }))
      break
    }
    case 'can':
      canListeners.forEach((fn) => fn(m.frames as CanFrame[]))
      break
  }
}

export type CanFrame = {
  ts: number
  dir: 'rx' | 'tx'
  id: number
  ext: boolean
  rtr: boolean
  err: boolean
  data: string
  node?: number
  cmd?: number
  name?: string
  fields?: number[] | null
}
const canListeners = new Set<(f: CanFrame[]) => void>()
export function onCan(fn: (f: CanFrame[]) => void): () => void {
  canListeners.add(fn)
  return () => canListeners.delete(fn)
}

export function startClient(): void {
  rpc.onMessage(onMessage)
  rpc.onState((link) => {
    useApp.setState({ link })
    if (link === 'open') {
      lastGeneration = -1
      loadDevice()
    }
  })
  rpc.connect()
}
