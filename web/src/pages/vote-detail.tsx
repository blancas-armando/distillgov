import { useVote, useVotePositions } from '@/hooks/use-votes'
import { GlassCard } from '@/components/shared/glass-card'
import { StatCard } from '@/components/shared/stat-card'
import { PartyBadge } from '@/components/shared/party-badge'
import { ChamberBadge } from '@/components/shared/chamber-badge'
import { EmptyState } from '@/components/shared/empty-state'
import { cn } from '@/lib/utils'
import { formatDate, formatNumber } from '@/lib/format'
import { PARTY_CONFIG, RESULT_CONFIG } from '@/lib/constants'
import { pageTransition, staggerContainer, staggerItem } from '@/lib/animations'
import { motion } from 'framer-motion'
import { Link, useParams } from 'react-router'
import { useState } from 'react'
import { Check, X, Minus, ArrowLeft, FileText } from 'lucide-react'
import type { PartyTally, MemberPosition } from '@/api/types'

function FilterPill({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? 'bg-primary text-primary-foreground'
          : 'border border-input bg-card text-muted-foreground hover:text-foreground',
      )}
    >
      {label}
    </button>
  )
}

function PositionIcon({ position }: { position: string }) {
  const normalized = position.toLowerCase()
  if (normalized === 'yes' || normalized === 'yea') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-passed-light">
        <Check className="h-3.5 w-3.5 text-emerald-700" />
      </span>
    )
  }
  if (normalized === 'no' || normalized === 'nay') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-failed-light">
        <X className="h-3.5 w-3.5 text-red-700" />
      </span>
    )
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-100">
      <Minus className="h-3.5 w-3.5 text-neutral-500" />
    </span>
  )
}

function PartyBreakdownBar({ tally }: { tally: PartyTally }) {
  const config = PARTY_CONFIG[tally.party as keyof typeof PARTY_CONFIG]
  const partyLabel = config?.label ?? tally.party
  const total = tally.yes + tally.no + tally.present + tally.not_voting

  if (total === 0) return null

  const yesPct = (tally.yes / total) * 100
  const noPct = (tally.no / total) * 100
  const presentPct = (tally.present / total) * 100
  const notVotingPct = (tally.not_voting / total) * 100

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {config && (
          <span className={cn('h-2.5 w-2.5 rounded-full', config.color)} />
        )}
        <span className="text-sm font-medium">{partyLabel}</span>
        <span className="text-xs text-text-tertiary">
          {total} members
        </span>
      </div>

      <div className="flex h-3 overflow-hidden rounded-full bg-neutral-100">
        {tally.yes > 0 && (
          <div
            className="bg-passed transition-all duration-500"
            style={{ width: `${yesPct}%` }}
            title={`Yes: ${tally.yes}`}
          />
        )}
        {tally.no > 0 && (
          <div
            className="bg-failed transition-all duration-500"
            style={{ width: `${noPct}%` }}
            title={`No: ${tally.no}`}
          />
        )}
        {tally.present > 0 && (
          <div
            className="bg-neutral-300 transition-all duration-500"
            style={{ width: `${presentPct}%` }}
            title={`Present: ${tally.present}`}
          />
        )}
        {tally.not_voting > 0 && (
          <div
            className="bg-neutral-200 transition-all duration-500"
            style={{ width: `${notVotingPct}%` }}
            title={`Not Voting: ${tally.not_voting}`}
          />
        )}
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {tally.yes > 0 && (
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-passed" />
            <span className="font-medium text-emerald-700">{tally.yes} Yes</span>
          </span>
        )}
        {tally.no > 0 && (
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-failed" />
            <span className="font-medium text-red-700">{tally.no} No</span>
          </span>
        )}
        {tally.present > 0 && (
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-neutral-300" />
            <span className="text-text-secondary">{tally.present} Present</span>
          </span>
        )}
        {tally.not_voting > 0 && (
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-neutral-200" />
            <span className="text-text-tertiary">{tally.not_voting} Not Voting</span>
          </span>
        )}
      </div>
    </div>
  )
}

