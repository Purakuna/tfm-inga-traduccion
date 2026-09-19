// Tipos de la API HTTP. Reflejan la seccion 5 del contrato
// docs/superpowers/specs/2026-09-19-inga-wiki-agent-design.md (y las formas de
// datos de las secciones 2 y 3 que la API devuelve tal cual).

export type Direccion = 'inga2es' | 'es2inga'
export type Mode = 'fast' | 'agent'
export type Confidence = 'low' | 'medium' | 'high'

export type PageKind = 'lemma' | 'suffix' | 'grammar' | 'convention' | 'case'
export type PageStatus = 'active' | 'superseded'
export type FactSection = 'meaning' | 'morphology' | 'usage' | 'example' | 'note'
export type FactStatus = 'active' | 'pending' | 'superseded' | 'rejected'
export type SourceType = 'dictionary' | 'grammar' | 'corpus' | 'feedback'
export type FeedbackStatus = 'new' | 'auto_applied' | 'pending_review' | 'approved' | 'rejected'
export type Verdict = 'supported' | 'needs_review' | 'contradicted'
export type Stage = 'normalize' | 'navigate' | 'retrieve' | 'think' | 'tool' | 'write'

// ---------- wiki ----------

export interface FactSource {
  type: SourceType
  ref: string
  quote: string
}

export interface Fact {
  id: string
  section: FactSection
  text: string
  status: FactStatus
  created_by: string
  created_at: string
  superseded_by?: string | null
  sources: FactSource[]
}

export interface WikiPage {
  id: string
  kind: PageKind
  slug: string
  title: string
  summary: string
  status: PageStatus
  version: number
  updated_at: string
  aliases: string[]
  facts: Fact[]
}

export interface PageSummary {
  id: string
  kind: PageKind
  title: string
  summary: string
  n_facts?: number
}

export interface PageList {
  items: PageSummary[]
  total: number
}

// stats(): "pages per kind, facts per status, feedback per status". El contrato
// no fija las claves, asi que se lee de forma tolerante (ver lib/stats.ts).
export type WikiStats = Record<string, unknown>

export interface Health {
  ok: boolean
  model: string
  wiki: WikiStats
}

export interface ExampleSentence {
  direccion: Direccion
  text: string
  label: string
}

// ---------- cuerpos de peticion ----------

export interface TranslateBody {
  text: string
  direccion: Direccion
  mode: Mode
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface AskBody {
  translation_id: string
  question: string
  history: ChatTurn[]
}

export interface FeedbackBody {
  translation_id?: string
  direccion: Direccion
  source_text: string
  model_output: string
  correction: string
  comment: string
  author: string
}

export interface ReviewBody {
  decision: 'approve' | 'reject'
  reviewer: string
  note: string
}

// ---------- eventos SSE ----------

export interface StatusPayload {
  stage: Stage
  message: string
}

export interface ResolvedToken {
  token: string
  normalized: string
  lemma_pages: string[]
  suffix_pages: string[]
  resolved: boolean
}

export interface NavigationPayload {
  normalized: string
  tokens: ResolvedToken[]
}

export interface PageRef {
  id: string
  kind: PageKind
  title: string
  summary: string
}

export interface PagesPayload {
  pages: PageRef[]
}

export interface CorpusExample {
  inga: string
  es: string
  ref: string
}

export interface ExamplesPayload {
  examples: CorpusExample[]
}

export interface ToolCallPayload {
  id: number
  name: string
  args: Record<string, unknown>
}

export interface ToolResultPayload {
  id: number
  name: string
  summary: string
  chars: number
}

export interface ResultPayload {
  translation_id: string
  translation: string
  alternatives: string[]
  confidence: Confidence
  notes: string
  used_pages: string[]
  mode: Mode
  elapsed_s: number
}

export interface AnswerDeltaPayload {
  text: string
}

export interface AnswerPayload {
  text: string
  cited_pages: string[]
}

export interface TriageFact {
  fact_id: string
  page_id: string
  text: string
  status: FactStatus
}

export interface TriagePayload {
  feedback_id: number
  verdict: Verdict
  status: 'auto_applied' | 'pending_review'
  rationale: string
  evidence: FactSource[]
  facts: TriageFact[]
}

export interface ErrorPayload {
  message: string
}

export type SseEvent =
  | { type: 'status'; data: StatusPayload }
  | { type: 'navigation'; data: NavigationPayload }
  | { type: 'pages'; data: PagesPayload }
  | { type: 'examples'; data: ExamplesPayload }
  | { type: 'tool_call'; data: ToolCallPayload }
  | { type: 'tool_result'; data: ToolResultPayload }
  | { type: 'result'; data: ResultPayload }
  | { type: 'answer_delta'; data: AnswerDeltaPayload }
  | { type: 'answer'; data: AnswerPayload }
  | { type: 'triage'; data: TriagePayload }
  | { type: 'error'; data: ErrorPayload }
  | { type: 'done'; data: Record<string, never> }

export type SseEventType = SseEvent['type']

// ---------- feedback ----------

// triage_json guarda lo que devolvio el agente (seccion 4). Puede llegar como
// texto JSON o ya como objeto; lib/feedback.ts lo lee de las dos maneras.
export interface TriageRecord {
  verdict?: Verdict
  rationale?: string
  evidence?: FactSource[]
  actions?: unknown[]
  status?: 'auto_applied' | 'pending_review'
}

// En GET /api/feedback los facts vienen del store ("id") con su page_id; en el
// evento triage vienen como "fact_id". Se aceptan ambos nombres.
export interface FeedbackFact {
  id?: string
  fact_id?: string
  page_id: string
  text: string
  status: FactStatus
  section?: FactSection
}

export interface FeedbackRow {
  id: number
  created_at: string
  author: string
  direccion: Direccion
  source_text: string
  model_output: string
  correction: string
  comment: string
  translation_id: string | null
  status: FeedbackStatus
  triage_json: string | TriageRecord | null
  reviewer: string | null
  reviewed_at: string | null
  review_note: string | null
  facts?: FeedbackFact[]
}
