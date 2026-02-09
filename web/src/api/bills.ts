import { fetchApi } from './client'
import type { BillList, BillDetail, BillActionList, BillVoteList, CategoryList, SubjectList } from './types'

export type ListBillsParams = {
  q?: string
  subject?: string
  congress?: number
  status?: string
  bill_type?: string
  policy_area?: string
  sponsor_id?: string
  chamber?: string
  limit?: number
  offset?: number
}

export function listBills(params?: ListBillsParams) {
  return fetchApi<BillList>('/bills', { params })
}

export function getBill(billId: string) {
  return fetchApi<BillDetail>(`/bills/${billId}`)
}

export function getBillActions(billId: string) {
  return fetchApi<BillActionList>(`/bills/${billId}/actions`)
}

export function getBillVotes(billId: string) {
  return fetchApi<BillVoteList>(`/bills/${billId}/votes`)
}

export function getCategories() {
  return fetchApi<CategoryList>('/bills/categories')
}

export function getSubjects(params?: { q?: string; limit?: number; offset?: number }) {
  return fetchApi<SubjectList>('/bills/subjects', { params })
}
