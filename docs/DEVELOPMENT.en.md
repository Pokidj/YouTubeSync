# Development and Maintenance

[Español](DESARROLLO.md) | **English**

## Languages

`Config.language` accepts `es` (default) and `en`; unknown values fall back to
Spanish. Select it in Settings > General and restart the app to apply it.
`youtube_sync_i18n.py` and `youtube_sync_translations.py` contain the catalog;
`youtube_sync_i18n_widgets.py` adapts Qt presentation without translating model
values. Persisted states, keys, fingerprints, IDs, titles, paths and playlist
names never change. Diagnostics are classified and redacted before translation.
Table headers and state cells are translated when drawn; enum combo models keep
canonical values. Language tests cover these contracts.

## Requirements

- Windows and Python 3.12.
- Dependencies in `outputs/youtube-sync-modern/requirements.txt`.
- Your own OAuth JSON and connectivity only for real YouTube operations.

## Run From a Clone

```powershell
git clone https://github.com/Pokidj/YouTubeSync.git
cd YouTubeSync
python -m venv outputs/youtube-sync-modern/.venv
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m pip install -r outputs/youtube-sync-modern/requirements.txt
./outputs/youtube-sync-modern/.venv/Scripts/python.exe outputs/youtube-sync-modern/src/youtube_sync_modern.py
```

The internal `youtube-sync-modern` directory is retained for compatibility;
the visible product name is YouTubeSync.

## Architecture

| Path | Responsibility |
| --- | --- |
| `outputs/youtube-sync-modern/src/youtube_sync_modern.py` | Qt window, settings, tables, channel, thumbnails, tray and actions. |
| `outputs/youtube-sync-modern/src/youtube_sync_engine.py` | Independent engine: configuration, SQLite, OAuth, YouTube client and synchronization. |
| `outputs/youtube-sync-modern/assets` | Current icons and logo. |
| `outputs/youtube-sync-modern/build_exe.ps1` | Windows PyInstaller packaging. |
| `tests/test_layout.py` | Layout tests without real YouTube operations. |

The UI imports its own `youtube_sync_engine` directly. It does not dynamically
load the old application's files. `archive` keeps historical source and is not
part of current builds or active test discovery. The Qt project does not need
Tkinter, Pillow or pystray.

The current distribution remains complete in `dist/YouTubeSync`, including
`_internal`; the active `.venv` is used for development and rebuilding.
Temporary tests, `__pycache__`, `build` and old release packages can be regenerated.
Never mix their executables with the active distribution. Recovered test data
is private under `archive/local-data`; active user data remains in AppData.

Network work runs on threads and returns through signals or the event queue.
The channel table is populated in batches. Thumbnails are cached in memory;
the preview repaints without decoding the image on every resize.

## Tests

```powershell
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m unittest discover -s tests -v
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m py_compile outputs/youtube-sync-modern/src/youtube_sync_modern.py outputs/youtube-sync-modern/src/youtube_sync_engine.py
git diff --check
```

UI tests use Qt offscreen and substitute storage and loading actions. They check
window sizes, image aspect ratio, long content, Play button access and splitter
reflow. They do not authenticate real accounts, upload, delete remotely or prove
that an installed application works with a particular account.

Tk tests remain archived with that version. Active tests target Qt and its own
engine. Engine extraction preserved the configuration/token/SQLite formats and
data location. OAuth tests use simulated credentials to check concurrency,
token retention on network failure and renewal after revocation.

For real-operation QA, use disposable files/videos and verify results on YouTube
and disk. Pay special attention to cancellation, retry, restart persistence and
keeping local files on mismatches.

## Build and Distribute

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

The script prepares dependencies and generates:

```text
outputs/youtube-sync-modern/dist/YouTubeSync/
  YouTubeSync.exe
  _internal/
```

The build loads `outputs/youtube-sync-modern/build_hooks/hook-ssl.py`, which
includes auxiliary trust data when required by the Python runtime. Direct
PyInstaller invocations must preserve this hooks directory: a successful build
does not guarantee HTTPS works if runtime data is missing.

The authoritative specification is
`outputs/youtube-sync-modern/packaging/YouTubeSync.spec`. It excludes an unrelated
`icuuc.dll` that may be found on PATH so Qt uses the Windows ICU API. Do not replace
it with a generic packaging command that loses this exclusion. The Spanish Qt
base translation is packaged for consistent standard dialog buttons.

