$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = $env:PYTHON
if (-not $Python) {
    $Python = "python"
}

if (-not (Test-Path ".\.venv")) {
    & $Python -m venv .venv
}

$VenvPython = ".\.venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

& $VenvPython -m PyInstaller `
    --noconfirm `
    --distpath "$Root\dist" `
    --workpath "$Root\build" `
    ".\packaging\YouTubeSync.spec"
if ($LASTEXITCODE -ne 0) { throw "No se pudo compilar YouTubeSync." }

Write-Host ""
Write-Host "EXE creado en: $Root\dist\YouTubeSync\YouTubeSync.exe"
