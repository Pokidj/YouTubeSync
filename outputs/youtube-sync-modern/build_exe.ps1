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
    --windowed `
    --name YouTubeSync `
    --icon ".\assets\youtube-sync.ico" `
    --add-data ".\assets;assets" `
    --add-data "..\youtube-sync\src\youtube_sync_app.py;legacy" `
    --paths "..\youtube-sync\src" `
    --hidden-import youtube_sync_app `
    ".\src\youtube_sync_modern.py"

Write-Host ""
Write-Host "EXE creado en: $Root\dist\YouTubeSync\YouTubeSync.exe"
