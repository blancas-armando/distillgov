import { cn } from '@/lib/utils'

type FilterSelectProps = {
  value: string
  onChange: (value: string) => void
  children: React.ReactNode
  className?: string
}

export function FilterSelect({ value, onChange, children, className }: FilterSelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        'h-9 rounded-lg border border-input bg-card px-3 pr-8 text-sm font-medium appearance-none cursor-pointer',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
        className,
      )}
    >
      {children}
    </select>
  )
}
