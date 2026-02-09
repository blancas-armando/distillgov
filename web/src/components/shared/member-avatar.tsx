import { useState } from 'react'
import { cn } from '@/lib/utils'

type MemberAvatarProps = {
  imageUrl: string | null
  name: string | null
  party: string | null
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeClasses = {
  sm: 'h-10 w-10 text-xs',
  md: 'h-14 w-14 text-sm',
  lg: 'h-20 w-20 text-lg',
}

const ringClasses = {
  D: 'ring-dem',
  R: 'ring-rep',
  I: 'ring-ind',
}

export function MemberAvatar({ imageUrl, name, party, size = 'md', className }: MemberAvatarProps) {
  const [failed, setFailed] = useState(false)

  const initials = name
    ? name.split(' ').map(w => w[0]).filter(Boolean).slice(0, 2).join('')
    : '?'

  const ringColor = party ? ringClasses[party as keyof typeof ringClasses] ?? 'ring-neutral-300' : 'ring-neutral-300'

  return (
    <div
      className={cn(
        'relative flex items-center justify-center overflow-hidden rounded-full bg-neutral-100 ring-2',
        ringColor,
        sizeClasses[size],
        className,
      )}
    >
      {imageUrl && !failed ? (
        <img
          src={imageUrl}
          alt={name ?? 'Member'}
          className="h-full w-full object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="font-medium text-text-secondary">{initials}</span>
      )}
    </div>
  )
}
