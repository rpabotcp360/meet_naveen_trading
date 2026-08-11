Get-Process -Name "node","python" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*Trading*"
} | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "Stopped Trading processes (if any were running)." -ForegroundColor Yellow
