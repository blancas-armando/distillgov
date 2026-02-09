import { fetchApi } from './client'
import type { CommitteeList, CommitteeDetail } from './types'

export function listCommittees(params?: { q?: string; chamber?: string; limit?: number; offset?: number }) {
  return fetchApi<CommitteeList>('/committees', { params })
}

export function getCommittee(committeeId: string) {
  return fetchApi<CommitteeDetail>(`/committees/${committeeId}`)
}
