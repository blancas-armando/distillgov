import { cn } from '@/lib/utils'
import { formatChamber } from '@/lib/format'

type ChamberBadgeProps = {
  chamber: string | null
  className?: string
}

export function ChamberBadge({ chamber, className }: ChamberBadgeProps) {
  if (!chamber) return null

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        chamber === 'senate' ? 'bg-violet-50 text-violet-700' : 'bg-sky-50 text-sky-700',
        className,
      )}
    >
      {formatChamber(chamber)}
    </span>
  )
}
