# Windows weekly backup-download scheduled task (plan §9.7)
# - Runs weekly; runs ASAP after a missed start (machine was off)
# - Hidden window; credentials live in a user-restricted config file,
#   never on the command line.
#
# Usage:
#   .\scripts\install_backup_task.ps1 -DownloadScript <abs-path>\download_backup.py -OutputDir D:\backups\muscle

param(
    [Parameter(Mandatory = $true)]
    [string]$DownloadScript,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [string]$TaskName = "MuscleTrainingBackupDownload",
    [string]$RunAt = "MON 09:00"
)

$ErrorActionPreference = "Stop"

$python = (Get-Command python).Source

# Hidden window: run python via powershell -WindowStyle Hidden
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -Command ""& '$python' '$DownloadScript' --output-dir '$OutputDir'"" " `
    -WorkingDirectory (Split-Path -Parent $DownloadScript)

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $RunAt
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Hidden window
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "[OK] Scheduled task installed: $TaskName"
Write-Host "     Every Monday $RunAt downloads to $OutputDir (catches up ASAP after a missed run)"
Write-Host ""
Write-Host "Credentials (user-restricted, never on the command line):"
Write-Host "  1. Create $env:USERPROFILE\.muscle_training\backup.conf with:"
Write-Host "     [backup]"
Write-Host "     OSS_ENDPOINT=..."
Write-Host "     OSS_ACCESS_KEY_ID=...(read-only backup credentials)"
Write-Host "     OSS_ACCESS_KEY_SECRET=..."
Write-Host "     BACKUP_BUCKET=..."
Write-Host "  2. Lock it down:"
Write-Host "     icacls ""$env:USERPROFILE\.muscle_training\backup.conf"" /inheritance:r /grant:r ""${env:USERNAME}:R"""
Write-Host ""
Write-Host "The age private key stays on this machine (or offline); only the public key lives in the cloud."
