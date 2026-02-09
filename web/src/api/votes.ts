import { fetchApi } from './client'
import type { VoteList, Vote, VotePositions } from './types'

export type ListVotesParams = {
  congress?: number
  chamber?: string
  result?: string
  bill_id?: string
  passage_only?: boolean
  limit?: number
  offset?: number
}

export function listVotes(params?: ListVotesParams) {
  return fetchApi<VoteList>('/votes', { params })
}

export function getVote(voteId: string) {
  return fetchApi<Vote>(`/votes/${voteId}`)
}

export function getVotePositions(voteId: string, params?: { party?: string; position?: string }) {
  return fetchApi<VotePositions>(`/votes/${voteId}/positions`, { params })
}
