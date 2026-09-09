# PowerShell script to register the ChartAcademy Daily Watcher task in Windows Task Scheduler
$TaskName = "ChartAcademyDailyWatcher"
$ScriptPath = Join-Path $PSScriptRoot "run.py"
$PythonPath = (Get-Command python).Source

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Registering Windows Task Scheduler Job: $TaskName" -ForegroundColor Cyan
Write-Host " Python Executable : $PythonPath" -ForegroundColor Gray
Write-Host " Target Script     : $ScriptPath" -ForegroundColor Gray
Write-Host " Trigger Time      : Daily at 11:58 AM (120s pre-alert before 12:00 PM)" -ForegroundColor Yellow
Write-Host " Mode              : Background (--background flag enabled)" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

# Check if task already exists and unregister it
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Updating existing scheduled task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Define Action: Runs with --background so real daily runs stay quietly behind other apps
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`" --background" -WorkingDirectory $PSScriptRoot

# Define Daily Trigger at 11:58 AM
$Trigger = New-ScheduledTaskTrigger -Daily -At 11:58AM

# Define Settings: Wake computer, run on battery, allow demand run
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1 -Minutes 15)

# Register Scheduled Task under current user
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Autonomous daily ChartAcademy masterclass watcher and points tracker at 12:00 PM IST." | Out-Null

    Write-Host "`nTask '$TaskName' successfully registered!" -ForegroundColor Green
    Write-Host "To view or manage it in Windows Task Scheduler:" -ForegroundColor Gray
    Write-Host "  taskschd.msc -> Task Scheduler Library -> $TaskName" -ForegroundColor Gray
} catch {
    Write-Host "`nError registering task: $_" -ForegroundColor Red
    Write-Host "Note: If required, please run PowerShell as Administrator." -ForegroundColor Yellow
}
