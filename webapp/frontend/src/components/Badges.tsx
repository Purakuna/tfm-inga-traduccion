import type { FactSource, FactStatus, PageKind } from '../api/types'
import { FACT_STATUS, KIND, SOURCE, splitPageId } from '../lib/labels'
import { usePageDrawer } from './PageDrawer'

const KIND_TONE: Record<string, string> = {
  lemma: 'bg-forest-soft text-forest border-forest/30',
  suffix: 'bg-carmin-soft text-carmin border-carmin/30',
  grammar: 'bg-rio-soft text-rio border-rio/30',
  convention: 'bg-oro-soft text-oro border-oro/30',
  case: 'bg-arcilla-soft text-arcilla border-arcilla/30',
}
const NEUTRAL = 'bg-surface-2 text-ink-2 border-line-strong'

export function kindTone(kind: string): string {
  return KIND_TONE[kind] ?? NEUTRAL
}

export function KindBadge({ kind, className = '' }: { kind: PageKind | string; className?: string }) {
  const label = (KIND as Record<string, { one: string }>)[kind]?.one ?? kind
  return (
    <span className={`inline-flex items-center rounded-[5px] border px-1.5 py-0.5 text-xs font-semibold ${kindTone(kind)} ${className}`}>
      {label}
    </span>
  )
}

const STATUS_TONE: Record<FactStatus, string> = {
  active: 'bg-forest-soft text-forest border-forest/30',
  pending: 'bg-oro-soft text-oro border-oro/40',
  superseded: 'bg-surface-2 text-ink-3 border-line-strong',
  rejected: 'bg-carmin-soft text-carmin border-carmin/30',
}

export function FactStatusBadge({ status }: { status: FactStatus }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-[5px] border px-1.5 py-0.5 text-xs font-semibold ${STATUS_TONE[status] ?? NEUTRAL}`}>
      <span aria-hidden="true" className="size-1.5 rotate-45 bg-current" />
      {FACT_STATUS[status] ?? status}
    </span>
  )
}

/** Chip con el id de una pagina; al pulsarlo abre el cajon de la pagina. */
export function PageChip({ id, marked = false, className = '' }: { id: string; marked?: boolean; className?: string }) {
  const { open } = usePageDrawer()
  const { kind, slug } = splitPageId(id)
  return (
    <button
      type="button"
      onClick={() => open(id)}
      title={`Abrir ${id}`}
      className={`code group inline-flex max-w-full items-center gap-1.5 rounded-[5px] border px-1.5 py-1 leading-none transition-[filter,transform] hover:brightness-95 active:scale-[0.98] dark:hover:brightness-125 ${kindTone(kind)} ${className}`}
    >
      {marked && <span aria-hidden="true" className="size-1.5 shrink-0 rotate-45 bg-oro-fill" />}
      <span className="truncate">
        <span className="opacity-70">{kind}:</span>
        <span className="font-medium">{slug}</span>
      </span>
      {marked && <span className="sr-only">(usada en la traducción)</span>}
    </button>
  )
}

const SOURCE_TONE: Record<string, string> = {
  dictionary: 'text-forest',
  grammar: 'text-rio',
  corpus: 'text-arcilla',
  feedback: 'text-oro',
}

export function SourceList({ sources, className = '' }: { sources: FactSource[]; className?: string }) {
  if (!sources?.length) return null
  return (
    <ul className={`space-y-1.5 ${className}`}>
      {sources.map((s, i) => (
        <li key={`${s.ref}-${i}`} className="border-l-2 border-line-strong pl-3 text-sm">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className={`font-semibold ${SOURCE_TONE[s.type] ?? 'text-ink-2'}`}>{SOURCE[s.type] ?? s.type}</span>
            <span className="code text-ink-2 break-all">{s.ref}</span>
          </div>
          {s.quote && <q className="mt-0.5 block font-display text-[1.02rem] leading-snug text-ink-2 italic">{s.quote}</q>}
        </li>
      ))}
    </ul>
  )
}
