@echo off
setlocal
set "APP_DIR=%~dp0dist\YouTubeSync"
if not exist "%APP_DIR%\_internal\python312.dll" goto missing
start "" "%APP_DIR%\YouTubeSync.exe"
exit /b 0
:missing
echo Falta la compilacion completa. Ejecuta build_exe.ps1 primero.
echo No ejecutes los archivos de la carpeta build.
pause
exit /b 1
