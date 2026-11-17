# YouTubeSync

Version final 1.0 de YouTubeSync basada en PySide6/Qt.

Este es el unico proyecto activo. Incluye su propio motor en
`src/youtube_sync_engine.py` para:

- Configuracion y registro local.
- OAuth de YouTube.
- Subida en segundo plano.
- Consulta del canal.

No importa codigo de la version anterior, conservada en `archive`.
Usa `Abrir-YouTubeSync.cmd` en la raiz del repositorio para abrir esta version.

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
