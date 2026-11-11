#!/usr/bin/env node
/**
 * Generate TypeScript types from OpenAPI schema
 */

import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { resolve } from 'path';

const OPENAPI_PATH = resolve(__dirname, '../contracts/openapi.json');
const OUTPUT_PATH = resolve(__dirname, '../apps/web/src/api/generated/schema.ts');

async function generateTypes() {
  console.log('🔄 Generating TypeScript types from OpenAPI schema...');

  // Check if OpenAPI schema exists
  if (!existsSync(OPENAPI_PATH)) {
    console.error('❌ OpenAPI schema not found at:', OPENAPI_PATH);
    console.log('💡 Run: python scripts/export_openapi.py');
    process.exit(1);
  }

  try {
    // Generate types using openapi-typescript
    execSync(
      `npx openapi-typescript ${OPENAPI_PATH} -o ${OUTPUT_PATH}`,
      { stdio: 'inherit' }
    );

    console.log('✅ TypeScript types generated successfully!');
    console.log('📁 Output:', OUTPUT_PATH);
  } catch (error) {
    console.error('❌ Failed to generate types:', error.message);
    process.exit(1);
  }
}

generateTypes();
