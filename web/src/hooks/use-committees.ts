import { useQuery } from '@tanstack/react-query'
import { listCommittees, getCommittee } from '@/api/committees'

export function useCommittees(params?: { q?: string; chamber?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['committees', params],
    queryFn: () => listCommittees(params),
  })
}

export function useCommittee(committeeId: string) {
  return useQuery({
    queryKey: ['committees', committeeId],
    queryFn: () => getCommittee(committeeId),
    enabled: !!committeeId,
  })
}
