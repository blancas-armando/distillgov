import { cn } from '@/lib/utils'
import { STATUS_CONFIG } from '@/lib/constants'

type StatusBadgeProps = {
  status: string | null
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  if (!status) return null

  const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG]
  const label = config?.label ?? status.replace(/_/g, ' ')
  const color = config?.color ?? 'bg-neutral-100 text-neutral-600'

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
        color,
        className,
      )}
    >
      {label}
    </span>
  )
}
