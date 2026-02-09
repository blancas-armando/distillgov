import { useQuery } from '@tanstack/react-query'
import { listMembers, getMember, getMembersByZip, getMemberVotes, getMemberBills } from '@/api/members'
import type { ListMembersParams, MemberVotesParams } from '@/api/members'

export function useMembers(params?: ListMembersParams) {
  return useQuery({
    queryKey: ['members', params],
    queryFn: () => listMembers(params),
  })
}

export function useMember(bioguideId: string) {
  return useQuery({
    queryKey: ['members', bioguideId],
    queryFn: () => getMember(bioguideId),
    enabled: !!bioguideId,
  })
}

export function useMembersByZip(zipCode: string) {
  return useQuery({
    queryKey: ['members', 'by-zip', zipCode],
    queryFn: () => getMembersByZip(zipCode),
    enabled: zipCode.length === 5,
  })
}

export function useMemberVotes(bioguideId: string, params?: MemberVotesParams) {
  return useQuery({
    queryKey: ['members', bioguideId, 'votes', params],
    queryFn: () => getMemberVotes(bioguideId, params),
    enabled: !!bioguideId,
  })
}

export function useMemberBills(bioguideId: string, params?: { role?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['members', bioguideId, 'bills', params],
    queryFn: () => getMemberBills(bioguideId, params),
    enabled: !!bioguideId,
  })
}
