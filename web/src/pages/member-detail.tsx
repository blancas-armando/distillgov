import { useMember, useMemberVotes, useMemberBills } from '@/hooks/use-members'
import { GlassCard } from '@/components/shared/glass-card'
import { StatCard } from '@/components/shared/stat-card'
import { MemberAvatar } from '@/components/shared/member-avatar'
import { PartyBadge } from '@/components/shared/party-badge'
import { ChamberBadge } from '@/components/shared/chamber-badge'
import { StatusBadge } from '@/components/shared/status-badge'
import { EmptyState } from '@/components/shared/empty-state'
import { cn } from '@/lib/utils'
import { formatDate, formatNumber, formatPercent, formatState, formatBillId } from '@/lib/format'
import { pageTransition, staggerContainer, staggerItem } from '@/lib/animations'
import { motion } from 'framer-motion'
import { Link, useParams } from 'react-router'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Phone, Globe, Mail, ExternalLink } from 'lucide-react'

const POSITION_STYLES: Record<string, string> = {
  Yes: 'bg-passed-light text-emerald-800',
  Yea: 'bg-passed-light text-emerald-800',
  No: 'bg-failed-light text-red-800',
  Nay: 'bg-failed-light text-red-800',
  'Not Voting': 'bg-neutral-100 text-neutral-500',
  Present: 'bg-pending-light text-amber-800',
}

function PositionBadge({ position }: { position: string }) {
  const style = POSITION_STYLES[position] ?? 'bg-neutral-100 text-neutral-600'
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', style)}>
      {position}
    </span>
  )
}

function ContactLink({
  href,
  icon: Icon,
  label,
}: {
  href: string
  icon: React.ComponentType<{ className?: string }>
  label: string
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="glass flex items-center gap-3 rounded-xl px-4 py-3 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
    >
      <Icon className="h-4 w-4 text-text-secondary" />
      <span className="text-sm font-medium">{label}</span>
      <ExternalLink className="ml-auto h-3.5 w-3.5 text-text-tertiary" />
    </a>
  )
}

function HeroSkeleton() {
  return (
    <div className="glass animate-pulse rounded-2xl p-8">
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <div className="h-20 w-20 rounded-full bg-neutral-200" />
        <div className="flex-1 space-y-3 text-center sm:text-left">
          <div className="mx-auto h-8 w-48 rounded bg-neutral-200 sm:mx-0" />
          <div className="mx-auto flex justify-center gap-2 sm:mx-0 sm:justify-start">
            <div className="h-5 w-16 rounded-full bg-neutral-200" />
            <div className="h-5 w-16 rounded-full bg-neutral-200" />
          </div>
          <div className="mx-auto h-4 w-32 rounded bg-neutral-200 sm:mx-0" />
        </div>
      </div>
    </div>
  )
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="glass animate-pulse rounded-2xl p-6">
          <div className="h-3 w-20 rounded bg-neutral-200" />
          <div className="mt-3 h-8 w-16 rounded bg-neutral-200" />
        </div>
      ))}
    </div>
  )
}

function VotesTab({ bioguideId }: { bioguideId: string }) {
  const { data, isLoading } = useMemberVotes(bioguideId, { limit: 30 })
  const votes = data?.votes ?? []

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="glass animate-pulse rounded-xl p-4">
            <div className="h-4 w-3/4 rounded bg-neutral-200" />
            <div className="mt-2 h-3 w-1/2 rounded bg-neutral-200" />
          </div>
        ))}
      </div>
    )
  }

  if (votes.length === 0) {
    return <EmptyState title="No votes recorded" description="This member has no recorded votes yet." />
  }

  return (
    <motion.div className="space-y-3" variants={staggerContainer} initial="initial" animate="animate">
      {votes.map((vote) => (
        <motion.div key={vote.vote_id} variants={staggerItem}>
          <Link
            to={`/votes/${vote.vote_id}`}
            className="glass flex items-center gap-4 rounded-xl px-4 py-3 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {vote.question ?? vote.description ?? 'Vote'}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-secondary">
                <span>{formatDate(vote.vote_date)}</span>
                {vote.result && (
                  <>
                    <span className="text-text-tertiary">·</span>
                    <span>{vote.result}</span>
                  </>
                )}
                {vote.bill_id && (
                  <>
                    <span className="text-text-tertiary">·</span>
                    <span>{vote.bill_id}</span>
                  </>
                )}
              </div>
            </div>
            <PositionBadge position={vote.position} />
          </Link>
        </motion.div>
      ))}
    </motion.div>
  )
}

