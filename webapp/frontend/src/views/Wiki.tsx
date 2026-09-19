import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ChevronLeft, ChevronRight, Search, X } from 'lucide-react'
import { api } from '../api/client'
import type { PageKind, PageList, WikiPage, WikiStats } from '../api/types'
import { KindBadge } from '../components/Badges'
import { ImageSlot } from '../components/ImageSlot'
import { PageBody } from '../components/PageBody'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/States'
import { FACT_STATUS, KIND, KINDS } from '../lib/labels'
import { readStats } from '../lib/stats'

const LIMIT = 24

export default function Wiki() {
  const { pageId: rawId } = useParams()
  const pageId = rawId ? decodeURIComponent(rawId) : null
  const [params, setParams] = useSearchParams()
  const kind = (params.get('tipo') ?? '') as PageKind | ''
  const q = params.get('q') ?? ''
  const offset = Math.max(0, Number(params.get('desde') ?? 0) || 0)

  const [draft, setDraft] = useState(q)
  const [list, setList] = useState<PageList | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [listLoading, setListLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const [stats, setStats] = useState<WikiStats | null>(null)
  const navigate = useNavigate()

  const update = (next: { tipo?: string; q?: string; desde?: number }) => {
    const sp = new URLSearchParams(params)
    for (const [k, v] of Object.entries(next)) {
      if (v === '' || v === 0 || v === undefined) sp.delete(k)
      else sp.set(k, String(v))
    }
    setParams(sp, { replace: true })
  }

  // La busqueda espera a que se deje de escribir.
  useEffect(() => {
    if (draft === q) return
    const t = setTimeout(() => update({ q: draft.trim(), desde: 0 }), 280)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft])

  useEffect(() => {
    const ctrl = new AbortController()
    setListLoading(true)
    setListError(null)
    api
      .wikiPages({ kind, q, offset, limit: LIMIT }, ctrl.signal)
      .then((r) => {
        setList({ items: r.items ?? [], total: r.total ?? r.items?.length ?? 0 })
        setListLoading(false)
      })
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return
        setListError(e instanceof Error ? e.message : 'Error desconocido.')
        setListLoading(false)
      })
    return () => ctrl.abort()
  }, [kind, q, offset, attempt])

  useEffect(() => {
    const ctrl = new AbortController()
    api.wikiStats(ctrl.signal).then(setStats).catch(() => undefined)
    return () => ctrl.abort()
  }, [])

  const total = list?.total ?? 0
  const from = total === 0 ? 0 : offset + 1
  const to = Math.min(offset + LIMIT, total)
  const search = params.toString() ? `?${params.toString()}` : ''

  return (
    <div className="mx-auto w-full max-w-[76rem] px-4 pt-6 sm:px-6 sm:pt-10">
      <div className="grid gap-8 lg:grid-cols-[22rem_1fr] lg:gap-10">
        {/* ---------- lista ---------- */}
        <aside className={pageId ? 'hidden lg:block' : ''} aria-label="Páginas de la wiki">
          <h1 className={`text-4xl sm:text-5xl ${pageId ? 'lg:text-4xl' : ''}`}>Wiki</h1>
          <p className="mt-2 text-ink-2">Lo que el agente sabe del inga. Cada hecho cita su fuente.</p>

          <div className="relative mt-5">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-3" aria-hidden="true" />
            <label htmlFor="wiki-q" className="sr-only">
              Buscar en la wiki
            </label>
            <input
              id="wiki-q"
              type="search"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Busca un lema, un sufijo o una glosa"
              className="field pr-9 pl-9 [&::-webkit-search-cancel-button]:hidden"
            />
            {draft && (
              <button type="button" onClick={() => setDraft('')} aria-label="Borrar la búsqueda" className="absolute top-1/2 right-2 -translate-y-1/2 rounded p-1 text-ink-3 hover:text-ink">
                <X className="size-4" aria-hidden="true" />
              </button>
            )}
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label="Filtrar por tipo de página">
            {(['', ...KINDS] as (PageKind | '')[]).map((k) => {
              const on = kind === k
              const count = k && stats ? readStats(stats).pages?.[k] : undefined
              return (
                <button
                  key={k || 'todos'}
                  type="button"
                  aria-pressed={on}
                  onClick={() => update({ tipo: k, desde: 0 })}
                  className={`rounded-lg border px-2.5 py-1.5 text-sm font-semibold transition-colors ${
                    on ? 'border-primary bg-primary text-on-primary' : 'border-line-strong text-ink-2 hover:bg-surface hover:text-ink'
                  }`}
                >
                  {k ? KIND[k].many : 'Todo'}
                  {typeof count === 'number' && <span className={`ml-1.5 font-normal tabular-nums ${on ? 'opacity-80' : 'text-ink-3'}`}>{count.toLocaleString('es-CO')}</span>}
                </button>
              )
            })}
          </div>

          <div className="mt-5">
            {listError ? (
              <ErrorBlock title="No se pudo cargar la lista" message={listError} onRetry={() => setAttempt((n) => n + 1)} />
            ) : !list && listLoading ? (
              <LoadingBlock label="Cargando páginas" />
            ) : list && list.items.length === 0 ? (
              <EmptyBlock title="Nada con esa búsqueda">
                {q ? (
                  <>
                    Ninguna página coincide con <strong>{q}</strong>. Prueba con la raíz de la palabra o con la glosa en español.
                  </>
                ) : (
                  'Todavía no hay páginas de este tipo.'
                )}
              </EmptyBlock>
            ) : (
              list && (
                <>
                  <p className="text-sm text-ink-3 tabular-nums" aria-live="polite">
                    {from.toLocaleString('es-CO')} a {to.toLocaleString('es-CO')} de {total.toLocaleString('es-CO')} páginas
                  </p>
                  <ul className={`mt-2 divide-y divide-line border-y border-line transition-opacity ${listLoading ? 'opacity-50' : ''}`}>
                    {list.items.map((p) => {
                      const current = p.id === pageId
                      return (
                        <li key={p.id}>
                          <Link
                            to={`/wiki/${encodeURIComponent(p.id)}${search}`}
                            aria-current={current ? 'page' : undefined}
                            className={`relative block px-3 py-3 transition-colors ${current ? 'bg-surface' : 'hover:bg-surface/70'}`}
                          >
                            {current && <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px] bg-carmin" />}
                            <span className="flex items-baseline justify-between gap-3">
                              <span className={`truncate text-xl leading-tight font-bold ${p.kind === 'lemma' || p.kind === 'suffix' ? 'inga' : 'font-display'}`}>{p.title}</span>
                              <KindBadge kind={p.kind} className="shrink-0" />
                            </span>
                            <span className="mt-0.5 line-clamp-2 text-sm text-ink-2">{p.summary}</span>
                          </Link>
                        </li>
                      )
                    })}
                  </ul>
                  {total > LIMIT && (
                    <nav className="mt-3 flex items-center justify-between" aria-label="Paginación">
                      <button type="button" className="btn btn-quiet btn-sm" disabled={offset === 0} onClick={() => update({ desde: Math.max(0, offset - LIMIT) })}>
                        <ChevronLeft className="size-4" aria-hidden="true" />
                        Anteriores
                      </button>
                      <span className="text-sm text-ink-3 tabular-nums">
                        {Math.floor(offset / LIMIT) + 1} / {Math.ceil(total / LIMIT)}
                      </span>
                      <button type="button" className="btn btn-quiet btn-sm" disabled={offset + LIMIT >= total} onClick={() => update({ desde: offset + LIMIT })}>
                        Siguientes
                        <ChevronRight className="size-4" aria-hidden="true" />
                      </button>
                    </nav>
                  )}
                </>
              )
            )}
          </div>
        </aside>

        {/* ---------- detalle ---------- */}
        <div className={`min-w-0 ${pageId ? '' : 'hidden lg:block'}`}>
          {pageId ? (
            <>
              <button type="button" onClick={() => navigate(`/wiki${search}`)} className="btn btn-quiet btn-sm mb-5 lg:hidden">
                <ArrowLeft className="size-4" aria-hidden="true" />
                Volver a la lista
              </button>
              <PageDetail key={pageId} pageId={pageId} />
            </>
          ) : (
            <WikiWelcome stats={stats} />
          )}
        </div>
      </div>
    </div>
  )
}

