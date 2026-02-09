import { createBrowserRouter, RouterProvider } from 'react-router'
import { RootLayout } from '@/components/layout/root-layout'
import { Home } from '@/pages/home'
import { YourReps } from '@/pages/your-reps'
import { MemberDirectory } from '@/pages/member-directory'
import { MemberDetailPage } from '@/pages/member-detail'
import { BillsListPage } from '@/pages/bills-list'
import { BillDetailPage } from '@/pages/bill-detail'
import { VotesListPage } from '@/pages/votes-list'
import { VoteDetailPage } from '@/pages/vote-detail'
import { NotFound } from '@/pages/not-found'

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'reps', element: <YourReps /> },
      { path: 'members', element: <MemberDirectory /> },
      { path: 'members/:bioguideId', element: <MemberDetailPage /> },
      { path: 'bills', element: <BillsListPage /> },
      { path: 'bills/:billId', element: <BillDetailPage /> },
      { path: 'votes', element: <VotesListPage /> },
      { path: 'votes/:voteId', element: <VoteDetailPage /> },
      { path: '*', element: <NotFound /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
