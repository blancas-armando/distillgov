import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import type { LucideIcon } from 'lucide-react'

type StatCardProps = {
  label: string
  value: string | number
  sublabel?: string
  icon?: LucideIcon
  iconColor?: string
  className?: string
}

export function StatCard({
  label,
  value,
  sublabel,
  icon: Icon,
  iconColor = 'bg-muted text-muted-foreground',
  className,
}: StatCardProps) {
  return (
    <Card className={cn('gap-0 py-0', className)}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <p className="text-[13px] font-medium text-muted-foreground">{label}</p>
          {Icon && (
            <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg', iconColor)}>
              <Icon className="h-4 w-4" />
            </div>
          )}
        </div>
        <p className="mt-1 text-3xl font-bold tracking-tight">{value}</p>
        {sublabel && <p className="mt-1 text-xs text-muted-foreground">{sublabel}</p>}
      </CardContent>
    </Card>
  )
}
