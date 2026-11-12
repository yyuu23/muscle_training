# Windows 周备份下载计划任务（plan §9.7）
# - 每周执行一次；错过（关机）后尽快补执行
# - 隐藏窗口运行；凭据放用户权限限制的配置文件，不放命令行参数
#
# 用法：
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

# 动作：下载脚本 + 输出目录重定向到日志（凭据从用户配置文件/环境变量读取）
$action = New-ScheduledTaskAction -Execute $python -Argument """$DownloadScript"" --output-dir ""$OutputDir""" -WorkingDirectory (Split-Path -Parent $DownloadScript)

# 触发器：每周一 09:00，错过尽快补执行（StartWhenAvailable）
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $RunAt
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# 隐藏窗口运行
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "[OK] 计划任务已安装: $TaskName"
Write-Host "     每周一 $RunAt 下载到 $OutputDir（错过后开机尽快补执行）"
Write-Host ""
Write-Host "凭据配置（用户权限限制，不入命令行）："
Write-Host "  1. 复制 .env.example 中备份相关变量到 `$HOME\.muscle_training\backup.conf"
Write-Host "     [backup]"
Write-Host "     OSS_ENDPOINT=..."
Write-Host "     OSS_ACCESS_KEY_ID=...(只读备份凭据)"
Write-Host "     OSS_ACCESS_KEY_SECRET=..."
Write-Host "     BACKUP_BUCKET=..."
Write-Host "  2. icacls `"$env:USERPROFILE\.muscle_training\backup.conf`" /inheritance:r /grant:r `"${env:USERNAME}:R`""
Write-Host ""
Write-Host "age 私钥保存在本机或离线位置；云端只有公钥。"
