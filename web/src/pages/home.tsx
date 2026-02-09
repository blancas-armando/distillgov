import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { motion } from 'framer-motion'
import {
  Search, TrendingUp, ArrowRight, Vote, Gavel,
  ScrollText, FileCheck, Users, FileText, Clock,
} from 'lucide-react'
import { useRecentActivity, useTrendingSubjects } from '@/hooks/use-activity'
import { useCongressSummary } from '@/hooks/use-stats'
import { StatCard } from '@/components/shared/stat-card'
import { ChamberBadge } from '@/components/shared/chamber-badge'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { formatDate, formatNumber, formatPercent } from '@/lib/format'
import { pageTransition } from '@/lib/animations'
import { RESULT_CONFIG } from '@/lib/constants'
import type { ActivityItem } from '@/api/types'

const EVENT_ICONS: Record<string, typeof Vote> = {
  vote: Vote,
  introduced: ScrollText,
  enacted: FileCheck,
  signed: FileCheck,
}

function getEventIcon(eventType: string) {
  return EVENT_ICONS[eventType] ?? Gavel
}

function getEventLabel(eventType: string) {
  const labels: Record<string, string> = {
    vote: 'Vote',
    introduced: 'Introduced',
    enacted: 'Enacted',
    signed: 'Signed',
  }
  return labels[eventType] ?? eventType.replace(/_/g, ' ')
}

function getActivityHref(item: ActivityItem): string | null {
  if (item.vote_id) return `/votes/${item.vote_id}`
  if (item.bill_id) return `/bills/${item.bill_id}`
  return null
}

