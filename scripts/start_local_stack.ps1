param(
    [int]$DockerWaitSeconds = 180,
    [int]$HealthWaitSeconds = 300,
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Test-DockerReady {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        docker info 1>$null 2>$null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Start-DockerDesktop {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        docker desktop start 1>$null 2>$null
        if ($LASTEXITCODE -eq 0) {
            return
        }
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    $candidates = @(
        (Join-Path $env:ProgramFiles "Docker/Docker/Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Docker/Docker Desktop.exe")
    )
    $executable = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $executable) {
        throw "Docker Desktop is not installed in a known location."
    }
    Start-Process -FilePath $executable -WindowStyle Hidden
}

function Wait-DockerReady {
    if (-not (Test-DockerReady)) {
        Start-DockerDesktop
    }
    $deadline = (Get-Date).AddSeconds($DockerWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerReady) {
            return
        }
        Start-Sleep -Seconds 3
    }
    throw "Docker did not become ready within $DockerWaitSeconds seconds."
}

function Get-DotEnvValue([string]$Name) {
    $line = Get-Content -LiteralPath (Join-Path $Root ".env") |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=" } |
        Select-Object -Last 1
    if (-not $line) {
        return $null
    }
    return ($line -split "=", 2)[1].Trim().Trim('"')
}

function Wait-DatabaseHealthy {
    $deadline = (Get-Date).AddSeconds($HealthWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        $containerId = docker compose ps -q database
        if ($LASTEXITCODE -eq 0 -and $containerId) {
            $status = docker inspect --format "{{.State.Health.Status}}" $containerId 2>$null
            if ($status -eq "healthy") {
                return
            }
        }
        Start-Sleep -Seconds 3
    }
    throw "PostgreSQL did not become healthy within $HealthWaitSeconds seconds."
}

function Sync-DatabasePassword {
    $password = Get-DotEnvValue "WANDERMIND_POSTGRES_PASSWORD"
    if (-not $password -or $password -notmatch "^[A-Za-z0-9_-]{16,128}$") {
        throw "WANDERMIND_POSTGRES_PASSWORD must contain 16-128 safe characters."
    }
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        "ALTER ROLE wandermind WITH PASSWORD '$password';" |
            docker compose exec -T database psql -v ON_ERROR_STOP=1 -U wandermind -d postgres 1>$null 2>$null
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "Unable to synchronize the PostgreSQL role password."
    }
}

function Wait-ApplicationHealthy {
    $deadline = (Get-Date).AddSeconds($HealthWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -TimeoutSec 10
            if (
                $health.status -eq "ok" -and
                $health.autopilot_worker_running -eq $true -and
                $health.guardian.running -eq $true
            ) {
                return $health
            }
        } catch {
        }
        Start-Sleep -Seconds 3
    }
    throw "WanderMind did not become healthy within $HealthWaitSeconds seconds."
}

if (-not (Test-Path -LiteralPath (Join-Path $Root ".env"))) {
    throw "Missing $Root/.env. Configure local secrets before starting WanderMind."
}
$runtimeAdapter = Get-DotEnvValue "WANDERMIND_RUNTIME_ADAPTER"
$apiKey = Get-DotEnvValue "WANDERMIND_LLM_API_KEY"
if ($runtimeAdapter -eq "openai" -and (-not $apiKey -or $apiKey.Length -lt 10)) {
    throw "WANDERMIND_LLM_API_KEY is required for the openai runtime adapter."
}
$apiKey = $null

Push-Location $Root
try {
    Wait-DockerReady
    docker compose up -d database
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to start PostgreSQL."
    }
    Wait-DatabaseHealthy
    Sync-DatabasePassword

    if ($Build) {
        docker compose up -d --build
    } else {
        docker compose up -d
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to start WanderMind."
    }

    $health = Wait-ApplicationHealthy
    Write-Host "WanderMind is healthy at http://127.0.0.1:8080/"
    Write-Host "Runtime: $($health.runtime); Autopilot: $($health.autopilot_worker_running); Guardian: $($health.guardian.running)"
} finally {
    Pop-Location
}
