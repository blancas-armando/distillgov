import { useMembersByZip, useMember } from '@/hooks/use-members'
import { GlassCard } from '@/components/shared/glass-card'
import { MemberAvatar } from '@/components/shared/member-avatar'
import { PartyBadge } from '@/components/shared/party-badge'
import { ChamberBadge } from '@/components/shared/chamber-badge'
import { PageHeader } from '@/components/shared/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { cn } from '@/lib/utils'
import { formatPercent, formatNumber, formatState } from '@/lib/format'
import { PARTY_CONFIG } from '@/lib/constants'
import { pageTransition, staggerContainer, staggerItem, easeOut } from '@/lib/animations'
import { motion } from 'framer-motion'
import { Link, useSearchParams } from 'react-router'
import { useState, useEffect } from 'react'
import { MapPin, Search, ArrowRight, Phone, Globe } from 'lucide-react'

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-xl bg-white/40 px-4 py-3">
      <span className="text-lg font-semibold tracking-tight">{value}</span>
      <span className="text-[11px] font-medium text-text-tertiary">{label}</span>
    </div>
  )
}

function RepCardSkeleton() {
  return (
    <GlassCard className="animate-pulse">
      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
        <div className="h-20 w-20 shrink-0 rounded-full bg-neutral-200" />
        <div className="flex-1 space-y-3 text-center sm:text-left">
          <div className="mx-auto h-6 w-40 rounded bg-neutral-200 sm:mx-0" />
          <div className="mx-auto flex gap-2 sm:mx-0">
            <div className="h-5 w-12 rounded-full bg-neutral-200" />
            <div className="h-5 w-16 rounded-full bg-neutral-200" />
          </div>
          <div className="mx-auto h-4 w-24 rounded bg-neutral-100 sm:mx-0" />
        </div>
      </div>
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex flex-col items-center gap-1 rounded-xl bg-white/40 px-4 py-3">
            <div className="h-5 w-12 rounded bg-neutral-200" />
            <div className="h-3 w-16 rounded bg-neutral-100" />
          </div>
        ))}
      </div>
    </GlassCard>
  )
}

