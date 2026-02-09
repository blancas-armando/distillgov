import { useMembers } from '@/hooks/use-members'
import { MemberCard } from '@/components/shared/member-card'
import { PageHeader } from '@/components/shared/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { FilterSelect } from '@/components/shared/filter-select'
import { US_STATES } from '@/lib/constants'
import { formatNumber } from '@/lib/format'
import { pageTransition, staggerContainer, staggerItem } from '@/lib/animations'
import { motion } from 'framer-motion'
import { useSearchParams } from 'react-router'
import { Card, CardContent } from '@/components/ui/card'

function SkeletonCard() {
  return (
    <Card className="gap-0 py-0">
      <CardContent className="flex items-center gap-4 p-4">
        <div className="h-14 w-14 animate-pulse rounded-full bg-muted" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-32 animate-pulse rounded bg-muted" />
          <div className="flex gap-2">
            <div className="h-5 w-12 animate-pulse rounded-full bg-muted" />
            <div className="h-5 w-14 animate-pulse rounded-full bg-muted" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function MemberDirectory() {
  const [searchParams, setSearchParams] = useSearchParams()

  const chamber = searchParams.get('chamber') ?? ''
  const party = searchParams.get('party') ?? ''
  const state = searchParams.get('state') ?? ''

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

  const { data, isLoading } = useMembers({
    chamber: chamber || undefined,
    party: party || undefined,
    state: state || undefined,
    current: true,
    limit: 60,
  })

  const members = data?.members ?? []
  const total = data?.total ?? 0

  return (
    <motion.div {...pageTransition}>
      <PageHeader title="Members" description="Representatives and Senators in Congress">
        {!isLoading && (
          <span className="text-sm text-muted-foreground">
            {formatNumber(total)} members
          </span>
        )}
      </PageHeader>

      <div className="mb-8 flex flex-wrap items-center gap-3">
        <FilterSelect value={chamber} onChange={(v) => setFilter('chamber', v)}>
          <option value="">All Chambers</option>
          <option value="house">House</option>
          <option value="senate">Senate</option>
        </FilterSelect>

        <FilterSelect value={party} onChange={(v) => setFilter('party', v)}>
          <option value="">All Parties</option>
          <option value="D">Democrat</option>
          <option value="R">Republican</option>
          <option value="I">Independent</option>
        </FilterSelect>

        <FilterSelect value={state} onChange={(v) => setFilter('state', v)}>
          <option value="">All States</option>
          {Object.entries(US_STATES).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </FilterSelect>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 12 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : members.length === 0 ? (
        <EmptyState
          title="No members found"
          description="Try adjusting your filters to see more results."
        />
      ) : (
        <motion.div
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {members.map((member) => (
            <motion.div key={member.bioguide_id} variants={staggerItem}>
              <MemberCard member={member} />
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  )
}
