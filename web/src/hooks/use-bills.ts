import { useQuery } from '@tanstack/react-query'
import { listBills, getBill, getBillActions, getBillVotes, getCategories, getSubjects } from '@/api/bills'
import type { ListBillsParams } from '@/api/bills'

export function useBills(params?: ListBillsParams) {
  return useQuery({
    queryKey: ['bills', params],
    queryFn: () => listBills(params),
  })
}

export function useBill(billId: string) {
  return useQuery({
    queryKey: ['bills', billId],
    queryFn: () => getBill(billId),
    enabled: !!billId,
  })
}

export function useBillActions(billId: string) {
  return useQuery({
    queryKey: ['bills', billId, 'actions'],
    queryFn: () => getBillActions(billId),
    enabled: !!billId,
  })
}

export function useBillVotes(billId: string) {
  return useQuery({
    queryKey: ['bills', billId, 'votes'],
    queryFn: () => getBillVotes(billId),
    enabled: !!billId,
  })
}

export function useCategories() {
  return useQuery({
    queryKey: ['bills', 'categories'],
    queryFn: getCategories,
  })
}

export function useSubjects(params?: { q?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['bills', 'subjects', params],
    queryFn: () => getSubjects(params),
  })
}
