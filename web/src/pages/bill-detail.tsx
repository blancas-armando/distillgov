import { useBill, useBillActions, useBillVotes } from '@/hooks/use-bills'
import { GlassCard } from '@/components/shared/glass-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { PartyBadge } from '@/components/shared/party-badge'
import { ChamberBadge } from '@/components/shared/chamber-badge'
import { cn } from '@/lib/utils'
import { formatDate, formatBillId, formatNumber } from '@/lib/format'
import { pageTransition, staggerContainer, staggerItem } from '@/lib/animations'
import { motion } from 'framer-motion'
import { Link, useParams } from 'react-router'
import { ExternalLink, FileText, ArrowLeft } from 'lucide-react'

function CosponsorBar({
  dem,
  rep,
  ind,
  total,
}: {
  dem: number
  rep: number
  ind: number
  total: number
}) {
  if (total === 0) {
    return (
      <p className="text-sm text-text-tertiary">No cosponsors</p>
    )
  }

  const demPct = (dem / total) * 100
  const repPct = (rep / total) * 100
  const indPct = (ind / total) * 100

  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between">
        <span className="text-sm font-medium text-text-secondary">
          {formatNumber(total)} Cosponsor{total !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="flex h-3 overflow-hidden rounded-full">
        {dem > 0 && (
          <div
            className="bg-dem transition-all duration-500"
            style={{ width: `${demPct}%` }}
          />
        )}
        {rep > 0 && (
          <div
            className="bg-rep transition-all duration-500"
            style={{ width: `${repPct}%` }}
          />
        )}
        {ind > 0 && (
          <div
            className="bg-ind transition-all duration-500"
            style={{ width: `${indPct}%` }}
          />
        )}
      </div>

      <div className="mt-2 flex gap-4">
        {dem > 0 && (
          <span className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span className="h-2 w-2 rounded-full bg-dem" />
            {dem} Democrat{dem !== 1 ? 's' : ''}
          </span>
        )}
        {rep > 0 && (
          <span className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span className="h-2 w-2 rounded-full bg-rep" />
            {rep} Republican{rep !== 1 ? 's' : ''}
          </span>
        )}
        {ind > 0 && (
          <span className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span className="h-2 w-2 rounded-full bg-ind" />
            {ind} Independent{ind !== 1 ? 's' : ''}
          </span>
        )}
      </div>
    </div>
  )
}