function PageDetail({ pageId }: { pageId: string }) {
  const [page, setPage] = useState<WikiPage | null>(null)
  const [error, setError] = useState<{ message: string; notFound: boolean } | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const ctrl = new AbortController()
    setError(null)
    api
      .wikiPage(pageId, ctrl.signal)
      .then(setPage)
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return
        const status = (e as { status?: number }).status
        setError({ message: e instanceof Error ? e.message : 'Error desconocido.', notFound: status === 404 })
      })
    return () => ctrl.abort()
  }, [pageId, attempt])

  if (error?.notFound) {
    return (
      <div className="panel">
        <EmptyBlock title="Esa página no existe" action={<Link to="/wiki" className="btn btn-quiet btn-sm">Ver todas las páginas</Link>}>
          No hay ninguna página con el identificador <span className="code">{pageId}</span>.
        </EmptyBlock>
      </div>
    )
  }
  if (error) return <ErrorBlock title="No se pudo abrir la página" message={error.message} onRetry={() => setAttempt((n) => n + 1)} />
  if (!page) return <LoadingBlock label="Abriendo la página" className="panel" />
  return (
    <div className="panel p-5 sm:p-8">
      <p className="code mb-4 text-ink-3">{page.id}</p>
      <PageBody page={page} />
    </div>
  )
}