function BillsTab({ bioguideId }: { bioguideId: string }) {
  const { data, isLoading } = useMemberBills(bioguideId, { limit: 30 })
  const bills = data?.bills ?? []

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="glass animate-pulse rounded-xl p-4">
            <div className="h-4 w-3/4 rounded bg-neutral-200" />
            <div className="mt-2 h-3 w-1/2 rounded bg-neutral-200" />
          </div>
        ))}
      </div>
    )
  }

  if (bills.length === 0) {
    return <EmptyState title="No bills found" description="This member has no associated bills yet." />
  }

  return (
    <motion.div className="space-y-3" variants={staggerContainer} initial="initial" animate="animate">
      {bills.map((bill) => (
        <motion.div key={bill.bill_id} variants={staggerItem}>
          <Link
            to={`/bills/${bill.bill_id}`}
            className="glass flex items-start gap-4 rounded-xl px-4 py-3 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
          >
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="shrink-0 text-sm font-semibold text-text-secondary">
                  {formatBillId(bill.bill_type, bill.bill_number)}
                </span>
                <StatusBadge status={bill.status} />
              </div>
              <p className="mt-1 text-sm font-medium leading-snug">
                {bill.title ?? 'Untitled bill'}
              </p>
              <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-text-secondary">
                <span>{formatDate(bill.introduced_date)}</span>
                {bill.policy_area && (
                  <>
                    <span className="text-text-tertiary">·</span>
                    <span>{bill.policy_area}</span>
                  </>
                )}
                <span className="text-text-tertiary">·</span>
                <span className="capitalize">{bill.role}</span>
              </div>
            </div>
          </Link>
        </motion.div>
      ))}
    </motion.div>
  )
}

function CommitteesTab({ committees }: { committees: { committee_id: string; name: string; role: string | null }[] }) {
  if (committees.length === 0) {
    return <EmptyState title="No committee assignments" description="Committee data is not available for this member." />
  }

  return (
    <motion.div className="space-y-3" variants={staggerContainer} initial="initial" animate="animate">
      {committees.map((committee) => (
        <motion.div key={committee.committee_id} variants={staggerItem}>
          <GlassCard className="flex items-center justify-between gap-4 !p-4">
            <div className="min-w-0">
              <p className="text-sm font-medium">{committee.name}</p>
              {committee.role && (
                <p className="mt-0.5 text-xs text-text-secondary capitalize">{committee.role}</p>
              )}
            </div>
          </GlassCard>
        </motion.div>
      ))}
    </motion.div>
  )
}

