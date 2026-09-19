// Datos del modo demostracion (VITE_MOCK=1). Son simulados: sirven para ensenar
// la interfaz sin backend, no son la wiki real ni citas verificadas.

import type {
  CorpusExample,
  Direccion,
  ExampleSentence,
  Fact,
  FactSection,
  FactSource,
  FeedbackRow,
  PageKind,
  ResolvedToken,
  ToolCallPayload,
  ToolResultPayload,
  WikiPage,
} from '../types'

let factSeq = 0x1a2b3c00
export function newFactId(): string {
  factSeq += 0x111
  return `f_${factSeq.toString(16).padStart(8, '0').slice(-8)}`
}

function fact(
  section: FactSection,
  text: string,
  sources: FactSource[],
  extra: Partial<Fact> = {},
): Fact {
  return {
    id: newFactId(),
    section,
    text,
    status: 'active',
    created_by: 'seed',
    created_at: '2026-09-19T09:12:00',
    sources,
    ...extra,
  }
}

const dic = (lema: string, quote: string): FactSource => ({ type: 'dictionary', ref: `lema:${lema}`, quote })
const gram = (ref: string, quote: string): FactSource => ({ type: 'grammar', ref, quote })
const corp = (ref: string, quote: string): FactSource => ({ type: 'corpus', ref, quote })

function page(
  kind: PageKind,
  slug: string,
  title: string,
  summary: string,
  facts: Fact[],
  aliases: string[] = [],
  version = 1,
): WikiPage {
  return {
    id: `${kind}:${slug}`,
    kind,
    slug,
    title,
    summary,
    status: 'active',
    version,
    updated_at: '2026-09-19T09:12:00',
    aliases,
    facts,
  }
}

function lemma(slug: string, cat: string, glosa: string, extraFacts: Fact[] = [], aliases: string[] = []): WikiPage {
  return page(
    'lemma',
    slug,
    slug,
    `${cat}: ${glosa}`,
    [fact('meaning', `${slug} (${cat}): ${glosa}.`, [dic(slug, `${slug} (${cat}): ${glosa}`)]), ...extraFacts],
    aliases,
  )
}

const tukuiOld = fact(
  'usage',
  'Como verbo, "tukui" solo significa terminar o acabarse.',
  [dic('tukui', 'tukui (v): terminar, acabar')],
  { status: 'superseded' },
)
const tukuiNew = fact(
  'usage',
  'Como verbo, "tukui" significa terminar y también volverse o llegar a ser: "sinchi tukui" es hacerse fuerte.',
  [
    dic('tukui', 'tukui (v): terminar, acabar; volverse, llegar a ser'),
    { type: 'feedback', ref: 'feedback:3', quote: 'En "sinchi tuku" no es terminar, es volverse fuerte.' },
  ],
  { created_by: 'feedback', created_at: '2026-09-19T10:41:00' },
)
tukuiOld.superseded_by = tukuiNew.id

