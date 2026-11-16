/**
 * Design-token regression tests (node env, reads global.css from disk).
 *
 * These guard the exact failure mode that made the old UI render broken:
 * Tailwind 4 utility classes silently no-op when their theme tokens are
 * undefined (the v3 tailwind.config.js was never loaded by v4). If one
 * of these tests fails, a whole page has gone visually broken — not
 * just "less pretty".
 */

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const rawCss = readFileSync(new URL('./global.css', import.meta.url), 'utf-8')
/** Comments may *mention* fonts for documentation; only real @imports fail. */
const css = rawCss.replace(/\/\*[\s\S]*?\*\//g, '')

describe('global.css design tokens', () => {
  it('loads the stylesheet', () => {
    expect(css.length).toBeGreaterThan(1000)
  })

  it('maps the theme via @theme inline so utilities flip with .dark', () => {
    expect(css).toContain('@theme inline')
    expect(css).toContain('@custom-variant dark')
    // semantic aliases used across pages
    for (const token of [
      '--color-bg', '--color-surface', '--color-text',
      '--color-primary', '--color-primary-contrast',
      '--color-success', '--color-danger', '--color-warning',
      '--shadow-strong',
    ]) {
      expect(css).toContain(token)
    }
  })

  it('defines the primary 50–900 scale used by primary-* classes', () => {
    for (const step of [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]) {
      expect(css).toContain(`--color-primary-${step}`)
    }
    // and the dark overrides flip the scale
    expect(css).toMatch(/\.dark\s*\{[^}]*--p600/s)
  })

  it('defines keyframes for every custom animate-* token', () => {
    for (const name of ['fade-in', 'slide-up', 'scale-in', 'count-pop', 'shimmer', 'toast-in', 'typing', 'page-enter', 'float-particle']) {
      expect(css).toMatch(new RegExp(`@keyframes\\s+${name}\\b`))
      expect(css).toContain(`--animate-${name}`)
    }
  })

  it('ships the ambient background layers (gradient flow + particles)', () => {
    expect(css).toMatch(/@keyframes\s+gradient-flow\b/)
    expect(css).toMatch(/\.app-bg\s*\{/)
    expect(css).toMatch(/\.app-bg-gradient\s*\{[^}]*gradient-flow/s)
    expect(css).toMatch(/\.particle\s*\{[^}]*float-particle/s)
    // both themes provide particle colors (light dust / dark fireflies)
    expect(css).toMatch(/:root\s*\{[^}]*--particle-1/s)
    expect(css).toMatch(/\.dark\s*\{[^}]*--particle-1/s)
  })

  it('frosted-glass cards with a solid variant for data-dense surfaces', () => {
    expect(css).toMatch(/\.card\s*\{[^}]*backdrop-filter/s)
    expect(css).toMatch(/\.card-solid\s*\{[^}]*backdrop-filter/s)
    expect(css).toMatch(/--card-border/)
  })

  it('defines the responsive page container (phone → desktop widths)', () => {
    expect(css).toMatch(/\.page-container\s*\{/)
    expect(css).toMatch(/@media \(min-width: 1024px\)/)
    expect(css).toMatch(/@media \(min-width: 1280px\)/)
  })

  it('styles the .input class (all forms depend on it)', () => {
    expect(css).toMatch(/\.input,\s*\n\s*\.input-field\s*\{/)
  })

  it('never imports web fonts (mainland-China direct-connect deployment)', () => {
    expect(css).not.toContain('fonts.googleapis.com')
    expect(css).not.toContain('@import url(')
    expect(css).toContain('--font-sans')
  })

  it('defines the safe-area helpers used by the bottom navigation', () => {
    expect(css).toMatch(/\.safe-area-bottom\s*\{[^}]*env\(safe-area-inset-bottom\)/s)
  })

  it('respects prefers-reduced-motion', () => {
    expect(css).toContain('@media (prefers-reduced-motion: reduce)')
  })
})
