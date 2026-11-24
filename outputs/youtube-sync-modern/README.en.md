# YouTubeSync

[Español](README.md) | **English**

YouTubeSync version 1.0, built with PySide6/Qt. This is the only active project.
Its independent engine, `src/youtube_sync_engine.py`, provides configuration,
local records, YouTube OAuth, background uploads and channel queries.

It does not import the previous version kept under `archive`. Use
`Abrir-YouTubeSync.cmd` at the repository root to start the current version.
Spanish is the default; English is selectable in Settings > General > Language
and applies after restarting. See the [user guide](../../docs/USER_GUIDE.en.md).

## Development

```powershell
.\.venv\Scripts\python.exe .\src\youtube_sync_modern.py
```

## Build

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\build_exe.ps1
```

The final executable is `dist\YouTubeSync\YouTubeSync.exe`.
Keep its complete `_internal` folder alongside it.
