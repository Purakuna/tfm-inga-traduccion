import { useCallback, useEffect, useReducer, useRef } from 'react'
import { api } from '../api/client'
import type {
  CorpusExample,
  NavigationPayload,
  PageRef,
  ResultPayload,
  SseEvent,
  Stage,
  ToolCallPayload,
  ToolResultPayload,
  TranslateBody,
} from '../api/types'

export type LogItem =
  | { kind: 'status'; key: string; t: number; stage: Stage; message: string }
  | { kind: 'navigation'; key: string; t: number; total: number; resolved: number; normalized: string }
  | { kind: 'pages'; key: string; t: number; count: number }
  | { kind: 'examples'; key: string; t: number; count: number }
  | { kind: 'tool'; key: string; t: number; call: ToolCallPayload; result: ToolResultPayload | null }
  | { kind: 'result'; key: string; t: number; elapsed: number }
  | { kind: 'error'; key: string; t: number; message: string }

export type Phase = 'idle' | 'running' | 'done' | 'error' | 'stopped'

export interface RunState {
  phase: Phase
  request: TranslateBody | null
  stage: Stage | null
  navigation: NavigationPayload | null
  pages: PageRef[]
  examples: CorpusExample[]
  log: LogItem[]
  result: ResultPayload | null
  error: string | null
  startedAt: number
  restored: boolean
}

export interface Snapshot {
  request: TranslateBody
  navigation: NavigationPayload | null
  pages: PageRef[]
  examples: CorpusExample[]
  result: ResultPayload
}

const IDLE: RunState = {
  phase: 'idle',
  request: null,
  stage: null,
  navigation: null,
  pages: [],
  examples: [],
  log: [],
  result: null,
  error: null,
  startedAt: 0,
  restored: false,
}

type Action =
  | { type: 'start'; request: TranslateBody; at: number }
  | { type: 'event'; event: SseEvent; at: number }
  | { type: 'stop' }
  | { type: 'reset' }
  | { type: 'restore'; snapshot: Snapshot }

let seq = 0
const key = () => `l${++seq}`

function reduce(state: RunState, action: Action): RunState {
  switch (action.type) {
    case 'start':
      return { ...IDLE, phase: 'running', request: action.request, startedAt: action.at }
    case 'reset':
      return IDLE
    case 'stop':
      return state.phase === 'running' ? { ...state, phase: 'stopped' } : state
    case 'restore': {
      const s = action.snapshot
      return { ...IDLE, phase: 'done', restored: true, request: s.request, navigation: s.navigation, pages: s.pages, examples: s.examples, result: s.result }
    }
    case 'event': {
      if (state.phase !== 'running') return state
      const t = (action.at - state.startedAt) / 1000
      const ev = action.event
      switch (ev.type) {
        case 'status':
          return { ...state, stage: ev.data.stage, log: [...state.log, { kind: 'status', key: key(), t, stage: ev.data.stage, message: ev.data.message }] }
        case 'navigation': {
          const tokens = ev.data.tokens ?? []
          return {
            ...state,
            navigation: { normalized: ev.data.normalized ?? '', tokens },
            log: [
              ...state.log,
              { kind: 'navigation', key: key(), t, total: tokens.length, resolved: tokens.filter((x) => x.resolved).length, normalized: ev.data.normalized ?? '' },
            ],
          }
        }
        case 'pages':
          return { ...state, pages: ev.data.pages ?? [], log: [...state.log, { kind: 'pages', key: key(), t, count: ev.data.pages?.length ?? 0 }] }
        case 'examples':
          return { ...state, examples: ev.data.examples ?? [], log: [...state.log, { kind: 'examples', key: key(), t, count: ev.data.examples?.length ?? 0 }] }
        case 'tool_call':
          return { ...state, stage: 'tool', log: [...state.log, { kind: 'tool', key: key(), t, call: ev.data, result: null }] }
        case 'tool_result': {
          // Se empareja por id; si el id no aparece, con la ultima llamada abierta del mismo nombre.
          let idx = state.log.findIndex((l) => l.kind === 'tool' && l.result === null && l.call.id === ev.data.id)
          if (idx === -1) idx = state.log.findIndex((l) => l.kind === 'tool' && l.result === null && l.call.name === ev.data.name)
          if (idx === -1) return state
          const log = state.log.slice()
          const item = log[idx]
          if (item.kind === 'tool') log[idx] = { ...item, result: ev.data }
          return { ...state, log }
        }
        case 'result':
          return {
            ...state,
            result: { ...ev.data, alternatives: ev.data.alternatives ?? [], used_pages: ev.data.used_pages ?? [] },
            log: [...state.log, { kind: 'result', key: key(), t, elapsed: ev.data.elapsed_s ?? t }],
          }
        case 'error':
          return { ...state, error: ev.data.message, log: [...state.log, { kind: 'error', key: key(), t, message: ev.data.message }] }
        case 'done': {
          if (state.result && !state.error) return { ...state, phase: 'done' }
          if (state.result) return { ...state, phase: 'done' }
          const message = state.error ?? 'El servidor terminó sin enviar una traducción.'
          return {
            ...state,
            phase: 'error',
            error: message,
            log: state.error ? state.log : [...state.log, { kind: 'error', key: key(), t, message }],
          }
        }
        default:
          return state
      }
    }
  }
}

export function useTranslate(onFinished?: (snapshot: Snapshot) => void) {
  const [state, dispatch] = useReducer(reduce, IDLE)
  const ctrl = useRef<AbortController | null>(null)
  const finished = useRef(onFinished)
  finished.current = onFinished

  const start = useCallback((request: TranslateBody) => {
    ctrl.current?.abort()
    const c = new AbortController()
    ctrl.current = c
    dispatch({ type: 'start', request, at: performance.now() })
    void api
      .translate(
        request,
        (event) => {
          if (c.signal.aborted) return
          dispatch({ type: 'event', event, at: performance.now() })
        },
        c.signal,
      )
      .then(() => {
        if (ctrl.current === c) ctrl.current = null
      })
  }, [])

  // Cuando un run termina bien se entrega la instantanea (para el historial).
  const reported = useRef<string | null>(null)
  useEffect(() => {
    if (state.phase === 'done' && !state.restored && state.result && state.request && reported.current !== state.result.translation_id) {
      reported.current = state.result.translation_id
      finished.current?.({ request: state.request, navigation: state.navigation, pages: state.pages, examples: state.examples, result: state.result })
    }
  }, [state])

  const stop = useCallback(() => {
    ctrl.current?.abort()
    ctrl.current = null
    dispatch({ type: 'stop' })
  }, [])

  const reset = useCallback(() => {
    ctrl.current?.abort()
    ctrl.current = null
    dispatch({ type: 'reset' })
  }, [])

  const restore = useCallback((snapshot: Snapshot) => {
    ctrl.current?.abort()
    ctrl.current = null
    dispatch({ type: 'restore', snapshot })
  }, [])

  useEffect(() => () => ctrl.current?.abort(), [])

  return { state, start, stop, reset, restore }
}
