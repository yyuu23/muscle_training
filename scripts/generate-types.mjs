#!/usr/bin/env node
/**
 * Generate TypeScript types from the OpenAPI schema (plan §4.3):
 * contracts/openapi.json → apps/web/src/api/generated/schema.ts
 */

import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const OPENAPI_PATH = resolve(HERE, '../contracts/openapi.json');
const OUTPUT_PATH = resolve(HERE, '../apps/web/src/api/generated/schema.ts');

if (!existsSync(OPENAPI_PATH)) {
  console.error('[FAIL] OpenAPI schema not found at:', OPENAPI_PATH);
  console.error('Run: pnpm contracts:generate (regenerates both) or uv run --project apps/api python -m app.cli export-openapi');
  process.exit(1);
}

console.log('Generating TypeScript types from OpenAPI schema...');
try {
  // Prefer the workspace-local binary; fall back to npx
  const localBin = resolve(HERE, '../node_modules/.bin/openapi-typescript');
  const bin = existsSync(localBin)
    ? localBin
    : 'npx';
  const args = existsSync(localBin)
    ? [OPENAPI_PATH, '-o', OUTPUT_PATH]
    : ['openapi-typescript', OPENAPI_PATH, '-o', OUTPUT_PATH];

  execFileSync(bin, args, { stdio: 'inherit', shell: process.platform === 'win32' });
  console.log('[OK] TypeScript types generated:', OUTPUT_PATH);
} catch (error) {
  console.error('[FAIL] Failed to generate types:', error.message);
  process.exit(1);
}
