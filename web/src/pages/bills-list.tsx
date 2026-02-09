import { useBills, useCategories } from '@/hooks/use-bills'
import { PageHeader } from '@/components/shared/page-header'
import { StatusBadge } from '@/components/shared/status-badge'
import { PartyBadge } from '@/components/shared/party-badge'
import { EmptyState } from '@/components/shared/empty-state'
import { FilterSelect } from '@/components/shared/filter-select'
import { Card, CardContent } from '@/components/ui/card'
import { formatDate, formatNumber, formatBillId } from '@/lib/format'
import { pageTransition, staggerContainer, staggerItem } from '@/lib/animations'
import { motion } from 'framer-motion'
import { Link, useSearchParams } from 'react-router'
import { Search, Clock } from 'lucide-react'

function SkeletonCard() {
  return (
    <Card className="gap-0 py-0">
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center justify-between">
          <div className="h-4 w-20 animate-pulse rounded bg-muted" />
          <div className="h-5 w-16 animate-pulse rounded-full bg-muted" />
        </div>
        <div className="h-5 w-full animate-pulse rounded bg-muted" />
        <div className="h-5 w-3/4 animate-pulse rounded bg-muted" />
        <div className="flex items-center gap-3 pt-1">
          <div className="h-5 w-20 animate-pulse rounded-full bg-muted" />
          <div className="h-4 w-24 animate-pulse rounded bg-muted" />
        </div>
      </CardContent>
    </Card>
  )
}

export function BillsListPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const q = searchParams.get('q') ?? ''
  const status = searchParams.get('status') ?? ''
  const policyArea = searchParams.get('policy_area') ?? ''
  const chamber = searchParams.get('chamber') ?? ''

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

  const { data, isLoading } = useBills({
    q: q || undefined,
    status: status || undefined,
    policy_area: policyArea || undefined,
    chamber: chamber || undefined,
    limit: 30,
  })

  const { data: categoriesData } = useCategories()

  const bills = data?.bills ?? []
  const total = data?.total ?? 0
  const categories = categoriesData?.categories ?? []

  return (
    <motion.div {...pageTransition}>
      <PageHeader title="Legislation" description="Bills, resolutions, and joint resolutions in Congress">
        {!isLoading && (
          <span className="text-sm text-muted-foreground">
            {formatNumber(total)} bills
          </span>
        )}
      </PageHeader>

      <div className="mb-6">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={q}
            onChange={(e) => setFilter('q', e.target.value)}
            placeholder="Search bills by title, keyword, or bill number..."
            className="h-10 w-full rounded-lg border border-input bg-card pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1"
          />
        </div>
      </div>

      <div className="mb-8 flex flex-wrap items-center gap-3">
        <FilterSelect value={status} onChange={(v) => setFilter('status', v)}>
          <option value="">All Statuses</option>
          <option value="introduced">Introduced</option>
          <option value="in_committee">In Committee</option>
          <option value="passed_house">Passed House</option>
          <option value="passed_senate">Passed Senate</option>
          <option value="enacted">Enacted</option>
        </FilterSelect>

        <FilterSelect value={policyArea} onChange={(v) => setFilter('policy_area', v)}>
          <option value="">All Policy Areas</option>
          {categories.map((cat) => (
            <option key={cat.name} value={cat.name}>
              {cat.name} ({cat.bill_count})
            </option>
          ))}
        </FilterSelect>

        <FilterSelect value={chamber} onChange={(v) => setFilter('chamber', v)}>
          <option value="">All Chambers</option>
          <option value="house">House</option>
          <option value="senate">Senate</option>
        </FilterSelect>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : bills.length === 0 ? (
        <EmptyState
          title="No bills found"
          description="Try adjusting your search or filters to see more results."
        />
      ) : (
        <motion.div
          className="grid grid-cols-1 gap-3 lg:grid-cols-2"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {bills.map((bill) => (
            <motion.div key={bill.bill_id} variants={staggerItem}>
              <Link to={`/bills/${bill.bill_id}`}>
                <Card className="group gap-0 py-0 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-3">
                      <span className="shrink-0 text-xs font-semibold tracking-wide text-muted-foreground">
                        {formatBillId(bill.bill_type, bill.bill_number)}
                      </span>
                      <StatusBadge status={bill.status} />
                    </div>

                    <h3 className="mt-2 line-clamp-2 text-sm font-semibold leading-snug">
                      {bill.short_title ?? bill.title ?? 'Untitled Bill'}
                    </h3>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {bill.sponsor_name && (
                        <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                          {bill.sponsor_name}
                          <PartyBadge party={bill.sponsor_party} />
                        </span>
                      )}
                    </div>

                    <div className="mt-3 flex items-center justify-between">
                      {bill.policy_area && (
                        <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                          {bill.policy_area}
                        </span>
                      )}

                      {bill.latest_action_date && (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {formatDate(bill.latest_action_date)}
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  )
}
