# PowerShell script to create Desktop shortcut for UIG Billing App
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = [System.Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "UIG Billing.lnk"
$TargetPath = Join-Path $AppDir "launch_uig_billing.bat"
$IconPath = Join-Path $AppDir "uig_billing.ico"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $AppDir
$Shortcut.IconLocation = $IconPath
$Shortcut.Description = "US Immigration Group - Legal Billing System"
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.Save()

Write-Host ""
Write-Host "=== Desktop shortcut created ===" -ForegroundColor Green
Write-Host "Location: $ShortcutPath" -ForegroundColor Cyan
Write-Host "Icon: $IconPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click 'UIG Billing' on your Desktop to launch!" -ForegroundColor Yellow
