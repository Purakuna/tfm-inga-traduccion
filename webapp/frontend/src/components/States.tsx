import { RotateCw, TriangleAlert } from 'lucide-react'
import { ChumbeLoader, Rombo } from './Chumbe'

export function LoadingBlock({ label = 'Cargando', className = '' }: { label?: string; className?: string }) {
  return (
    <div className={`flex min-h-40 items-center justify-center ${className}`}>
      <ChumbeLoader label={label} />
    </div>
  )
}

export function ErrorBlock({
  title = 'No se pudo cargar',
  message,
  onRetry,
  className = '',
}: {
  title?: string
  message: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <div role="alert" className={`rounded-xl border border-carmin/40 bg-carmin-soft p-4 text-ink ${className}`}>
      <div className="flex items-start gap-3">
        <TriangleAlert className="mt-0.5 size-5 shrink-0 text-carmin" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{title}</p>
          <p className="mt-0.5 text-sm text-ink-2 break-words">{message}</p>
          {onRetry && (
            <button type="button" onClick={onRetry} className="btn btn-quiet btn-sm mt-3">
              <RotateCw className="size-4" aria-hidden="true" />
              Reintentar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function EmptyBlock({
  title,
  children,
  action,
  className = '',
}: {
  title: string
  children?: React.ReactNode
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={`flex flex-col items-center px-6 py-12 text-center ${className}`}>
      <span className="flex items-center gap-1 text-line-strong" aria-hidden="true">
        <Rombo size={10} state="outline" />
        <Rombo size={18} state="nested" className="text-oro-fill" />
        <Rombo size={10} state="outline" />
      </span>
      <p className="mt-4 font-display text-xl font-bold">{title}</p>
      {children && <div className="mt-1.5 max-w-md text-sm text-ink-2">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