function ActionTimeline({ billId }: { billId: string }) {
  const { data, isLoading } = useBillActions(billId)

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex gap-4 animate-pulse">
            <div className="h-4 w-20 rounded bg-neutral-200" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-full rounded bg-neutral-200" />
              <div className="h-4 w-2/3 rounded bg-neutral-200" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  const actions = data?.actions ?? []

  if (actions.length === 0) {
    return <p className="text-sm text-text-tertiary">No actions recorded.</p>
  }

  return (
    <div className="relative">
      <div className="absolute left-[83px] top-2 bottom-2 w-px bg-border" />

      <div className="space-y-0">
        {actions.map((action, idx) => {
          const isFirst = idx === 0

          return (
            <div key={idx} className="relative flex gap-4 py-3">
              <span
                className={cn(
                  'w-[72px] shrink-0 text-right text-xs leading-5',
                  isFirst ? 'font-medium text-text' : 'text-text-tertiary',
                )}
              >
                {formatDate(action.action_date)}
              </span>

              <div className="relative flex items-start">
                <span
                  className={cn(
                    'mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full border-2 border-white',
                    isFirst ? 'bg-text' : 'bg-neutral-300',
                  )}
                />
              </div>

              <div className="flex-1 min-w-0">
                <p
                  className={cn(
                    'text-sm leading-5',
                    isFirst ? 'font-medium text-text' : 'text-text-secondary',
                  )}
                >
                  {action.action_text}
                </p>
                {action.chamber && (
                  <div className="mt-1">
                    <ChamberBadge chamber={action.chamber} />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function RelatedVotes({ billId }: { billId: string }) {
  const { data, isLoading } = useBillVotes(billId)

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="glass animate-pulse rounded-2xl p-4">
            <div className="space-y-2">
              <div className="h-4 w-full rounded bg-neutral-200" />
              <div className="flex gap-3">
                <div className="h-5 w-16 rounded-full bg-neutral-200" />
                <div className="h-5 w-20 rounded bg-neutral-200" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  const votes = data?.votes ?? []

  if (votes.length === 0) {
    return <p className="text-sm text-text-tertiary">No roll call votes recorded for this bill.</p>
  }

  return (
    <div className="space-y-3">
      {votes.map((vote) => {
        const isPassed = vote.result === 'Passed' || vote.result === 'Agreed to'

        return (
          <Link key={vote.vote_id} to={`/votes/${vote.vote_id}`}>
            <GlassCard hover className="group">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium leading-snug">
                    {vote.question ?? 'Roll Call Vote'}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <ChamberBadge chamber={vote.chamber} />
                    <span className="text-xs text-text-tertiary">
                      {formatDate(vote.vote_date)}
                    </span>
                  </div>
                </div>

                <div className="shrink-0 text-right">
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                      isPassed
                        ? 'bg-passed-light text-emerald-800'
                        : 'bg-failed-light text-red-800',
                    )}
                  >
                    {vote.result ?? 'Unknown'}
                  </span>
                  {(vote.yea_count !== null || vote.nay_count !== null) && (
                    <p className="mt-1 text-xs text-text-tertiary">
                      {vote.yea_count ?? 0} - {vote.nay_count ?? 0}
                    </p>
                  )}
                </div>
              </div>
            </GlassCard>
          </Link>
        )
      })}
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="animate-pulse space-y-8">
      <div className="space-y-3">
        <div className="h-5 w-24 rounded bg-neutral-200" />
        <div className="h-8 w-3/4 rounded bg-neutral-200" />
        <div className="h-8 w-1/2 rounded bg-neutral-200" />
        <div className="flex gap-2">
          <div className="h-6 w-20 rounded-full bg-neutral-200" />
          <div className="h-6 w-28 rounded-full bg-neutral-200" />
        </div>
      </div>
      <div className="glass rounded-2xl p-6 space-y-3">
        <div className="h-5 w-full rounded bg-neutral-200" />
        <div className="h-5 w-full rounded bg-neutral-200" />
        <div className="h-5 w-2/3 rounded bg-neutral-200" />
      </div>
      <div className="glass rounded-2xl p-6 space-y-3">
        <div className="h-5 w-40 rounded bg-neutral-200" />
        <div className="h-3 w-full rounded-full bg-neutral-200" />
        <div className="flex gap-4">
          <div className="h-4 w-20 rounded bg-neutral-200" />
          <div className="h-4 w-20 rounded bg-neutral-200" />
        </div>
      </div>
    </div>
  )
}

export function BillDetailPage() {
  const { billId } = useParams<{ billId: string }>()
  const { data: bill, isLoading } = useBill(billId!)

  if (isLoading) {
    return (
      <motion.div {...pageTransition}>
        <Link
          to="/bills"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-text-secondary transition-colors hover:text-text"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All Bills
        </Link>
        <DetailSkeleton />
      </motion.div>
    )
  }

  if (!bill) {
    return (
      <motion.div {...pageTransition} className="py-16 text-center">
        <p className="text-lg font-medium text-text-secondary">Bill not found</p>
        <Link
          to="/bills"
          className="mt-4 inline-flex items-center gap-1.5 text-sm text-text-secondary transition-colors hover:text-text"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to all bills
        </Link>
      </motion.div>
    )
  }

  return (
    <motion.div {...pageTransition}>
      <Link
        to="/bills"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-text-secondary transition-colors hover:text-text"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All Bills
      </Link>

      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="space-y-8"
      >
        {/* Header */}
        <motion.div variants={staggerItem}>
          <span className="text-sm font-semibold tracking-wide text-text-secondary">
            {formatBillId(bill.bill_type, bill.bill_number)}
          </span>

          <h1 className="mt-2 text-2xl font-bold leading-tight tracking-tight">
            {bill.short_title ?? bill.title ?? 'Untitled Bill'}
          </h1>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <StatusBadge status={bill.status} />
            {bill.policy_area && (
              <span className="rounded-lg bg-neutral-100 px-2.5 py-1 text-xs font-medium text-text-secondary">
                {bill.policy_area}
              </span>
            )}
            {bill.introduced_date && (
              <span className="text-sm text-text-tertiary">
                Introduced {formatDate(bill.introduced_date)}
              </span>
            )}
          </div>
        </motion.div>

        {/* Sponsor */}
        <motion.div variants={staggerItem}>
          <GlassCard>
            <p className="mb-1 text-xs font-medium uppercase tracking-wider text-text-tertiary">
              Sponsor
            </p>
            <div className="flex items-center gap-2">
              {bill.sponsor_id ? (
                <Link
                  to={`/members/${bill.sponsor_id}`}
                  className="text-[15px] font-medium transition-colors hover:text-text-secondary"
                >
                  {bill.sponsor_name ?? 'Unknown'}
                </Link>
              ) : (
                <span className="text-[15px] font-medium">
                  {bill.sponsor_name ?? 'Unknown'}
                </span>
              )}
              <PartyBadge party={bill.sponsor_party} />
            </div>
          </GlassCard>
        </motion.div>

        {/* Summary */}
        {bill.summary && (
          <motion.div variants={staggerItem}>
            <GlassCard>
              <p className="mb-3 text-xs font-medium uppercase tracking-wider text-text-tertiary">
                Summary
              </p>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {bill.summary}
              </p>
            </GlassCard>
          </motion.div>
        )}

        {/* Subjects */}
        {bill.subjects.length > 0 && (
          <motion.div variants={staggerItem}>
            <GlassCard>
              <p className="mb-3 text-xs font-medium uppercase tracking-wider text-text-tertiary">
                Subjects
              </p>
              <div className="flex flex-wrap gap-2">
                {bill.subjects.map((subject) => (
                  <span
                    key={subject}
                    className="rounded-lg bg-neutral-100 px-2.5 py-1 text-xs font-medium text-text-secondary"
                  >
                    {subject}
                  </span>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Cosponsor Breakdown */}
        <motion.div variants={staggerItem}>
          <GlassCard>
            <p className="mb-4 text-xs font-medium uppercase tracking-wider text-text-tertiary">
              Cosponsorship
            </p>
            <CosponsorBar
              dem={bill.dem_cosponsors}
              rep={bill.rep_cosponsors}
              ind={bill.ind_cosponsors}
              total={bill.total_cosponsors}
            />
          </GlassCard>
        </motion.div>

        {/* Action Timeline */}
        <motion.div variants={staggerItem}>
          <GlassCard>
            <p className="mb-4 text-xs font-medium uppercase tracking-wider text-text-tertiary">
              Action Timeline
            </p>
            <ActionTimeline billId={billId!} />
          </GlassCard>
        </motion.div>

        {/* Related Votes */}
        <motion.div variants={staggerItem}>
          <h2 className="mb-4 text-lg font-semibold">Related Votes</h2>
          <RelatedVotes billId={billId!} />
        </motion.div>

        {/* Full Text Link */}
        {bill.full_text_url && (
          <motion.div variants={staggerItem}>
            <a
              href={bill.full_text_url}
              target="_blank"
              rel="noopener noreferrer"
              className="glass inline-flex items-center gap-2 rounded-2xl px-5 py-3 text-sm font-medium transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5"
            >
              <FileText className="h-4 w-4" />
              Read Full Text
              <ExternalLink className="h-3.5 w-3.5 text-text-tertiary" />
            </a>
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  )
}
