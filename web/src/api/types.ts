// Activity
export type ActivityItem = {
  event_type: string
  date: string | null
  title: string
  description: string | null
  bill_id: string | null
  vote_id: string | null
  chamber: string | null
  policy_area: string | null
  result: string | null
}

export type ActivityFeed = {
  items: ActivityItem[]
  total: number
  offset: number
  limit: number
}

export type TrendingSubject = {
  subject: string
  bill_count: number
}

// Members
export type Member = {
  bioguide_id: string
  first_name: string | null
  last_name: string | null
  full_name: string | null
  party: string | null
  state: string | null
  district: number | null
  chamber: string | null
  is_current: boolean | null
  image_url: string | null
  official_url: string | null
}

export type MemberCommittee = {
  committee_id: string
  name: string
  role: string | null
}

export type RecentVote = {
  vote_id: string
  vote_date: string | null
  question: string | null
  position: string
}

export type RecentBill = {
  bill_id: string
  title: string | null
  introduced_date: string | null
  status: string | null
}

export type MemberDetail = Member & {
  phone: string | null
  office_address: string | null
  contact_form: string | null
  twitter: string | null
  facebook: string | null
  youtube: string | null
  leadership_role: string | null
  start_date: string | null
  committees: MemberCommittee[]
  recent_votes: RecentVote[]
  recent_bills: RecentBill[]
  bills_sponsored: number
  bills_enacted: number
  bills_passed: number
  sponsor_success_rate: number
  votes_cast: number
  votes_missed: number
  attendance_rate: number | null
  party_loyalty_pct: number | null
  activity_score: number | null
}

export type MemberComparison = {
  members: MemberDetail[]
  shared_votes: number
  agreement_rate: number | null
  shared_bills_cosponsored: number
}

export type MemberList = {
  members: Member[]
  total: number
  offset: number
  limit: number
}

export type MemberVote = {
  vote_id: string
  vote_date: string | null
  chamber: string | null
  question: string | null
  description: string | null
  result: string | null
  bill_id: string | null
  position: string
}

export type MemberVoteList = {
  votes: MemberVote[]
  total: number
  offset: number
  limit: number
}

export type MemberBill = {
  bill_id: string
  bill_type: string
  bill_number: number
  title: string | null
  introduced_date: string | null
  status: string | null
  policy_area: string | null
  role: string
}

export type MemberBillList = {
  bills: MemberBill[]
  total: number
  offset: number
  limit: number
}

// Bills
export type Bill = {
  bill_id: string
  congress: number
  bill_type: string
  bill_number: number
  title: string | null
  short_title: string | null
  introduced_date: string | null
  sponsor_id: string | null
  sponsor_name: string | null
  sponsor_party: string | null
  policy_area: string | null
  origin_chamber: string | null
  latest_action: string | null
  latest_action_date: string | null
  status: string | null
}

export type BillDetail = Bill & {
  summary: string | null
  full_text_url: string | null
  subjects: string[]
  total_cosponsors: number
  dem_cosponsors: number
  rep_cosponsors: number
  ind_cosponsors: number
}

export type BillList = {
  bills: Bill[]
  total: number
  offset: number
  limit: number
}

export type BillAction = {
  action_date: string | null
  action_text: string | null
  action_type: string | null
  chamber: string | null
}

export type BillActionList = {
  actions: BillAction[]
  total: number
}

export type BillVote = {
  vote_id: string
  vote_date: string | null
  chamber: string | null
  question: string | null
  result: string | null
  yea_count: number | null
  nay_count: number | null
}

export type BillVoteList = {
  votes: BillVote[]
  total: number
}

export type Subject = {
  name: string
  bill_count: number
}

export type SubjectList = {
  subjects: Subject[]
  total: number
}

export type Category = {
  name: string
  bill_count: number
}

export type CategoryList = {
  categories: Category[]
}

// Votes
export type Vote = {
  vote_id: string
  congress: number
  chamber: string
  roll_call: number
  vote_date: string | null
  question: string | null
  description: string | null
  result: string | null
  bill_id: string | null
  yea_count: number | null
  nay_count: number | null
  present_count: number | null
  not_voting: number | null
}

export type VoteList = {
  votes: Vote[]
  total: number
  offset: number
  limit: number
}

export type MemberPosition = {
  bioguide_id: string
  full_name: string | null
  party: string | null
  state: string | null
  position: string
}

export type PartyTally = {
  party: string
  yes: number
  no: number
  present: number
  not_voting: number
  total: number
}

export type VotePositions = {
  vote_id: string
  question: string | null
  result: string | null
  bill_id: string | null
  party_breakdown: PartyTally[]
  positions: MemberPosition[]
  total: number
}

// Committees
export type CommitteeMember = {
  bioguide_id: string
  full_name: string | null
  party: string | null
  state: string | null
  chamber: string | null
  role: string | null
  image_url: string | null
}

export type Committee = {
  committee_id: string
  name: string
  chamber: string | null
  committee_type: string | null
  parent_id: string | null
  url: string | null
  member_count: number
}

export type CommitteeDetail = Committee & {
  members: CommitteeMember[]
}

export type CommitteeList = {
  committees: Committee[]
  total: number
  offset: number
  limit: number
}

// Stats
export type CongressSummary = {
  congress: number
  total_bills: number
  enacted: number
  passed: number
  in_committee: number
  introduced_only: number
  stale: number
  recently_active: number
  enactment_rate_pct: number | null
}

export type PolicyBreakdown = {
  policy_area: string
  congress: number
  total_bills: number
  enacted: number
  passed: number
  in_committee: number
  enactment_rate_pct: number | null
}

export type ChamberComparison = {
  chamber: string | null
  congress: number
  total_bills: number
  enacted: number
  passed: number
  avg_days_pending: number | null
  avg_days_to_enactment: number | null
}

export type PartyBreakdown = {
  party: string | null
  congress: number
  bills_sponsored: number
  enacted: number
  passed: number
  enactment_rate_pct: number | null
}

export type MemberScorecard = {
  bioguide_id: string
  full_name: string | null
  party: string | null
  state: string | null
  chamber: string | null
  bills_sponsored: number
  bills_enacted: number
  bills_passed: number
  sponsor_success_rate: number | null
  votes_cast: number
  votes_missed: number
  attendance_rate: number | null
  party_loyalty_pct: number | null
  activity_score: number | null
}
