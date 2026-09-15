param(
    [string]$Python = "python",
    [string]$Pnpm = "pnpm.cmd"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

& $Python -m venv (Join-Path $Root "backend/.venv")
& (Join-Path $Root "backend/.venv/Scripts/python.exe") -m pip install --upgrade pip
& (Join-Path $Root "backend/.venv/Scripts/python.exe") -m pip install -e "$Root/backend[dev]"
Push-Location (Join-Path $Root "frontend")
try {
    & $Pnpm install --frozen-lockfile
} finally {
    Pop-Location
}
Write-Host "WanderMind development environment is ready."
