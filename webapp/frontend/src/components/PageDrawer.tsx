import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowUpRight, X } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../api/client'
import type { WikiPage } from '../api/types'
import { PageBody } from './PageBody'
import { ErrorBlock, LoadingBlock } from './States'

interface DrawerApi {
  open: (pageId: string) => void
  close: () => void
}

const Ctx = createContext<DrawerApi>({ open: () => undefined, close: () => undefined })

export function usePageDrawer(): DrawerApi {
  return useContext(Ctx)
}

export function PageDrawerProvider({ children }: { children: React.ReactNode }) {
  const [pageId, setPageId] = useState<string | null>(null)
  const opener = useRef<HTMLElement | null>(null)
  const location = useLocation()

  const open = useCallback((id: string) => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setPageId(id)
  }, [])
  const close = useCallback(() => {
    setPageId(null)
    // El foco vuelve al chip que abrio el cajon.
    requestAnimationFrame(() => opener.current?.focus())
  }, [])

  useEffect(() => setPageId(null), [location.pathname])

  const value = useMemo(() => ({ open, close }), [open, close])
  return (
    <Ctx.Provider value={value}>
      {children}
      <AnimatePresence>{pageId && <Drawer key="drawer" pageId={pageId} onClose={close} />}</AnimatePresence>
    </Ctx.Provider>
  )
}

function Drawer({ pageId, onClose }: { pageId: string; onClose: () => void }) {
  const [page, setPage] = useState<WikiPage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const panel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    setPage(null)
    setError(null)
    api
      .wikiPage(pageId, ctrl.signal)
      .then(setPage)
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted) setError(e instanceof Error ? e.message : 'Error desconocido.')
      })
    return () => ctrl.abort()
  }, [pageId, attempt])

  useEffect(() => {
    panel.current?.focus()
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      onClose()
      return
    }
    if (e.key !== 'Tab' || !panel.current) return
    const items = panel.current.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),input,textarea,select,[tabindex]:not([tabindex="-1"])')
    if (items.length === 0) return
    const first = items[0]
    const last = items[items.length - 1]
    if (e.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  return (
    <div className="fixed inset-0 z-50" onKeyDown={onKeyDown}>
      <motion.div
        className="absolute inset-0 bg-[#07100c]/55 backdrop-blur-[2px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        aria-hidden="true"
      />
      <motion.div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={`Página ${pageId}`}
        tabIndex={-1}
        className="absolute inset-x-0 bottom-0 flex max-h-[88dvh] flex-col rounded-t-2xl border border-line bg-surface shadow-2xl outline-none sm:inset-y-0 sm:right-0 sm:left-auto sm:max-h-none sm:w-[min(34rem,92vw)] sm:rounded-none sm:rounded-l-2xl"
        initial={{ opacity: 0, x: 0, y: 40 }}
        animate={{ opacity: 1, x: 0, y: 0 }}
        exit={{ opacity: 0, y: 40 }}
        transition={{ type: 'spring', damping: 30, stiffness: 320 }}
      >
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
          <span className="code truncate text-ink-2">{pageId}</span>
          <div className="flex items-center gap-1">
            <Link to={`/wiki/${encodeURIComponent(pageId)}`} className="btn btn-quiet btn-sm">
              Abrir en la wiki
              <ArrowUpRight className="size-4" aria-hidden="true" />
            </Link>
            <button type="button" onClick={onClose} className="btn btn-quiet btn-sm btn-icon" aria-label="Cerrar">
              <X className="size-4" aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5">
          {error ? (
            <ErrorBlock title="No se pudo abrir la página" message={error} onRetry={() => setAttempt((n) => n + 1)} />
          ) : page ? (
            <PageBody page={page} compact />
          ) : (
            <LoadingBlock label="Abriendo la página" />
          )}
        </div>
      </motion.div>
    </div>
  )
}