export const PAGES: WikiPage[] = [
  lemma('achka', 'adj', 'mucho, bastante, harto', [
    fact('usage', 'Va antes del nombre o del verbo que cuantifica: "achka runakuna", mucha gente.', [
      corp('San Marcos 3:8', 'achka runakuna'),
    ]),
  ]),
  lemma(
    'iukai',
    'v',
    'tener, poseer',
    [
      fact('morphology', 'La raíz es "iuka-": los sufijos se añaden tras quitar la -i de la forma de cita (iuka-ngapa, iuka-ni).', [
        gram('levinsohn:L412-L431', 'La forma de cita del verbo termina en -i; los sufijos se unen a la raíz.'),
      ]),
      fact('note', 'En grafías de otras variedades quechuas aparece como "yukay"; aquí se normaliza y -> i.', [
        dic('iukai', 'iukai (v): tener'),
      ]),
    ],
    ['yukai', 'yukay'],
  ),
  lemma('sinchi', 'adj', 'fuerte, duro, recio', [
    fact('meaning', 'sinchi (s): en entradas que parten del español aparece bajo "brujo" junto a "millaipa iacha" y "samai pagta".', [
      dic('brujo', 'brujo (s): millaipa iacha, samai pagta, sinchi'),
    ]),
    fact(
      'usage',
      'Con "tukui" forma "sinchi tukui": fortalecerse, hacerse fuerte.',
      [{ type: 'feedback', ref: 'feedback:2', quote: 'sinchi tukui se dice cuando alguien se fortalece' }],
      { status: 'pending', created_by: 'feedback', created_at: '2026-09-19T10:20:00' },
    ),
  ]),
  page(
    'lemma',
    'tukui',
    'tukui',
    'adj: todo, todos. v: terminar; volverse, llegar a ser.',
    [
      fact('meaning', 'tukui (adj): todo, todos, entero.', [dic('tukui', 'tukui (adj): todo, todos')]),
      fact('meaning', 'tukui (v): terminar, acabarse; volverse, convertirse en.', [
        dic('tukui', 'tukui (v): terminar, acabar; volverse, llegar a ser'),
      ]),
      tukuiOld,
      tukuiNew,
      fact('note', 'La forma "tuku" sin sufijo es ambigua entre la raíz verbal y el adjetivo apocopado. El contexto decide.', [
        gram('levinsohn:L1804-L1822', 'La raíz desnuda del verbo aparece ante otro verbo en construcciones de cambio de estado.'),
      ]),
    ],
    ['tuku'],
    3,
  ),
  lemma(
    'iuiai',
    'v',
    'pensar, recordar, acordarse',
    [
      fact('meaning', 'iuiai (s): pensamiento, memoria, entendimiento.', [dic('iuiai', 'iuiai (s): pensamiento, memoria')]),
      fact('morphology', 'Raíz "iuia-": iuia-ngapa (para pensar), iuia-rii (acordarse).', [
        gram('levinsohn:L412-L431', 'La forma de cita del verbo termina en -i; los sufijos se unen a la raíz.'),
      ]),
    ],
    ['yuyai', 'yuyay'],
  ),
  lemma('wasi', 's', 'casa, vivienda', [], ['huasi']),
  lemma('iaku', 's', 'agua; río', [], ['yaku']),
  lemma('runa', 's', 'persona, gente; hombre'),
  lemma('alpa', 's', 'tierra, suelo, terreno', [], ['allpa']),
  lemma('atun', 'adj', 'grande', [], ['hatun', 'jatun']),
  lemma('suma', 'adj', 'bonito, bueno, agradable', [], ['sumaj']),
  lemma('mikui', 'v', 'comer', [fact('meaning', 'mikui (s): comida, alimento.', [dic('mikui', 'mikui (s): comida')])]),
  lemma('rimai', 'v', 'hablar, decir', [fact('meaning', 'rimai (s): palabra, habla, idioma.', [dic('rimai', 'rimai (s): palabra, idioma')])]),
  lemma('kawsai', 'v', 'vivir', [fact('meaning', 'kawsai (s): vida.', [dic('kawsai', 'kawsai (s): vida')])], ['kausai']),
  lemma('kai', 'v', 'ser, estar', [
    fact('note', 'Homógrafo de "kai" (dem): este, esta, esto.', [dic('kai', 'kai (dem): este, esta')]),
  ]),
  lemma('nukanchi', 'pron', 'nosotros', [], ['ñukanchi', 'nukanchi']),
  lemma('sacha', 's', 'monte, selva, bosque'),
  lemma('urku', 's', 'montaña, cerro', [], ['urcu']),
  lemma('tamia', 's', 'lluvia'),
  lemma('chagra', 's', 'chacra, huerta de cultivo', [], ['chakra']),
  lemma('iacha', 'adj', 'sabio, conocedor', [], ['yacha']),
  lemma('mana', 'adv', 'no (negación)'),
  lemma('samui', 'v', 'venir'),
  lemma('rii', 'v', 'ir'),
  page(
    'suffix',
    'ngapa',
    '-ngapa (propósito)',
    "Sufijo verbal de propósito: 'para + infinitivo'.",
    [
      fact('morphology', 'Se une a la raíz verbal: iuka-ngapa (para tener), miku-ngapa (para comer).', [
        gram('levinsohn:L1201-L1230', '-ngapa indica el propósito de la acción principal: mikungapa samurka, vino para comer.'),
      ]),
      fact('usage', 'La cláusula con -ngapa suele ir antes del verbo principal. El sujeto de ambas acciones es el mismo.', [
        gram('levinsohn:L1231-L1248', 'Cuando el sujeto es el mismo se usa -ngapa; con sujeto diferente, -chu.'),
      ]),
      fact('example', 'Mikungapa samurka. "Vino para comer."', [gram('levinsohn:L1205-L1206', 'Mikungapa samurka.')]),
    ],
    ['-ngapa', 'ngapa', '-ngapaj'],
    2,
  ),
  page(
    'suffix',
    'kuna',
    '-kuna (plural)',
    'Sufijo nominal de plural.',
    [
      fact('morphology', 'Se añade al nombre antes de los sufijos de caso: wasi-kuna-pi, en las casas.', [
        gram('levinsohn:L640-L655', 'El plural -kuna precede a los sufijos de caso.'),
      ]),
    ],
    ['-kuna', 'kuna', '-cuna'],
  ),
  page(
    'suffix',
    'ta',
    '-ta (objeto directo)',
    'Marca el objeto directo del verbo.',
    [
      fact('morphology', 'Se une al nombre o frase nominal que recibe la acción: iaku-ta upiani, bebo agua.', [
        gram('levinsohn:L702-L720', '-ta señala el complemento directo.'),
      ]),
    ],
    ['-ta', 'ta'],
  ),
  page(
    'suffix',
    'pi',
    '-pi (locativo)',
    "Sufijo de lugar: 'en'.",
    [fact('morphology', 'wasi-pi, en la casa; sacha-pi, en el monte.', [gram('levinsohn:L731-L744', '-pi indica el lugar donde ocurre la acción.')])],
    ['-pi', 'pi'],
  ),
  page(
    'suffix',
    'ka',
    '-ka (tópico)',
    'Marca el tema del que se habla.',
    [fact('usage', 'Destaca el tópico de la oración: wasi-ka atunmi, la casa (de la que hablamos) es grande.', [gram('rosetta:L210-L226', '-ka: marcador de tópico.')])],
    ['-ka', 'ka', '-ca'],
  ),
  page(
    'suffix',
    'mi',
    '-mi (afirmación directa)',
    'Evidencial: el hablante afirma lo que sabe de primera mano.',
    [fact('usage', 'Se une al elemento enfocado de la oración: atun-mi ka, es grande (lo afirmo).', [gram('rosetta:L230-L251', '-mi: evidencial directo, foco.')])],
    ['-mi', 'mi'],
  ),
  page(
    'grammar',
    'orden-sov',
    'Orden sujeto - objeto - verbo',
    'El verbo principal va al final de la oración.',
    [
      fact('usage', 'El orden básico es sujeto, objeto, verbo. Las cláusulas subordinadas preceden a la principal.', [
        gram('levinsohn:L120-L148', 'En inga el verbo ocupa normalmente la posición final.'),
      ]),
      fact('example', 'Nukanchi iakuta upianchi. "Nosotros bebemos agua."', [gram('levinsohn:L131-L132', 'Nukanchi iakuta upianchi.')]),
    ],
  ),
  page(
    'grammar',
    'clausulas-de-proposito',
    'Cláusulas de propósito',
    'Cómo se expresa "para + verbo" con -ngapa y -chu.',
    [
      fact('usage', 'Mismo sujeto: raíz + -ngapa. Sujeto distinto: raíz + -chu.', [
        gram('levinsohn:L1231-L1248', 'Cuando el sujeto es el mismo se usa -ngapa; con sujeto diferente, -chu.'),
      ]),
    ],
  ),
  page(
    'convention',
    'ortografia-y-i',
    'Ortografía: y se escribe i',
    'La wiki usa la ortografía del diccionario: "iukai", no "yukay".',
    [
      fact('note', 'Antes de buscar se normaliza y -> i ante vocal, qu/c -> k y hu -> w cuando el diccionario lo confirma.', [
        dic('iukai', 'iukai (v): tener'),
        dic('iuiai', 'iuiai (v): pensar, recordar'),
      ]),
    ],
  ),
  page(
    'case',
    'tuku-ambiguo',
    'Caso: "tuku" entre "todo" y "volverse"',
    'Decisión registrada tras una corrección sobre "sinchi tuku".',
    [
      fact(
        'note',
        'Ante adjetivo + "tuku" + verbo, preferir la lectura verbal "volverse" (sinchi tuku: hacerse fuerte).',
        [
          { type: 'feedback', ref: 'feedback:3', quote: 'En "sinchi tuku" no es terminar, es volverse fuerte.' },
          dic('tukui', 'tukui (v): terminar, acabar; volverse, llegar a ser'),
        ],
        { created_by: 'feedback', created_at: '2026-09-19T10:41:00' },
      ),
      fact(
        'note',
        '"tuku" al final de frase nominal se lee siempre como "todo".',
        [{ type: 'feedback', ref: 'feedback:5', quote: 'tuku siempre es todo' }],
        { status: 'rejected', created_by: 'feedback', created_at: '2026-09-19T11:02:00' },
      ),
    ],
  ),
]

