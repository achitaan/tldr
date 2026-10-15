import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import 'katex/dist/katex.min.css'

const DesignGallery = lazy(() => import('./design-gallery/DesignGallery'))

const root = document.getElementById('root')
if (!root) throw new Error('App root was not found.')

createRoot(root).render(
  <StrictMode>
    {new URLSearchParams(window.location.search).get('designs') === '1'
      ? <Suspense fallback={<div role="status">Loading design gallery…</div>}><DesignGallery /></Suspense>
      : <App />}
  </StrictMode>,
)
