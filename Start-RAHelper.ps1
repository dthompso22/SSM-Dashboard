# Start-RAHelper.ps1
# Starts the local RA data helper so the Refresh Data button works.
# Keep this window open while using the dashboard.

Write-Host ""
Write-Host "RA Helper" -ForegroundColor Cyan
Write-Host "Listening on http://localhost:7474" -ForegroundColor Cyan
Write-Host "Keep this window open. Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

python "$PSScriptRoot\ra_helper.py"