export function Home() {
  const [zipCode, setZipCode] = useState('')
  const navigate = useNavigate()

  const { data: summaries, isLoading: summaryLoading } = useCongressSummary()
  const { data: activity, isLoading: activityLoading } = useRecentActivity({ limit: 8 })
  const { data: trending } = useTrendingSubjects({ limit: 12 })

  const congress = summaries?.at(-1)

  function handleZipSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = zipCode.trim()
    if (trimmed.length === 5 && /^\d{5}$/.test(trimmed)) {
      navigate(`/reps?zip=${trimmed}`)
    }
  }

  return (
    <motion.div {...pageTransition} className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track bills, votes, and your representatives
          </p>
        </div>
        <form onSubmit={handleZipSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={5}
              placeholder="Zip code"
              value={zipCode}
              onChange={(e) => setZipCode(e.target.value.replace(/\D/g, ''))}
              className="h-9 w-32 rounded-lg border border-input bg-card pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1"
            />
          </div>
          <button
            type="submit"
            disabled={zipCode.length !== 5}
            className={cn(
              'flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium transition-colors',
              zipCode.length === 5
                ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                : 'cursor-not-allowed bg-muted text-muted-foreground',
            )}
          >
            Find reps
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </form>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {summaryLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="gap-0 py-0">
              <CardContent className="p-5">
                <div className="h-3 w-20 animate-pulse rounded bg-muted" />
                <div className="mt-4 h-8 w-24 animate-pulse rounded bg-muted" />
                <div className="mt-2 h-3 w-28 animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ))
        ) : congress ? (
          <>
            <StatCard
              label="Total Bills"
              value={formatNumber(congress.total_bills)}
              sublabel={`${congress.congress}th Congress`}
              icon={ScrollText}
              iconColor="bg-blue-50 text-blue-600"
            />
            <StatCard
              label="Enacted"
              value={formatNumber(congress.enacted)}
              sublabel="Signed into law"
              icon={FileCheck}
              iconColor="bg-emerald-50 text-emerald-600"
            />
            <StatCard
              label="Enactment Rate"
              value={formatPercent(congress.enactment_rate_pct)}
              sublabel="Of bills introduced"
              icon={TrendingUp}
              iconColor="bg-amber-50 text-amber-600"
            />
            <StatCard
              label="In Committee"
              value={formatNumber(congress.in_committee)}
              sublabel="Under review"
              icon={Clock}
              iconColor="bg-violet-50 text-violet-600"
            />
          </>
        ) : null}
      </div>

      {/* Quick navigation */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <QuickNavCard
          to="/members"
          icon={Users}
          iconColor="bg-blue-50 text-blue-600"
          title="Members"
          subtitle="538 representatives"
        />
        <QuickNavCard
          to="/bills"
          icon={FileText}
          iconColor="bg-emerald-50 text-emerald-600"
          title="Legislation"
          subtitle={congress ? `${formatNumber(congress.total_bills)} bills` : 'Browse bills'}
        />
        <QuickNavCard
          to="/votes"
          icon={Vote}
          iconColor="bg-violet-50 text-violet-600"
          title="Votes"
          subtitle="Roll call votes"
        />
      </div>

      {/* Trending subjects */}
      {trending && trending.length > 0 && (
        <section>
          <SectionHeader icon={TrendingUp} title="Trending Subjects" />
          <div className="flex flex-wrap gap-2">
            {trending.map((subject) => (
              <Link
                key={subject.subject}
                to={`/bills?subject=${encodeURIComponent(subject.subject)}`}
              >
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  {subject.subject}
                  <span className="ml-1.5 text-muted-foreground">{subject.bill_count}</span>
                </Badge>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Recent activity */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <SectionHeader icon={Gavel} title="Recent Activity" />
          <Link
            to="/votes"
            className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            All votes <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {activityLoading ? (
          <Card className="gap-0 py-0">
            <CardContent className="divide-y p-0">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-start gap-3 px-5 py-4">
                  <div className="h-9 w-9 animate-pulse rounded-lg bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                    <div className="h-3 w-1/3 animate-pulse rounded bg-muted" />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : activity && activity.items.length > 0 ? (
          <Card className="gap-0 py-0">
            <CardContent className="divide-y p-0">
              {activity.items.map((item, i) => {
                const href = getActivityHref(item)
                const Icon = getEventIcon(item.event_type)
                const key = `${item.event_type}-${item.bill_id ?? item.vote_id ?? i}`
                const resultConfig = item.result
                  ? RESULT_CONFIG[item.result as keyof typeof RESULT_CONFIG]
                  : null

                const content = (
                  <div className="flex items-start gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium leading-snug">{item.title}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="text-xs capitalize text-muted-foreground">{getEventLabel(item.event_type)}</span>
                        {item.date && (
                          <>
                            <span className="text-muted-foreground">&middot;</span>
                            <span className="text-xs text-muted-foreground">{formatDate(item.date)}</span>
                          </>
                        )}
                        <ChamberBadge chamber={item.chamber} />
                        {resultConfig && (
                          <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', resultConfig.color)}>
                            {resultConfig.label}
                          </span>
                        )}
                      </div>
                    </div>
                    {href && <ArrowRight className="mt-1.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                  </div>
                )

                return href ? (
                  <Link key={key} to={href} className="block px-5 py-4 transition-colors hover:bg-accent/50">
                    {content}
                  </Link>
                ) : (
                  <div key={key} className="px-5 py-4">{content}</div>
                )
              })}
            </CardContent>
          </Card>
        ) : (
          <Card className="gap-0 py-0">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
                <Gavel className="h-5 w-5 text-muted-foreground" />
              </div>
              <p className="mt-4 text-sm font-medium text-muted-foreground">No recent activity</p>
              <p className="mt-1 text-xs text-muted-foreground">Congressional activity will appear here once data is available.</p>
            </CardContent>
          </Card>
        )}
      </section>
    </motion.div>
  )
}

function SectionHeader({ icon: Icon, title }: { icon: typeof Vote; title: string }) {
  return (
    <div className="mb-4 flex items-center gap-2">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <h2 className="text-sm font-semibold">{title}</h2>
    </div>
  )
}

function QuickNavCard({
  to,
  icon: Icon,
  iconColor,
  title,
  subtitle,
}: {
  to: string
  icon: typeof Vote
  iconColor: string
  title: string
  subtitle: string
}) {
  return (
    <Link to={to} className="group">
      <Card className="gap-0 py-0 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
        <CardContent className="flex items-center gap-4 p-4">
          <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg', iconColor)}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold">{title}</p>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
        </CardContent>
      </Card>
    </Link>
  )
}
