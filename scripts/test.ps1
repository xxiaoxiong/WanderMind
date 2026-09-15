param([string]$Pnpm = "pnpm.cmd")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Temp = Join-Path $Root ".tmp"
New-Item -ItemType Directory -Force -Path $Temp | Out-Null
$env:TEMP = $Temp
$env:TMP = $Temp

Push-Location (Join-Path $Root "backend")
try {
    & ./.venv/Scripts/python.exe -m ruff format --check .
    & ./.venv/Scripts/python.exe -m ruff check .
    & ./.venv/Scripts/python.exe -m mypy src tests
    & ./.venv/Scripts/python.exe -m pytest -q
} finally {
    Pop-Location
}

Push-Location (Join-Path $Root "frontend")
try {
    & $Pnpm run lint
    & $Pnpm run test
    & $Pnpm run build
    & $Pnpm run test:e2e
} finally {
    Pop-Location
}
