# build the frontend and package everything into one windows exe (backend/dist/vayn-odrv.exe).
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location "$root\frontend"
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location
Push-Location "$root\backend"
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm vayn-odrv.spec
Pop-Location
