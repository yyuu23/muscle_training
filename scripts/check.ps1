# 统一检查入口：后端 lint+单测，前端 lint+typecheck+单测
# 用法：.\scripts\check.ps1 [-SkipBackend] [-SkipFrontend]

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

    Write-Host "==> 后端单元测试..."
    Push-Location (Join-Path $root "apps/api")
    uv run pytest tests/unit -m "not integration and not live" -q
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Pop-Location
}

if (-not $SkipFrontend) {
    Write-Host "==> 前端 lint + typecheck + 单元测试..."
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
    Write-Host "[FAIL] 存在未通过的检查" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] 全部检查通过"