function WikiWelcome({ stats }: { stats: WikiStats | null }) {
  const s = readStats(stats)
  return (
    <div className="panel overflow-hidden">
      <ImageSlot name="selva" className="h-56" />
      <div className="p-6 sm:p-8">
        <h2 className="text-3xl">Elige una página de la lista</h2>
        <p className="mt-2 max-w-[60ch] text-ink-2">
          Los lemas salen del diccionario, los sufijos y la gramática de la gramática pedagógica, y los casos nacen de correcciones de hablantes. Ningún hecho entra sin una
          fuente que se pueda citar.
        </p>
        {(s.pages || s.facts) && (
          <dl className="mt-6 grid gap-x-10 gap-y-5 sm:grid-cols-2">
            {s.pages && (
              <div>
                <dt className="text-sm font-semibold text-ink-2">Páginas</dt>
                <dd className="mt-1.5 space-y-1">
                  {Object.entries(s.pages).map(([k, n]) => (
                    <div key={k} className="flex items-baseline justify-between gap-4 border-b border-line pb-1">
                      <span>{(KIND as Record<string, { many: string }>)[k]?.many ?? k}</span>
                      <span className="font-display text-xl font-bold tabular-nums">{n.toLocaleString('es-CO')}</span>
                    </div>
                  ))}
                </dd>
              </div>
            )}
            {s.facts && (
              <div>
                <dt className="text-sm font-semibold text-ink-2">Hechos</dt>
                <dd className="mt-1.5 space-y-1">
                  {Object.entries(s.facts).map(([k, n]) => (
                    <div key={k} className="flex items-baseline justify-between gap-4 border-b border-line pb-1">
                      <span>{(FACT_STATUS as Record<string, string>)[k] ?? k}</span>
                      <span className="font-display text-xl font-bold tabular-nums">{n.toLocaleString('es-CO')}</span>
                    </div>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        )}
      </div>
    </div>
  )
}
