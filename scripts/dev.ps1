# Dev environment start/stop (plan §11.2)
# Usage:
#   .\scripts\dev.ps1          # start db + migrate + api + web + worker
#   .\scripts\dev.ps1 -Stop    # stop dev processes (db container kept)
#   .\scripts\dev.ps1 -SkipWorker

param(
    [switch]$Stop,
    [switch]$SkipWorker
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if ($Stop) {
    Get-Process | Where-Object {
        ($_.ProcessName -eq "uvicorn") -or
        ($_.ProcessName -eq "node" -and $_.CommandLine -match "vite") -or
        ($_.ProcessName -eq "python" -and $_.CommandLine -match "app.jobs.worker")
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Dev processes stopped (db container kept: docker compose -f compose.dev.yml down removes it)"
    exit 0
}

# 1. Database
Write-Host "==> Starting PostgreSQL (pgvector)..."
docker compose -f (Join-Path $root "compose.dev.yml") up -d db

# 2. Migrations (explicit step, never auto-run at app startup)
Write-Host "==> Running alembic migrations..."
Push-Location $root
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
Pop-Location

# 3. API
Write-Host "==> Starting FastAPI (http://127.0.0.1:8000)..."
Start-Process -NoNewWindow uv -ArgumentList @(
    "run", "--project", "apps/api", "uvicorn", "app.main:app",
    "--reload", "--host", "127.0.0.1", "--port", "8000"
) -WorkingDirectory $root

# 4. Worker
if (-not $SkipWorker) {
    Write-Host "==> Starting background worker..."
    Start-Process -NoNewWindow uv -ArgumentList @(
        "run", "--project", "apps/api", "python", "-m", "app.jobs.worker"
    ) -WorkingDirectory $root
}

# 5. Frontend (pnpm is a .cmd shim on Windows → run through cmd)
Write-Host "==> Starting Vite..."
Start-Process -NoNewWindow cmd -ArgumentList "/c", "pnpm --filter @fitness/web dev" -WorkingDirectory $root

Write-Host ""
Write-Host "[OK] Dev environment started:"
Write-Host "    API   http://127.0.0.1:8000/docs"
Write-Host "    Web   http://localhost:5173  (check Vite output for the actual port)"
Write-Host "    Stop  .\scripts\dev.ps1 -Stop"
