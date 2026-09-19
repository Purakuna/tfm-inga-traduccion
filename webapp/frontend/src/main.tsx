import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/alegreya/wght.css'
import '@fontsource-variable/alegreya/wght-italic.css'
import '@fontsource-variable/instrument-sans/wght.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
