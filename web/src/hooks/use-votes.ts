import { useQuery } from '@tanstack/react-query'
import { listVotes, getVote, getVotePositions } from '@/api/votes'
import type { ListVotesParams } from '@/api/votes'

export function useVotes(params?: ListVotesParams) {
  return useQuery({
    queryKey: ['votes', params],
    queryFn: () => listVotes(params),
  })
}

export function useVote(voteId: string) {
  return useQuery({
    queryKey: ['votes', voteId],
    queryFn: () => getVote(voteId),
    enabled: !!voteId,
  })
}

export function useVotePositions(voteId: string, params?: { party?: string; position?: string }) {
  return useQuery({
    queryKey: ['votes', voteId, 'positions', params],
    queryFn: () => getVotePositions(voteId, params),
    enabled: !!voteId,
  })
}
