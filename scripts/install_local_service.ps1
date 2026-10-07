param(
    [switch]$SkipPowerSettings
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$StartupDirectory = [Environment]::GetFolderPath("Startup")
$StartupFile = Join-Path $StartupDirectory "WanderMind.cmd"
$StartScript = Join-Path $PSScriptRoot "start_local_stack.ps1"
$WatchScript = Join-Path $PSScriptRoot "watch_local_stack.ps1"
$BackupScript = Join-Path $PSScriptRoot "backup_and_prune.ps1"

$startupCommand = @"
@echo off
start "" /min powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "$StartScript"
"@
[System.IO.File]::WriteAllText($StartupFile, $startupCommand, (New-Object System.Text.ASCIIEncoding))

$watchAction = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WatchScript`""
$backupAction = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$BackupScript`""

& schtasks.exe /Create /TN "WanderMind Stack Guardian" /SC MINUTE /MO 5 /TR $watchAction /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install the WanderMind Stack Guardian scheduled task."
}
& schtasks.exe /Create /TN "WanderMind Database Backup" /SC HOURLY /MO 6 /TR $backupAction /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install the WanderMind Database Backup scheduled task."
}

if (-not $SkipPowerSettings) {
    powercfg.exe /change standby-timeout-ac 0
    powercfg.exe /change hibernate-timeout-ac 0
}

Write-Host "Startup entry installed: $StartupFile"
Write-Host "Scheduled task installed: WanderMind Stack Guardian"
Write-Host "Scheduled task installed: WanderMind Database Backup"
