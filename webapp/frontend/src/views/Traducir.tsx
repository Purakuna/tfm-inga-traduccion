import { Markdown } from '../components/Markdown'
import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowLeftRight, Check, Copy, CornerDownLeft, Square, Trash2, X } from 'lucide-react'
import { api } from '../api/client'
import type { Direccion, ExampleSentence, Mode, Stage } from '../api/types'
import { AskChat } from '../components/AskChat'
import { KindBadge } from '../components/Badges'
import { ChumbeBand, ChumbeLoader, ConfidenceRombos, Rombo, StageBand } from '../components/Chumbe'
import { CorrectionForm } from '../components/CorrectionForm'
import { ImageSlot } from '../components/ImageSlot'
import { usePageDrawer } from '../components/PageDrawer'
import { ErrorBlock } from '../components/States'
import { Timeline } from '../components/Timeline'
import { TokenLoom } from '../components/TokenLoom'
import { CONFIDENCE, DIRECCION, MODE, formatDate } from '../lib/labels'
import { readJson, useStored, writeJson } from '../lib/storage'
import { useTranslate, type Snapshot } from '../lib/useTranslate'

const HISTORY_KEY = 'inga.historial'
const HISTORY_MAX = 20
const MAX_CHARS = 600

interface HistoryEntry extends Snapshot {
  at: string
}

const STAGES_AGENT: Stage[] = ['normalize', 'navigate', 'retrieve', 'think', 'tool', 'write']
const STAGES_FAST: Stage[] = ['normalize', 'navigate', 'retrieve', 'think', 'write']

const CONF_TONE = { low: 'text-carmin', medium: 'text-oro', high: 'text-forest' } as const

