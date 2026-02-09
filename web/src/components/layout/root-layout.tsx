import { Outlet } from 'react-router'
import { Sidebar } from './sidebar'
import { MobileNav } from './mobile-nav'

export function RootLayout() {
  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="main-content min-h-screen pb-24 lg:pb-0">
        <div className="mx-auto max-w-6xl px-5 py-6 sm:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>
      <MobileNav />
    </div>
  )
}
