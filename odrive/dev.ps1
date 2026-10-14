# start the backend and the vite dev server together (windows).
#   .\dev.ps1          real device (native usb, falls back to ascii)
#   .\dev.ps1 mock     simulated device
param([string]$mode = "auto")
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:ODRV_MODE = $mode
$env:ODRV_NO_BROWSER = "1"
$backend = Start-Process -PassThru -NoNewWindow -FilePath "$root\backend\.venv\Scripts\python.exe" -ArgumentList "run.py" -WorkingDirectory "$root\backend"
Start-Sleep -Seconds 2
try {
    Push-Location "$root\frontend"
    npm run dev
} finally {
    Pop-Location
    Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
}
