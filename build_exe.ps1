$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = $env:PYTHON
if (-not $Python) { $Python = "python" }
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { & $Python -m venv .venv }
$VenvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $VenvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
& $VenvPython -B scripts/build_brand_assets.py
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron generar los iconos de marca.' }
& $VenvPython -m PyInstaller --noconfirm --distpath "$PSScriptRoot/dist" --workpath "$PSScriptRoot/build" packaging/YouTubeSync.spec
if ($LASTEXITCODE -ne 0) { throw 'No se pudo compilar YouTubeSync.' }
Write-Host "YouTubeSync: $PSScriptRoot/dist/YouTubeSync/YouTubeSync.exe"
