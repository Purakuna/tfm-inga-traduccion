// "Pregunta por que": chat atado a una traduccion. La respuesta llega por
// answer_delta y se cierra con answer (texto completo + paginas citadas).

import { useEffect, useRef, useState } from 'react'
import { SendHorizontal, Square } from 'lucide-react'
import { api } from '../api/client'
import type { ChatTurn, ResolvedToken } from '../api/types'
import { PageChip } from './Badges'
import { ChumbeLoader } from './Chumbe'
import { Markdown } from './Markdown'
import { ToolCallLine } from './Timeline'

interface Message {
  role: 'user' | 'assistant'
  content: string
  cited: string[]
  streaming: boolean
  activity: { name: string; args: Record<string, unknown>; done: boolean }[]
  error: string | null
}

function suggestions(tokens: ResolvedToken[], notes: string): string[] {
  const out: string[] = []
  // Si las notas del agente nombran una palabra entre comillas, esa es la duda interesante.
  const multi = tokens.find((t) => notes.toLowerCase().includes(`"${t.token.toLowerCase()}"`)) ?? tokens.find((t) => t.resolved)
  if (multi) out.push(`¿Por qué tradujiste "${multi.token}" así?`)
  const suf = tokens.find((t) => t.suffix_pages.length > 0)
  if (suf) out.push(`¿Qué hace el sufijo de "${suf.token}"?`)
  out.push('¿De qué no estás seguro?')
  return out
}

export function AskChat({ translationId, tokens, notes = '' }: { translationId: string; tokens: ResolvedToken[]; notes?: string }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const ctrl = useRef<AbortController | null>(null)
  const scroller = useRef<HTMLDivElement>(null)

  useEffect(() => () => ctrl.current?.abort(), [])
  useEffect(() => {
    const el = scroller.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  const patchLast = (fn: (m: Message) => Message) =>
    setMessages((ms) => (ms.length ? [...ms.slice(0, -1), fn(ms[ms.length - 1])] : ms))

  const send = (question: string) => {
    const q = question.trim()
    if (!q || busy) return
    const history: ChatTurn[] = messages.filter((m) => m.content && !m.error).map((m) => ({ role: m.role, content: m.content }))
    setMessages((ms) => [
      ...ms,
      { role: 'user', content: q, cited: [], streaming: false, activity: [], error: null },
      { role: 'assistant', content: '', cited: [], streaming: true, activity: [], error: null },
    ])
    setDraft('')
    setBusy(true)
    const c = new AbortController()
    ctrl.current = c
    void api
      .ask(
        { translation_id: translationId, question: q, history },
        (ev) => {
          if (c.signal.aborted) return
          switch (ev.type) {
            case 'answer_delta':
              patchLast((m) => ({ ...m, content: m.content + (ev.data.text ?? '') }))
              break
            case 'answer':
              patchLast((m) => ({ ...m, content: ev.data.text || m.content, cited: ev.data.cited_pages ?? [] }))
              break
            case 'tool_call':
              patchLast((m) => ({ ...m, activity: [...m.activity, { name: ev.data.name, args: ev.data.args, done: false }] }))
              break
            case 'tool_result':
              patchLast((m) => ({ ...m, activity: m.activity.map((a, i) => (i === m.activity.length - 1 ? { ...a, done: true } : a)) }))
              break
            case 'error':
              patchLast((m) => ({ ...m, error: ev.data.message }))
              break
            case 'done':
              patchLast((m) => ({
                ...m,
                streaming: false,
                error: m.error ?? (m.content ? null : 'El servidor terminó sin responder.'),
              }))
              break
          }
        },
        c.signal,
      )
      .finally(() => {
        if (ctrl.current === c) {
          ctrl.current = null
          setBusy(false)
        }
      })
  }

  const stop = () => {
    ctrl.current?.abort()
    ctrl.current = null
    setBusy(false)
    patchLast((m) => ({ ...m, streaming: false }))
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scroller} className="max-h-[26rem] min-h-32 flex-1 space-y-4 overflow-y-auto pr-1" aria-live="polite">
        {messages.length === 0 && (
          <div>
            <p className="text-sm text-ink-2">
              El agente responde a partir de la traza de esta traducción: las páginas que leyó, los ejemplos y sus consultas. Cita sus fuentes y dice lo que no sabe.
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {suggestions(tokens, notes).map((s) => (
                <li key={s}>
                  <button type="button" onClick={() => send(s)} className="rounded-lg border border-line-strong px-3 py-2 text-left text-sm transition-colors hover:bg-surface-2">
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === 'user' ? (
            <p key={i} className="ml-auto w-fit max-w-[88%] rounded-xl rounded-br-sm bg-primary px-3.5 py-2 text-[0.95rem] text-on-primary">
              {m.content}
            </p>
          ) : (
            <div key={i} className="max-w-[94%]">
              {m.activity.length > 0 && (
                <ul className="mb-2 space-y-1">
                  {m.activity.map((a, j) => (
                    <li key={j} className={`flex items-start gap-2 text-sm ${a.done ? 'opacity-70' : ''}`}>
                      <span className="mt-1.5 size-1.5 shrink-0 rotate-45 bg-rio" aria-hidden="true" />
                      <ToolCallLine name={a.name} args={a.args} />
                    </li>
                  ))}
                </ul>
              )}
              {m.content ? (
                <Markdown
                  text={m.content}
                  className="text-[0.98rem] leading-relaxed"
                  tail={m.streaming ? <span aria-hidden="true" className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[3px] bg-oro-fill" style={{ animation: 'caret 1s steps(1) infinite' }} /> : null}
                />
              ) : m.streaming ? (
                <ChumbeLoader label="Revisando la traza" />
              ) : null}
              {m.error && <p role="alert" className="mt-2 rounded-lg border border-carmin/40 bg-carmin-soft px-3 py-2 text-sm">{m.error}</p>}
              {m.cited.length > 0 && (
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  <span className="text-xs text-ink-3">Páginas citadas</span>
                  {m.cited.map((id) => (
                    <PageChip key={id} id={id} />
                  ))}
                </div>
              )}
            </div>
          ),
        )}
      </div>

      <form
        className="mt-4 flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          send(draft)
        }}
      >
        <label htmlFor="ask-input" className="sr-only">
          Tu pregunta sobre esta traducción
        </label>
        <textarea
          id="ask-input"
          rows={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(draft)
            }
          }}
          placeholder="Pregunta por una palabra o una decisión"
          className="field max-h-32 min-h-11 resize-none"
        />
        {busy ? (
          <button type="button" onClick={stop} className="btn btn-quiet btn-icon shrink-0" aria-label="Detener la respuesta">
            <Square className="size-4" aria-hidden="true" />
          </button>
        ) : (
          <button type="submit" disabled={!draft.trim()} className="btn btn-primary btn-icon shrink-0" aria-label="Enviar pregunta">
            <SendHorizontal className="size-4" aria-hidden="true" />
          </button>
        )}
      </form>
    </div>
  )
}
