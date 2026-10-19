# start the backend and the vite dev server together (windows).
#   .\dev.ps1          real device (native usb, falls back to ascii)
#   .\dev.ps1 mock     simulated device
param([string]$mode = "")
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
# mode comes from backend/.env unless this script is given an argument
if ($mode) { $env:ODRV_MODE = $mode }
# vite is the ui in dev, so do not also open the backend page
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
