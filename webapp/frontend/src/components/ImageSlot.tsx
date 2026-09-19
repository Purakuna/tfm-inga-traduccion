import { useEffect, useState } from 'react'

type Name = 'hero' | 'montana' | 'selva' | 'paramo'

/**
 * Hueco de imagen con respaldo disenado. El degradado (clase img-fallback-*)
 * siempre esta debajo; la foto entra con un fundido si carga y se retira si
 * falla, asi que el hueco nunca queda roto ni vacio.
 */
export function ImageSlot({
  name,
  alt = '',
  className = '',
  imgClassName = '',
  children,
}: {
  name: Name
  alt?: string
  className?: string
  imgClassName?: string
  children?: React.ReactNode
}) {
  const [state, setState] = useState<'loading' | 'ok' | 'missing'>('loading')
  return (
    <div className={`relative isolate overflow-hidden img-fallback-${name} ${className}`}>
      <FallbackWeave />
      {state !== 'missing' && (
        <img
          src={`/img/${name}.jpg`}
          alt={alt}
          decoding="async"
          onLoad={() => setState('ok')}
          onError={() => setState('missing')}
          className={`absolute inset-0 -z-0 h-full w-full object-cover transition-opacity duration-700 ${
            state === 'ok' ? 'opacity-100' : 'opacity-0'
          } ${imgClassName}`}
        />
      )}
      {children}
    </div>
  )
}

/** Trama muy tenue de rombos sobre el degradado, para que el respaldo no sea plano. */
function FallbackWeave() {
  return (
    <svg aria-hidden="true" className="absolute inset-0 -z-0 h-full w-full opacity-[0.13]">
      <defs>
        <pattern id="fb-weave" width="44" height="44" patternUnits="userSpaceOnUse">
          <path d="M22 4 40 22 22 40 4 22Z" fill="none" stroke="#fff" strokeWidth="1" />
          <path d="M22 14 30 22 22 30 14 22Z" fill="none" stroke="#fff" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#fb-weave)" />
    </svg>
  )
}

/** Comprueba si un recurso de /img existe (para patron-chumbe.png como textura). */
export function useImageOk(src: string): boolean {
  const [ok, setOk] = useState(false)
  useEffect(() => {
    let alive = true
    const img = new Image()
    img.onload = () => alive && setOk(true)
    img.onerror = () => alive && setOk(false)
    img.src = src
    return () => {
      alive = false
    }
  }, [src])
  return ok
}
