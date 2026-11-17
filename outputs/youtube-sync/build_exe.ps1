$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $root

function Get-PythonCommand {
    if ($env:PYTHON -and (Get-Command $env:PYTHON -ErrorAction SilentlyContinue)) {
        return @($env:PYTHON)
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    throw "No encuentro Python. Instala Python 3.10 o superior, o ejecuta: `$env:PYTHON='C:\ruta\a\python.exe'"
}

[string[]]$python = @(Get-PythonCommand)

function Invoke-Python {
    param([string[]]$ArgsList)
    if ($python.Length -gt 1) {
        & $python[0] @($python[1..($python.Length - 1)]) @ArgsList
    } else {
        & $python[0] @ArgsList
    }
}

if (-not (Test-Path ".venv")) {
    Invoke-Python @("-m", "venv", ".venv")
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

& ".\.venv\Scripts\pyinstaller.exe" `
    --noconfirm `
    --clean `
    --windowed `
    --name "YouTubeSync" `
    --icon ".\assets\youtube-sync.ico" `
    --add-data ".\assets\youtube-sync-logo.png;assets" `
    --add-data ".\assets\youtube-sync.ico;assets" `
    ".\src\youtube_sync_app.py"

Write-Host ""
Write-Host "EXE creado en: $root\dist\YouTubeSync\YouTubeSync.exe"