export const EXAMPLES: ExampleSentence[] = [
  { direccion: 'inga2es', text: 'Achka yukangapa, sinchi tuku yuyangapa.', label: 'Propósito con -ngapa' },
  { direccion: 'inga2es', text: 'Nukanchi sachapi kawsanchi.', label: 'Locativo -pi' },
  { direccion: 'inga2es', text: 'Wasika atunmi ka.', label: 'Tópico y afirmación' },
  { direccion: 'inga2es', text: 'Runakuna mikungapa samurka.', label: 'Plural y propósito' },
  { direccion: 'es2inga', text: 'La casa es grande.', label: 'Oración con "ser"' },
  { direccion: 'es2inga', text: 'Nosotros vivimos en el monte.', label: 'Lugar' },
  { direccion: 'es2inga', text: 'La gente vino para comer.', label: 'Propósito' },
]

export interface Scenario {
  normalized: string
  tokens: ResolvedToken[]
  examples: CorpusExample[]
  translation: string
  alternatives: string[]
  confidence: 'low' | 'medium' | 'high'
  notes: string
  tools: { call: Omit<ToolCallPayload, 'id'>; result: Omit<ToolResultPayload, 'id' | 'name'> }[]
}

const tok = (token: string, normalized: string, lemmas: string[], suffixes: string[] = []): ResolvedToken => ({
  token,
  normalized,
  lemma_pages: lemmas,
  suffix_pages: suffixes,
  resolved: lemmas.length > 0,
})

