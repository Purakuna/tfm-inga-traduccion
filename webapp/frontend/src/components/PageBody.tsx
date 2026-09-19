import { useMemo, useState } from 'react'
import type { Fact, FactSection, WikiPage } from '../api/types'
import { SECTION, SECTIONS, formatDate } from '../lib/labels'
import { FactStatusBadge, KindBadge, SourceList } from './Badges'

const INACTIVE = new Set(['superseded', 'rejected'])

/** Cuerpo de una pagina de la wiki: se usa en la vista Wiki y en el cajon. */
export function PageBody({ page, compact = false }: { page: WikiPage; compact?: boolean }) {
  const [showInactive, setShowInactive] = useState(false)
  const facts = page.facts ?? []
  const inactiveCount = facts.filter((f) => INACTIVE.has(f.status)).length

  const groups = useMemo(() => {
    const visible = facts.filter((f) => showInactive || !INACTIVE.has(f.status))
    const known: { section: string; label: string; facts: Fact[] }[] = SECTIONS.map((s) => ({
      section: s,
      label: SECTION[s],
      facts: visible.filter((f) => f.section === s),
    }))
    const other = visible.filter((f) => !SECTIONS.includes(f.section as FactSection))
    if (other.length) known.push({ section: 'otros', label: 'Otros', facts: other })
    return known.filter((g) => g.facts.length > 0)
  }, [facts, showInactive])

  const isInga = page.kind === 'lemma' || page.kind === 'suffix'

  return (
    <article>
      <header>
        <div className="flex flex-wrap items-center gap-2 text-sm text-ink-2">
          <KindBadge kind={page.kind} />
          {page.status === 'superseded' && (
            <span className="rounded-[5px] border border-line-strong bg-surface-2 px-1.5 py-0.5 text-xs font-semibold text-ink-3">Página reemplazada</span>
          )}
          <span>versión {page.version}</span>
          {page.updated_at && <span className="text-ink-3">actualizada el {formatDate(page.updated_at)}</span>}
        </div>
        <h1 className={`mt-3 break-words ${isInga ? 'inga !font-bold' : ''} ${compact ? 'text-4xl' : 'text-4xl sm:text-5xl'}`}>{page.title}</h1>
        {page.summary && <p className="mt-3 max-w-[62ch] text-lg leading-snug text-ink-2">{page.summary}</p>}
        {page.aliases?.length > 0 && (
          <p className="mt-3 text-sm text-ink-2">
            También se busca como{' '}
            {page.aliases.map((a, i) => (
              <span key={a}>
                <span className="inga text-base text-ink italic">{a}</span>
                {i < page.aliases.length - 1 ? ', ' : ''}
              </span>
            ))}
          </p>
        )}
      </header>

      {groups.length === 0 ? (
        <p className="mt-8 rounded-xl border border-dashed border-line-strong p-5 text-sm text-ink-2">
          Esta página todavía no tiene hechos activos.
        </p>
      ) : (
        groups.map((g) => (
          <section key={g.section} className="mt-8" aria-labelledby={`sec-${page.id}-${g.section}`}>
            <h2 id={`sec-${page.id}-${g.section}`} className="flex items-center gap-3 text-xl">
              {g.label}
              <span className="h-px flex-1 bg-line" aria-hidden="true" />
              <span className="font-sans text-sm font-normal text-ink-3">{g.facts.length}</span>
            </h2>
            <ul className="mt-3 space-y-4">
              {g.facts.map((f) => (
                <FactItem key={f.id} fact={f} />
              ))}
            </ul>
          </section>
        ))
      )}

      {inactiveCount > 0 && (
        <button type="button" onClick={() => setShowInactive((v) => !v)} className="btn btn-quiet btn-sm mt-8" aria-pressed={showInactive}>
          {showInactive ? 'Ocultar' : 'Mostrar'} {inactiveCount} {inactiveCount === 1 ? 'hecho reemplazado o rechazado' : 'hechos reemplazados o rechazados'}
        </button>
      )}
    </article>
  )
}

function FactItem({ fact }: { fact: Fact }) {
  const inactive = INACTIVE.has(fact.status)
  return (
    <li className={`rounded-xl border p-4 ${fact.status === 'pending' ? 'border-oro/50 bg-oro-soft/40' : 'border-line bg-bg/50'} ${inactive ? 'opacity-70' : ''}`}>
      <p className={`max-w-[68ch] text-[1.02rem] leading-relaxed ${fact.status === 'superseded' ? 'line-through decoration-ink-3/60' : ''}`}>{fact.text}</p>
      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-3">
        <FactStatusBadge status={fact.status} />
        <span>
          {fact.created_by === 'seed' ? 'De las fuentes iniciales' : fact.created_by === 'feedback' ? 'De una corrección' : `Por ${fact.created_by}`}
        </span>
        <span className="code !text-xs">{fact.id}</span>
        {fact.superseded_by && <span>reemplazado por <span className="code !text-xs">{fact.superseded_by}</span></span>}
      </div>
      <SourceList sources={fact.sources} className="mt-3" />
    </li>
  )
}
