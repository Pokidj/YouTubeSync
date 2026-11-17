# YouTubeSync

Version final 1.0 de YouTubeSync basada en PySide6/Qt.

Este proyecto es independiente de la version estable en `outputs/youtube-sync`.
La app reutiliza el motor probado de la version estable para:

- Configuracion y registro local.
- OAuth de YouTube.
- Subida en segundo plano.
- Consulta del canal.

## Ejecutar en desarrollo

```powershell
.\.venv\Scripts\python.exe .\src\youtube_sync_modern.py
```

## Compilar

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\build_exe.ps1
```

El ejecutable final quedara en:

```text
dist\YouTubeSync\YouTubeSync.exe
```
