import type { FeedbackFact, FeedbackRow, TriageRecord } from '../api/types'

/** triage_json puede llegar como texto o como objeto, o no llegar. */
export function triageOf(row: FeedbackRow): TriageRecord | null {
  const raw = row.triage_json ?? (row as unknown as { triage?: unknown }).triage
  if (!raw) return null
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw) as unknown
      return parsed && typeof parsed === 'object' ? (parsed as TriageRecord) : null
    } catch {
      return null
    }
  }
  return typeof raw === 'object' ? (raw as TriageRecord) : null
}

export function factKey(f: FeedbackFact, i: number): string {
  return f.fact_id ?? f.id ?? `${f.page_id}-${i}`
}
