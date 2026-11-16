/**
 * Test-only type shims. The web app has no @types/node (frontend-only
 * types), but design-tokens.test.ts reads global.css from disk via
 * node:fs under the vitest node environment.
 */

declare module 'node:fs' {
  export function readFileSync(path: string | URL, encoding: string): string
}
