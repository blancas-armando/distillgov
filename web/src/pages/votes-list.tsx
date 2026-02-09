import { useVotes } from '@/hooks/use-votes'
import { ChamberBadge } from '@/components/shared/chamber-badge'
import { PageHeader } from '@/components/shared/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { FilterSelect } from '@/components/shared/filter-select'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { formatDate, formatNumber } from '@/lib/format'
import { RESULT_CONFIG } from '@/lib/constants'
import { pageTransition, staggerContainer, staggerItem } from '@/lib/animations'
import { motion } from 'framer-motion'
import { Link, useSearchParams } from 'react-router'
import { FileText } from 'lucide-react'

function PassageToggle({
  active,
  onToggle,
}: {
  active: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        'h-9 rounded-lg px-3 text-sm font-medium transition-colors',
        active
          ? 'bg-primary text-primary-foreground'
          : 'border border-input bg-card text-muted-foreground hover:text-foreground',
      )}
    >
      Passage votes only
    </button>
  )
}

function VoteBar({ yea, nay }: { yea: number; nay: number }) {
  const total = yea + nay
  if (total === 0) return null

  const yeaPct = (yea / total) * 100
  const nayPct = (nay / total) * 100

  return (
    <div className="space-y-1.5">
      <div className="flex h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="rounded-l-full bg-passed transition-all duration-300"
          style={{ width: `${yeaPct}%` }}
        />
        <div
          className="rounded-r-full bg-failed transition-all duration-300"
          style={{ width: `${nayPct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs">
        <span className="font-medium text-emerald-700">
          {formatNumber(yea)} Yea
        </span>
        <span className="font-medium text-red-700">
          {formatNumber(nay)} Nay
        </span>
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <Card className="gap-0 py-0">
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center justify-between">
          <div className="h-3 w-24 animate-pulse rounded bg-muted" />
          <div className="h-5 w-16 animate-pulse rounded-full bg-muted" />
        </div>
        <div className="h-5 w-4/5 animate-pulse rounded bg-muted" />
        <div className="flex items-center gap-2">
          <div className="h-5 w-14 animate-pulse rounded-full bg-muted" />
          <div className="h-5 w-14 animate-pulse rounded-full bg-muted" />
        </div>
        <div className="h-2 w-full animate-pulse rounded-full bg-muted" />
      </CardContent>
    </Card>
  )
}

export function VotesListPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const chamber = searchParams.get('chamber') ?? ''
  const result = searchParams.get('result') ?? ''
  const passageOnly = searchParams.get('passage_only') === 'true'

  function setFilter(key: string, value: string) {
    setSearchParams((prev) => {
      if (value) {
        prev.set(key, value)
      } else {
        prev.delete(key)
      }
      prev.delete('offset')
      return prev
    })
  }

  function togglePassageOnly() {
    setSearchParams((prev) => {
      if (passageOnly) {
        prev.delete('passage_only')
      } else {
        prev.set('passage_only', 'true')
      }
      prev.delete('offset')
      return prev
    })
  }

  const { data, isLoading } = useVotes({
    chamber: chamber || undefined,
    result: result || undefined,
    passage_only: passageOnly,
    limit: 30,
  })

  const votes = data?.votes ?? []
  const total = data?.total ?? 0

  return (
    <motion.div {...pageTransition}>
      <PageHeader title="Votes" description="Roll call votes in Congress">
        {!isLoading && (
          <span className="text-sm text-muted-foreground">
            {formatNumber(total)} votes
          </span>
        )}
      </PageHeader>

      <div className="mb-8 flex flex-wrap items-center gap-3">
        <FilterSelect value={chamber} onChange={(v) => setFilter('chamber', v)}>
          <option value="">All Chambers</option>
          <option value="house">House</option>
          <option value="senate">Senate</option>
        </FilterSelect>

        <FilterSelect value={result} onChange={(v) => setFilter('result', v)}>
          <option value="">All Results</option>
          <option value="Passed">Passed</option>
          <option value="Failed">Failed</option>
          <option value="Agreed to">Agreed to</option>
        </FilterSelect>

        <PassageToggle active={passageOnly} onToggle={togglePassageOnly} />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : votes.length === 0 ? (
        <EmptyState
          title="No votes found"
          description="Try adjusting your filters to see more results."
        />
      ) : (
        <motion.div
          className="grid grid-cols-1 gap-3 lg:grid-cols-2"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {votes.map((vote) => {
            const resultConfig = vote.result
              ? RESULT_CONFIG[vote.result as keyof typeof RESULT_CONFIG]
              : null

            return (
              <motion.div key={vote.vote_id} variants={staggerItem}>
                <Link to={`/votes/${vote.vote_id}`}>
                  <Card className="gap-0 py-0 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
                    <CardContent className="p-5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">
                          {formatDate(vote.vote_date)}
                        </span>
                        {resultConfig && (
                          <span
                            className={cn(
                              'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                              resultConfig.color,
                            )}
                          >
                            {resultConfig.label}
                          </span>
                        )}
                      </div>

                      <p className="mt-2 line-clamp-2 text-sm font-semibold leading-snug">
                        {vote.question ?? vote.description ?? 'Roll call vote'}
                      </p>

                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <ChamberBadge chamber={vote.chamber} />
                        {vote.bill_id && (
                          <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                            <FileText className="h-3 w-3" />
                            Related Bill
                          </span>
                        )}
                      </div>

                      {vote.yea_count != null && vote.nay_count != null && (
                        <div className="mt-4">
                          <VoteBar yea={vote.yea_count} nay={vote.nay_count} />
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            )
          })}
        </motion.div>
      )}
    </motion.div>
  )
}
