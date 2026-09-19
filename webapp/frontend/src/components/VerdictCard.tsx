import { Markdown } from './Markdown'
import { Link } from 'react-router-dom'
import { CircleCheckBig, Hourglass } from 'lucide-react'
import type { FactSource, FactStatus, Verdict } from '../api/types'
import { VERDICT } from '../lib/labels'
import { FactStatusBadge, PageChip, SourceList } from './Badges'

export interface VerdictFact {
  key: string
  page_id: string
  text: string
  status: FactStatus
}

/** Tarjeta de veredicto del triage: aplicada sola o en cola de revision. */
export function VerdictCard({
  status,
  verdict,
  rationale,
  evidence,
  facts,
  feedbackId,
  showQueueLink = true,
  headless = false,
}: {
  status: 'auto_applied' | 'pending_review'
  verdict?: Verdict
  rationale?: string
  evidence: FactSource[]
  facts: VerdictFact[]
  feedbackId?: number
  showQueueLink?: boolean
  /** Sin cabecera de estado: en el historial el estado ya va en la tarjeta. */
  headless?: boolean
}) {
  const applied = status === 'auto_applied'
  return (
    <div className={`overflow-hidden rounded-xl border ${headless ? 'border-line' : applied ? 'border-forest/50' : 'border-oro/60'}`}>
      {!headless && <div className={`flex items-start gap-3 px-4 py-3 ${applied ? 'bg-forest-soft' : 'bg-oro-soft'}`}>
        {applied ? <CircleCheckBig className="mt-0.5 size-5 shrink-0 text-forest" aria-hidden="true" /> : <Hourglass className="mt-0.5 size-5 shrink-0 text-oro" aria-hidden="true" />}
        <div className="min-w-0">
          <p className="font-display text-xl leading-tight font-bold">{applied ? 'Corrección aplicada a la wiki' : 'Corrección en la cola de revisión'}</p>
          <p className="mt-0.5 text-sm text-ink-2">
            {applied
              ? 'Una fuente escrita la corrobora y el código la volvió a verificar. Las próximas traducciones ya la usan.'
              : 'Ninguna fuente escrita la corrobora todavía. Queda como hecho pendiente hasta que una persona la revise.'}
          </p>
        </div>
      </div>}
      <div className="space-y-4 bg-surface px-4 py-4">
        {(verdict || rationale) && (
          <div>
            <p className="text-sm font-semibold text-ink-2">
              Veredicto del agente{verdict ? `: ${VERDICT[verdict] ?? verdict}` : ''}
              {feedbackId !== undefined && <span className="code ml-2 font-normal text-ink-3">feedback:{feedbackId}</span>}
            </p>
            {rationale && <Markdown text={rationale} className="mt-1 max-w-[68ch] text-[0.97rem] leading-relaxed" />}
          </div>
        )}
        <div>
          <p className="text-sm font-semibold text-ink-2">Evidencia</p>
          {evidence.length ? <SourceList sources={evidence} className="mt-2" /> : <p className="mt-1 text-sm text-ink-3">El agente no adjuntó evidencia.</p>}
        </div>
        <div>
          <p className="text-sm font-semibold text-ink-2">{headless ? 'Hechos' : applied ? 'Hechos escritos' : 'Hechos propuestos'}</p>
          {facts.length ? (
            <ul className="mt-2 space-y-2">
              {facts.map((f) => (
                <li key={f.key} className="rounded-lg border border-line bg-bg/50 p-3">
                  <p className="text-[0.95rem] leading-snug">{f.text}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <PageChip id={f.page_id} />
                    <FactStatusBadge status={f.status} />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-sm text-ink-3">No se escribió ningún hecho.</p>
          )}
        </div>
        {!applied && showQueueLink && (
          <Link to="/revision" className="link text-sm">
            Ver la cola de revisión
          </Link>
        )}
      </div>
    </div>
  )
}
