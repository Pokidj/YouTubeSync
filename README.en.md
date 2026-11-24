# YouTubeSync

[Español](README.md) | **English**

A Windows application that watches a folder and uploads videos to YouTube.
Built with PySide6/Qt, with Spanish and English interfaces, automatic uploads,
upload verification, channel management and checked local cleanup.

Current version: **1.0**.

![YouTubeSync](outputs/youtube-sync-modern/assets/youtube-sync-logo.png)

## Documentation

- [User guide](docs/USER_GUIDE.en.md): installation, setup, uploads, channel,
  cleanup and troubleshooting.
- [Development and architecture](docs/DEVELOPMENT.en.md): structure, running,
  building, testing and maintenance.
- [Changelog](CHANGELOG.en.md).
- [Publishing updates](docs/RELEASES.en.md): preparing GitHub Releases packages.
- [Upload verification](docs/UPLOAD_VERIFICATION.en.md): persistent identity,
  receipts, manual confirmation and deletion safeguards.

## Features

- Folder watching and upload titles based on file creation date.
- Automatic ON/OFF mode, selected uploads, cancellation and explicit retries.
- Persistent local records and YouTube checks.
- Channel thumbnails, search, filters, visibility and playlist management.
- Browser playback and sharing links.
- Local cleanup with fresh YouTube verification.
- Tabbed settings, system tray and configurable Windows startup.
- Separate Console window in Settings, with filters and diagnostic copy/export
  that redacts recognizable credential fields.
- Guided first connection, channel confirmation and user-owned credentials.
- Guided local/YouTube comparison, dedicated browser playback session, and
  explicit manual matching separate from automatic verification.

Uploads and queries are subject to YouTube limits. Settings can check stable
GitHub Releases and download verified packages. Installation remains manual;
the running executable is not replaced automatically.

## Development

Requires Windows and Python 3.12. PySide6/Qt is the only active interface.

```powershell
python -m venv outputs/youtube-sync-modern/.venv
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m pip install -r outputs/youtube-sync-modern/requirements.txt
./outputs/youtube-sync-modern/.venv/Scripts/python.exe outputs/youtube-sync-modern/src/youtube_sync_modern.py
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

The executable is generated at
`outputs/youtube-sync-modern/dist/YouTubeSync/YouTubeSync.exe`.
Distribute the entire `YouTubeSync` folder, including `_internal`.

## Structure

- `outputs/youtube-sync-modern/src`, `assets`, `packaging`, `build_hooks`:
  source, resources and configuration for the only active application.
- `outputs/youtube-sync-modern/dist/YouTubeSync`: complete current build.
  `YouTubeSync.exe` and its required `_internal` folder are here.
- `outputs/youtube-sync-modern/.venv`: development and build dependencies.
- `docs`, `tests`, `scripts`: documentation, tests and maintenance tools.
- `archive/youtube-sync-legacy`: previous version, outside active development.
- `archive/local-data`: private backup of recovered old test data. Excluded
  from Git and never used automatically as application configuration.

Obsolete screenshots, prototypes, packages, environments and build caches have
been removed. Build/release tools can recreate `build` and `work`; these do not
contain source required to run the app.

Use **Abrir-YouTubeSync.cmd** at the repository root to start the application.
It is the recommended entry point. The product is called YouTubeSync; `modern`
in the directory name identifies the Qt project.

The independent engine is
`outputs/youtube-sync-modern/src/youtube_sync_engine.py`. It does not depend
on the archived application. `%APPDATA%\YouTubeSync` remains the data location
for settings, authorization and upload records.

## Configuration

Choose **Español** (default) or **English** in **Settings > General > Language**.
Save and restart YouTubeSync to apply the language. File names, video titles,
playlist names, URLs and upload confirmations are not translated or changed.

On first launch, **Connect my channel** guides you through your own project,
API, desktop credentials, browser authorization, channel confirmation and
folder selection. It is also available in Settings > YouTube. Existing JSON
owners can skip the preparation steps. The app keeps a managed copy and
remembers authorization.

Each user supplies their own project. Shared credentials are not distributed
and projects are not rotated automatically to expand quota.

Credentials, tokens, databases, videos and generated builds are excluded from
the repository. No personal configuration is included.

## Test

```powershell
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m unittest discover -s tests -v
```
