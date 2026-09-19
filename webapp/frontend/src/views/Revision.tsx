import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Check, X } from 'lucide-react'
import { api } from '../api/client'
import type { FeedbackRow, FeedbackStatus } from '../api/types'
import { VerdictCard } from '../components/VerdictCard'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/States'
import { factKey, triageOf } from '../lib/feedback'
import { DIRECCION, FEEDBACK_STATUS, formatDate } from '../lib/labels'
import { useStored } from '../lib/storage'

type Tab = 'pending' | 'history'

const STATUS_TONE: Record<FeedbackStatus, string> = {
  new: 'bg-surface-2 text-ink-2 border-line-strong',
  auto_applied: 'bg-forest-soft text-forest border-forest/30',
  pending_review: 'bg-oro-soft text-oro border-oro/40',
  approved: 'bg-forest-soft text-forest border-forest/30',
  rejected: 'bg-carmin-soft text-carmin border-carmin/30',
}

export default function Revision() {
  const [tab, setTab] = useState<Tab>('pending')
  const [rows, setRows] = useState<FeedbackRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [reviewer, setReviewer] = useStored('inga.revisor', '')
  const [pendingCount, setPendingCount] = useState<number | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    setRows(null)
    setError(null)
    api
      .listFeedback(tab === 'pending' ? 'pending_review' : undefined, ctrl.signal)
      .then((r) => {
        const all = Array.isArray(r) ? r : []
        if (tab === 'pending') {
          setRows(all)
          setPendingCount(all.length)
        } else {
          setRows(all.filter((x) => x.status !== 'pending_review'))
          setPendingCount(all.filter((x) => x.status === 'pending_review').length)
        }
      })
      .catch((e: unknown) => !ctrl.signal.aborted && setError(e instanceof Error ? e.message : 'Error desconocido.'))
    return () => ctrl.abort()
  }, [tab, attempt])

  const onReviewed = useCallback((id: number) => {
    setRows((rs) => rs?.filter((r) => r.id !== id) ?? rs)
    setPendingCount((n) => (n === null ? n : Math.max(0, n - 1)))
  }, [])

  return (
    <div className="mx-auto w-full max-w-[60rem] px-4 pt-6 sm:px-6 sm:pt-10">
      <h1 className="text-4xl sm:text-5xl">Revisión</h1>
      <p className="mt-2 max-w-[64ch] text-ink-2">
        Correcciones que el agente no pudo corroborar con una fuente escrita. Al aprobar una, sus hechos pendientes pasan a activos en la wiki; al rechazarla, quedan
        marcados como rechazados. Nada se borra.
      </p>

      <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
        <div className="seg" role="tablist" aria-label="Correcciones">
          {(
            [
              ['pending', 'Pendientes'],
              ['history', 'Historial'],
            ] as const
          ).map(([k, label]) => (
            <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>
              {tab === k && <motion.span layoutId="seg-rev" className="absolute inset-0 rounded-[7px] border border-line bg-surface shadow-sm" transition={{ type: 'spring', duration: 0.35 }} />}
              <span className="relative">
                {label}
                {k === 'pending' && pendingCount !== null && pendingCount > 0 && (
                  <span className="ml-1.5 rounded-full bg-carmin px-1.5 py-0.5 text-xs text-[#fff] tabular-nums dark:text-[#0b1712]">{pendingCount}</span>
                )}
              </span>
            </button>
          ))}
        </div>
        {tab === 'pending' && (
          <div className="w-full sm:w-64">
            <label htmlFor="reviewer" className="label">
              Quién revisa
            </label>
            <input id="reviewer" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Tu nombre" autoComplete="name" className="field" />
          </div>
        )}
      </div>

      <div className="mt-6">
        {error ? (
          <ErrorBlock title="No se pudo cargar la cola" message={error} onRetry={() => setAttempt((n) => n + 1)} />
        ) : rows === null ? (
          <LoadingBlock label="Cargando correcciones" />
        ) : rows.length === 0 ? (
          <div className="panel">
            {tab === 'pending' ? (
              <EmptyBlock title="La cola está vacía">No hay correcciones esperando revisión. Las nuevas llegan desde "Sugerir corrección" en el traductor.</EmptyBlock>
            ) : (
              <EmptyBlock title="Sin historial todavía">Aquí aparecerán las correcciones aplicadas, aprobadas y rechazadas.</EmptyBlock>
            )}
          </div>
        ) : (
          <ul className="space-y-6">
            <AnimatePresence initial={false}>
              {rows.map((row) => (
                <motion.li key={row.id} layout="position" exit={{ opacity: 0, height: 0, marginBottom: 0 }} transition={{ duration: 0.35 }} className="overflow-hidden">
                  <FeedbackCard row={row} reviewer={reviewer} reviewable={tab === 'pending'} onReviewed={onReviewed} />
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </div>
    </div>
  )
}

function FeedbackCard({ row, reviewer, reviewable, onReviewed }: { row: FeedbackRow; reviewer: string; reviewable: boolean; onReviewed: (id: number) => void }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [decided, setDecided] = useState<'approve' | 'reject' | null>(null)
  const triage = triageOf(row)
  const targetInga = row.direccion === 'es2inga'
  const dir = DIRECCION[row.direccion] ?? { from: 'Origen', to: 'Destino' }

  const decide = async (decision: 'approve' | 'reject') => {
    if (!reviewer.trim()) {
      setError('Escribe tu nombre en "Quién revisa" antes de decidir.')
      document.getElementById('reviewer')?.focus()
      return
    }
    setBusy(decision)
    setError(null)
    try {
      await api.reviewFeedback(row.id, { decision, reviewer: reviewer.trim(), note: note.trim() })
      setDecided(decision)
      setTimeout(() => onReviewed(row.id), 1100)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <article className="panel overflow-hidden" aria-label={`Corrección ${row.id}`}>
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line px-4 py-3 text-sm sm:px-6">
        <span className="code text-ink-2">feedback:{row.id}</span>
        <span className={`rounded-[5px] border px-1.5 py-0.5 text-xs font-semibold ${STATUS_TONE[row.status] ?? STATUS_TONE.new}`}>{FEEDBACK_STATUS[row.status] ?? row.status}</span>
        <span className="text-ink-2">
          {row.author || 'anónimo'}, {formatDate(row.created_at)}
        </span>
      </header>

      <div className="grid gap-5 px-4 py-5 sm:px-6 md:grid-cols-3">
        <Cell label={`Frase (${dir.from.toLowerCase()})`} text={row.source_text} inga={!targetInga} />
        <Cell label="El modelo tradujo" text={row.model_output} inga={targetInga} tone="muted" />
        <Cell label="La persona propone" text={row.correction} inga={targetInga} tone="strong" />
      </div>

      {row.comment && (
        <p className="mx-4 mb-5 border-l-2 border-oro-fill pl-3 text-[0.97rem] text-ink-2 sm:mx-6">
          <span className="font-semibold text-ink">Su explicación.</span> {row.comment}
        </p>
      )}

      <div className="px-4 pb-5 sm:px-6">
        <VerdictCard
          status={row.status === 'auto_applied' ? 'auto_applied' : 'pending_review'}
          verdict={triage?.verdict}
          rationale={triage?.rationale}
          evidence={triage?.evidence ?? []}
          facts={(row.facts ?? []).map((f, i) => ({ key: factKey(f, i), page_id: f.page_id, text: f.text, status: f.status }))}
          showQueueLink={false}
          headless={!reviewable && row.status !== 'auto_applied'}
        />
      </div>

      {reviewable ? (
        <footer className="border-t border-line bg-surface-2/60 px-4 py-4 sm:px-6">
          {decided ? (
            <p role="status" className={`flex items-center gap-2 font-semibold ${decided === 'approve' ? 'text-forest' : 'text-carmin'}`}>
              {decided === 'approve' ? <Check className="size-5" aria-hidden="true" /> : <X className="size-5" aria-hidden="true" />}
              {decided === 'approve' ? 'Aprobada. Sus hechos ya están activos en la wiki.' : 'Rechazada. Sus hechos quedaron marcados como rechazados.'}
            </p>
          ) : (
            <>
              <label htmlFor={`note-${row.id}`} className="label">
                Nota de revisión (opcional)
              </label>
              <textarea id={`note-${row.id}`} rows={2} value={note} onChange={(e) => setNote(e.target.value)} className="field resize-y" placeholder="Por qué la apruebas o la rechazas" />
              {error && (
                <p role="alert" className="mt-2 text-sm font-semibold text-carmin">
                  {error}
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className="btn btn-primary" disabled={busy !== null} onClick={() => decide('approve')}>
                  <Check className="size-4" aria-hidden="true" />
                  {busy === 'approve' ? 'Aprobando' : 'Aprobar'}
                </button>
                <button type="button" className="btn btn-danger" disabled={busy !== null} onClick={() => decide('reject')}>
                  <X className="size-4" aria-hidden="true" />
                  {busy === 'reject' ? 'Rechazando' : 'Rechazar'}
                </button>
              </div>
            </>
          )}
        </footer>
      ) : (
        (row.reviewer || row.review_note) && (
          <footer className="border-t border-line bg-surface-2/60 px-4 py-3 text-sm sm:px-6">
            <p>
              <span className="font-semibold">{row.status === 'rejected' ? 'Rechazada' : 'Revisada'} por {row.reviewer ?? 'alguien'}</span>
              {row.reviewed_at && <span className="text-ink-2">, {formatDate(row.reviewed_at)}</span>}
            </p>
            {row.review_note && <p className="mt-0.5 text-ink-2">{row.review_note}</p>}
          </footer>
        )
      )}
    </article>
  )
}

function Cell({ label, text, inga, tone }: { label: string; text: string; inga: boolean; tone?: 'muted' | 'strong' }) {
  return (
    <div className={tone === 'strong' ? 'md:border-l-2 md:border-forest md:pl-4' : ''}>
      <p className="text-sm font-semibold text-ink-2">{label}</p>
      <p
        className={`mt-1 leading-snug ${inga ? 'inga text-[1.35rem]' : 'font-display text-[1.2rem]'} ${
          tone === 'muted' ? 'text-ink-2 line-through decoration-carmin/50 decoration-1' : ''
        }`}
      >
        {text || '(vacío)'}
      </p>
    </div>
  )
}
