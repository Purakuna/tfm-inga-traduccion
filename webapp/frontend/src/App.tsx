import { lazy, Suspense } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { MotionConfig } from 'motion/react'
import { Layout } from './components/Layout'
import { PageDrawerProvider } from './components/PageDrawer'
import { EmptyBlock, LoadingBlock } from './components/States'
import Traducir from './views/Traducir'

const Wiki = lazy(() => import('./views/Wiki'))
const Revision = lazy(() => import('./views/Revision'))
const Acerca = lazy(() => import('./views/Acerca'))

function NotFound() {
  return (
    <div className="mx-auto max-w-[40rem] px-4 pt-16">
      <div className="panel">
        <EmptyBlock title="Esta dirección no lleva a ninguna parte" action={<Link to="/" className="btn btn-primary">Ir al traductor</Link>}>
          La página que buscas no existe o cambió de lugar.
        </EmptyBlock>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <PageDrawerProvider>
          <Suspense fallback={<LoadingBlock className="min-h-[60dvh]" />}>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<Traducir />} />
                <Route path="wiki" element={<Wiki />} />
                <Route path="wiki/:pageId" element={<Wiki />} />
                <Route path="revision" element={<Revision />} />
                <Route path="acerca" element={<Acerca />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </Suspense>
        </PageDrawerProvider>
      </BrowserRouter>
    </MotionConfig>
  )
}
