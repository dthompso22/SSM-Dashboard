# Create-Shortcut.ps1
# Run this once to create a desktop shortcut for the RA Dashboard.
# After it's on your desktop, right-click it -> "Pin to taskbar" for one-click launch.

$ShortcutPath = [Environment]::GetFolderPath('Desktop') + "\RA Dashboard.lnk"
$WshShell     = New-Object -ComObject WScript.Shell
$Shortcut     = $WshShell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath       = "$PSScriptRoot\Launch.bat"
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description      = "Launch RA Dashboard"
$Shortcut.IconLocation     = "shell32.dll,14"

$Shortcut.Save()

Write-Host ""
Write-Host "  Shortcut created on your Desktop: 'RA Dashboard'" -ForegroundColor Green
Write-Host "  To put it on your taskbar: right-click it -> Pin to taskbar" -ForegroundColor Cyan
Write-Host ""
