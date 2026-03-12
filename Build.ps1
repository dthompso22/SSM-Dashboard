# Build.ps1 — Regenerate the static site shell.
# Run this when you change the layout/code, then /deploy to publish.
#
# To update RA data: just click "Refresh Data" in the live dashboard
# (requires Start-RAHelper.ps1 to be running).

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "Building static site..." -ForegroundColor Cyan
python "$PSScriptRoot\build.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: build.py failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Done!  Static files are in .\dist\" -ForegroundColor Green
Write-Host "Run /deploy in Claude Code to publish to Epic Pages." -ForegroundColor Green
Write-Host ""
