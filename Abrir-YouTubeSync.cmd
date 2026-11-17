@echo off
setlocal
set "APP_DIR=%~dp0outputs\youtube-sync-modern\dist\YouTubeSync"
if not exist "%APP_DIR%\_internal\python312.dll" goto missing
start "" "%APP_DIR%\YouTubeSync.exe"
exit /b 0
:missing
echo Falta la compilacion de YouTubeSync. Ejecuta build_exe.ps1 primero.
pause
exit /b 1
