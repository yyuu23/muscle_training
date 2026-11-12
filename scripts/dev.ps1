# 开发环境一键启动/停止（plan §11.2）
# 用法：
#   .\scripts\dev.ps1          # 启动 db + api + web + worker
#   .\scripts\dev.ps1 -Stop    # 停止全部开发进程

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
    Write-Host "[OK] 开发进程已停止（数据库容器保留：docker compose -f compose.dev.yml down 可移除）"
    exit 0
}

# 1. 数据库
Write-Host "==> 启动 PostgreSQL (pgvector)..."
docker compose -f (Join-Path $root "compose.dev.yml") up -d db

# 2. 迁移（显式步骤，不随启动自动执行）
Write-Host "==> 执行数据库迁移..."
Push-Location $root
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
Pop-Location

# 3. API
Write-Host "==> 启动 FastAPI (http://127.0.0.1:8000)..."
Start-Process -NoNewWindow uv -ArgumentList @(
    "run", "--project", "apps/api", "uvicorn", "app.main:app",
    "--reload", "--host", "127.0.0.1", "--port", "8000"
) -WorkingDirectory $root

# 4. Worker
if (-not $SkipWorker) {
    Write-Host "==> 启动后台 Worker..."
    Start-Process -NoNewWindow uv -ArgumentList @(
        "run", "--project", "apps/api", "python", "-m", "app.jobs.worker"
    ) -WorkingDirectory $root
}

# 5. 前端
Write-Host "==> 启动 Vite (http://localhost:5173)..."
Start-Process -NoNewWindow pnpm -ArgumentList @("--filter", "@fitness/web", "dev") -WorkingDirectory $root

Write-Host ""
Write-Host "[OK] 开发环境已启动："
Write-Host "    API   http://127.0.0.1:8000/docs"
Write-Host "    Web   http://localhost:5173"
Write-Host "    停止  .\scripts\dev.ps1 -Stop"
