# Start-RADashboard.ps1
# Launcher for the SSM Health RA Tracker dashboard

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppFile   = Join-Path $ScriptDir "ra_dashboard.py"
$Port      = 5050
$Url       = "http://localhost:$Port"

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "    SSM Health RA Tracker" -ForegroundColor White
Write-Host "    Technical Coordinator Dashboard" -ForegroundColor Gray
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""

# ── Check / install Flask ──────────────────────────────────────────────────────
Write-Host "  Checking Flask installation..." -ForegroundColor Gray
$flaskCheck = python -m flask --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Flask not found. Installing..." -ForegroundColor Yellow
    python -m pip install flask
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  ERROR: Failed to install Flask. Please run:" -ForegroundColor Red
        Write-Host "    python -m pip install flask" -ForegroundColor White
        Write-Host ""
        exit 1
    }
    Write-Host "  Flask installed successfully." -ForegroundColor Green
} else {
    Write-Host "  Flask is ready." -ForegroundColor Green
}

Write-Host ""
Write-Host "  Starting server at $Url ..." -ForegroundColor White
Write-Host "  (Press Ctrl+C in this window to stop)" -ForegroundColor Gray
Write-Host ""

# ── Open browser after short delay ────────────────────────────────────────────
$browserJob = Start-Job -ScriptBlock {
    param($url)
    Start-Sleep -Seconds 2
    Start-Process $url
} -ArgumentList $Url

# ── Launch the app (blocks until Ctrl+C) ──────────────────────────────────────
Set-Location $ScriptDir
python $AppFile

# Clean up background job if app exits
Stop-Job $browserJob -ErrorAction SilentlyContinue
Remove-Job $browserJob -ErrorAction SilentlyContinue
