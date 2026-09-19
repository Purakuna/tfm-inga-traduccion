// Backend simulado dentro del navegador. Implementa la seccion 5 con las mismas
// formas y devuelve Responses reales: los streams salen como bytes SSE con
// \r\n y cortes de chunk arbitrarios, para que el parser trabaje igual que con
// sse-starlette.

import type {
  AskBody,
  FeedbackBody,
  FeedbackRow,
  PageRef,
  ReviewBody,
  SseEventType,
  TranslateBody,
  TriagePayload,
  WikiPage,
} from '../types'
import { EXAMPLES, FEEDBACK_SEED, PAGES, answerFor, newFactId, scenarioFor, type Scenario } from './data'

const SPEED = Number(import.meta.env.VITE_MOCK_SPEED ?? '1') || 1
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms / SPEED))

const pages: WikiPage[] = structuredClone(PAGES)
const feedback: FeedbackRow[] = structuredClone(FEEDBACK_SEED)
const translations = new Map<string, Scenario>()

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

type Emit = (type: SseEventType, data: unknown) => Promise<void>

/** Response SSE cuyo cuerpo se va escribiendo desde `run`. */
function sse(run: (emit: Emit) => Promise<void>, signal?: AbortSignal | null): Response {
  const encoder = new TextEncoder()
  let cancelled = false
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      const emit: Emit = async (type, data) => {
        if (cancelled || signal?.aborted) throw new DOMException('aborted', 'AbortError')
        const bytes = encoder.encode(`event: ${type}\r\ndata: ${JSON.stringify(data)}\r\n\r\n`)
        // Corte en un punto cualquiera (puede caer dentro de un caracter UTF-8).
        const cut = 1 + Math.floor(Math.random() * (bytes.length - 1))
        controller.enqueue(bytes.slice(0, cut))
        await sleep(4)
        if (cancelled) return
        controller.enqueue(bytes.slice(cut))
      }
      void run(emit)
        .catch(async (err: unknown) => {
          if (cancelled || signal?.aborted) return
          const message = err instanceof Error ? err.message : 'Fallo del mock.'
          await emit('error', { message }).catch(() => undefined)
        })
        .then(() => emit('done', {}).catch(() => undefined))
        .finally(() => {
          if (!cancelled) {
            try {
              controller.close()
            } catch {
              /* ya cerrado */
            }
          }
        })
    },
    cancel() {
      cancelled = true
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

function pageRef(id: string): PageRef | null {
  const p = pages.find((x) => x.id === id)
  return p ? { id: p.id, kind: p.kind, title: p.title, summary: p.summary } : null
}

function hex(n: number): string {
  let s = ''
  for (let i = 0; i < n; i++) s += Math.floor(Math.random() * 16).toString(16)
  return s
}

// ---------- /api/translate ----------

function translate(body: TranslateBody, signal?: AbortSignal | null): Response {
  return sse(async (emit) => {
    const started = performance.now()
    const text = (body.text ?? '').trim()
    if (!text) throw new Error('El texto está vacío.')
    if (/\berror\b/i.test(text) && text.length < 12) throw new Error('Error simulado: Gemini no respondió a tiempo (504).')
    const sc = scenarioFor(body.direccion, text)
    const agent = body.mode === 'agent'

    await emit('status', { stage: 'normalize', message: 'Normalizando la ortografía' })
    await sleep(450)
    await emit('status', { stage: 'navigate', message: 'Buscando cada palabra en la wiki' })
    await sleep(550)
    await emit('navigation', { normalized: sc.normalized, tokens: sc.tokens })
    await sleep(sc.tokens.length * 260 + 300)

    await emit('status', { stage: 'retrieve', message: 'Cargando páginas y ejemplos del corpus' })
    await sleep(400)
    const ids = [...sc.tokens.flatMap((t) => t.lemma_pages), ...sc.tokens.flatMap((t) => t.suffix_pages)]
    const refs = [...new Set(ids)].map(pageRef).filter((p): p is PageRef => p !== null)
    await emit('pages', { pages: refs })
    await sleep(500)
    await emit('examples', { examples: sc.examples })
    await sleep(450)

    await emit('status', {
      stage: 'think',
      message: agent ? 'El agente decide qué más necesita consultar' : 'Traduciendo con las páginas cargadas',
    })
    await sleep(agent ? 700 : 1100)

    if (agent) {
      let n = 0
      for (const t of sc.tools) {
        n += 1
        await emit('status', { stage: 'tool', message: `Consulta ${n} de ${sc.tools.length}` })
        await emit('tool_call', { id: n, ...t.call })
        await sleep(850)
        await emit('tool_result', { id: n, name: t.call.name, ...t.result })
        await sleep(450)
      }
    }

    await emit('status', { stage: 'write', message: 'Redactando la traducción' })
    await sleep(800)
    const translation_id = hex(32)
    translations.set(translation_id, sc)
    await emit('result', {
      translation_id,
      translation: sc.translation,
      alternatives: sc.alternatives,
      confidence: sc.confidence,
      notes: sc.notes,
      used_pages: refs.map((r) => r.id),
      mode: body.mode,
      elapsed_s: Math.round((performance.now() - started) / 10) / 100,
    })
  }, signal)
}

// ---------- /api/ask ----------

function ask(body: AskBody, signal?: AbortSignal | null): Response {
  return sse(async (emit) => {
    const sc = translations.get(body.translation_id) ?? null
    const ans = answerFor(body.question ?? '', sc)
    await emit('status', { stage: 'think', message: 'Revisando la traza de la traducción' })
    await sleep(600)
    if (ans.tool) {
      await emit('tool_call', { id: 1, name: 'wiki_leer', args: { page_id: ans.tool } })
      await sleep(700)
      await emit('tool_result', { id: 1, name: 'wiki_leer', summary: `Página ${ans.tool} releída.`, chars: 1100 })
      await sleep(300)
    }
    await emit('status', { stage: 'write', message: 'Respondiendo' })
    const parts = ans.text.match(/\S+\s*/g) ?? [ans.text]
    for (let i = 0; i < parts.length; i += 3) {
      await emit('answer_delta', { text: parts.slice(i, i + 3).join('') })
      await sleep(55)
    }
    await emit('answer', { text: ans.text, cited_pages: ans.cited })
  }, signal)
}

// ---------- /api/feedback ----------

function submitFeedback(body: FeedbackBody, signal?: AbortSignal | null): Response {
  return sse(async (emit) => {
    if (!body.correction?.trim()) throw new Error('La corrección está vacía.')
    const id = Math.max(0, ...feedback.map((f) => f.id)) + 1
    const row: FeedbackRow = {
      id,
      created_at: new Date().toISOString().slice(0, 19),
      author: body.author || 'anónimo',
      direccion: body.direccion,
      source_text: body.source_text,
      model_output: body.model_output,
      correction: body.correction,
      comment: body.comment ?? '',
      translation_id: body.translation_id ?? null,
      status: 'new',
      triage_json: null,
      reviewer: null,
      reviewed_at: null,
      review_note: null,
      facts: [],
    }
    feedback.unshift(row)

    // Regla del mock: si la correccion usa "todo/todos/entero" el diccionario
    // simulado la respalda (lema:tukui adj) y se aplica sola; si no, va a revision.
    const supported = /\b(todo|todos|entero|del todo)\b/i.test(body.correction)
    const quoteFb = (body.comment || body.correction).slice(0, 280)

    await emit('status', { stage: 'think', message: 'El agente investiga la corrección' })
    await sleep(700)
    await emit('tool_call', { id: 1, name: 'wiki_leer', args: { page_id: 'lemma:tukui' } })
    await sleep(800)
    await emit('tool_result', { id: 1, name: 'wiki_leer', summary: 'tukui: adj "todo, todos"; v "terminar; volverse".', chars: 1184 })
    await sleep(350)
    await emit('tool_call', { id: 2, name: 'documento_buscar', args: { consulta: 'tukui', documento: 'diccionario' } })
    await sleep(900)
    await emit('tool_result', {
      id: 2,
      name: 'documento_buscar',
      summary: supported ? '2 entradas: "tukui (adj): todo, todos" y "tukui (v)".' : '2 entradas; ninguna cubre lo que propone la corrección.',
      chars: 640,
    })
    await sleep(350)
    await emit('tool_call', { id: 3, name: 'corpus_buscar', args: { texto: body.source_text.slice(0, 60), direccion: body.direccion, k: 3 } })
    await sleep(850)
    await emit('tool_result', { id: 3, name: 'corpus_buscar', summary: '3 ejemplos de entrenamiento; ninguno decide el caso.', chars: 702 })
    await sleep(400)
    await emit('status', { stage: 'write', message: supported ? 'Verificando la evidencia y aplicando' : 'Dejando la propuesta en la cola de revisión' })
    await sleep(800)

    const factId = newFactId()
    const factText = supported
      ? `En "${body.source_text.slice(0, 80)}", "tuku" admite la lectura "todo" (tukui adj): ${body.correction.slice(0, 160)}`
      : `Propuesta de un hablante para "${body.source_text.slice(0, 80)}": ${body.correction.slice(0, 200)}`
    const pageId = 'lemma:tukui'
    const triage: TriagePayload = {
      feedback_id: id,
      verdict: supported ? 'supported' : 'needs_review',
      status: supported ? 'auto_applied' : 'pending_review',
      rationale: supported
        ? 'El diccionario registra "tukui (adj): todo, todos", que respalda la lectura propuesta. La evidencia se volvió a comprobar por código (el lema existe en el léxico), así que el hecho se escribió como activo.'
        : 'La corrección es plausible, pero no encontré una fuente escrita (diccionario, gramática o corpus de entrenamiento) que la respalde. Sin corroboración no se aplica sola: el hecho queda pendiente hasta que una persona lo revise.',
      evidence: supported
        ? [
            { type: 'dictionary', ref: 'lema:tukui', quote: 'tukui (adj): todo, todos' },
            { type: 'feedback', ref: `feedback:${id}`, quote: quoteFb },
          ]
        : [{ type: 'feedback', ref: `feedback:${id}`, quote: quoteFb }],
      facts: [{ fact_id: factId, page_id: pageId, text: factText, status: supported ? 'active' : 'pending' }],
    }

    const target = pages.find((p) => p.id === pageId)
    if (target) {
      target.facts.push({
        id: factId,
        section: 'usage',
        text: factText,
        status: supported ? 'active' : 'pending',
        created_by: 'feedback',
        created_at: row.created_at,
        sources: triage.evidence,
      })
      target.version += 1
      target.updated_at = row.created_at
    }
    row.status = triage.status
    row.triage_json = { verdict: triage.verdict, rationale: triage.rationale, evidence: triage.evidence, actions: [{ op: 'add_fact', page_id: pageId }] }
    row.facts = [{ id: factId, page_id: pageId, section: 'usage', text: factText, status: supported ? 'active' : 'pending' }]

    await emit('triage', triage)
  }, signal)
}

function review(id: number, body: ReviewBody): Response {
  const row = feedback.find((f) => f.id === id)
  if (!row) return json({ detail: `No existe el feedback ${id}.` }, 404)
  if (row.status !== 'pending_review') return json({ detail: 'Este feedback ya fue revisado.' }, 409)
  const approve = body.decision === 'approve'
  row.status = approve ? 'approved' : 'rejected'
  row.reviewer = body.reviewer
  row.reviewed_at = new Date().toISOString().slice(0, 19)
  row.review_note = body.note
  for (const f of row.facts ?? []) {
    f.status = approve ? 'active' : 'rejected'
    for (const p of pages) {
      const pf = p.facts.find((x) => x.id === (f.id ?? f.fact_id))
      if (pf) pf.status = f.status
    }
  }
  return json(row)
}

// ---------- wiki ----------

const fold = (s: string) =>
  s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')

function listPages(params: URLSearchParams): Response {
  const kind = params.get('kind') ?? ''
  const q = fold(params.get('q') ?? '').trim().replace(/^-/, '')
  const offset = Number(params.get('offset') ?? 0) || 0
  const limit = Number(params.get('limit') ?? 50) || 50
  let found = pages.filter((p) => !kind || p.kind === kind)
  if (q) {
    const rank = (p: WikiPage) => {
      if (fold(p.slug).startsWith(q) || p.aliases.some((a) => fold(a).replace(/^-/, '').startsWith(q))) return 0
      if (fold(p.title).includes(q) || fold(p.summary).includes(q)) return 1
      if (p.facts.some((f) => fold(f.text).includes(q))) return 2
      return -1
    }
    found = found
      .map((p) => ({ p, r: rank(p) }))
      .filter((x) => x.r >= 0)
      .sort((a, b) => a.r - b.r)
      .map((x) => x.p)
  }
  const items = found.slice(offset, offset + limit).map((p) => ({
    id: p.id,
    kind: p.kind,
    title: p.title,
    summary: p.summary,
    n_facts: p.facts.filter((f) => f.status === 'active' || f.status === 'pending').length,
  }))
  return json({ items, total: found.length })
}

function stats() {
  const count = <T extends string>(xs: T[]) =>
    xs.reduce<Record<string, number>>((acc, x) => ((acc[x] = (acc[x] ?? 0) + 1), acc), {})
  return {
    pages: count(pages.map((p) => p.kind)),
    facts: count(pages.flatMap((p) => p.facts.map((f) => f.status))),
    feedback: count(feedback.map((f) => f.status)),
  }
}

// ---------- enrutador ----------

export async function mockFetch(input: string, init?: RequestInit): Promise<Response> {
  const url = new URL(input, 'http://mock.local')
  const path = url.pathname
  const method = (init?.method ?? 'GET').toUpperCase()
  const body = typeof init?.body === 'string' ? (JSON.parse(init.body) as unknown) : undefined
  const signal = init?.signal

  if (method === 'POST' && path === '/api/translate') return translate(body as TranslateBody, signal)
  if (method === 'POST' && path === '/api/ask') return ask(body as AskBody, signal)
  if (method === 'POST' && path === '/api/feedback') return submitFeedback(body as FeedbackBody, signal)

  await sleep(260 + Math.random() * 240)
  if (signal?.aborted) throw new DOMException('aborted', 'AbortError')

  if (path === '/api/health') return json({ ok: true, model: 'mock (sin backend)', wiki: stats() })
  if (path === '/api/examples') return json(EXAMPLES)
  if (path === '/api/wiki/stats') return json(stats())
  if (path === '/api/wiki/pages') return listPages(url.searchParams)
  if (path.startsWith('/api/wiki/pages/')) {
    const id = decodeURIComponent(path.slice('/api/wiki/pages/'.length))
    const p = pages.find((x) => x.id === id)
    return p ? json(p) : json({ detail: `No existe la página ${id}.` }, 404)
  }
  if (method === 'GET' && path === '/api/feedback') {
    const status = url.searchParams.get('status')
    return json(feedback.filter((f) => !status || f.status === status))
  }
  const m = /^\/api\/feedback\/(\d+)\/review$/.exec(path)
  if (method === 'POST' && m) return review(Number(m[1]), body as ReviewBody)

  return json({ detail: 'Ruta no implementada en el mock.' }, 404)
}
