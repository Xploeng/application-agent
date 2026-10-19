import { queryOptions } from '@tanstack/react-query'

export const STATUSES = [
  'lead', 'to_apply', 'applied', 'interview', 'offer', 'rejected', 'withdrawn', 'ghosted', 'dismissed',
] as const
export type Status = (typeof STATUSES)[number]

export interface AppRow {
  id: number
  company: string
  role: string
  status: Status
  url: string | null
}

export interface AppDetail extends AppRow {
  location: string | null
  source: string | null
  posting_captured_at: string | null
  posting_text: string | null
  evaluator_reason: string | null
}

export interface ReviewQueue {
  lead_ids: number[]
  reasons: string[]
}

export type Choice = 'apply' | 'dismiss' | 'skip'

export interface Decision {
  id: number
  decision: Exclude<Choice, 'skip'> // a skip never writes anything
  reason: string | null
}

export interface ApplyResult {
  applied: { to_apply: number; dismissed: number; notes: number }
  conflicts: number[]
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const applicationsQuery = queryOptions({
  queryKey: ['applications'],
  queryFn: () => call<AppRow[]>('/api/applications'),
})

export const applicationQuery = (id: number) =>
  queryOptions({
    queryKey: ['application', id],
    queryFn: () => call<AppDetail>(`/api/applications/${id}`),
  })

export const reviewQuery = queryOptions({
  queryKey: ['review'],
  queryFn: () => call<ReviewQueue>('/api/review'),
})

export const postReview = (decisions: Decision[]) =>
  call<ApplyResult>('/api/review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decisions }),
  })
