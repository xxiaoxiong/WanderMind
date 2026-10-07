param(
    [int]$RetainCount = 56
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BackupDirectory = Join-Path $Root "backups"
$RuntimeDirectory = Join-Path $Root "runtime"
$LogPath = Join-Path $RuntimeDirectory "backup.log"
New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $RuntimeDirectory | Out-Null

try {
    & (Join-Path $PSScriptRoot "backup.ps1")
    Get-ChildItem -LiteralPath $BackupDirectory -Filter "wandermind_*.dump" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip $RetainCount |
        Remove-Item -Force
    Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "$(Get-Date -Format o) Backup and retention completed."
} catch {
    Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "$(Get-Date -Format o) Backup failed: $($_.Exception.Message)"
    throw
}
