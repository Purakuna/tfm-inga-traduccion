import type { Confidence, Direccion, FactSection, FactStatus, FeedbackStatus, Mode, PageKind, SourceType, Stage, Verdict } from '../api/types'

export const DIRECCION: Record<Direccion, { from: string; to: string }> = {
  inga2es: { from: 'Inga', to: 'Español' },
  es2inga: { from: 'Español', to: 'Inga' },
}

export const MODE: Record<Mode, { label: string; hint: string }> = {
  fast: { label: 'Rápido', hint: 'Una sola llamada con las páginas que resolvió cada palabra.' },
  agent: { label: 'Agente', hint: 'El agente consulta la wiki, el corpus y los documentos todas las veces que necesite antes de responder.' },
}

export const KIND: Record<PageKind, { one: string; many: string }> = {
  lemma: { one: 'Lema', many: 'Lemas' },
  suffix: { one: 'Sufijo', many: 'Sufijos' },
  grammar: { one: 'Gramática', many: 'Gramática' },
  convention: { one: 'Convención', many: 'Convenciones' },
  case: { one: 'Caso', many: 'Casos' },
}
export const KINDS = Object.keys(KIND) as PageKind[]

export const SECTION: Record<FactSection, string> = {
  meaning: 'Significado',
  morphology: 'Morfología',
  usage: 'Uso',
  example: 'Ejemplos',
  note: 'Notas',
}
export const SECTIONS = Object.keys(SECTION) as FactSection[]

export const FACT_STATUS: Record<FactStatus, string> = {
  active: 'Activo',
  pending: 'Pendiente',
  superseded: 'Reemplazado',
  rejected: 'Rechazado',
}

export const SOURCE: Record<SourceType, string> = {
  dictionary: 'Diccionario',
  grammar: 'Gramática',
  corpus: 'Corpus',
  feedback: 'Corrección',
}

export const STAGE: Record<Stage, string> = {
  normalize: 'Normalizar',
  navigate: 'Navegar',
  retrieve: 'Recuperar',
  think: 'Pensar',
  tool: 'Consultar',
  write: 'Redactar',
}

export const CONFIDENCE: Record<Confidence, { label: string; level: 1 | 2 | 3 }> = {
  low: { label: 'Confianza baja', level: 1 },
  medium: { label: 'Confianza media', level: 2 },
  high: { label: 'Confianza alta', level: 3 },
}

export const VERDICT: Record<Verdict, string> = {
  supported: 'Respaldada por las fuentes',
  needs_review: 'Necesita revisión humana',
  contradicted: 'Contradice una fuente',
}

export const FEEDBACK_STATUS: Record<FeedbackStatus, string> = {
  new: 'Sin analizar',
  auto_applied: 'Aplicada automáticamente',
  pending_review: 'Pendiente de revisión',
  approved: 'Aprobada',
  rejected: 'Rechazada',
}

export const TOOL: Record<string, string> = {
  wiki_leer: 'Leer página de la wiki',
  wiki_buscar: 'Buscar en la wiki',
  buscar_por_glosa: 'Buscar por glosa en español',
  corpus_buscar: 'Buscar ejemplos en el corpus',
  documento_buscar: 'Buscar en un documento fuente',
  documento_leer: 'Leer un documento fuente',
}

export function splitPageId(id: string): { kind: string; slug: string } {
  const i = id.indexOf(':')
  return i === -1 ? { kind: '', slug: id } : { kind: id.slice(0, i), slug: id.slice(i + 1) }
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso.includes('T') || iso.includes(' ') ? iso.replace(' ', 'T') : iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('es-CO', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
