import { NavLink } from 'react-router'
import { cn } from '@/lib/utils'
import { Home, Users, FileText, Vote, MapPin, Landmark } from 'lucide-react'
import { Separator } from '@/components/ui/separator'

const generalNav = [
  { to: '/', label: 'Overview', icon: Home },
  { to: '/reps', label: 'Your Reps', icon: MapPin },
]

const dataNav = [
  { to: '/members', label: 'Members', icon: Users },
  { to: '/bills', label: 'Legislation', icon: FileText },
  { to: '/votes', label: 'Votes', icon: Vote },
]

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 hidden h-screen w-60 flex-col border-r border-border bg-card lg:flex">
      <div className="flex h-14 items-center gap-2.5 px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-900">
          <Landmark className="h-3.5 w-3.5 text-white" />
        </div>
        <NavLink to="/" className="text-sm font-semibold tracking-tight">
          distillgov
        </NavLink>
      </div>

      <Separator />

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <SectionLabel>General</SectionLabel>
        <NavGroup items={generalNav} />

        <SectionLabel className="mt-6">Data</SectionLabel>
        <NavGroup items={dataNav} />
      </nav>

      <Separator />

      <div className="px-5 py-3">
        <p className="text-[11px] text-muted-foreground">
          Congress, distilled.
        </p>
      </div>
    </aside>
  )
}

function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={cn('mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground', className)}>
      {children}
    </p>
  )
}

function NavGroup({ items }: { items: typeof generalNav }) {
  return (
    <ul className="space-y-0.5">
      {items.map(item => (
        <li key={item.to}>
          <NavLink
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        </li>
      ))}
    </ul>
  )
}
