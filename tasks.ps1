<#
.SYNOPSIS
    BoostRAG — task runner cho Windows PowerShell (Make-equivalent).

.DESCRIPTION
    Wrapper around `docker compose` + dev commands. Chạy `./tasks.ps1 help`
    để xem danh sách task.

.EXAMPLE
    pwsh ./tasks.ps1 up
    pwsh ./tasks.ps1 migrate
    pwsh ./tasks.ps1 migration-new -Name "add foo"

.NOTES
    Requires: Docker Desktop. Tương đương Makefile cho user dùng PowerShell.
#>

param(
    [Parameter(Position = 0)]
    [string]$Task = 'help',

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest,

    [string]$Name
)

$ErrorActionPreference = 'Stop'

function Show-Help {
    Write-Host ""
    Write-Host "BoostRAG — task runner (PowerShell)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:  pwsh ./tasks.ps1 <task> [args]"
    Write-Host ""
    Write-Host "Compose:" -ForegroundColor Yellow
    Write-Host "  up                 Khởi động toàn bộ stack (detached)"
    Write-Host "  up-infra           Chỉ khởi động infra (postgres, qdrant, redis, minio)"
    Write-Host "  down               Stop & remove containers"
    Write-Host "  logs               Tail logs tất cả service"
    Write-Host "  ps                 Liệt kê service đang chạy"
    Write-Host ""
    Write-Host "Backend:" -ForegroundColor Yellow
    Write-Host "  backend-shell      Mở shell trong container backend"
    Write-Host "  migrate            Alembic upgrade head"
    Write-Host "  migration-new      Tạo migration — pwsh ./tasks.ps1 migration-new -Name 'msg'"
    Write-Host "  seed               Seed admin user từ env SEED_ADMIN_*"
    Write-Host "  lint-backend       Ruff lint"
    Write-Host "  format-backend     Ruff format"
    Write-Host "  type-backend       Mypy type-check"
    Write-Host "  test-backend       Pytest"
    Write-Host ""
    Write-Host "Frontend:" -ForegroundColor Yellow
    Write-Host "  frontend-shell     Mở shell trong container frontend"
    Write-Host "  lint-frontend      ESLint"
    Write-Host "  format-frontend    Prettier"
    Write-Host "  type-frontend      TS type-check"
    Write-Host "  test-frontend      Vitest"
    Write-Host ""
    Write-Host "All-in-one:" -ForegroundColor Yellow
    Write-Host "  check              Lint + type + test cả 2 stack"
    Write-Host "  clean              Xóa volumes + caches (CẨN THẬN: mất data dev)"
    Write-Host ""
}

function Invoke-Cmd {
    param([string[]]$ArgList)
    Write-Host "+ $($ArgList -join ' ')" -ForegroundColor DarkGray
    & $ArgList[0] @($ArgList | Select-Object -Skip 1)
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

switch ($Task) {
    'help'            { Show-Help }
    'up'              { Invoke-Cmd @('docker', 'compose', 'up', '-d') }
    'up-infra'        { Invoke-Cmd @('docker', 'compose', 'up', '-d', 'postgres', 'qdrant', 'redis', 'minio', 'minio-init') }
    'down'            { Invoke-Cmd @('docker', 'compose', 'down') }
    'logs'            { Invoke-Cmd @('docker', 'compose', 'logs', '-f', '--tail=100') }
    'ps'              { Invoke-Cmd @('docker', 'compose', 'ps') }

    'backend-shell'   { Invoke-Cmd @('docker', 'compose', 'exec', 'backend', 'bash') }
    'migrate'         { Invoke-Cmd @('docker', 'compose', 'exec', 'backend', 'alembic', 'upgrade', 'head') }
    'migration-new'   {
        if (-not $Name) { throw "Pass migration name with -Name 'msg'" }
        Invoke-Cmd @('docker', 'compose', 'exec', 'backend', 'alembic', 'revision', '--autogenerate', '-m', $Name)
    }
    'seed'            { Invoke-Cmd @('docker', 'compose', 'exec', 'backend', 'python', '-m', 'app.scripts.seed_admin') }
    'lint-backend'    { Invoke-Cmd @('docker', 'compose', 'exec', 'backend', 'ruff', 'check', 'app/', 'tests/') }
    'format-backend'  { Invoke-Cmd @('docker', 'compose', 'exec', 'backend', 'ruff', 'format', 'app/', 'tests/') }
    'type-backend'    { Invoke-Cmd @('docker', 'compose', 'exec', 'backend', 'mypy', 'app/') }
    'test-backend'    { Invoke-Cmd @('docker', 'compose', 'exec', 'backend', 'pytest', '-q') }

    'frontend-shell'  { Invoke-Cmd @('docker', 'compose', 'exec', 'frontend', 'sh') }
    'lint-frontend'   { Invoke-Cmd @('docker', 'compose', 'exec', 'frontend', 'pnpm', 'lint') }
    'format-frontend' { Invoke-Cmd @('docker', 'compose', 'exec', 'frontend', 'pnpm', 'format') }
    'type-frontend'   { Invoke-Cmd @('docker', 'compose', 'exec', 'frontend', 'pnpm', 'type-check') }
    'test-frontend'   { Invoke-Cmd @('docker', 'compose', 'exec', 'frontend', 'pnpm', 'test') }

    'check' {
        & $PSCommandPath lint-backend
        & $PSCommandPath type-backend
        & $PSCommandPath test-backend
        & $PSCommandPath lint-frontend
        & $PSCommandPath type-frontend
        & $PSCommandPath test-frontend
        Write-Host "`n✓ Tất cả check pass" -ForegroundColor Green
    }

    'clean'           { Invoke-Cmd @('docker', 'compose', 'down', '-v') }

    default {
        Write-Host "Unknown task: $Task" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
