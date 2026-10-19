import { describe, expect, it } from 'vitest'

import { combineReason, currentLead, type Pending, toBatch } from './review'

const p = (id: number, decision: Pending['decision'], ticked: string[] = [], text = ''): Pending =>
  ({ id, decision, ticked, text })

describe('currentLead', () => {
  it('is the first lead without a pending decision', () => {
    expect(currentLead([4, 7, 9], [])).toBe(4)
    expect(currentLead([4, 7, 9], [p(4, 'apply'), p(7, 'skip')])).toBe(9)
    expect(currentLead([4, 7, 9], [p(4, 'apply'), p(7, 'skip'), p(9, 'dismiss')])).toBeUndefined()
  })

  it('goes back to the undone lead after dropping the last decision', () => {
    const pending = [p(4, 'apply'), p(7, 'dismiss')]
    expect(currentLead([4, 7, 9], pending.slice(0, -1))).toBe(7)
  })

  it('ignores pending ids that left the queue', () => {
    expect(currentLead([7, 9], [p(4, 'dismiss')])).toBe(7)
  })
})

describe('combineReason', () => {
  it('joins ticked reasons and trimmed free text', () => {
    expect(combineReason(['AI-adjacent', 'boring use case'], ' also too senior ')).toBe(
      'AI-adjacent; boring use case; also too senior',
    )
  })

  it('is null when nothing is given', () => {
    expect(combineReason([], '   ')).toBeNull()
  })
})

describe('toBatch', () => {
  it('drops skips and keeps reasons', () => {
    expect(toBatch([p(1, 'apply'), p(2, 'dismiss', ['consulting']), p(3, 'skip'), p(4, 'apply', [], 'remote ok')])).toEqual([
      { id: 1, decision: 'apply', reason: null },
      { id: 2, decision: 'dismiss', reason: 'consulting' },
      { id: 4, decision: 'apply', reason: 'remote ok' },
    ])
  })
})