const key = (direccion: Direccion, text: string) =>
  `${direccion}|${text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim()}`

const SCENARIOS: Record<string, Scenario> = {
  [key('inga2es', 'Achka yukangapa, sinchi tuku yuyangapa.')]: {
    normalized: 'achka iukangapa, sinchi tuku iuiangapa.',
    tokens: [
      tok('Achka', 'achka', ['lemma:achka']),
      tok('yukangapa', 'iukangapa', ['lemma:iukai'], ['suffix:ngapa']),
      tok('sinchi', 'sinchi', ['lemma:sinchi']),
      tok('tuku', 'tuku', ['lemma:tukui']),
      tok('yuyangapa', 'iuiangapa', ['lemma:iuiai'], ['suffix:ngapa']),
    ],
    examples: [
      { inga: 'Achka runakuna paita katirkakuna.', es: 'Mucha gente le seguía.', ref: 'San Marcos 3:7' },
      { inga: 'Sinchi tukuspa kawsaichi.', es: 'Vivid fortaleciéndoos.', ref: 'Efesios 6:10' },
      { inga: 'Kawsaita iukangapa samuichi.', es: 'Venid para tener vida.', ref: 'San Juan 5:40' },
    ],
    translation: 'Para tener mucho, hay que pensar en hacerse fuerte.',
    alternatives: ['Para tener bastante, hay que proponerse ser fuerte.', 'Para tener mucho, piensa en fortalecerte del todo.'],
    confidence: 'medium',
    notes:
      '"tuku" es ambiguo: puede ser la raíz de "tukui" (volverse, llegar a ser) o el adjetivo "tukui" (todo). Se eligió la lectura verbal porque va entre un adjetivo y un verbo (sinchi tuku: hacerse fuerte). No hay verbo principal conjugado, así que "hay que" es una inferencia.',
    tools: [
      {
        call: { name: 'wiki_leer', args: { page_id: 'lemma:tukui' } },
        result: { summary: 'tukui: 2 sentidos (adj "todo"; v "terminar, volverse") y una nota sobre la forma "tuku".', chars: 1184 },
      },
      {
        call: { name: 'corpus_buscar', args: { texto: 'sinchi tuku', direccion: 'inga2es', k: 3 } },
        result: { summary: '3 versículos con "sinchi tuku-"; en los tres se tradujo como fortalecerse.', chars: 612 },
      },
      {
        call: { name: 'documento_buscar', args: { consulta: '-ngapa', documento: 'gramatica' } },
        result: { summary: '4 coincidencias; L1201-L1230 describe -ngapa como propósito con el mismo sujeto.', chars: 2210 },
      },
    ],
  },
  [key('inga2es', 'Nukanchi sachapi kawsanchi.')]: {
    normalized: 'nukanchi sachapi kawsanchi.',
    tokens: [
      tok('Nukanchi', 'nukanchi', ['lemma:nukanchi']),
      tok('sachapi', 'sachapi', ['lemma:sacha'], ['suffix:pi']),
      tok('kawsanchi', 'kawsanchi', ['lemma:kawsai']),
    ],
    examples: [{ inga: 'Sachapi kawsarka.', es: 'Vivía en el monte.', ref: 'San Marcos 1:13' }],
    translation: 'Nosotros vivimos en el monte.',
    alternatives: ['Nosotros vivimos en la selva.'],
    confidence: 'high',
    notes: '"sacha" cubre monte, selva y bosque; se eligió "monte" por ser la glosa más frecuente en el diccionario.',
    tools: [
      {
        call: { name: 'wiki_leer', args: { page_id: 'suffix:pi' } },
        result: { summary: '-pi: locativo "en". Ejemplos wasipi, sachapi.', chars: 402 },
      },
    ],
  },
  [key('inga2es', 'Wasika atunmi ka.')]: {
    normalized: 'wasika atunmi ka.',
    tokens: [
      tok('Wasika', 'wasika', ['lemma:wasi'], ['suffix:ka']),
      tok('atunmi', 'atunmi', ['lemma:atun'], ['suffix:mi']),
      tok('ka', 'ka', ['lemma:kai']),
    ],
    examples: [{ inga: 'Chi wasika atunmi karka.', es: 'Aquella casa era grande.', ref: 'San Lucas 6:48' }],
    translation: 'La casa es grande.',
    alternatives: [],
    confidence: 'high',
    notes: '-ka marca el tópico y -mi la afirmación directa; ninguno se traduce con una palabra en español.',
    tools: [
      {
        call: { name: 'wiki_leer', args: { page_id: 'suffix:mi' } },
        result: { summary: '-mi: evidencial directo, se une al elemento enfocado.', chars: 388 },
      },
    ],
  },
  [key('inga2es', 'Runakuna mikungapa samurka.')]: {
    normalized: 'runakuna mikungapa samurka.',
    tokens: [
      tok('Runakuna', 'runakuna', ['lemma:runa'], ['suffix:kuna']),
      tok('mikungapa', 'mikungapa', ['lemma:mikui'], ['suffix:ngapa']),
      tok('samurka', 'samurka', ['lemma:samui']),
    ],
    examples: [{ inga: 'Achka runakuna samurkakuna.', es: 'Vino mucha gente.', ref: 'San Marcos 3:8' }],
    translation: 'La gente vino para comer.',
    alternatives: ['Las personas vinieron a comer.'],
    confidence: 'high',
    notes: 'El verbo está en singular (samurka) aunque el sujeto lleva -kuna; en el corpus es habitual.',
    tools: [
      {
        call: { name: 'wiki_leer', args: { page_id: 'suffix:ngapa' } },
        result: { summary: '-ngapa: propósito, mismo sujeto. Ejemplo idéntico: mikungapa samurka.', chars: 731 },
      },
    ],
  },
  [key('es2inga', 'La casa es grande.')]: {
    normalized: 'la casa es grande.',
    tokens: [
      { token: 'La', normalized: 'la', lemma_pages: [], suffix_pages: [], resolved: false },
      tok('casa', 'casa', ['lemma:wasi']),
      tok('es', 'es', ['lemma:kai']),
      tok('grande', 'grande', ['lemma:atun']),
    ],
    examples: [{ inga: 'Chi wasika atunmi karka.', es: 'Aquella casa era grande.', ref: 'San Lucas 6:48' }],
    translation: 'Wasika atunmi ka.',
    alternatives: ['Wasi atunmi.'],
    confidence: 'medium',
    notes: 'El artículo "la" no tiene equivalente; el tópico se marca con -ka. El verbo "ka" puede omitirse en presente.',
    tools: [
      {
        call: { name: 'buscar_por_glosa', args: { palabra_es: 'grande' } },
        result: { summary: '1 lema: atun (adj).', chars: 96 },
      },
      {
        call: { name: 'wiki_leer', args: { page_id: 'suffix:ka' } },
        result: { summary: '-ka: marcador de tópico.', chars: 310 },
      },
    ],
  },
  [key('es2inga', 'Nosotros vivimos en el monte.')]: {
    normalized: 'nosotros vivimos en el monte.',
    tokens: [
      tok('Nosotros', 'nosotros', ['lemma:nukanchi']),
      tok('vivimos', 'vivimos', ['lemma:kawsai']),
      { token: 'en', normalized: 'en', lemma_pages: [], suffix_pages: ['suffix:pi'], resolved: true },
      { token: 'el', normalized: 'el', lemma_pages: [], suffix_pages: [], resolved: false },
      tok('monte', 'monte', ['lemma:sacha', 'lemma:urku']),
    ],
    examples: [{ inga: 'Sachapi kawsarka.', es: 'Vivía en el monte.', ref: 'San Marcos 1:13' }],
    translation: 'Nukanchi sachapi kawsanchi.',
    alternatives: ['Nukanchi urkupi kawsanchi.'],
    confidence: 'medium',
    notes: '"monte" puede ser "sacha" (selva, monte con vegetación) o "urku" (cerro). Se eligió "sacha" por el ejemplo del corpus.',
    tools: [
      {
        call: { name: 'buscar_por_glosa', args: { palabra_es: 'monte' } },
        result: { summary: '2 lemas: sacha (s), urku (s).', chars: 164 },
      },
    ],
  },
  [key('es2inga', 'La gente vino para comer.')]: {
    normalized: 'la gente vino para comer.',
    tokens: [
      { token: 'La', normalized: 'la', lemma_pages: [], suffix_pages: [], resolved: false },
      tok('gente', 'gente', ['lemma:runa']),
      tok('vino', 'vino', ['lemma:samui']),
      { token: 'para', normalized: 'para', lemma_pages: [], suffix_pages: ['suffix:ngapa'], resolved: true },
      tok('comer', 'comer', ['lemma:mikui']),
    ],
    examples: [{ inga: 'Achka runakuna samurkakuna.', es: 'Vino mucha gente.', ref: 'San Marcos 3:8' }],
    translation: 'Runakuna mikungapa samurka.',
    alternatives: [],
    confidence: 'high',
    notes: 'La gramática trae el mismo ejemplo (mikungapa samurka).',
    tools: [
      {
        call: { name: 'documento_buscar', args: { consulta: 'para comer', documento: 'gramatica' } },
        result: { summary: '1 coincidencia en L1205: "Mikungapa samurka. Vino para comer."', chars: 540 },
      },
    ],
  },
}

