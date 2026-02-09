import { fetchApi } from './client'
import type { ActivityFeed, TrendingSubject } from './types'

export type RecentActivityParams = {
  subject?: string
  policy_area?: string
  member?: string
  zip_code?: string
  chamber?: string
  days?: number
  limit?: number
  offset?: number
}

export function getRecentActivity(params?: RecentActivityParams) {
  return fetchApi<ActivityFeed>('/activity/recent', { params })
}

export function getTrendingSubjects(params?: { days?: number; limit?: number }) {
  return fetchApi<TrendingSubject[]>('/activity/trending-subjects', { params })
}
