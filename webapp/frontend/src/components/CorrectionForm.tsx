// "Sugerir correccion": envia el feedback y muestra el triage en vivo hasta la
// tarjeta de veredicto.

import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Direccion, TriagePayload } from '../api/types'
import { useStored } from '../lib/storage'
import { DIRECCION } from '../lib/labels'
import { ChumbeLoader } from './Chumbe'
import { ErrorBlock } from './States'
import { ToolCallLine } from './Timeline'
import { VerdictCard } from './VerdictCard'

interface Step {
  key: number
  kind: 'status' | 'tool'
  text?: string
  name?: string
  args?: Record<string, unknown>
  id?: number
  summary?: string
}

export function CorrectionForm({
  translationId,
  direccion,
  sourceText,
  modelOutput,
}: {
  translationId: string
  direccion: Direccion
  sourceText: string
  modelOutput: string
}) {
  const [correction, setCorrection] = useState('')
  const [comment, setComment] = useState('')
  const [author, setAuthor] = useStored('inga.autor', '')
  const [phase, setPhase] = useState<'form' | 'running' | 'done' | 'error'>('form')
  const [steps, setSteps] = useState<Step[]>([])
  const [triage, setTriage] = useState<TriagePayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const ctrl = useRef<AbortController | null>(null)
  const seq = useRef(0)
  const targetInga = direccion === 'es2inga'

  useEffect(() => () => ctrl.current?.abort(), [])

  const submit = () => {
    if (!correction.trim() || phase === 'running') return
    setPhase('running')
    setSteps([])
    setTriage(null)
    setError(null)
    const c = new AbortController()
    ctrl.current = c
    let gotTriage = false
    let gotError: string | null = null
    void api.sendFeedback(
      {
        translation_id: translationId,
        direccion,
        source_text: sourceText,
        model_output: modelOutput,
        correction: correction.trim(),
        comment: comment.trim(),
        author: author.trim() || 'anónimo',
      },
      (ev) => {
        if (c.signal.aborted) return
        switch (ev.type) {
          case 'status':
            setSteps((s) => [...s, { key: ++seq.current, kind: 'status', text: ev.data.message }])
            break
          case 'tool_call':
            setSteps((s) => [...s, { key: ++seq.current, kind: 'tool', id: ev.data.id, name: ev.data.name, args: ev.data.args }])
            break
          case 'tool_result':
            setSteps((s) => s.map((x) => (x.kind === 'tool' && x.id === ev.data.id && !x.summary ? { ...x, summary: ev.data.summary } : x)))
            break
          case 'triage':
            gotTriage = true
            setTriage(ev.data)
            break
          case 'error':
            gotError = ev.data.message
            break
          case 'done':
            if (gotTriage) setPhase('done')
            else {
              setError(gotError ?? 'El servidor terminó sin enviar un veredicto.')
              setPhase('error')
            }
            break
        }
      },
      c.signal,
    )
  }

  if (phase === 'done' && triage) {
    return (
      <div>
        <VerdictCard
          status={triage.status}
          verdict={triage.verdict}
          rationale={triage.rationale}
          evidence={triage.evidence ?? []}
          facts={(triage.facts ?? []).map((f, i) => ({ key: f.fact_id ?? String(i), page_id: f.page_id, text: f.text, status: f.status }))}
          feedbackId={triage.feedback_id}
        />
        <button
          type="button"
          className="btn btn-quiet btn-sm mt-4"
          onClick={() => {
            setPhase('form')
            setCorrection('')
            setComment('')
          }}
        >
          Sugerir otra corrección
        </button>
      </div>
    )
  }

  if (phase === 'running') {
    return (
      <div aria-live="polite">
        <p className="text-sm text-ink-2">
          Tu corrección: <span className={`${targetInga ? 'inga text-lg' : ''} text-ink`}>{correction}</span>
        </p>
        <ol className="mt-4 space-y-2.5 border-l border-line-strong pl-4">
          {steps.map((s) => (
            <li key={s.key} className="relative text-[0.95rem]">
              <span aria-hidden="true" className={`absolute top-[7px] -left-[20.5px] size-2 rotate-45 ${s.kind === 'tool' ? 'bg-rio' : 'bg-forest'}`} />
              {s.kind === 'status' ? (
                <span>{s.text}</span>
              ) : (
                <>
                  <ToolCallLine name={s.name ?? ''} args={s.args ?? {}} />
                  {s.summary && <p className="mt-0.5 text-sm text-ink-2">{s.summary}</p>}
                </>
              )}
            </li>
          ))}
        </ol>
        <ChumbeLoader label="El agente está comprobando la corrección con sus fuentes" className="mt-4" />
      </div>
    )
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <p className="text-sm text-ink-2">
        Si la traducción está mal, escribe cómo debería ser. El agente la contrasta con el diccionario, la gramática y el corpus: si alguna fuente la respalda se aplica
        de inmediato; si no, pasa a revisión humana.
      </p>
      {phase === 'error' && error && <ErrorBlock title="No se pudo analizar la corrección" message={error} />}
      <div>
        <label htmlFor="fb-correction" className="label">
          Traducción correcta al {DIRECCION[direccion].to.toLowerCase()}
        </label>
        <textarea
          id="fb-correction"
          required
          rows={2}
          value={correction}
          onChange={(e) => setCorrection(e.target.value)}
          placeholder={modelOutput}
          className={`field resize-y ${targetInga ? 'inga text-xl' : ''}`}
        />
      </div>
      <div>
        <label htmlFor="fb-comment" className="label">
          Por qué (opcional, ayuda al agente a buscar)
        </label>
        <textarea id="fb-comment" rows={2} value={comment} onChange={(e) => setComment(e.target.value)} className="field resize-y" />
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-40 flex-1">
          <label htmlFor="fb-author" className="label">
            Tu nombre (opcional)
          </label>
          <input id="fb-author" value={author} onChange={(e) => setAuthor(e.target.value)} autoComplete="name" className="field" />
        </div>
        <button type="submit" disabled={!correction.trim()} className="btn btn-primary">
          Enviar corrección
        </button>
      </div>
    </form>
  )
}
