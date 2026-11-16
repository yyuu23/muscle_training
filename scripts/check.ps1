# Unified checks: backend lint+unit tests, frontend lint+typecheck+unit tests
# Usage: .\scripts\check.ps1 [-SkipBackend] [-SkipFrontend]

param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$failed = $false

if (-not $SkipBackend) {
    Write-Host "==> Ruff..."
    Push-Location $root
    uv run --project apps/api ruff check apps/api
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Pop-Location

    Write-Host "==> Backend unit tests..."
    Push-Location (Join-Path $root "apps/api")
    uv run pytest tests/unit -m "not integration and not live" -q
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Pop-Location
}

if (-not $SkipFrontend) {
    Write-Host "==> Frontend lint + typecheck + unit tests..."
    Push-Location $root
    pnpm --filter @fitness/web lint
    if ($LASTEXITCODE -ne 0) { $failed = $true }

    pnpm --filter @fitness/web typecheck
    if ($LASTEXITCODE -ne 0) { $failed = $true }

    pnpm --filter @fitness/web test -- --run
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Pop-Location
}

if ($failed) {
    Write-Host "[FAIL] Some checks did not pass" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] All checks passed"