function SkeletonHeader() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-4 w-20 rounded bg-neutral-200" />
      <div className="h-8 w-3/4 rounded bg-neutral-200" />
      <div className="flex gap-3">
        <div className="h-5 w-16 rounded-full bg-neutral-200" />
        <div className="h-5 w-20 rounded-full bg-neutral-200" />
        <div className="h-5 w-24 rounded-full bg-neutral-200" />
      </div>
    </div>
  )
}

function SkeletonBreakdown() {
  return (
    <div className="glass rounded-2xl p-6 space-y-6 animate-pulse">
      <div className="h-5 w-36 rounded bg-neutral-200" />
      <div className="space-y-4">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <div className="h-4 w-24 rounded bg-neutral-200" />
            <div className="h-3 w-full rounded-full bg-neutral-100" />
            <div className="flex gap-4">
              <div className="h-3 w-16 rounded bg-neutral-100" />
              <div className="h-3 w-16 rounded bg-neutral-100" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function positionSortKey(m: MemberPosition): string {
  const partyOrder = m.party === 'D' ? '0' : m.party === 'R' ? '1' : '2'
  return `${partyOrder}-${m.state ?? ''}-${m.full_name ?? ''}`
}

export function VoteDetailPage() {
  const { voteId } = useParams()
  const [partyFilter, setPartyFilter] = useState('')
  const [positionFilter, setPositionFilter] = useState('')

  const { data: vote, isLoading: voteLoading } = useVote(voteId ?? '')
  const { data: positions, isLoading: positionsLoading } = useVotePositions(
    voteId ?? '',
    {
      party: partyFilter || undefined,
      position: positionFilter || undefined,
    },
  )

  const resultConfig = vote?.result
    ? RESULT_CONFIG[vote.result as keyof typeof RESULT_CONFIG]
    : null

  const sortedPositions = [...(positions?.positions ?? [])].sort((a, b) =>
    positionSortKey(a).localeCompare(positionSortKey(b)),
  )

  return (
    <motion.div {...pageTransition} className="space-y-8">
      {/* Back link */}
      <Link
        to="/votes"
        className="inline-flex items-center gap-1.5 text-sm text-text-tertiary transition-colors hover:text-text"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All votes
      </Link>

      {/* Header */}
      {voteLoading ? (
        <SkeletonHeader />
      ) : vote ? (
        <div>
          <p className="text-sm text-text-tertiary">
            {formatDate(vote.vote_date)}
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight">
            {vote.question ?? vote.description ?? 'Roll call vote'}
          </h1>
          {vote.description && vote.question && (
            <p className="mt-2 text-text-secondary">{vote.description}</p>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <ChamberBadge chamber={vote.chamber} />
            {resultConfig && (
              <span
                className={cn(
                  'inline-flex items-center rounded-full px-3 py-1 text-sm font-medium',
                  resultConfig.color,
                )}
              >
                {resultConfig.label}
              </span>
            )}
            {vote.bill_id && (
              <Link
                to={`/bills/${vote.bill_id}`}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full px-3 py-1',
                  'text-sm font-medium text-text-secondary',
                  'glass-input hover:text-text',
                )}
              >
                <FileText className="h-3.5 w-3.5" />
                View Bill
              </Link>
            )}
          </div>
        </div>
      ) : (
        <EmptyState title="Vote not found" />
      )}

      {/* Vote Totals */}
      {vote && (
        <motion.div
          className="grid grid-cols-2 gap-4 sm:grid-cols-4"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          <motion.div variants={staggerItem}>
            <StatCard
              label="Yea"
              value={formatNumber(vote.yea_count ?? 0)}
              className="border-l-2 border-l-passed"
            />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatCard
              label="Nay"
              value={formatNumber(vote.nay_count ?? 0)}
              className="border-l-2 border-l-failed"
            />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatCard
              label="Present"
              value={formatNumber(vote.present_count ?? 0)}
              className="border-l-2 border-l-neutral-300"
            />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatCard
              label="Not Voting"
              value={formatNumber(vote.not_voting ?? 0)}
              className="border-l-2 border-l-neutral-200"
            />
          </motion.div>
        </motion.div>
      )}

      {/* Party Breakdown */}
      {positionsLoading ? (
        <SkeletonBreakdown />
      ) : positions && positions.party_breakdown.length > 0 ? (
        <GlassCard>
          <h2 className="text-lg font-semibold">Party Breakdown</h2>
          <div className="mt-6 space-y-6">
            {positions.party_breakdown.map((tally) => (
              <PartyBreakdownBar key={tally.party} tally={tally} />
            ))}
          </div>
        </GlassCard>
      ) : null}

      {/* Member Positions */}
      {(positions || positionsLoading) && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              Member Positions
            </h2>
            {positions && (
              <span className="text-sm text-text-tertiary">
                {formatNumber(sortedPositions.length)} members
              </span>
            )}
          </div>

          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-text-tertiary uppercase tracking-wider mr-1">
              Party
            </span>
            <FilterPill
              label="All"
              active={partyFilter === ''}
              onClick={() => setPartyFilter('')}
            />
            <FilterPill
              label="Democrat"
              active={partyFilter === 'D'}
              onClick={() => setPartyFilter(partyFilter === 'D' ? '' : 'D')}
            />
            <FilterPill
              label="Republican"
              active={partyFilter === 'R'}
              onClick={() => setPartyFilter(partyFilter === 'R' ? '' : 'R')}
            />
            <FilterPill
              label="Independent"
              active={partyFilter === 'I'}
              onClick={() => setPartyFilter(partyFilter === 'I' ? '' : 'I')}
            />

            <span className="mx-1 h-4 w-px bg-border" />

            <span className="text-xs font-medium text-text-tertiary uppercase tracking-wider mr-1">
              Position
            </span>
            <FilterPill
              label="All"
              active={positionFilter === ''}
              onClick={() => setPositionFilter('')}
            />
            <FilterPill
              label="Yes"
              active={positionFilter === 'Yes'}
              onClick={() => setPositionFilter(positionFilter === 'Yes' ? '' : 'Yes')}
            />
            <FilterPill
              label="No"
              active={positionFilter === 'No'}
              onClick={() => setPositionFilter(positionFilter === 'No' ? '' : 'No')}
            />
          </div>

          {positionsLoading ? (
            <GlassCard className="space-y-3 animate-pulse">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="h-6 w-6 rounded-full bg-neutral-200" />
                  <div className="h-4 w-40 rounded bg-neutral-200" />
                  <div className="h-5 w-10 rounded-full bg-neutral-100" />
                  <div className="h-4 w-8 rounded bg-neutral-100" />
                </div>
              ))}
            </GlassCard>
          ) : sortedPositions.length === 0 ? (
            <EmptyState
              title="No positions found"
              description="Try adjusting the filters above."
            />
          ) : (
            <GlassCard className="p-0 overflow-hidden">
              <div className="divide-y divide-border-subtle">
                {sortedPositions.map((member) => (
                  <Link
                    key={member.bioguide_id}
                    to={`/members/${member.bioguide_id}`}
                    className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-white/40"
                  >
                    <PositionIcon position={member.position} />
                    <div className="min-w-0 flex-1">
                      <span className="text-sm font-medium">
                        {member.full_name}
                      </span>
                    </div>
                    <PartyBadge party={member.party} />
                    <span className="w-8 text-right text-xs text-text-secondary">
                      {member.state}
                    </span>
                  </Link>
                ))}
              </div>
            </GlassCard>
          )}
        </div>
      )}
    </motion.div>
  )
}
