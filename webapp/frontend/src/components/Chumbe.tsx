// Motivos geometricos inspirados (de forma abstracta) en el chumbe, la faja
// tejida inga: rombos anidados y zigzag. Se usan como divisor, como cargador y
// como medidor de confianza.

import { useId } from 'react'
import type { Stage } from '../api/types'
import { STAGE } from '../lib/labels'

export function Rombo({
  size = 14,
  state = 'solid',
  className = '',
}: {
  size?: number
  state?: 'solid' | 'outline' | 'nested'
  className?: string
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true" className={className}>
      {state === 'solid' && <path d="M8 1 15 8 8 15 1 8Z" fill="currentColor" />}
      {state === 'outline' && <path d="M8 2 14 8 8 14 2 8Z" fill="none" stroke="currentColor" strokeWidth="1.6" />}
      {state === 'nested' && (
        <>
          <path d="M8 1.5 14.5 8 8 14.5 1.5 8Z" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8 5.2 10.8 8 8 10.8 5.2 8Z" fill="currentColor" />
        </>
      )}
    </svg>
  )
}

/** Franja tejida decorativa. Hereda el ancho del contenedor. */
export function ChumbeBand({ className = '', height = 26 }: { className?: string; height?: number }) {
  const id = useId().replace(/:/g, '')
  return (
    <svg
      aria-hidden="true"
      className={`block w-full ${className}`}
      height={height}
      preserveAspectRatio="xMidYMid slice"
      role="presentation"
    >
      <defs>
        <pattern id={`ch-${id}`} width="52" height="26" patternUnits="userSpaceOnUse">
          {/* Colores fijos: la faja es la misma tela en los dos temas. */}
          <rect width="52" height="26" fill="#1d4a38" />
          <path d="M0 2.5H52M0 23.5H52" stroke="#d9a441" strokeWidth="1.5" />
          <path d="M13 5 21 13 13 21 5 13Z" fill="none" stroke="#f2f7f3" strokeWidth="1.6" />
          <path d="M13 9.5 16.5 13 13 16.5 9.5 13Z" fill="#c8364f" />
          <path d="M26 13 32 7 39 13 46 7 52 13M26 13 32 19 39 13 46 19 52 13" fill="none" stroke="#f2f7f3" strokeWidth="1.3" opacity="0.75" />
          <path d="M39 10.6 41.4 13 39 15.4 36.6 13Z" fill="#d9a441" />
        </pattern>
      </defs>
      <rect width="100%" height={height} fill={`url(#ch-${id})`} />
    </svg>
  )
}

/** Cargador: tres rombos que laten en secuencia. */
export function ChumbeLoader({ label, className = '' }: { label?: string; className?: string }) {
  return (
    <span role="status" className={`inline-flex items-center gap-2 text-ink-2 ${className}`}>
      <span className="inline-flex items-center gap-0.5 text-oro-fill" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span key={i} style={{ animation: `pulso-rombo 1.2s ${i * 0.18}s ease-in-out infinite`, display: 'inline-flex' }}>
            <Rombo size={11} />
          </span>
        ))}
      </span>
      {label ? <span className="text-sm">{label}</span> : <span className="sr-only">Cargando</span>}
    </span>
  )
}

/** Medidor de confianza: uno, dos o tres rombos llenos. */
export function ConfidenceRombos({ level, className = '' }: { level: 1 | 2 | 3; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-0.5 ${className}`} aria-hidden="true">
      {[1, 2, 3].map((i) => (
        <Rombo key={i} size={13} state={i <= level ? 'solid' : 'outline'} className={i <= level ? '' : 'opacity-50'} />
      ))}
    </span>
  )
}

/**
 * Las etapas del agente como una hilera de rombos unidos por un hilo. Es una
 * secuencia real (normalizar -> ... -> redactar), por eso lleva orden y rotulos.
 */
export function StageBand({
  stages,
  current,
  finished,
  failed,
}: {
  stages: Stage[]
  current: Stage | null
  finished: boolean
  failed: boolean
}) {
  const idx = current ? stages.indexOf(current) : -1
  return (
    <ol className="flex w-full items-start" aria-label="Etapas de la traducción">
      {stages.map((s, i) => {
        const done = finished || i < idx
        const isCurrent = !finished && i === idx
        const color = isCurrent ? (failed ? 'text-carmin' : 'text-oro-fill') : done ? 'text-forest' : 'text-line-strong'
        return (
          <li key={s} className="relative flex min-w-0 flex-1 flex-col items-center gap-1.5" aria-current={isCurrent ? 'step' : undefined}>
            {i > 0 && (
              <span
                aria-hidden="true"
                className={`absolute top-[8px] right-1/2 h-px w-full -translate-y-1/2 ${done || isCurrent ? 'bg-forest' : 'bg-line-strong'}`}
                style={{ transition: 'background-color .4s' }}
              />
            )}
            <span
              className={`relative z-10 inline-flex bg-surface px-1 ${color}`}
              style={isCurrent && !failed ? { animation: 'pulso-rombo 1.3s ease-in-out infinite' } : undefined}
            >
              <Rombo size={16} state={done ? 'solid' : isCurrent ? 'nested' : 'outline'} />
            </span>
            <span
              className={`max-w-full px-0.5 text-[0.72rem] leading-tight whitespace-nowrap sm:text-xs ${
                isCurrent ? 'font-semibold text-ink' : `hidden sm:block ${done ? 'text-ink-2' : 'text-ink-3'}`
              }`}
            >
              {STAGE[s]}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
