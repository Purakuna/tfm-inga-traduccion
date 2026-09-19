// Lector de Server-Sent Events sobre POST (fetch + ReadableStream).
//
// - Tolera cortes de chunk en cualquier punto (a mitad de linea, entre \r y \n,
//   a mitad de un caracter UTF-8).
// - Acepta finales de linea \n, \r\n y \r (sse-starlette emite \r\n).
// - Ignora comentarios (": ping") y campos que no usa (id, retry).
// - Siempre termina: con `done`, con el cierre del stream, con abort o con un
//   fallo de red. Los fallos se entregan como evento `error` antes de resolver.

import type { SseEvent, SseEventType } from './types'

const KNOWN: ReadonlySet<string> = new Set<SseEventType>([
  'status',
  'navigation',
  'pages',
  'examples',
  'tool_call',
  'tool_result',
  'result',
  'answer_delta',
  'answer',
  'triage',
  'error',
  'done',
])

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>

export interface StreamOptions {
  signal?: AbortSignal
  fetcher?: FetchLike
}

export type StreamEnd = 'done' | 'closed' | 'aborted' | 'failed'

/** Parser incremental: se le da texto y llama a onMessage por cada mensaje completo. */
export class SseParser {
  private buffer = ''
  private eventName = ''
  private dataLines: string[] = []
  private readonly onMessage: (event: string, data: string) => void

  constructor(onMessage: (event: string, data: string) => void) {
    this.onMessage = onMessage
  }

  push(chunk: string): void {
    this.buffer += chunk
    let start = 0
    for (;;) {
      const nl = this.nextBreak(start)
      if (nl === null) break
      this.line(this.buffer.slice(start, nl.at))
      start = nl.at + nl.len
    }
    this.buffer = this.buffer.slice(start)
  }

  /** Cierre del stream: procesa lo que quedo sin salto final. */
  end(): void {
    if (this.buffer.length > 0) {
      this.line(this.buffer.replace(/\r$/, ''))
      this.buffer = ''
    }
    this.dispatch()
  }

  private nextBreak(from: number): { at: number; len: number } | null {
    for (let i = from; i < this.buffer.length; i++) {
      const c = this.buffer.charCodeAt(i)
      if (c === 10) return { at: i, len: 1 }
      if (c === 13) {
        // Un \r al final del buffer puede ser la mitad de un \r\n: se espera.
        if (i + 1 >= this.buffer.length) return null
        return { at: i, len: this.buffer.charCodeAt(i + 1) === 10 ? 2 : 1 }
      }
    }
    return null
  }

  private line(line: string): void {
    if (line === '') {
      this.dispatch()
      return
    }
    if (line.startsWith(':')) return
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    let value = colon === -1 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'event') this.eventName = value
    else if (field === 'data') this.dataLines.push(value)
  }

  private dispatch(): void {
    if (this.eventName === '' && this.dataLines.length === 0) return
    const name = this.eventName || 'message'
    const data = this.dataLines.join('\n')
    this.eventName = ''
    this.dataLines = []
    this.onMessage(name, data)
  }
}

function toEvent(name: string, raw: string): SseEvent | null {
  if (!KNOWN.has(name)) return null
  let data: unknown = {}
  if (raw.trim() !== '') {
    try {
      data = JSON.parse(raw)
    } catch {
      if (name === 'error') data = { message: raw }
      else return { type: 'error', data: { message: `Evento "${name}" con datos ilegibles.` } }
    }
  }
  if (name === 'error') {
    const d = data as { message?: unknown; detail?: unknown }
    const message =
      typeof d?.message === 'string' ? d.message : typeof d?.detail === 'string' ? d.detail : 'Error desconocido del servidor.'
    return { type: 'error', data: { message } }
  }
  return { type: name, data } as SseEvent
}

async function errorFromResponse(res: Response): Promise<string> {
  let detail = ''
  try {
    const text = await res.text()
    try {
      const j = JSON.parse(text) as { detail?: unknown; message?: unknown }
      if (typeof j.detail === 'string') detail = j.detail
      else if (typeof j.message === 'string') detail = j.message
      else if (j.detail) detail = JSON.stringify(j.detail)
    } catch {
      detail = text.slice(0, 200)
    }
  } catch {
    /* sin cuerpo */
  }
  if (res.status === 502 || res.status === 503 || res.status === 504) {
    return 'No hay respuesta del servidor de traducción. Comprueba que el backend está encendido en el puerto 8010.'
  }
  return detail ? `El servidor respondió ${res.status}: ${detail}` : `El servidor respondió ${res.status}.`
}

/**
 * POST + lectura del stream. Llama a onEvent por cada evento (incluido `done`).
 * La promesa nunca rechaza: devuelve como termino el stream.
 */
export async function postStream(
  url: string,
  body: unknown,
  onEvent: (event: SseEvent) => void,
  options: StreamOptions = {},
): Promise<StreamEnd> {
  const { signal, fetcher = fetch } = options
  let sawDone = false
  let sawError = false

  const emit = (ev: SseEvent) => {
    if (sawDone) return
    if (ev.type === 'done') sawDone = true
    if (ev.type === 'error') sawError = true
    onEvent(ev)
  }
  const finish = (end: StreamEnd): StreamEnd => {
    // `done` siempre es lo ultimo que ve quien consume, pase lo que pase.
    if (!sawDone && end !== 'aborted') emit({ type: 'done', data: {} })
    return end
  }

  let res: Response
  try {
    res = await fetcher(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(body),
      signal,
    })
  } catch (err) {
    if (signal?.aborted) return finish('aborted')
    emit({
      type: 'error',
      data: {
        message:
          'No se pudo conectar con el servidor. Comprueba que el backend está encendido (puerto 8010) o usa el modo demostración.',
      },
    })
    void err
    return finish('failed')
  }

  if (!res.ok) {
    emit({ type: 'error', data: { message: await errorFromResponse(res) } })
    return finish('failed')
  }
  if (!res.body) {
    emit({ type: 'error', data: { message: 'El servidor no envió un stream de eventos.' } })
    return finish('failed')
  }

  const parser = new SseParser((name, raw) => {
    const ev = toEvent(name, raw)
    if (ev) emit(ev)
  })
  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')

  try {
    while (!sawDone) {
      const { value, done } = await reader.read()
      if (done) break
      parser.push(decoder.decode(value, { stream: true }))
    }
    if (!sawDone) {
      parser.push(decoder.decode())
      parser.end()
    }
  } catch {
    if (signal?.aborted) return finish('aborted')
    if (!sawError) emit({ type: 'error', data: { message: 'La conexión se cortó antes de terminar.' } })
    return finish('failed')
  } finally {
    reader.cancel().catch(() => undefined)
  }

  return finish(sawDone ? 'done' : 'closed')
}
