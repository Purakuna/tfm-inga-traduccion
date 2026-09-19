// El telar: la frase separada en palabras; cada palabra baja por un hilo hasta
// las paginas de la wiki que la explican (lema + sufijos).

import { motion } from 'motion/react'
import type { Direccion, NavigationPayload, ResolvedToken } from '../api/types'
import { PageChip } from './Badges'

const STEP = 0.24

export function TokenLoom({
  sourceText,
  direccion,
  navigation,
  usedPages,
  animate,
}: {
  sourceText: string
  direccion: Direccion
  navigation: NavigationPayload | null
  usedPages: string[]
  animate: boolean
}) {
  const inga = direccion === 'inga2es'
  if (!navigation) {
    const words = sourceText.split(/\s+/).filter(Boolean).slice(0, 40)
    return (
      <div className="flex flex-wrap gap-x-5 gap-y-6" aria-hidden="true">
        {words.map((w, i) => (
          <div key={i} className="flex flex-col items-center">
            <span className={`${inga ? 'inga' : 'font-display'} text-[1.7rem] leading-none text-ink-3 sm:text-[2.1rem]`}>{w}</span>
            <span className="mt-2 h-7 w-px bg-line-strong" style={{ animation: `pulso-rombo 1.4s ${i * 0.12}s ease-in-out infinite` }} />
          </div>
        ))}
      </div>
    )
  }

  const used = new Set(usedPages)
  const changed = navigation.normalized && navigation.normalized.trim().toLowerCase() !== sourceText.trim().toLowerCase()

  return (
    <div>
      <ul className="flex flex-wrap items-start gap-x-4 gap-y-7 sm:gap-x-6">
        {navigation.tokens.map((t, i) => (
          <Token key={`${t.token}-${i}`} token={t} index={i} inga={inga} used={used} animate={animate} />
        ))}
      </ul>
      {changed && (
        <motion.p
          className="mt-6 border-t border-line pt-3 text-sm text-ink-2"
          initial={animate ? { opacity: 0 } : false}
          animate={{ opacity: 1 }}
          transition={{ delay: animate ? navigation.tokens.length * STEP : 0 }}
        >
          Ortografía normalizada para buscar en la wiki:{' '}
          <span className={`${inga ? 'inga italic' : ''} text-base text-ink`}>{navigation.normalized}</span>
        </motion.p>
      )}
    </div>
  )
}

function Token({ token, index, inga, used, animate }: { token: ResolvedToken; index: number; inga: boolean; used: Set<string>; animate: boolean }) {
  const delay = animate ? index * STEP : 0
  const lemmas = token.lemma_pages ?? []
  const suffixes = token.suffix_pages ?? []
  const pagesCount = lemmas.length + suffixes.length
  const respelled = token.normalized && token.normalized !== token.token.toLowerCase()

  return (
    <li className="flex min-w-0 flex-col items-center">
      <motion.span
        className={`${inga ? 'inga' : 'font-display font-medium'} text-[1.7rem] leading-none sm:text-[2.1rem]`}
        initial={animate ? { opacity: 0.3 } : false}
        animate={{ opacity: 1 }}
        transition={{ delay, duration: 0.35 }}
      >
        {token.token}
      </motion.span>

      {/* hilo */}
      <motion.span
        aria-hidden="true"
        className={`mt-2 w-px origin-top ${pagesCount ? 'h-7 bg-oro-fill' : 'h-7 border-l border-dashed border-line-strong'}`}
        initial={animate ? { scaleY: 0 } : false}
        animate={{ scaleY: 1 }}
        transition={{ delay: delay + 0.1, duration: 0.3, ease: 'easeOut' }}
      />

      <motion.div
        className="flex flex-col items-center gap-1"
        initial={animate ? { opacity: 0, y: -8 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: delay + 0.3, duration: 0.3 }}
      >
        {respelled && <span className={`${inga ? 'inga italic' : ''} text-sm leading-none text-ink-2`}>{token.normalized}</span>}
        {pagesCount > 0 ? (
          <span className="flex items-center justify-center gap-1 whitespace-nowrap">
            {lemmas.map((id) => (
              <PageChip key={id} id={id} marked={used.has(id)} />
            ))}
            {suffixes.map((id) => (
              <span key={id} className="inline-flex items-center gap-1">
                {lemmas.length > 0 && <span className="text-xs text-ink-3" aria-hidden="true">+</span>}
                <PageChip id={id} marked={used.has(id)} />
              </span>
            ))}
          </span>
        ) : (
          <span className="rounded-[5px] border border-dashed border-line-strong px-1.5 py-1 text-xs leading-none text-ink-3">
            {token.resolved ? 'resuelta' : 'sin página'}
          </span>
        )}
      </motion.div>
    </li>
  )
}
