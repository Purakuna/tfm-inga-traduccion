// Bitacora en vivo: estados, navegacion y cada llamada del agente a sus herramientas.

import { AnimatePresence, motion } from 'motion/react'
import { Check, TriangleAlert } from 'lucide-react'
import type { LogItem } from '../lib/useTranslate'
import { STAGE, TOOL } from '../lib/labels'
import { ChumbeLoader, Rombo } from './Chumbe'

function formatArgs(args: Record<string, unknown>): string {
  return Object.entries(args ?? {})
    .map(([k, v]) => `${k}=${typeof v === 'string' ? `"${v}"` : JSON.stringify(v)}`)
    .join(', ')
}

export function ToolCallLine({ name, args }: { name: string; args: Record<string, unknown> }) {
  return (
    <span className="code break-words text-ink">
      <span className="font-medium text-rio">{name}</span>
      <span className="text-ink-3">(</span>
      {formatArgs(args)}
      <span className="text-ink-3">)</span>
    </span>
  )
}

function Marker({ item, live }: { item: LogItem; live: boolean }) {
  if (item.kind === 'error') return <TriangleAlert className="size-4 text-carmin" aria-hidden="true" />
  if (item.kind === 'result') return <Check className="size-4 text-forest" aria-hidden="true" />
  if (item.kind === 'tool') return <Rombo size={14} state="nested" className={item.result ? 'text-rio' : 'text-oro-fill'} />
  return <Rombo size={12} state={live ? 'nested' : 'solid'} className={live ? 'text-oro-fill' : 'text-forest'} />
}

function Body({ item }: { item: LogItem }) {
  switch (item.kind) {
    case 'status':
      return (
        <p>
          <span className="font-semibold">{STAGE[item.stage] ?? item.stage}.</span> <span className="text-ink-2">{item.message}</span>
        </p>
      )
    case 'navigation':
      return (
        <p>
          <span className="font-semibold">
            {item.resolved} de {item.total} palabras
          </span>{' '}
          <span className="text-ink-2">encontraron página en la wiki.</span>
        </p>
      )
    case 'pages':
      return (
        <p>
          <span className="font-semibold">{item.count} {item.count === 1 ? 'página cargada' : 'páginas cargadas'}</span>{' '}
          <span className="text-ink-2">en el contexto del modelo.</span>
        </p>
      )
    case 'examples':
      return (
        <p>
          <span className="font-semibold">{item.count} {item.count === 1 ? 'ejemplo' : 'ejemplos'} del corpus</span>{' '}
          <span className="text-ink-2">{item.count === 0 ? 'parecidos a la frase.' : 'parecidos a la frase, solo del conjunto de entrenamiento.'}</span>
        </p>
      )
    case 'tool':
      return (
        <div>
          <p className="text-sm text-ink-2">{TOOL[item.call.name] ?? 'Herramienta'}</p>
          <p className="mt-0.5">
            <ToolCallLine name={item.call.name} args={item.call.args} />
          </p>
          <div className="mt-1.5 min-h-6 border-l-2 border-line-strong pl-3 text-sm">
            {item.result ? (
              <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-ink-2">
                {item.result.summary}{' '}
                {typeof item.result.chars === 'number' && <span className="whitespace-nowrap text-ink-3">{item.result.chars.toLocaleString('es-CO')} caracteres</span>}
              </motion.p>
            ) : (
              <ChumbeLoader label="Esperando el resultado" />
            )}
          </div>
        </div>
      )
    case 'result':
      return (
        <p>
          <span className="font-semibold">Traducción lista</span> <span className="text-ink-2">en {item.elapsed.toLocaleString('es-CO', { maximumFractionDigits: 1 })} s.</span>
        </p>
      )
    case 'error':
      return (
        <p className="text-carmin">
          <span className="font-semibold">Error.</span> {item.message}
        </p>
      )
  }
}

export function Timeline({ log: fullLog, running }: { log: LogItem[]; running: boolean }) {
  // El estado "tool" solo anuncia la llamada que viene justo despues; la llamada ya lo cuenta.
  const log = fullLog.filter((l) => !(l.kind === 'status' && l.stage === 'tool'))
  return (
    <ol className="relative" aria-live="polite" aria-label="Bitácora del agente">
      <span aria-hidden="true" className="absolute top-2 bottom-2 left-[7px] w-px bg-line-strong" />
      <AnimatePresence initial={false}>
        {log.map((item, i) => {
          const live = running && i === log.length - 1
          return (
            <motion.li
              key={item.key}
              layout="position"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.28 }}
              className="relative flex gap-3 pb-4 last:pb-0"
            >
              <span className="relative z-10 mt-[3px] flex size-[15px] shrink-0 items-center justify-center bg-surface">
                <Marker item={item} live={live} />
              </span>
              <div className="min-w-0 flex-1 text-[0.95rem] leading-snug">
                <Body item={item} />
              </div>
              <span className="mt-0.5 shrink-0 text-xs text-ink-3 tabular-nums">{item.t.toFixed(1)} s</span>
            </motion.li>
          )
        })}
      </AnimatePresence>
    </ol>
  )
}
