# Start-Dashboard.ps1
# Double-click to launch the RA Dashboard.
# Pulls the latest data, starts the server, opens your browser.
# Close this window to stop the server.

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "  RA Dashboard" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────" -ForegroundColor DarkGray

Write-Host "  Pulling latest from git..." -ForegroundColor Gray
$pull = git pull --rebase 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK" -ForegroundColor Green
} else {
    Write-Host "  WARNING: git pull failed - starting with local data" -ForegroundColor Yellow
}

Write-Host "  Starting server at http://localhost:5050 ..." -ForegroundColor Gray

# Open browser after the server has a moment to start
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 1
    Start-Process "http://localhost:5050"
} | Out-Null

Write-Host ""
python "$PSScriptRoot\ra_dashboard.py"
