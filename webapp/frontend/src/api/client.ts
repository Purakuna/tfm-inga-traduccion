// Cliente de la API (seccion 5). Con VITE_MOCK=1 todas las llamadas pasan por
// mockFetch, que responde con las mismas formas (incluido el stream SSE en
// bytes), de modo que el parser y la UI ejercitan el mismo camino que en real.

import { postStream, type FetchLike, type StreamEnd } from './sse'
import type {
  AskBody,
  ExampleSentence,
  FeedbackBody,
  FeedbackRow,
  FeedbackStatus,
  Health,
  PageKind,
  PageList,
  ReviewBody,
  SseEvent,
  TranslateBody,
  WikiPage,
  WikiStats,
} from './types'

export const IS_MOCK = import.meta.env.VITE_MOCK === '1'

let fetcherPromise: Promise<FetchLike> | null = null

function getFetcher(): Promise<FetchLike> {
  if (!fetcherPromise) {
    fetcherPromise = IS_MOCK
      ? import('./mock').then((m) => m.mockFetch)
      : Promise.resolve((input: string, init?: RequestInit) => fetch(input, init))
  }
  return fetcherPromise
}

export class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const fetcher = await getFetcher()
  let res: Response
  try {
    res = await fetcher(path, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    })
  } catch (err) {
    if (init?.signal?.aborted) throw err
    throw new ApiError('No se pudo conectar con el servidor. Comprueba que el backend está encendido en el puerto 8010.', 0)
  }
  if (!res.ok) {
    let detail = ''
    try {
      const j = (await res.json()) as { detail?: unknown }
      detail = typeof j.detail === 'string' ? j.detail : j.detail ? JSON.stringify(j.detail) : ''
    } catch {
      /* cuerpo no JSON */
    }
    if (res.status === 404) throw new ApiError(detail || 'No existe lo que se pidió.', 404)
    if (res.status >= 502 && res.status <= 504) {
      throw new ApiError('El servidor de traducción no responde. Comprueba que el backend está encendido en el puerto 8010.', res.status)
    }
    throw new ApiError(detail ? `El servidor respondió ${res.status}: ${detail}` : `El servidor respondió ${res.status}.`, res.status)
  }
  return (await res.json()) as T
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

type OnEvent = (event: SseEvent) => void

async function stream(path: string, body: unknown, onEvent: OnEvent, signal?: AbortSignal): Promise<StreamEnd> {
  const fetcher = await getFetcher()
  return postStream(path, body, onEvent, { signal, fetcher })
}

export const api = {
  health: (signal?: AbortSignal) => request<Health>('/api/health', { signal }),
  examples: (signal?: AbortSignal) => request<ExampleSentence[]>('/api/examples', { signal }),

  translate: (body: TranslateBody, onEvent: OnEvent, signal?: AbortSignal) => stream('/api/translate', body, onEvent, signal),
  ask: (body: AskBody, onEvent: OnEvent, signal?: AbortSignal) => stream('/api/ask', body, onEvent, signal),
  sendFeedback: (body: FeedbackBody, onEvent: OnEvent, signal?: AbortSignal) => stream('/api/feedback', body, onEvent, signal),

  listFeedback: (status?: FeedbackStatus, signal?: AbortSignal) =>
    request<FeedbackRow[]>(`/api/feedback${qs({ status })}`, { signal }),
  reviewFeedback: (id: number, body: ReviewBody) =>
    request<FeedbackRow>(`/api/feedback/${id}/review`, { method: 'POST', body: JSON.stringify(body) }),

  wikiStats: (signal?: AbortSignal) => request<WikiStats>('/api/wiki/stats', { signal }),
  wikiPages: (params: { kind?: PageKind | ''; q?: string; offset?: number; limit?: number }, signal?: AbortSignal) =>
    request<PageList>(`/api/wiki/pages${qs(params)}`, { signal }),
  // El id lleva ":" ("lemma:sinchi"); se codifica como un solo segmento de ruta.
  wikiPage: (pageId: string, signal?: AbortSignal) =>
    request<WikiPage>(`/api/wiki/pages/${encodeURIComponent(pageId)}`, { signal }),
}
