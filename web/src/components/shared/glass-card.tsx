import { cn } from '@/lib/utils'

type GlassCardProps = {
  children: React.ReactNode
  className?: string
  hover?: boolean
}

export function GlassCard({ children, className, hover }: GlassCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card p-6 shadow-sm',
        hover && 'transition-all duration-200 hover:shadow-md hover:-translate-y-0.5',
        className,
      )}
    >
      {children}
    </div>
  )
}
