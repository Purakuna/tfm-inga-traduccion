// Markdown minimo para las respuestas del agente. Sin dependencias ni HTML crudo: todo
// se arma como nodos de React, asi que el texto del modelo nunca se inyecta como marcado.
// Cubre lo que el agente escribe de verdad: parrafos, listas, titulos, negrita, cursiva,
// codigo en linea y citas de pagina como [lemma:sinchi], que se vuelven chips que abren la pagina.
import type { ReactNode } from 'react'
import { PageChip } from './Badges'

const PAGE_KINDS = 'lemma|suffix|grammar|convention|case'
const INLINE = new RegExp(
  [
    '(\\*\\*[^*\\n]+?\\*\\*)', // negrita
    '(`[^`\\n]+?`)', // codigo
    `(\\[(?:${PAGE_KINDS}):[^\\]\\s]+\\])`, // cita de pagina
    '(\\*[^*\\s][^*\\n]*?\\*)', // cursiva
  ].join('|'),
  'g',
)

function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let n = 0
  for (const m of text.matchAll(INLINE)) {
    const i = m.index ?? 0
    if (i > last) out.push(text.slice(last, i))
    const tok = m[0]
    const key = `${keyBase}-${n++}`
    if (tok.startsWith('**')) out.push(<strong key={key} className="font-semibold text-ink">{inline(tok.slice(2, -2), key)}</strong>)
    else if (tok.startsWith('`')) out.push(<code key={key} className="inga rounded-[4px] bg-ink/[0.07] px-1 py-px text-[1.02em] dark:bg-white/[0.09]">{tok.slice(1, -1)}</code>)
    else if (tok.startsWith('[')) out.push(<PageChip key={key} id={tok.slice(1, -1)} className="mx-0.5 align-baseline text-[0.82em]" />)
    else out.push(<em key={key}>{inline(tok.slice(1, -1), key)}</em>)
    last = i + tok.length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

type Block =
  | { type: 'p'; lines: string[] }
  | { type: 'h'; level: number; text: string }
  | { type: 'ul' | 'ol'; items: string[] }

function parse(src: string): Block[] {
  const blocks: Block[] = []
  let cur: Block | null = null
  const flush = () => {
    if (cur) blocks.push(cur)
    cur = null
  }
  for (const raw of src.replace(/\r\n/g, '\n').split('\n')) {
    const line = raw.trimEnd()
    if (!line.trim()) {
      flush()
      continue
    }
    const h = /^(#{1,4})\s+(.*)$/.exec(line)
    const ul = /^\s*[-*•]\s+(.*)$/.exec(line)
    const ol = /^\s*\d+[.)]\s+(.*)$/.exec(line)
    if (h) {
      flush()
      blocks.push({ type: 'h', level: h[1].length, text: h[2] })
    } else if (ul || ol) {
      const type = ul ? 'ul' : 'ol'
      if (!cur || cur.type !== type) {
        flush()
        cur = { type, items: [] }
      }
      ;(cur as { items: string[] }).items.push((ul ?? ol)![1])
    } else if (cur && (cur.type === 'ul' || cur.type === 'ol') && /^\s{2,}\S/.test(raw)) {
      // linea de continuacion de un item de lista
      cur.items[cur.items.length - 1] += ' ' + line.trim()
    } else {
      if (!cur || cur.type !== 'p') {
        flush()
        cur = { type: 'p', lines: [] }
      }
      ;(cur as { lines: string[] }).lines.push(line.trim())
    }
  }
  flush()
  return blocks
}

export function Markdown({ text, className = '', tail }: { text: string; className?: string; tail?: ReactNode }) {
  const blocks = parse(text)
  return (
    <div className={`space-y-2.5 ${className}`}>
      {blocks.map((b, i) => {
        const last = i === blocks.length - 1
        const end = last ? tail : null
        if (b.type === 'h') {
          return (
            <p key={i} className="display pt-1 text-[1.08rem] font-semibold text-ink">
              {inline(b.text, `h${i}`)}
              {end}
            </p>
          )
        }
        if ('items' in b) {
          const List = b.type
          return (
            <List key={i} className={`space-y-1.5 pl-5 ${b.type === 'ul' ? 'list-disc' : 'list-decimal'} marker:text-ink-3`}>
              {b.items.map((it, j) => (
                <li key={j} className="pl-1">
                  {inline(it, `l${i}-${j}`)}
                  {j === b.items.length - 1 ? end : null}
                </li>
              ))}
            </List>
          )
        }
        return (
          <p key={i}>
            {b.lines.map((l, j) => (
              <span key={j}>
                {j > 0 && <br />}
                {inline(l, `p${i}-${j}`)}
              </span>
            ))}
            {end}
          </p>
        )
      })}
    </div>
  )
}
