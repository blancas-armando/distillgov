import { Link } from 'react-router'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { MemberAvatar } from './member-avatar'
import { PartyBadge } from './party-badge'
import { ChamberBadge } from './chamber-badge'
import { formatState } from '@/lib/format'
import type { Member } from '@/api/types'

type MemberCardProps = {
  member: Member
  className?: string
}

export function MemberCard({ member, className }: MemberCardProps) {
  return (
    <Link to={`/members/${member.bioguide_id}`}>
      <Card className={cn('gap-0 py-0 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5', className)}>
        <CardContent className="flex items-center gap-4 p-4">
          <MemberAvatar
            imageUrl={member.image_url}
            name={member.full_name}
            party={member.party}
            size="md"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{member.full_name}</p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <PartyBadge party={member.party} />
              <ChamberBadge chamber={member.chamber} />
              <span className="text-xs text-muted-foreground">
                {formatState(member.state, member.district, member.chamber)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
