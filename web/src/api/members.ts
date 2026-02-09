import { fetchApi } from './client'
import type { MemberList, MemberDetail, MemberComparison, MemberVoteList, MemberBillList } from './types'

export type ListMembersParams = {
  chamber?: string
  party?: string
  state?: string
  current?: boolean
  limit?: number
  offset?: number
}

export function listMembers(params?: ListMembersParams) {
  return fetchApi<MemberList>('/members', { params })
}

export function getMembersByZip(zipCode: string) {
  return fetchApi<MemberList>(`/members/by-zip/${zipCode}`)
}

export function getMember(bioguideId: string) {
  return fetchApi<MemberDetail>(`/members/${bioguideId}`)
}

export function compareMembers(ids: string) {
  return fetchApi<MemberComparison>('/members/compare', { params: { ids } })
}

export type MemberVotesParams = {
  subject?: string
  policy_area?: string
  passage_only?: boolean
  limit?: number
  offset?: number
}

export function getMemberVotes(bioguideId: string, params?: MemberVotesParams) {
  return fetchApi<MemberVoteList>(`/members/${bioguideId}/votes`, { params })
}

export function getMemberBills(bioguideId: string, params?: { role?: string; limit?: number; offset?: number }) {
  return fetchApi<MemberBillList>(`/members/${bioguideId}/bills`, { params })
}
