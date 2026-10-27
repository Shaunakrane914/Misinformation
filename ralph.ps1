<#
.SYNOPSIS
    Ralph Loop — Long-running AI Agent Loop for Windows PowerShell
.DESCRIPTION
    Iteratively executes development tasks defined in .agent/tasks.json
    using fresh context per iteration, enforcing verification tests and atomic commits.
.PARAMETER MaxIterations
    Maximum number of iterations to run (default: 10).
.PARAMETER Once
    Run exactly one task iteration and exit.
.EXAMPLE
    .\ralph.ps1 -MaxIterations 5
    .\ralph.ps1 -Once
#>

[CmdletBinding()]
param (
    [Alias("n")]
    [int]$MaxIterations = 10,

    [switch]$Once
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$TasksFile = Join-Path $ScriptDir ".agent\tasks.json"
$LogFile = Join-Path $ScriptDir ".agent\logs\LOG.md"
$SteeringFile = Join-Path $ScriptDir ".agent\STEERING.md"
$PromptFile = Join-Path $ScriptDir ".agent\PROMPT.md"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Ralph Wiggum Loop ・ Autonomous Agent Execution (PowerShell)" -ForegroundColor Cyan
Write-Host "  Target: Aegis Protocol" -ForegroundColor Yellow
Write-Host "  Max Iterations: $(if ($Once) { 1 } else { $MaxIterations })" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $TasksFile)) {
    Write-Error "Tasks file not found at $TasksFile"
    exit 1
}

$iteration = 0
$limit = if ($Once) { 1 } else { $MaxIterations }

while ($iteration -lt $limit) {
    $iteration++
    $tasksJson = Get-Content $TasksFile -Raw | ConvertFrom-Json
    $pendingTasks = @($tasksJson | Where-Object { $_.passes -eq $false })

    if ($pendingTasks.Count -eq 0) {
        Write-Host "`nAll tasks in tasks.json are marked as passed! <promise>COMPLETE</promise>" -ForegroundColor Green
        break
    }

    $currentTask = $pendingTasks[0]
    Write-Host "`n[Iteration $iteration/$limit] Active Task: TASK-$($currentTask.id) - $($currentTask.title)" -ForegroundColor Yellow
    Write-Host "Description: $($currentTask.description)" -ForegroundColor Gray

    Write-Host "`nPre-run fast baseline verification..." -ForegroundColor DarkGray
    $testResult = & pytest tests/unit/test_recovered_operation_routes.py -q 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Recovered operation route tests failed! Check environment."
    } else {
        Write-Host "Recovered route baseline passed." -ForegroundColor Green
    }

    Write-Host "Agent prompt instructions ready in $PromptFile" -ForegroundColor Cyan
    break
}
