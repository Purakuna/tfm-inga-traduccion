import { useEffect, useState } from 'react'
import { NavLink, Outlet, Link } from 'react-router-dom'
import { BookOpenText, ClipboardCheck, Info, Languages, Moon, Sun } from 'lucide-react'
import { api, IS_MOCK } from '../api/client'
import type { Health } from '../api/types'
import { useTheme } from '../lib/theme'
import { ChumbeBand } from './Chumbe'
import { useImageOk } from './ImageSlot'

const NAV = [
  { to: '/', label: 'Traducir', icon: Languages, end: true },
  { to: '/wiki', label: 'Wiki', icon: BookOpenText, end: false },
  { to: '/revision', label: 'Revisión', icon: ClipboardCheck, end: false },
  { to: '/acerca', label: 'Acerca', icon: Info, end: false },
]

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5 rounded-md" aria-label="Inga Wiki, inicio">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="var(--primary)" />
        <path d="M16 4.5 27.5 16 16 27.5 4.5 16Z" fill="none" stroke="var(--on-primary)" strokeWidth="2.2" />
        <path d="M16 11 21 16 16 21 11 16Z" fill="var(--oro-fill)" />
      </svg>
      <span className="font-display text-[1.35rem] leading-none font-extrabold tracking-tight">Inga Wiki</span>
    </Link>
  )
}

function BackendStatus() {
  const [health, setHealth] = useState<Health | null>(null)
  const [down, setDown] = useState(false)

  useEffect(() => {
    if (IS_MOCK) return
    const ctrl = new AbortController()
    api
      .health(ctrl.signal)
      .then((h) => setHealth(h))
      .catch(() => !ctrl.signal.aborted && setDown(true))
    return () => ctrl.abort()
  }, [])

  if (IS_MOCK) {
    return (
      <span
        className="rounded-[5px] border border-oro/40 bg-oro-soft px-2 py-1 text-xs font-semibold text-oro"
        title="VITE_MOCK=1: las respuestas son simuladas en el navegador, sin backend."
      >
        Demostración
      </span>
    )
  }
  if (down) {
    return (
      <span className="rounded-[5px] border border-carmin/40 bg-carmin-soft px-2 py-1 text-xs font-semibold text-carmin" title="No hay respuesta en /api/health">
        Sin backend
      </span>
    )
  }
  if (!health) return null
  return (
    <span className="hidden items-center gap-1.5 text-xs text-ink-2 md:inline-flex" title="Modelo que usa el backend">
      <span className="size-1.5 rotate-45 bg-forest" aria-hidden="true" />
      {health.model}
    </span>
  )
}

export function Layout() {
  const [theme, toggleTheme] = useTheme()
  const hasTexture = useImageOk('/img/patron-chumbe.png')

  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#contenido" className="btn btn-primary sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60]">
        Saltar al contenido
      </a>

      <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 w-full max-w-[76rem] items-center gap-4 px-4 sm:h-16 sm:px-6">
          <Logo />
          <nav aria-label="Secciones" className="ml-4 hidden items-center gap-1 sm:flex">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `relative rounded-md px-3 py-2 text-[0.95rem] font-semibold transition-colors ${
                    isActive ? 'text-ink' : 'text-ink-2 hover:text-ink'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {n.label}
                    {isActive && <span aria-hidden="true" className="absolute inset-x-3 -bottom-[1px] h-[3px] bg-carmin" />}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <BackendStatus />
            <button
              type="button"
              onClick={toggleTheme}
              className="btn btn-quiet btn-sm btn-icon"
              aria-label={theme === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
            >
              {theme === 'dark' ? <Sun className="size-4" aria-hidden="true" /> : <Moon className="size-4" aria-hidden="true" />}
            </button>
          </div>
        </div>
      </header>

      <main id="contenido" className="flex-1 pb-20 sm:pb-0">
        <Outlet />
      </main>

      <footer className="relative mt-16 mb-16 sm:mb-0">
        <ChumbeBand />
        <div
          className="bg-bg-deep"
          style={
            hasTexture
              ? { backgroundImage: 'linear-gradient(var(--bg-deep), color-mix(in srgb, var(--bg-deep) 88%, transparent)), url(/img/patron-chumbe.png)', backgroundSize: 'auto, 220px' }
              : undefined
          }
        >
          <div className="mx-auto flex w-full max-w-[76rem] flex-col gap-1 px-4 py-6 text-sm text-ink-2 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <p>Traductor inga y español con fuentes citadas. Prototipo de investigación.</p>
            <p>
              Las traducciones pueden tener errores. <Link to="/acerca" className="link">Fuentes y límites</Link>
            </p>
          </div>
        </div>
      </footer>

      <nav aria-label="Secciones" className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 backdrop-blur-md sm:hidden">
        <ul className="grid grid-cols-4">
          {NAV.map((n) => (
            <li key={n.to}>
              <NavLink
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `relative flex flex-col items-center gap-0.5 py-2 text-xs font-semibold ${isActive ? 'text-ink' : 'text-ink-3'}`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && <span aria-hidden="true" className="absolute top-0 h-[3px] w-10 bg-carmin" />}
                    <n.icon className="size-5" aria-hidden="true" />
                    {n.label}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
