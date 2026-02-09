import { NavLink } from 'react-router'
import { cn } from '@/lib/utils'
import { Home, Users, FileText, Vote, MapPin } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/reps', label: 'Reps', icon: MapPin },
  { to: '/members', label: 'Members', icon: Users },
  { to: '/bills', label: 'Bills', icon: FileText },
  { to: '/votes', label: 'Votes', icon: Vote },
]

export function MobileNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-card lg:hidden">
      <ul className="flex items-center justify-around px-2 py-2">
        {navItems.map(item => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex flex-col items-center gap-0.5 rounded-lg px-3 py-1.5 text-[10px] font-medium transition-colors',
                  isActive ? 'text-foreground' : 'text-muted-foreground',
                )
              }
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
