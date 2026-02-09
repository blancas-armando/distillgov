import { fetchApi } from './client'
import type { CongressSummary, PolicyBreakdown, ChamberComparison, PartyBreakdown, MemberScorecard } from './types'

export function getCongressSummary() {
  return fetchApi<CongressSummary[]>('/stats/congress-summary')
}

export function getPolicyBreakdown(params?: { congress?: number }) {
  return fetchApi<PolicyBreakdown[]>('/stats/policy-breakdown', { params })
}

export function getChamberComparison() {
  return fetchApi<ChamberComparison[]>('/stats/chamber-comparison')
}

export function getPartyBreakdown() {
  return fetchApi<PartyBreakdown[]>('/stats/party-breakdown')
}

export type MemberScorecardParams = {
  chamber?: string
  party?: string
  state?: string
  sort?: string
  limit?: number
  offset?: number
}

export function getMemberScorecard(params?: MemberScorecardParams) {
  return fetchApi<MemberScorecard[]>('/stats/member-scorecard', { params })
}
