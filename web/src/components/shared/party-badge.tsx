import { cn } from '@/lib/utils'
import { PARTY_CONFIG } from '@/lib/constants'

type PartyBadgeProps = {
  party: string | null
  className?: string
  showLabel?: boolean
}

export function PartyBadge({ party, className, showLabel = false }: PartyBadgeProps) {
  const config = party ? PARTY_CONFIG[party as keyof typeof PARTY_CONFIG] : null

  if (!config) return null

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.lightBg,
        config.textColor,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.color)} />
      {showLabel ? config.label : party}
    </span>
  )
}
