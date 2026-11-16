import { describe, expect, it } from 'vitest'
import { formatDuration, formatWeight } from './format'

describe('formatDuration', () => {
  it('formats seconds below a minute as m:ss', () => {
    expect(formatDuration(0)).toBe('0:00')
    expect(formatDuration(59_000)).toBe('0:59')
  })

  it('formats minutes without leading hour', () => {
    expect(formatDuration(60_000)).toBe('1:00')
    expect(formatDuration(10 * 60_000 + 5_000)).toBe('10:05')
  })

  it('formats hours padded', () => {
    expect(formatDuration(3_600_000)).toBe('1:00:00')
    expect(formatDuration(3_600_000 + 61_000)).toBe('1:01:01')
  })
})

describe('formatWeight', () => {
  it('keeps integers compact', () => {
    expect(formatWeight(80)).toBe('80')
  })
  it('keeps one decimal for fractions', () => {
    expect(formatWeight(72.5)).toBe('72.5')
  })
})
