import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'
const KEY = 'inga.tema'

function current(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(current)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    const meta = document.querySelector('meta[name="theme-color"]')
    meta?.setAttribute('content', theme === 'dark' ? '#0b1712' : '#e4ebe5')
  }, [theme])

  const toggle = useCallback(() => {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark'
      try {
        localStorage.setItem(KEY, next)
      } catch {
        /* almacenamiento no disponible */
      }
      return next
    })
  }, [])

  return [theme, toggle]
}