export default function Traducir() {
  const [direccion, setDireccion] = useStored<Direccion>('inga.direccion', 'inga2es')
  const [mode, setMode] = useStored<Mode>('inga.modo.v2', 'fast')
  const [text, setText] = useState('')
  const [examples, setExamples] = useState<ExampleSentence[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>(() => readJson<HistoryEntry[]>(HISTORY_KEY, []))
  const [copied, setCopied] = useState(false)
  const [tab, setTab] = useState<'ask' | 'fix'>('ask')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const loomRef = useRef<HTMLElement>(null)

  const onFinished = useCallback((snap: Snapshot) => {
    setHistory((h) => {
      const next = [{ ...snap, at: new Date().toISOString() }, ...h.filter((e) => e.result.translation_id !== snap.result.translation_id)].slice(0, HISTORY_MAX)
      writeJson(HISTORY_KEY, next)
      return next
    })
  }, [])

  const { state, start, stop, reset, restore } = useTranslate(onFinished)
  const running = state.phase === 'running'
  const result = state.result
  const shown = state.request

  useEffect(() => {
    const ctrl = new AbortController()
    api
      .examples(ctrl.signal)
      .then((xs) => Array.isArray(xs) && setExamples(xs))
      .catch(() => undefined) // los ejemplos son un atajo; sin ellos la vista sigue completa
    return () => ctrl.abort()
  }, [])

  const translate = (override?: { text: string; direccion: Direccion }) => {
    const t = (override?.text ?? text).trim()
    if (!t || running) return
    setCopied(false)
    setTab('ask')
    start({ text: t, direccion: override?.direccion ?? direccion, mode })
    if (window.matchMedia('(max-width: 1023px)').matches) {
      requestAnimationFrame(() => loomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
    }
  }

  const swap = () => {
    if (running) return
    const next: Direccion = direccion === 'inga2es' ? 'es2inga' : 'inga2es'
    setDireccion(next)
    if (result && shown && shown.text.trim() === text.trim()) setText(result.translation)
    reset()
    inputRef.current?.focus()
  }

  const copy = async () => {
    if (!result) return
    try {
      await navigator.clipboard.writeText(result.translation)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* portapapeles no disponible */
    }
  }

  const pickExample = (ex: ExampleSentence) => {
    if (running) return
    setDireccion(ex.direccion)
    setText(ex.text)
    translate({ text: ex.text, direccion: ex.direccion })
  }

  const openHistory = (e: HistoryEntry) => {
    setDireccion(e.request.direccion)
    setText(e.request.text)
    restore(e)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const clearHistory = () => {
    setHistory([])
    writeJson(HISTORY_KEY, [])
  }

  const srcInga = direccion === 'inga2es'
  const viewDir = shown?.direccion ?? direccion
  const stages = (shown?.mode ?? mode) === 'agent' ? STAGES_AGENT : STAGES_FAST
  const visibleExamples = examples.filter((e) => e.direccion === direccion)
  const active = state.phase !== 'idle'

  return (
    <>
      <ImageSlot name="hero" className="h-[21rem] sm:h-[25rem]">
        <div className="absolute inset-0" style={{ background: 'var(--hero-veil)' }} />
        <div className="relative mx-auto flex h-full w-full max-w-[76rem] flex-col justify-center px-4 pt-4 pb-20 text-[#f2f7f3] sm:px-6 sm:pb-24">
          <h1 className="max-w-[18ch] text-[2.5rem] leading-[1.02] font-extrabold sm:text-6xl">Del inga al español, con el camino a la vista</h1>
          <p className="mt-4 max-w-[54ch] text-[1.05rem] leading-snug text-[#dbe7df] sm:text-lg">
            Un agente busca cada palabra en una wiki con fuentes citadas y te muestra qué leyó, qué consultó y por qué tradujo así.
          </p>
        </div>
      </ImageSlot>

      <div className="mx-auto w-full max-w-[76rem] px-4 sm:px-6">
        {/* ---------- traductor ---------- */}
        <section aria-label="Traductor" className="panel relative -mt-14 overflow-hidden sm:-mt-16">
          <div className="grid lg:grid-cols-2">
            {/* origen */}
            <div className="flex min-h-[15rem] flex-col p-4 transition-shadow focus-within:shadow-[inset_0_-3px_0_var(--oro-fill)] sm:p-6">
              <div className="flex items-center justify-between gap-2">
                <label htmlFor="src" className="font-display text-lg font-bold">
                  {DIRECCION[direccion].from}
                </label>
                <button type="button" onClick={swap} disabled={running} className="btn btn-quiet btn-sm" aria-label={`Invertir: traducir de ${DIRECCION[direccion].to} a ${DIRECCION[direccion].from}`}>
                  <ArrowLeftRight className="size-4" aria-hidden="true" />
                  <span className="hidden xs:inline">Invertir</span>
                </button>
              </div>
              <textarea
                id="src"
                ref={inputRef}
                value={text}
                maxLength={MAX_CHARS}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault()
                    translate()
                  }
                }}
                lang={srcInga ? 'inb' : 'es'}
                spellCheck={!srcInga}
                autoCapitalize="sentences"
                placeholder={srcInga ? 'Escribe una frase en inga' : 'Escribe una frase en español'}
                className={`mt-3 min-h-28 w-full flex-1 resize-none bg-transparent leading-tight outline-none placeholder:text-ink-3 ${
                  srcInga ? 'inga text-[1.75rem] sm:text-[2.1rem]' : 'font-display text-[1.6rem] sm:text-[1.9rem]'
                }`}
              />
              <div className="mt-2 flex items-center justify-between text-xs text-ink-3">
                <span className="tabular-nums">
                  {text.length} / {MAX_CHARS}
                </span>
                {text && !running && (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded px-1.5 py-1 font-semibold text-ink-2 hover:text-ink"
                    onClick={() => {
                      setText('')
                      reset()
                      inputRef.current?.focus()
                    }}
                  >
                    <X className="size-3.5" aria-hidden="true" />
                    Borrar
                  </button>
                )}
              </div>
            </div>

            {/* destino */}
            <div className="flex min-h-[15rem] flex-col border-t border-line bg-surface-2/60 p-4 sm:p-6 lg:border-t-0 lg:border-l" aria-live="polite">
              <div className="flex items-center justify-between gap-2">
                <p className="font-display text-lg font-bold">{DIRECCION[viewDir].to}</p>
                {result && (
                  <button type="button" onClick={copy} className="btn btn-quiet btn-sm">
                    {copied ? <Check className="size-4 text-forest" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
                    {copied ? 'Copiada' : 'Copiar'}
                  </button>
                )}
              </div>

              <div className="mt-3 flex-1">
                {result ? (
                  <motion.div key={result.translation_id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
                    <p className={`leading-tight ${viewDir === 'es2inga' ? 'inga text-[1.75rem] sm:text-[2.1rem]' : 'font-display text-[1.6rem] font-medium sm:text-[1.9rem]'}`} lang={viewDir === 'es2inga' ? 'inb' : 'es'}>
                      {result.translation}
                    </p>
                    <p className={`mt-4 inline-flex items-center gap-2 text-sm font-semibold ${CONF_TONE[result.confidence] ?? 'text-ink-2'}`}>
                      <ConfidenceRombos level={CONFIDENCE[result.confidence]?.level ?? 1} />
                      {CONFIDENCE[result.confidence]?.label ?? result.confidence}
                      <span className="font-normal text-ink-3">
                        {MODE[result.mode]?.label ?? result.mode}
                        {typeof result.elapsed_s === 'number' && `, ${result.elapsed_s.toLocaleString('es-CO', { maximumFractionDigits: 1 })} s`}
                      </span>
                    </p>
                  </motion.div>
                ) : running ? (
                  <div>
                    <div className="space-y-3" aria-hidden="true">
                      <div className="h-7 w-11/12 animate-pulse rounded bg-line/70" />
                      <div className="h-7 w-7/12 animate-pulse rounded bg-line/70" />
                    </div>
                    <ChumbeLoader className="mt-5" label={lastStatus(state.log)} />
                  </div>
                ) : state.phase === 'error' ? (
                  <ErrorBlock title="No se pudo traducir" message={state.error ?? 'Error desconocido.'} onRetry={() => shown && start(shown)} />
                ) : state.phase === 'stopped' ? (
                  <p className="text-ink-2">Traducción detenida.</p>
                ) : (
                  <p className="max-w-[40ch] text-ink-3">La traducción aparece aquí, con su nivel de confianza, alternativas y las dudas del agente.</p>
                )}
              </div>
            </div>
          </div>

          {/* notas y alternativas */}
          <AnimatePresence initial={false}>
            {result && (result.notes || result.alternatives.length > 0) && (
              <motion.div
                key={result.translation_id}
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden border-t border-line"
              >
                <div className="grid gap-6 p-4 sm:p-6 lg:grid-cols-2">
                  {result.notes && (
                    <div>
                      <h2 className="text-lg">Dudas y decisiones</h2>
                      <Markdown text={result.notes} className="mt-1.5 max-w-[66ch] text-[0.97rem] leading-relaxed text-ink-2" />
                    </div>
                  )}
                  {result.alternatives.length > 0 && (
                    <div>
                      <h2 className="text-lg">Alternativas</h2>
                      <ul className="mt-1.5 space-y-1.5">
                        {result.alternatives.map((a) => (
                          <li key={a} className="flex gap-2.5">
                            <Rombo size={9} className="mt-[0.55em] shrink-0 text-line-strong" />
                            <span className={viewDir === 'es2inga' ? 'inga text-xl' : 'font-display text-[1.15rem] leading-snug'}>{a}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* controles */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-line bg-surface px-4 py-3 sm:px-6">
            <div className="seg" role="group" aria-label="Modo de traducción">
              {(['fast', 'agent'] as Mode[]).map((m) => (
                <button key={m} type="button" aria-pressed={mode === m} disabled={running} onClick={() => setMode(m)}>
                  {mode === m && <motion.span layoutId="seg-mode" className="absolute inset-0 rounded-[7px] border border-line bg-surface shadow-sm" transition={{ type: 'spring', duration: 0.35 }} />}
                  <span className="relative">{MODE[m].label}</span>
                </button>
              ))}
            </div>
            <p className="order-last w-full text-sm text-ink-2 md:order-none md:w-auto md:flex-1">{MODE[mode].hint}</p>
            <div className="ml-auto flex items-center gap-2">
              {running ? (
                <button type="button" onClick={stop} className="btn btn-quiet">
                  <Square className="size-4" aria-hidden="true" />
                  Detener
                </button>
              ) : (
                <button type="button" onClick={() => translate()} disabled={!text.trim()} className="btn btn-primary">
                  Traducir
                  <kbd className="hidden items-center gap-0.5 rounded border border-on-primary/30 px-1 py-0.5 text-[0.7rem] font-medium opacity-80 md:inline-flex">
                    Ctrl <CornerDownLeft className="size-3" aria-hidden="true" />
                  </kbd>
                </button>
              )}
            </div>
          </div>
        </section>

        {/* ---------- ejemplos ---------- */}
        {visibleExamples.length > 0 && (
          <section className="mt-5" aria-labelledby="ej-title">
            <h2 id="ej-title" className="sr-only">
              Frases de ejemplo
            </h2>
            <ul className="flex flex-wrap items-center gap-2">
              <li className="mr-1 text-sm text-ink-2">Prueba con</li>
              {visibleExamples.map((ex) => (
                <li key={ex.text}>
                  <button
                    type="button"
                    disabled={running}
                    onClick={() => pickExample(ex)}
                    title={ex.label}
                    className="rounded-lg border border-line-strong bg-surface px-3 py-1.5 text-left transition-colors hover:border-ink-3 hover:bg-surface-2 disabled:opacity-50"
                  >
                    <span className={ex.direccion === 'inga2es' ? 'inga text-[1.1rem]' : 'text-[0.95rem]'}>{ex.text}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ---------- el telar ---------- */}
        <section ref={loomRef} aria-labelledby="telar-title" className="panel mt-8 scroll-mt-20 overflow-hidden">
          <div className="flex flex-col gap-4 border-b border-line p-4 sm:p-6 lg:flex-row lg:items-center lg:gap-10">
            <div className="shrink-0">
              <h2 id="telar-title" className="text-2xl">
                Cómo se tejió
              </h2>
              <p className="mt-1 text-sm text-ink-2">
                {state.restored
                  ? 'Traducción guardada en este navegador.'
                  : running
                    ? 'El agente está trabajando.'
                    : state.phase === 'error'
                      ? 'El proceso se interrumpió.'
                      : state.phase === 'stopped'
                        ? 'Detenido antes de terminar.'
                        : active
                          ? 'Pulsa una página para leerla.'
                          : 'Palabra por palabra, página por página.'}
              </p>
            </div>
            {active && !state.restored && (
              <div className="min-w-0 flex-1">
                <StageBand stages={stages} current={state.stage} finished={state.phase === 'done'} failed={state.phase === 'error' || state.phase === 'stopped'} />
              </div>
            )}
          </div>

          {!active || !shown ? (
            <div className="grid items-center gap-6 p-4 sm:p-6 md:grid-cols-[1fr_auto]">
              <div className="max-w-[60ch] text-ink-2">
                <p>
                  Al traducir, la frase se separa en palabras. Cada una baja por un hilo hasta las páginas de la wiki que la explican: su <KindBadge kind="lemma" /> del
                  diccionario y los <KindBadge kind="suffix" /> que lleva pegados. Debajo verás la bitácora del agente y todo lo que leyó.
                </p>
              </div>
              <IdleLoom />
            </div>
          ) : (
            <>
              <div className="p-4 sm:p-6">
                {!state.navigation && !running ? (
                  <p className="text-sm text-ink-2">No se llegó a separar la frase en palabras. Vuelve a intentarlo desde el traductor.</p>
                ) : (
                  <TokenLoom sourceText={shown.text} direccion={shown.direccion} navigation={state.navigation} usedPages={result?.used_pages ?? []} animate={!state.restored} />
                )}
                {result && result.used_pages.length > 0 && state.navigation && (
                  <p className="mt-4 flex items-center gap-2 text-xs text-ink-3">
                    <span aria-hidden="true" className="size-1.5 rotate-45 bg-oro-fill" />
                    El rombo dorado marca las páginas que el modelo dijo haber usado.
                  </p>
                )}
              </div>

              <div className="grid border-t border-line lg:grid-cols-2">
                <div className="p-4 sm:p-6">
                  <h3 className="text-xl">Bitácora del agente</h3>
                  <div className="mt-4">
                    {state.restored ? (
                      <p className="text-sm text-ink-2">La bitácora en vivo no se guarda en el historial. Vuelve a traducir la frase para verla de nuevo.</p>
                    ) : state.log.length === 0 ? (
                      <ChumbeLoader label="Conectando con el agente" />
                    ) : (
                      <Timeline log={state.log} running={running} />
                    )}
                  </div>
                </div>
                <div className="border-t border-line p-4 sm:p-6 lg:border-t-0 lg:border-l">
                  <h3 className="text-xl">Lo que leyó</h3>
                  <ReadingList pages={state.pages} examples={state.examples} running={running} usedPages={result?.used_pages ?? []} />
                </div>
              </div>
            </>
          )}
        </section>

        {/* ---------- preguntar / corregir ---------- */}
        {result && shown && (
          <motion.section
            key={result.translation_id}
            initial={state.restored ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25, duration: 0.4 }}
            className="panel mt-8 overflow-hidden"
            aria-label="Preguntar o corregir"
          >
            <div className="flex items-center gap-3 border-b border-line px-4 pt-3 sm:px-6" role="tablist" aria-label="Qué hacer con esta traducción">
              {(
                [
                  ['ask', 'Pregunta por qué'],
                  ['fix', 'Sugerir corrección'],
                ] as const
              ).map(([k, label]) => (
                <button
                  key={k}
                  type="button"
                  role="tab"
                  id={`tab-${k}`}
                  aria-selected={tab === k}
                  aria-controls={`panel-${k}`}
                  onClick={() => setTab(k)}
                  className={`relative -mb-px px-1 pt-1 pb-3 font-display text-[1.05rem] font-bold whitespace-nowrap transition-colors sm:text-xl ${tab === k ? 'text-ink' : 'text-ink-3 hover:text-ink-2'}`}
                >
                  {label}
                  {tab === k && <motion.span layoutId="tab-line" className="absolute inset-x-0 bottom-0 h-[3px] bg-carmin" />}
                </button>
              ))}
            </div>
            <div className="p-4 sm:p-6">
              <div role="tabpanel" id="panel-ask" aria-labelledby="tab-ask" hidden={tab !== 'ask'}>
                <AskChat key={result.translation_id} translationId={result.translation_id} tokens={state.navigation?.tokens ?? []} notes={result.notes ?? ''} />
              </div>
              <div role="tabpanel" id="panel-fix" aria-labelledby="tab-fix" hidden={tab !== 'fix'} className="max-w-2xl">
                <CorrectionForm key={result.translation_id} translationId={result.translation_id} direccion={shown.direccion} sourceText={shown.text} modelOutput={result.translation} />
              </div>
            </div>
          </motion.section>
        )}

        {/* ---------- historial ---------- */}
        {history.length > 0 && (
          <section className="mt-12" aria-labelledby="hist-title">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h2 id="hist-title" className="text-2xl">
                  Traducciones recientes
                </h2>
                <p className="text-sm text-ink-2">Se guardan solo en este navegador.</p>
              </div>
              <button type="button" onClick={clearHistory} className="btn btn-quiet btn-sm">
                <Trash2 className="size-4" aria-hidden="true" />
                Vaciar
              </button>
            </div>
            <ul className="mt-4 divide-y divide-line border-y border-line">
              {history.map((e) => {
                const fromInga = e.request.direccion === 'inga2es'
                return (
                  <li key={e.result.translation_id}>
                    <button type="button" onClick={() => openHistory(e)} className="grid w-full gap-x-6 gap-y-0.5 px-1 py-3 text-left transition-colors hover:bg-surface sm:grid-cols-[1fr_1fr_auto] sm:items-baseline">
                      <span className={`truncate ${fromInga ? 'inga text-xl' : 'text-[0.98rem]'}`}>{e.request.text}</span>
                      <span className={`truncate text-ink-2 ${fromInga ? 'text-[0.98rem]' : 'inga text-xl'}`}>{e.result.translation}</span>
                      <span className="flex items-center gap-2 text-xs whitespace-nowrap text-ink-3">
                        <ConfidenceRombos level={CONFIDENCE[e.result.confidence]?.level ?? 1} className={CONF_TONE[e.result.confidence]} />
                        {formatDate(e.at)}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
        )}
      </div>
    </>
  )
}

function lastStatus(log: ReturnType<typeof useTranslate>['state']['log']): string {
  const s = log.findLast((l) => l.kind === 'status')
  return s && s.kind === 'status' && s.message ? s.message : 'Trabajando'
}

/** Telar en reposo: un dibujo de hilos y rombos, sin datos. */
function IdleLoom() {
  return (
    <div className="hidden w-64 md:block" aria-hidden="true">
      <div className="flex justify-between px-3">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="flex flex-col items-center">
            <span className="h-2 w-8 rounded-sm bg-line-strong/70" />
            <span className="h-8 w-px bg-line-strong" />
            <Rombo size={14} state={i % 2 ? 'outline' : 'nested'} className={i % 2 ? 'text-line-strong' : 'text-oro-fill'} />
          </div>
        ))}
      </div>
      <ChumbeBand className="mt-3 rounded-sm opacity-90" height={26} />
    </div>
  )
}

function ReadingList({
  pages,
  examples,
  running,
  usedPages,
}: {
  pages: Snapshot['pages']
  examples: Snapshot['examples']
  running: boolean
  usedPages: string[]
}) {
  const { open } = usePageDrawer()
  const used = new Set(usedPages)
  if (pages.length === 0 && examples.length === 0) {
    return <div className="mt-4">{running ? <ChumbeLoader label="Todavía no ha cargado páginas" /> : <p className="text-sm text-ink-2">No se cargó ninguna página ni ejemplo.</p>}</div>
  }
  return (
    <div className="mt-4 space-y-6">
      {pages.length > 0 && (
        <ul className="grid gap-2 sm:grid-cols-2">
          <AnimatePresence initial={false}>
            {pages.map((p, i) => (
              <motion.li key={p.id} initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07, duration: 0.3 }}>
                <button
                  type="button"
                  onClick={() => open(p.id)}
                  className="group flex h-full w-full flex-col rounded-lg border border-line bg-bg/50 p-3 text-left transition-colors hover:border-line-strong hover:bg-surface-2"
                >
                  <span className="flex items-center justify-between gap-2">
                    <KindBadge kind={p.kind} />
                    {used.has(p.id) && <span title="Usada en la traducción" className="size-2 rotate-45 bg-oro-fill" />}
                  </span>
                  <span className={`mt-2 text-xl leading-tight ${p.kind === 'lemma' || p.kind === 'suffix' ? 'inga font-bold' : 'font-display font-bold'}`}>{p.title}</span>
                  <span className="mt-1 line-clamp-2 text-sm text-ink-2">{p.summary}</span>
                </button>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
      {examples.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-ink-2">Ejemplos parecidos del corpus de entrenamiento</h4>
          <ul className="mt-2 space-y-3">
            {examples.map((ex, i) => (
              <motion.li key={`${ex.ref}-${i}`} initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.09, duration: 0.3 }} className="border-l-2 border-arcilla/60 pl-3">
                <p className="inga text-[1.2rem] leading-snug" lang="inb">
                  {ex.inga}
                </p>
                <p className="text-[0.95rem] text-ink-2">{ex.es}</p>
                <p className="text-xs text-ink-3">{ex.ref}</p>
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
