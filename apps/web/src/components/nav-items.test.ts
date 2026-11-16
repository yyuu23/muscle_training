import { describe, expect, it } from 'vitest'
import { PRIMARY_NAV, SECONDARY_NAV, visibleItems } from './nav-items'

describe('nav model (plan §8.1)', () => {
  it('keeps the mobile bottom-bar order: 今日/记录/教练/我的', () => {
    expect(PRIMARY_NAV.map((i) => i.label)).toEqual(['今日', '记录', '教练', '我的'])
    expect(PRIMARY_NAV.map((i) => i.to)).toEqual(['/today', '/history', '/chat', '/settings'])
  })

  it('secondary destinations stay out of the primary bar', () => {
    const routes = PRIMARY_NAV.map((i) => i.to)
    for (const item of SECONDARY_NAV) {
      expect(routes).not.toContain(item.to)
    }
  })

  it('hides admin-only items from members', () => {
    const member = visibleItems(SECONDARY_NAV, 'member')
    expect(member.some((i) => i.adminOnly)).toBe(false)
    expect(member.map((i) => i.to)).toContain('/plans')
  })

  it('shows admin-only items to admins', () => {
    const admin = visibleItems(SECONDARY_NAV, 'admin')
    expect(admin.some((i) => i.adminOnly)).toBe(true)
  })
})
