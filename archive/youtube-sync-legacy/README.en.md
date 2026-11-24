# YouTubeSync (Archived)

[Español](README.md) | **English**

**Historical interface, not actively developed.** Current development/builds
are in `outputs/youtube-sync-modern`; use root `Abrir-YouTubeSync.cmd` for that app.
This document describes the old version, not the current verification guarantees.

## Historical Features

The Windows desktop app watched a configurable video folder and uploaded new or
pending files with creation-date titles such as `2025-06-18 14:32:05`. It kept
local duplicate-prevention history and also checked existing YouTube titles.
It had first-run setup, background operation while open, connection/channel
status, configurable extensions/scan/stability, named categories and playlists.

ON/OFF controlled scanning/uploads. Upload pending enabled Auto and requested
missing files; OFF requested cancellation after the current chunk. A progress
bar showed the current transfer. The Videos view had Pending, Uploaded and Issue
sections, plus folder/upload/pending/today-attempt counts. Refresh checked YouTube
and rescanned with Auto ON. Successful uploads moved from Pending to Uploaded.

No app-defined daily cap was imposed; only real API/project/channel responses
paused uploads. Persistent countdowns scheduled retries, estimated where needed.
A green/red indicator showed readiness/problems. Automatic local deletion after
configurable hours checked remote existence/content and local stability.

Settings had organized sections, scrolling/mouse-wheel support for small screens,
Windows startup options and a step-by-step OAuth JSON assistant that validated
and copied credentials into the app data directory. Large-folder scanning skipped
recently modified files without per-file waiting. Uploaded lists combined current
folder, permanent registry and channel checks. Console could be cleared without
touching persistent duplicate-prevention or upload records.

## Requirements and OAuth

Python 3.10+, your own Google Cloud Desktop app OAuth JSON (for example
`client_secret.json`) and YouTube Data API v3 enabled in that project.

1. Open Google Cloud Console and create/select a project.
2. Enable YouTube Data API v3.
3. Create an OAuth client ID of type Desktop app.
4. Download the JSON and select it on first launch.

## Historical Development and Build

Run inside this archived directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\src\youtube_sync_app.py
.\build_exe.ps1
```

The historical EXE is `dist\YouTubeSync\YouTubeSync.exe`. If it is locked, exit
through its tray menu before rebuilding. Do not confuse it with the active Qt app.

## Historical Behavior and Limitations

- The app had to remain running; minimizing kept it working through the tray.
- First authorization opened a browser. Configuration, token and database used
  `%APPDATA%\YouTubeSync`.
- Cleanup deleted only local files, never YouTube videos. It checked unchanged
  local identity and exact stored video ID; when missing, the old code attempted
  title recovery. This title-only recovery is **not** the current protocol.
- Manual cleanup showed verification results and asked confirmation, keeping
  discrepancies. Automatic cleanup aborted the whole batch on any mismatch.
- OAuth `youtube` scope supported uploads, reads and playlists. Permission changes
  could request consent again. The JSON assistant guided credential preparation,
  validation and managed copying.
- YouTube supplied no channel remaining-upload counter. Local attempts were never
  used as an artificial blocking limit.
- Retry-After was respected. Project daily quota used estimated Pacific midnight;
  channel `uploadLimitExceeded` used a conservative estimated 24-hour window.

For current identity, persistence and cleanup rules, read the
[active verification documentation](../../docs/UPLOAD_VERIFICATION.en.md).
