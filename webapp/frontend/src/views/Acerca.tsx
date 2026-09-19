import { Link } from 'react-router-dom'
import { ChumbeBand } from '../components/Chumbe'
import { ImageSlot } from '../components/ImageSlot'

const FUENTES = [
  {
    nombre: 'Diccionario inga',
    uso: 'Unas 4.900 entradas con lema, categoría y glosa. De aquí sale una página por cada lema inga.',
    cita: 'lema:sinchi',
  },
  {
    nombre: 'Gramática pedagógica de Levinsohn',
    uso: 'La base de las páginas de sufijos y de gramática. Cada hecho apunta al rango de líneas del texto digitalizado, junto con un apéndice morfosintáctico.',
    cita: 'levinsohn:L1201-L1230',
  },
  {
    nombre: 'Nuevo Testamento en inga, alineado con la Reina-Valera 1909',
    uso: 'Corpus paralelo versículo a versículo. Solo la parte de entrenamiento alimenta los ejemplos; las frases de validación y prueba nunca entran a la wiki.',
    cita: 'San Juan 3:16',
  },
  {
    nombre: 'Constitución Política de Colombia de 1991',
    uso: 'Texto paralelo de dominio jurídico, el único material del corpus que no es bíblico.',
    cita: '',
  },
]

export default function Acerca() {
  return (
    <div>
      <ImageSlot name="montana" className="h-56 sm:h-72">
        <div className="absolute inset-0" style={{ background: 'var(--hero-veil)' }} />
        <div className="relative mx-auto flex h-full w-full max-w-[60rem] items-end px-4 pb-8 sm:px-6">
          <h1 className="max-w-[20ch] text-4xl font-extrabold text-[#f2f7f3] sm:text-6xl">Un traductor que enseña sus fuentes</h1>
        </div>
      </ImageSlot>
      <ChumbeBand />

      <div className="mx-auto w-full max-w-[60rem] px-4 sm:px-6">
        <section className="mt-10 max-w-[66ch] space-y-4 text-[1.08rem] leading-relaxed">
          <p>
            El inga es una lengua quechua que hablan unas 18.000 personas, sobre todo en el Putumayo, en el piedemonte entre los Andes y la Amazonía colombiana. Casi no
            existen datos digitales en inga, y los traductores automáticos comerciales no lo cubren.
          </p>
          <p>
            Este proyecto prueba otra vía: en lugar de entrenar un modelo con millones de frases que no existen, se organiza lo poco que hay en una wiki donde cada hecho cita
            su fuente. Un agente lee esa wiki con herramientas, traduce y deja a la vista el camino que siguió. Cuando alguien lo corrige, investiga la corrección: si una
            fuente escrita la respalda, la aplica; si no, la deja en una{' '}
            <Link to="/revision" className="link">
              cola de revisión
            </Link>{' '}
            para que decida una persona.
          </p>
        </section>

        <section className="mt-14" aria-labelledby="fuentes">
          <h2 id="fuentes" className="text-3xl">
            Las fuentes
          </h2>
          <ul className="mt-5 grid gap-x-10 gap-y-7 md:grid-cols-2">
            {FUENTES.map((f) => (
              <li key={f.nombre} className="border-t-2 border-primary pt-3">
                <h3 className="text-xl">{f.nombre}</h3>
                <p className="mt-1.5 text-ink-2">{f.uso}</p>
                {f.cita && (
                  <p className="mt-2 text-sm text-ink-3">
                    Se cita como <span className="code text-ink-2">{f.cita}</span>
                  </p>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-6 max-w-[66ch] text-ink-2">
            Las correcciones de hablantes son la quinta fuente. Se citan como <span className="code">feedback:12</span> y siempre quedan a la vista junto al hecho que
            cambiaron.
          </p>
        </section>

        <section className="mt-14 grid gap-8 md:grid-cols-[1fr_18rem] md:items-start" aria-labelledby="limites">
          <div>
            <h2 id="limites" className="text-3xl">
              Los límites
            </h2>
            <ul className="mt-5 max-w-[66ch] space-y-4 text-[1.02rem] leading-relaxed">
              <li>
                <strong>Casi todo el corpus es bíblico.</strong> El sistema conoce mejor el vocabulario y el estilo del Nuevo Testamento que el habla de todos los días. Una
                frase cotidiana puede salir con un tono que no le corresponde.
              </li>
              <li>
                <strong>Las traducciones pueden estar mal.</strong> El nivel de confianza y las notas del agente son una orientación, no una garantía. No lo uses para nada
                que importe sin consultar a un hablante.
              </li>
              <li>
                <strong>La ortografía varía.</strong> La wiki sigue la del diccionario (iukai, no yukay). El sistema normaliza algunas grafías, pero no todas las que se usan
                en las comunidades.
              </li>
              <li>
                <strong>Lo que lo mejora son las correcciones de hablantes.</strong> El modelo de lenguaje no aprendió inga por su cuenta: solo sabe lo que está en la wiki, y la wiki viene de libros. Cada corrección revisada queda en la wiki con su
                origen, y es la única forma de que el sistema aprenda lo que no está en los libros.
              </li>
            </ul>
          </div>
          <ImageSlot name="paramo" className="h-56 rounded-xl md:h-80" />
        </section>
      </div>
    </div>
  )
}