Distribute the complete folder as a ZIP. Source and assets are tracked; generated
builds are excluded. Verified binaries may be attached to a GitHub Release.

Check the real packaged executable after building:

```powershell
./outputs/youtube-sync-modern/dist/YouTubeSync/YouTubeSync.exe --self-test ./qt-startup.json
./outputs/youtube-sync-modern/.venv/Scripts/python.exe scripts/check_distribution.py
```

Self-test writes an `ok: true` report on successful completion. It does not load
the user's database or start OAuth. Intermediate executables in `build` cannot
run alone. Root `Abrir-YouTubeSync.cmd` targets the only active distribution.

## Data and Credentials

Persistent data lives in `%APPDATA%\YouTubeSync`. The allowlist `.gitignore`
excludes environments, builds, JSON, tokens, databases and logs. Never add real
credentials to examples or fixtures. Inspect `git diff --cached` before publishing.

## Versions and Updates

`APP_VERSION` in `youtube_sync_version.py` controls the version in Settings. It
remains 1.0. Later changes stay under Unreleased in [CHANGELOG.en.md](../CHANGELOG.en.md)
until another version is prepared.

`youtube_sync_updater.py` checks the public Releases API and downloads the Windows
x64 ZIP with size limits, HTTPS, pinned origins, SHA-256 and path/manifest checks.
`youtube_sync_update_ui.py` performs work outside the Qt thread and presents it
in Settings; closing Settings cancels the download. Neither OAuth transport nor
YouTube quota controls are reused.

`scripts/create_release.py` tests the real EXE, checks its version and generates
the complete ZIP, manifest and checksum. Updates are not installed or executed
by the app. See [RELEASES.en.md](RELEASES.en.md) for publication and replacement.

## Conventions

- Save source and documentation as UTF-8.
- Do not rewrite text through PowerShell without specifying encoding.
- Keep YouTube operations outside the UI thread.
- Distinguish local records, transfer completion and remote processing.
- Document behavior changes and verified limitations in both changelogs.
- Add English catalog entries for new UI messages; never translate stored enums
  or user-authored names to implement localization.

## Identity and Reconciliation

`remote_video_state` normalizes `uploadStatus` and `processingStatus`; receipt is
not processing completion. `reconcile_local_uploads` updates records without
uploading or deleting files and skips the active transfer. A network error does
not mean the remote video is missing. The work stays outside the Qt thread,
including when Auto is OFF.

New uploads write `YouTubeSync-Fingerprint: sha256:<fingerprint>` into the
description. This is an app-calculated pre-transfer fingerprint, not an independent
YouTube checksum. Old markers were sampled and also need consistent original
filename and size. Equal title, date and duration never suffice. Insufficient
evidence requires review rather than automatic confirmation or deletion.

Reconciliation skips unchanged confirmed files. Periodic checks query unresolved
IDs in batches of 50. Fingerprints are computed in chunks and cached by path,
size and timestamps to avoid rereading unchanged clips.

## Quota Management

`QuotaAwareHttp` wraps authorized transport and preserves HTTP 308 resumable
handling. Exhaustion stores a persistent shared pause in `service_cache`.
Video Uploads quota blocks only transfers; `uploadLimitExceeded` remains a
channel restriction, not the general read budget. SSL is never disabled.

The worker reuses clients. The full catalog has a five-minute TTL and known-ID
index a one-minute TTL. New IDs are not hidden behind an older catalog copy.
Failed reads preserve previous confirmations. `waiting_quota` is waiting, not
a defective file.

A gallery snapshot is saved only after successful complete loading and is dated
when used offline. It never proves current presence or authorizes deletion. The
quota countdown is a planned retry time, not a real remaining-quota counter.

## First Connection

`youtube_sync_setup.py` contains the independent Qt wizard. `initialize_session`
opens it only when a folder or credential is missing; configured users keep their
normal startup. Authorization, channel/playlists and avatar loading run off-thread.

`Store.import_oauth_json` accepts desktop clients with official endpoints, stores
a client-ID-managed copy and preserves compatible tokens and quota pauses.
Import alone does not save settings. A separate provisional token is used during
setup; the active account changes only after channel/folder confirmation and
save. Cancellation cleans temporary data after any pending authorization finishes.

Do not start an upload worker during setup. Auto is an explicit choice and waits
for channel reconciliation after saving. `pause_after_current` also prevents the
rest of the batch from starting after the current file.
