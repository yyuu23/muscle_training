import { describe, expect, it } from 'vitest'
import { weekdayLabel } from './PlanDiff'
import { formatTimestamp } from './CitationLink'

describe('weekdayLabel', () => {
  it('maps 1..7 to 周一..周日', () => {
    expect(weekdayLabel(1)).toBe('周一')
    expect(weekdayLabel(7)).toBe('周日')
    expect(weekdayLabel(4)).toBe('周四')
  })
  it('falls back for out-of-range values', () => {
    expect(weekdayLabel(9)).toBe('星期9')
  })
})

describe('formatTimestamp (citation timestamps, plan §7.9 ms integers)', () => {
  it('formats milliseconds as mm:ss', () => {
    expect(formatTimestamp(0)).toBe('00:00')
    expect(formatTimestamp(65_000)).toBe('01:05')
    expect(formatTimestamp(754_000)).toBe('12:34')
  })
  it('returns empty string for missing timestamps', () => {
    expect(formatTimestamp(null)).toBe('')
    expect(formatTimestamp(undefined)).toBe('')
  })
})