function ContactTab({
  member,
}: {
  member: {
    phone: string | null
    office_address: string | null
    official_url: string | null
    contact_form: string | null
    twitter: string | null
    facebook: string | null
    youtube: string | null
  }
}) {
  const hasContact = member.phone || member.official_url || member.contact_form
  const hasSocial = member.twitter || member.facebook || member.youtube

  if (!hasContact && !hasSocial && !member.office_address) {
    return <EmptyState title="No contact information" description="Contact details are not available for this member." />
  }

  return (
    <motion.div className="space-y-6" variants={staggerContainer} initial="initial" animate="animate">
      {member.office_address && (
        <motion.div variants={staggerItem}>
          <GlassCard>
            <p className="text-xs font-medium uppercase tracking-wider text-text-tertiary">Office</p>
            <p className="mt-2 text-sm leading-relaxed">{member.office_address}</p>
          </GlassCard>
        </motion.div>
      )}

      {hasContact && (
        <motion.div className="space-y-2" variants={staggerItem}>
          <p className="text-xs font-medium uppercase tracking-wider text-text-tertiary">Contact</p>
          <div className="space-y-2">
            {member.phone && (
              <ContactLink href={`tel:${member.phone}`} icon={Phone} label={member.phone} />
            )}
            {member.official_url && (
              <ContactLink href={member.official_url} icon={Globe} label="Official Website" />
            )}
            {member.contact_form && (
              <ContactLink href={member.contact_form} icon={Mail} label="Contact Form" />
            )}
          </div>
        </motion.div>
      )}

      {hasSocial && (
        <motion.div className="space-y-2" variants={staggerItem}>
          <p className="text-xs font-medium uppercase tracking-wider text-text-tertiary">Social Media</p>
          <div className="space-y-2">
            {member.twitter && (
              <ContactLink
                href={`https://twitter.com/${member.twitter}`}
                icon={Globe}
                label={`@${member.twitter}`}
              />
            )}
            {member.facebook && (
              <ContactLink
                href={`https://facebook.com/${member.facebook}`}
                icon={Globe}
                label={member.facebook}
              />
            )}
            {member.youtube && (
              <ContactLink
                href={`https://youtube.com/${member.youtube}`}
                icon={Globe}
                label={member.youtube}
              />
            )}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

export function MemberDetailPage() {
  const { bioguideId } = useParams()
  const { data: member, isLoading } = useMember(bioguideId!)

  if (isLoading) {
    return (
      <motion.div className="space-y-8" {...pageTransition}>
        <HeroSkeleton />
        <StatsSkeleton />
      </motion.div>
    )
  }

  if (!member) {
    return (
      <motion.div {...pageTransition}>
        <EmptyState title="Member not found" description="We couldn't find a member with that ID." />
      </motion.div>
    )
  }

  return (
    <motion.div className="space-y-8" {...pageTransition}>
      {/* Hero */}
      <GlassCard className="!p-8">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
          <MemberAvatar
            imageUrl={member.image_url}
            name={member.full_name}
            party={member.party}
            size="lg"
          />
          <div className="text-center sm:text-left">
            <h1 className="text-2xl font-bold tracking-tight">{member.full_name}</h1>
            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <PartyBadge party={member.party} showLabel />
              <ChamberBadge chamber={member.chamber} />
              <span className="text-sm text-text-secondary">
                {formatState(member.state, member.district, member.chamber)}
              </span>
            </div>
            {member.leadership_role && (
              <p className="mt-2 text-sm font-medium text-text-secondary">{member.leadership_role}</p>
            )}
            {member.start_date && (
              <p className="mt-1 text-xs text-text-tertiary">Serving since {formatDate(member.start_date)}</p>
            )}
          </div>
        </div>
      </GlassCard>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <StatCard
          label="Party Loyalty"
          value={formatPercent(member.party_loyalty_pct)}
          sublabel="Votes with party"
        />
        <StatCard
          label="Attendance"
          value={formatPercent(member.attendance_rate)}
          sublabel={`${formatNumber(member.votes_missed)} missed`}
        />
        <StatCard
          label="Bills Sponsored"
          value={formatNumber(member.bills_sponsored)}
          sublabel={`${formatNumber(member.bills_passed)} passed`}
        />
        <StatCard
          label="Bills Enacted"
          value={formatNumber(member.bills_enacted)}
          sublabel="Signed into law"
        />
        <StatCard
          label="Activity Score"
          value={member.activity_score !== null ? member.activity_score.toFixed(0) : '\u2014'}
          sublabel="Out of 100"
        />
        <StatCard
          label="Success Rate"
          value={formatPercent(member.sponsor_success_rate)}
          sublabel="Sponsored bills passed"
        />
      </div>

      {/* Tabbed Content */}
      <Tabs defaultValue="votes">
        <TabsList variant="line" className="mb-6 w-full justify-start">
          <TabsTrigger value="votes">Votes</TabsTrigger>
          <TabsTrigger value="bills">Bills</TabsTrigger>
          <TabsTrigger value="committees">
            Committees
            {member.committees.length > 0 && (
              <span className="ml-1.5 text-text-tertiary">{member.committees.length}</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="contact">Contact</TabsTrigger>
        </TabsList>

        <TabsContent value="votes">
          <VotesTab bioguideId={bioguideId!} />
        </TabsContent>

        <TabsContent value="bills">
          <BillsTab bioguideId={bioguideId!} />
        </TabsContent>

        <TabsContent value="committees">
          <CommitteesTab committees={member.committees} />
        </TabsContent>

        <TabsContent value="contact">
          <ContactTab member={member} />
        </TabsContent>
      </Tabs>
    </motion.div>
  )
}
