import { Link } from 'react-router'

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-32 text-center">
      <h1 className="font-serif text-6xl tracking-tight">404</h1>
      <p className="mt-4 text-lg text-text-secondary">This page doesn't exist.</p>
      <Link
        to="/"
        className="mt-6 rounded-xl bg-text px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-80"
      >
        Back to Overview
      </Link>
    </div>
  )
}