function RepCard({ bioguideId }: { bioguideId: string }) {
  const { data: member, isLoading } = useMember(bioguideId)

  if (isLoading || !member) return <RepCardSkeleton />

  const partyConfig = member.party
    ? PARTY_CONFIG[member.party as keyof typeof PARTY_CONFIG]
    : null

  return (
    <GlassCard hover className="group">
      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
        <MemberAvatar
          imageUrl={member.image_url}
          name={member.full_name}
          party={member.party}
          size="lg"
        />

        <div className="min-w-0 flex-1 text-center sm:text-left">
          <h3 className="text-xl font-bold tracking-tight">{member.full_name}</h3>

          <div className="mt-2 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
            <PartyBadge party={member.party} showLabel />
            <ChamberBadge chamber={member.chamber} />
            <span className="text-sm text-text-secondary">
              {formatState(member.state, member.district, member.chamber)}
            </span>
          </div>

          {(member.phone || member.official_url) && (
            <div className="mt-3 flex flex-wrap items-center justify-center gap-4 sm:justify-start">
              {member.phone && (
                <a
                  href={`tel:${member.phone}`}
                  className="flex items-center gap-1.5 text-sm text-text-tertiary transition-colors hover:text-text"
                >
                  <Phone className="h-3.5 w-3.5" />
                  {member.phone}
                </a>
              )}
              {member.official_url && (
                <a
                  href={member.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-sm text-text-tertiary transition-colors hover:text-text"
                >
                  <Globe className="h-3.5 w-3.5" />
                  Website
                </a>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatPill
          label="Party Loyalty"
          value={member.party_loyalty_pct !== null ? formatPercent(member.party_loyalty_pct) : '--'}
        />
        <StatPill
          label="Attendance"
          value={member.attendance_rate !== null ? formatPercent(member.attendance_rate) : '--'}
        />
        <StatPill
          label="Bills Sponsored"
          value={formatNumber(member.bills_sponsored)}
        />
        <StatPill
          label="Activity Score"
          value={member.activity_score !== null ? formatPercent(member.activity_score) : '--'}
        />
      </div>

      {/* View profile link */}
      <Link
        to={`/members/${member.bioguide_id}`}
        className={cn(
          'mt-6 flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-medium transition-all duration-150',
          partyConfig
            ? `${partyConfig.lightBg} ${partyConfig.textColor} hover:opacity-80`
            : 'bg-neutral-100 text-text-secondary hover:bg-neutral-200',
        )}
      >
        View Full Profile
        <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </GlassCard>
  )
}

export function YourReps() {
  const [searchParams, setSearchParams] = useSearchParams()
  const zipFromUrl = searchParams.get('zip') ?? ''
  const [zipInput, setZipInput] = useState(zipFromUrl)
  const [activeZip, setActiveZip] = useState(zipFromUrl.length === 5 ? zipFromUrl : '')

  // Sync when URL changes externally (e.g. navigating from home)
  useEffect(() => {
    if (zipFromUrl.length === 5 && zipFromUrl !== activeZip) {
      setZipInput(zipFromUrl)
      setActiveZip(zipFromUrl)
    }
  }, [zipFromUrl]) // eslint-disable-line react-hooks/exhaustive-deps

  const { data, isLoading, error } = useMembersByZip(activeZip)
  const members = data?.members ?? []

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = zipInput.trim()
    if (trimmed.length === 5 && /^\d{5}$/.test(trimmed)) {
      setActiveZip(trimmed)
      setSearchParams({ zip: trimmed })
    }
  }

  function handleChangeZip() {
    setActiveZip('')
    setZipInput('')
    setSearchParams({})
  }

  // State 1: No active zip — show the hero search
  if (!activeZip) {
    return (
      <motion.div {...pageTransition} className="flex min-h-[60vh] flex-col items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, ease: easeOut }}
          className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-50 to-violet-50"
        >
          <MapPin className="h-7 w-7 text-text-tertiary" />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: easeOut }}
          className="text-center text-3xl font-bold tracking-tight sm:text-4xl"
        >
          Find Your Representatives
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.06, ease: easeOut }}
          className="mx-auto mt-4 max-w-md text-center text-lg text-text-secondary"
        >
          Enter your zip code to see who represents you in Congress
        </motion.p>

        <motion.form
          onSubmit={handleSubmit}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.12, ease: easeOut }}
          className="mt-10 w-full max-w-sm"
        >
          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-tertiary" />
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={5}
              placeholder="Enter zip code"
              value={zipInput}
              onChange={(e) => setZipInput(e.target.value.replace(/\D/g, ''))}
              autoFocus
              className="glass-input w-full rounded-2xl py-4 pl-12 pr-4 text-center text-lg tracking-widest placeholder:tracking-normal placeholder:text-text-tertiary"
            />
          </div>

          <button
            type="submit"
            disabled={zipInput.length !== 5}
            className={cn(
              'mt-4 flex w-full items-center justify-center gap-2 rounded-2xl py-4 text-sm font-medium transition-all duration-200',
              zipInput.length === 5
                ? 'bg-primary text-primary-foreground shadow-lg hover:bg-primary/90'
                : 'cursor-not-allowed bg-muted text-muted-foreground',
            )}
          >
            Find my reps
            <ArrowRight className="h-4 w-4" />
          </button>
        </motion.form>
      </motion.div>
    )
  }

  // State 2: Active zip — show results
  return (
    <motion.div {...pageTransition}>
      <PageHeader
        title="Your Representatives"
        description={`Showing results for ${activeZip}`}
      >
        <button
          onClick={handleChangeZip}
          className="flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-medium text-text-secondary transition-colors hover:bg-white/60 hover:text-text"
        >
          <MapPin className="h-3.5 w-3.5" />
          Change zip
        </button>
      </PageHeader>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RepCardSkeleton />
          <RepCardSkeleton />
          <RepCardSkeleton />
        </div>
      ) : error ? (
        <EmptyState
          title="Zip code lookup unavailable"
          description="Zip-to-district data hasn't been loaded yet. Run 'python -m ingestion.cli sync load-zips' to enable this feature."
        />
      ) : members.length === 0 ? (
        <EmptyState
          title="No representatives found"
          description={`We couldn't find any representatives for zip code ${activeZip}. Please check the zip code and try again.`}
        />
      ) : (
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="grid grid-cols-1 gap-6 lg:grid-cols-2"
        >
          {members.map((member) => (
            <motion.div key={member.bioguide_id} variants={staggerItem}>
              <RepCard bioguideId={member.bioguide_id} />
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  )
}