const ES_STOP = new Set(['el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'y', 'a', 'que', 'en', 'se', 'lo', 'al'])

/** Escenario generico para textos que el mock no conoce. */
function genericScenario(direccion: Direccion, text: string): Scenario {
  const normalized = text
    .toLowerCase()
    .replace(/y(?=[aeiou])/g, direccion === 'inga2es' ? 'i' : 'y')
  const words = text.match(/[\p{L}']+/gu) ?? []
  const tokens: ResolvedToken[] = words.map((w) => {
    const n = w.toLowerCase().replace(/y(?=[aeiou])/g, direccion === 'inga2es' ? 'i' : 'y')
    if (direccion === 'es2inga') {
      if (ES_STOP.has(n)) return { token: w, normalized: n, lemma_pages: [], suffix_pages: [], resolved: false }
      const hit = PAGES.filter((p) => p.kind === 'lemma' && new RegExp(`\\b${n.replace(/s$/, '')}`, 'i').test(p.summary))
      return tok(w, n, hit.slice(0, 2).map((p) => p.id))
    }
    const lemmas = PAGES.filter((p) => p.kind === 'lemma')
      .filter((p) => {
        const stem = p.slug.replace(/a?i$/, (m) => (m === 'ai' ? 'a' : ''))
        return n === p.slug || (stem.length >= 3 && n.startsWith(stem)) || p.aliases.some((a) => n === a)
      })
      .sort((a, b) => b.slug.length - a.slug.length)
    const lemmaPage = lemmas[0]
    const suffixes: string[] = []
    if (lemmaPage) {
      const rest = n.slice(lemmaPage.slug.replace(/i$/, '').length)
      for (const s of PAGES.filter((p) => p.kind === 'suffix')) if (rest.includes(s.slug)) suffixes.push(s.id)
    }
    return tok(w, n, lemmaPage ? [lemmaPage.id] : [], suffixes)
  })
  const resolved = tokens.filter((t) => t.resolved).length
  return {
    normalized,
    tokens,
    examples: [],
    translation:
      direccion === 'inga2es'
        ? '(demostración) Esta frase no está entre los ejemplos simulados.'
        : '(demostración) Kai rimaika mana tiami.',
    alternatives: [],
    confidence: 'low',
    notes: `El modo demostración solo conoce las frases de ejemplo. Se resolvieron ${resolved} de ${tokens.length} palabras contra la wiki simulada; la traducción real la produce el backend.`,
    tools: [
      {
        call: { name: 'wiki_buscar', args: { consulta: words[0] ?? text.slice(0, 20), tipo: '' } },
        result: { summary: resolved > 0 ? `${resolved} páginas candidatas.` : 'Sin coincidencias en la wiki.', chars: 120 },
      },
    ],
  }
}

export function scenarioFor(direccion: Direccion, text: string): Scenario {
  return SCENARIOS[key(direccion, text)] ?? genericScenario(direccion, text)
}

// ---------- respuestas de "Pregunta por que" ----------

export function answerFor(question: string, scenario: Scenario | null): { text: string; cited: string[]; tool?: string } {
  const q = question.toLowerCase()
  if (scenario && /tuku/.test(q)) {
    return {
      text:
        'Elegí "hacerse fuerte" porque "tuku" va entre el adjetivo "sinchi" y el verbo "iuiangapa". La página lemma:tukui registra dos sentidos: adjetivo "todo" y verbo "terminar; volverse, llegar a ser". Su nota (levinsohn:L1804-L1822) dice que la raíz verbal desnuda aparece ante otro verbo en construcciones de cambio de estado, y el caso case:tuku-ambiguo recoge la misma decisión tras una corrección anterior.\n\nLo que no es seguro: si el hablante quiso decir "todo", la frase sería "pensar en todo lo fuerte", que me parece menos natural, pero no tengo un ejemplo del corpus que lo descarte. Por eso la confianza quedó en media y dejé la otra lectura como alternativa.',
      cited: ['lemma:tukui', 'case:tuku-ambiguo', 'lemma:sinchi'],
      tool: 'lemma:tukui',
    }
  }
  if (/ngapa|para/.test(q)) {
    return {
      text:
        'Las dos formas en -ngapa (iukangapa, iuiangapa) son cláusulas de propósito. La página suffix:ngapa cita levinsohn:L1201-L1230: "-ngapa indica el propósito de la acción principal", con el ejemplo "mikungapa samurka", vino para comer. Por eso traduje "para tener" y "pensar en" como finalidad.\n\nLa frase no tiene verbo principal conjugado. "Hay que" lo añadí para que el español se sostenga; es una inferencia mía, no algo que esté en la wiki.',
      cited: ['suffix:ngapa', 'grammar:clausulas-de-proposito'],
      tool: 'suffix:ngapa',
    }
  }
  if (/confianza|segur/.test(q)) {
    return {
      text:
        'La confianza refleja cuánto de la frase quedó respaldado por páginas con fuente. Aquí todas las palabras resolvieron a un lema, pero una de ellas tiene dos lecturas posibles y la oración no trae verbo conjugado. Con una ambigüedad abierta y una inferencia, no corresponde marcar confianza alta.',
      cited: scenario ? scenario.tokens.flatMap((t) => t.lemma_pages).slice(0, 2) : [],
    }
  }
  const first = scenario?.tokens.find((t) => t.resolved)
  return {
    text: `Me apoyé en las páginas que aparecen bajo cada palabra. ${
      first ? `Por ejemplo, "${first.token}" resolvió a ${first.lemma_pages[0] ?? first.suffix_pages[0]}, cuya definición viene del diccionario. ` : ''
    }Si preguntas por una palabra concreta puedo citar el hecho y la fuente exactos. En modo demostración las respuestas son simuladas.`,
    cited: first ? [...first.lemma_pages, ...first.suffix_pages] : [],
  }
}

// ---------- feedback sembrado ----------

const NOW = '2026-09-19T'

export const FEEDBACK_SEED: FeedbackRow[] = [
  {
    id: 1,
    created_at: `${NOW}09:48:00`,
    author: 'Hablante de Santiago',
    direccion: 'inga2es',
    source_text: 'Nukanchi sachapi kawsanchi.',
    model_output: 'Nosotros vivimos en el monte.',
    correction: 'Nosotros vivimos en la selva.',
    comment: 'Sacha es más selva que monte cuando se habla del bajo Putumayo.',
    translation_id: 'mock0001',
    status: 'pending_review',
    triage_json: {
      verdict: 'needs_review',
      rationale:
        'El diccionario da "monte, selva, bosque" sin orden de preferencia y el corpus de entrenamiento no distingue por región. La corrección es plausible pero depende de la variedad local, que ninguna fuente escrita confirma.',
      evidence: [
        { type: 'dictionary', ref: 'lema:sacha', quote: 'sacha (s): monte, selva, bosque' },
        { type: 'feedback', ref: 'feedback:1', quote: 'Sacha es más selva que monte cuando se habla del bajo Putumayo.' },
      ],
      actions: [{ op: 'add_fact', page_id: 'lemma:sacha' }],
    },
    reviewer: null,
    reviewed_at: null,
    review_note: null,
    facts: [
      {
        id: 'f_9a41c0d2',
        page_id: 'lemma:sacha',
        section: 'usage',
        text: 'En el bajo Putumayo "sacha" se entiende ante todo como selva; "monte" es la glosa general.',
        status: 'pending',
      },
    ],
  },
  {
    id: 2,
    created_at: `${NOW}10:20:00`,
    author: 'Hablante de San Andrés',
    direccion: 'inga2es',
    source_text: 'Sinchi tukui.',
    model_output: 'Todo fuerte.',
    correction: 'Fortalecerse.',
    comment: 'sinchi tukui se dice cuando alguien se fortalece',
    translation_id: null,
    status: 'pending_review',
    triage_json: JSON.stringify({
      verdict: 'needs_review',
      rationale:
        'El sentido verbal de "tukui" está en el diccionario, pero no encontré la combinación "sinchi tukui" como expresión fija en la gramática ni en versículos de entrenamiento que pueda volver a verificar. Queda pendiente de una persona.',
      evidence: [{ type: 'feedback', ref: 'feedback:2', quote: 'sinchi tukui se dice cuando alguien se fortalece' }],
      actions: [{ op: 'add_fact', page_id: 'lemma:sinchi' }],
    }),
    reviewer: null,
    reviewed_at: null,
    review_note: null,
    facts: [
      {
        id: 'f_77b0e3aa',
        page_id: 'lemma:sinchi',
        section: 'usage',
        text: 'Con "tukui" forma "sinchi tukui": fortalecerse, hacerse fuerte.',
        status: 'pending',
      },
    ],
  },
  {
    id: 3,
    created_at: `${NOW}10:41:00`,
    author: 'Docente de Yunguillo',
    direccion: 'inga2es',
    source_text: 'Achka yukangapa, sinchi tuku yuyangapa.',
    model_output: 'Para tener mucho, hay que pensar en terminar fuerte.',
    correction: 'Para tener mucho, hay que pensar en hacerse fuerte.',
    comment: 'En "sinchi tuku" no es terminar, es volverse fuerte.',
    translation_id: 'mock0003',
    status: 'auto_applied',
    triage_json: {
      verdict: 'supported',
      rationale:
        'El diccionario registra "volverse, llegar a ser" como sentido de tukui (v). La corrección coincide con una fuente que se pudo volver a verificar, así que se aplicó sin esperar revisión.',
      evidence: [
        { type: 'dictionary', ref: 'lema:tukui', quote: 'tukui (v): terminar, acabar; volverse, llegar a ser' },
        { type: 'feedback', ref: 'feedback:3', quote: 'En "sinchi tuku" no es terminar, es volverse fuerte.' },
      ],
      actions: [{ op: 'supersede_fact' }, { op: 'upsert_page' }],
    },
    reviewer: null,
    reviewed_at: null,
    review_note: null,
    facts: [
      { id: tukuiNew.id, page_id: 'lemma:tukui', section: 'usage', text: tukuiNew.text, status: 'active' },
    ],
  },
  {
    id: 4,
    created_at: `${NOW}08:30:00`,
    author: 'Hablante de Colón',
    direccion: 'es2inga',
    source_text: 'La casa es grande.',
    model_output: 'Wasi atun ka.',
    correction: 'Wasika atunmi ka.',
    comment: 'Falta -ka y -mi, así suena incompleto.',
    translation_id: null,
    status: 'approved',
    triage_json: {
      verdict: 'needs_review',
      rationale: 'Los sufijos -ka y -mi están documentados, pero su obligatoriedad en esta oración no se pudo verificar con una fuente.',
      evidence: [{ type: 'grammar', ref: 'rosetta:L210-L226', quote: '-ka: marcador de tópico.' }],
      actions: [],
    },
    reviewer: 'Revisora de Santiago',
    reviewed_at: `${NOW}09:05:00`,
    review_note: 'Confirmado con la gramática, sección de evidenciales.',
    facts: [
      {
        id: 'f_31c9d410',
        page_id: 'suffix:mi',
        section: 'usage',
        text: 'En oraciones con "kai" en presente, el atributo suele llevar -mi: atunmi ka.',
        status: 'active',
      },
    ],
  },
  {
    id: 5,
    created_at: `${NOW}11:02:00`,
    author: 'anónimo',
    direccion: 'inga2es',
    source_text: 'Sinchi tuku yuyangapa.',
    model_output: 'Pensar en hacerse fuerte.',
    correction: 'Pensar en todo fuerte.',
    comment: 'tuku siempre es todo',
    translation_id: null,
    status: 'rejected',
    triage_json: {
      verdict: 'contradicted',
      rationale: 'El diccionario registra también el sentido verbal de "tukui", de modo que "siempre es todo" contradice una fuente.',
      evidence: [{ type: 'dictionary', ref: 'lema:tukui', quote: 'tukui (v): terminar, acabar; volverse, llegar a ser' }],
      actions: [],
    },
    reviewer: 'Revisor de Colón',
    reviewed_at: `${NOW}11:30:00`,
    review_note: 'Contradice el diccionario.',
    facts: [
      {
        id: 'f_5e02aa19',
        page_id: 'case:tuku-ambiguo',
        section: 'note',
        text: '"tuku" al final de frase nominal se lee siempre como "todo".',
        status: 'rejected',
      },
    ],
  },
]
