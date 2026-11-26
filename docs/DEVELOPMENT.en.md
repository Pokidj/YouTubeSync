# YouTubeSync Development

[Español](DESARROLLO.md) | **English**

Installation and usage belong in the [README](../README.en.md) and
[user guide](USER_GUIDE.en.md). This page covers development and maintenance.

## Environment

64-bit Windows, Python 3.12 and Inno Setup 7 for installer compilation.
Automated tests require no real credentials.

```powershell
git clone https://github.com/Pokidj/YouTubeSync.git
cd YouTubeSync
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/youtube_sync_app.py
```

Do not launch the main window against a real profile for QA: Auto may be ON.
Tests substitute storage and remote operations.

## Structure

| Path | Responsibility |
| --- | --- |
| `src/youtube_sync_app.py` | Qt window, settings, library, channel, guidance and tray. |
| `src/youtube_sync_engine.py` | SQLite, configuration, OAuth, API, identity and worker. |
| `src/youtube_sync_install.py` | Installer identity and coordinated updates. |
| `src/youtube_sync_updater.py` | Official Releases, HTTPS and SHA-256 downloads. |
| `src/youtube_sync_update_ui.py` | Update checks, download and installation UI. |
| `src/youtube_sync_i18n*.py`, `youtube_sync_translations.py` | Presentation languages, not stored states. |
| `src/youtube_sync_manual*.py`, `youtube_sync_*player.py` | Guided comparison and local/YouTube playback. |
| `src/youtube_sync_channel_*.py` | On YouTube catalog, identity, columns and view. |
| `src/youtube_sync_local_preview.py`, `youtube_sync_preview_*.py` | Local sidebar, shared details and panel visibility. |
| `src/youtube_sync_transport_ui.py`, `youtube_sync_player_controls.py` | Transport controls, availability and validated playback commands. |
| `src/youtube_sync_browser_pipe.py`, `youtube_sync_first_party_player.py` | Private communication with the playback browser. |
| `assets` | Logo, Lucide icons and license notices. |
| `packaging` | PyInstaller specification, manifest and installer script. |
| `build_hooks` | Auxiliary SSL runtime data. |
| `tests` | Tests without real YouTube accounts, uploads or deletions. |
| `scripts` | Distribution validation and installer generation. |
| `.github/workflows` | Build, validation and publication. |
| `docs` | Bilingual user, architecture, verification and publication guides. |

`.venv`, `build`, `dist`, `work`, `releases`, `.tools` and local backups are not
published. The complete working distribution is `dist/YouTubeSync`; `_internal`
is mandatory. Do not mix files from different builds.

## Architecture and Performance

Library and Channel share the `youtube_sync_table_settings.py` table editor.
`assets/youtube-sync-logo.svg` is the canonical logo; `scripts/build_brand_assets.py`
exports PNG and ICO without changing the geometry. The build script runs it before
packaging. [Brand, selection and prompts](BRANDING.md).

The UI imports its engine directly. Network, fingerprinting, thumbnails and media
analysis run off the Qt thread. Results use signals/a bounded event queue; channel
rows render in batches. Resize work is coalesced and images decoded once.

Identity/signature, not title or duration, determine confirmation. Receipts survive
restart and Console clearing. Receiving bytes is not finished processing. Manual
marks are separate and never authorize automatic cleanup. See the
[verification protocol](UPLOAD_VERIFICATION.en.md).

Unchanged confirmed files are not queried on every startup/timer. Unresolved IDs
use batches of 50 and a shared one-minute cache; full catalogs use five minutes.
Deletion checks bypass caches. Network/quota failures are not missing videos.
Pauses persist across clients; no repeated new-upload-session loops are created.

Playback uses a dedicated profile without reading passwords or copying personal
cookies. No OAuth tokens reach the player. Comparison documents are restricted
to 127.0.0.1 with random routes and validated events.

## Languages

`Config.language` is `es` by default or `en`, applied at restart. Qt adapters
translate presentation while retaining canonical models. Never translate names,
paths, IDs or persisted states. Diagnostics are classified/redacted first.
Add new messages to the English catalog and tests.

## Test and Build

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File build_exe.ps1
.\.venv\Scripts\python.exe scripts/check_distribution.py
.\.venv\Scripts\python.exe scripts/create_release.py
```

The PyInstaller specification preserves the SSL hook and excludes unrelated
PATH `icuuc.dll`. Do not replace it with a generic command. `--self-test` loads
no account or uploads; it checks assets, SSL, local playback and languages.
The version is also embedded in Windows PE resources.

Tests cover persistence, cancellation, HTTP 308, OAuth concurrency, quota,
identity false positives, deletion, layouts, languages and installers. They do
not authenticate private accounts; real QA needs disposable files/videos and
must never weaken automatic safeguards.

## Data and Security

Active data remains in `%APPDATA%\YouTubeSync`. The per-user installer preserves
it and reuses the existing program location. The updater checks origin, size,
SHA-256, PE header, product and version, rechecks the file before execution and
requires confirmation. The installer waits for the app, never force-kills it
or reboots Windows.

GitHub's digest establishes release integrity; it is not Authenticode and does
not protect a compromised publisher account. Never disable TLS, Windows security
or browser isolation.

Use UTF-8, keep scope focused and inspect Git's index before publication. Never
commit OAuth JSON, tokens, browser profiles, databases or logs. `APP_VERSION` in
`src/youtube_sync_version.py` controls versions. See [Publishing](RELEASES.en.md).

## Channel Player 1.1

Both sidebars share details/icons through `youtube_sync_preview_ui.py`.
`PreviewVisibility` manages selection, visibility and width without autoplay.
File commands bind to its identity, not a notice that might change. Pending
files do not offer guided matching.

`TransportControls` stays visible and separates selection, loading and actual
player data. Play requests loading; seeking, volume, skips and timestamp sharing
require valid availability/telemetry. Captions start off. Hiding/switching panels
stops playback; Escape returns full screen directly inline. Do not duplicate
Play or launch a second video process for full screen.

Local full screen shares one `QMediaPlayer` and `QAudioOutput`, changing only
`videoOutput` instead of reparenting native video widgets during frame delivery.
Returning restores the original output; closing/deleting releases the source.
Tests cover decoded frames, position, volume, Escape and close. Preview scrolls
reserve scrollbar width to avoid image-size/scrollbar visibility oscillation.

Public/unlisted videos retain the official iframe and its control API. Private
videos use `/embed/ID` as the top-level Chrome/Edge document in the dedicated
`playback-session` profile. The normal browser profile is never copied; no cookies,
passwords or OAuth tokens are read. YouTube remains responsible for granting access.

CDP uses two pipe handles inherited only by the app's Chrome/Edge process, with
no TCP debugging server. Reads and writes run outside the Qt thread. Arbitrary
origins, headless mode and isolation-disabling flags are not enabled. The client
selects only the app's random-token bootstrap target and attaches a CDP session
to that tab. It only permits target discovery/attach/detach and, within the owned
session, navigation and fixed official-player operations. It does not use cookie,
storage, authentication or network body APIs. Secondary launches joining an
existing profile do not replace the main process's private pipe.

Native ownership is pinned using HWND, PID and a random Windows property before
the title changes. The app never closes all Chrome processes. Residual caption
cropping requires `WM_NCHITTEST` to confirm a caption and accounts for Qt scaling.
Checks yield to the UI event loop.

References: [IFrame Player API](https://developers.google.com/youtube/iframe_api_reference),
[Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/),
[Chrome custom profiles](https://developer.chrome.com/blog/remote-debugging-port).
