import { useCallback, useState } from 'react'

export function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

export function writeJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* modo privado o cuota llena: la app sigue funcionando sin persistir */
  }
}

/** Estado que se recuerda en este navegador (nombre del revisor, autor, etc). */
export function useStored<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => readJson(key, initial))
  const set = useCallback(
    (v: T) => {
      setValue(v)
      writeJson(key, v)
    },
    [key],
  )
  return [value, set]
}
