import { defineConfig } from 'vitest/config'
import path from 'path'

/**
 * Vitest — node environment. These are pure-logic + asset regression
 * tests (no DOM); component tests would need jsdom, which is not in the
 * dependency tree yet.
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.{ts,tsx}'],
    globals: true,
  },
})
