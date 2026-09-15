param(
    [string]$OutputPath = "",
    [string]$Database = "wandermind",
    [string]$DatabaseUser = "wandermind"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $OutputPath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputPath = Join-Path $Root "backups/wandermind_$timestamp.dump"
}
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
$containerPath = "/tmp/wandermind_backup_$([guid]::NewGuid().ToString('N')).dump"

Push-Location $Root
try {
    docker compose exec -T database pg_dump -U $DatabaseUser -d $Database -Fc -f $containerPath
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed with exit code $LASTEXITCODE" }
    docker compose cp "database:$containerPath" $resolvedOutput
    if ($LASTEXITCODE -ne 0) { throw "docker compose cp failed with exit code $LASTEXITCODE" }
    Write-Host "Backup created: $resolvedOutput"
} finally {
    docker compose exec -T database rm -f $containerPath 2>$null
    Pop-Location
}
