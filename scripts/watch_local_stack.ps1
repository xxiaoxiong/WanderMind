param(
    [string]$HealthUrl = "http://127.0.0.1:8080/health"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RuntimeDirectory = Join-Path $Root "runtime"
$LogPath = Join-Path $RuntimeDirectory "watchdog.log"
New-Item -ItemType Directory -Force -Path $RuntimeDirectory | Out-Null

function Write-WatchdogLog([string]$Message) {
    Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "$(Get-Date -Format o) $Message"
}

$mutex = New-Object System.Threading.Mutex($false, "Local\WanderMindStackGuardian")
$lockTaken = $false
try {
    $lockTaken = $mutex.WaitOne(0)
    if (-not $lockTaken) {
        exit 0
    }

    $healthy = $false
    try {
        $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 10
        $healthy = (
            $health.status -eq "ok" -and
            $health.autopilot_worker_running -eq $true -and
            $health.guardian.running -eq $true
        )
    } catch {
        Write-WatchdogLog "Health probe failed: $($_.Exception.Message)"
    }

    if (-not $healthy) {
        Write-WatchdogLog "Repairing the local stack."
        & (Join-Path $PSScriptRoot "start_local_stack.ps1")
        Write-WatchdogLog "Local stack repair completed."
    }
} catch {
    Write-WatchdogLog "Guardian error: $($_.Exception.Message)"
    throw
} finally {
    if ($lockTaken) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
