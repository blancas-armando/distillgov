import { useQuery } from '@tanstack/react-query'
import { getRecentActivity, getTrendingSubjects } from '@/api/activity'
import type { RecentActivityParams } from '@/api/activity'

export function useRecentActivity(params?: RecentActivityParams) {
  return useQuery({
    queryKey: ['activity', 'recent', params],
    queryFn: () => getRecentActivity(params),
  })
}

export function useTrendingSubjects(params?: { days?: number; limit?: number }) {
  return useQuery({
    queryKey: ['activity', 'trending', params],
    queryFn: () => getTrendingSubjects(params),
  })
}
