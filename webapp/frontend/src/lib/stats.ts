import type { WikiStats } from '../api/types'

type Counts = Record<string, number>

function asCounts(v: unknown): Counts | null {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return null
  const out: Counts = {}
  for (const [k, n] of Object.entries(v as Record<string, unknown>)) if (typeof n === 'number') out[k] = n
  return Object.keys(out).length ? out : null
}

function pick(stats: WikiStats, needle: string): Counts | null {
  for (const [k, v] of Object.entries(stats)) {
    if (k.toLowerCase().includes(needle)) {
      const c = asCounts(v)
      if (c) return c
    }
  }
  return null
}

/** El contrato no fija las claves de stats(); se buscan por nombre aproximado. */
export function readStats(stats: WikiStats | null | undefined) {
  if (!stats) return { pages: null, facts: null, feedback: null, totalPages: null as number | null }
  const pages = pick(stats, 'page')
  const facts = pick(stats, 'fact')
  const feedback = pick(stats, 'feedback')
  let totalPages: number | null = pages ? Object.values(pages).reduce((a, b) => a + b, 0) : null
  for (const [k, v] of Object.entries(stats)) {
    if (typeof v === 'number' && k.toLowerCase().includes('page')) totalPages = v
  }
  return { pages, facts, feedback, totalPages }
}
