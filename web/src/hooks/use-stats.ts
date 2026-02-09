import { useQuery } from '@tanstack/react-query'
import { getCongressSummary, getPolicyBreakdown, getChamberComparison, getPartyBreakdown, getMemberScorecard } from '@/api/stats'
import type { MemberScorecardParams } from '@/api/stats'

export function useCongressSummary() {
  return useQuery({
    queryKey: ['stats', 'congress-summary'],
    queryFn: getCongressSummary,
  })
}

export function usePolicyBreakdown(params?: { congress?: number }) {
  return useQuery({
    queryKey: ['stats', 'policy-breakdown', params],
    queryFn: () => getPolicyBreakdown(params),
  })
}

export function useChamberComparison() {
  return useQuery({
    queryKey: ['stats', 'chamber-comparison'],
    queryFn: getChamberComparison,
  })
}

export function usePartyBreakdown() {
  return useQuery({
    queryKey: ['stats', 'party-breakdown'],
    queryFn: getPartyBreakdown,
  })
}

export function useMemberScorecard(params?: MemberScorecardParams) {
  return useQuery({
    queryKey: ['stats', 'member-scorecard', params],
    queryFn: () => getMemberScorecard(params),
  })
}
