// Pending lead-review decisions, kept in the browser until applied in one batch.
import type { Choice, Decision } from './api'

export interface Pending {
  id: number
  decision: Choice
  ticked: string[] // in reasons-list order
  text: string
}

const KEY = 'review.pending'

/** First lead without a pending decision. Decisions follow queue order, so undo = drop the last one. */
export const currentLead = (leadIds: number[], pending: Pending[]): number | undefined => {
  const decided = new Set(pending.map((p) => p.id))
  return leadIds.find((id) => !decided.has(id))
}

export const combineReason = (ticked: string[], text: string): string | null =>
  [...ticked, text.trim()].filter(Boolean).join('; ') || null

/** What gets written. Skips are pending only to keep the position; they never write. */
export const toBatch = (pending: Pending[]): Decision[] =>
  pending.flatMap(({ id, decision, ticked, text }) =>
    decision === 'skip' ? [] : [{ id, decision, reason: combineReason(ticked, text) }])

// Storage can be missing or throw (private mode, blocked site data); the React state is then the only copy.
export function loadPending(): Pending[] {
  try {
    const value = JSON.parse(window.localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

export function savePending(pending: Pending[]) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(pending))
  } catch {
    // keep going in memory
  }
}
