param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,
    [string]$Database = "wandermind",
    [string]$DatabaseUser = "wandermind",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
if (-not $Force) {
    throw "Restore replaces matching database objects. Re-run with -Force after verifying the backup."
}
$Root = Split-Path -Parent $PSScriptRoot
$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
$containerPath = "/tmp/wandermind_restore_$([guid]::NewGuid().ToString('N')).dump"

Push-Location $Root
try {
    docker compose cp $resolvedInput "database:$containerPath"
    if ($LASTEXITCODE -ne 0) { throw "docker compose cp failed with exit code $LASTEXITCODE" }
    docker compose exec -T database pg_restore -U $DatabaseUser -d $Database --clean --if-exists $containerPath
    if ($LASTEXITCODE -ne 0) { throw "pg_restore failed with exit code $LASTEXITCODE" }
    Write-Host "Restore completed from: $resolvedInput"
} finally {
    docker compose exec -T database rm -f $containerPath 2>$null
    Pop-Location
}
