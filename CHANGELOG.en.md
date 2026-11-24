# Changelog

[Español](CHANGELOG.md) | **English**

Changes after 1.0 remain **Unreleased** until a new version is assigned. The
application still reports **1.0**; this history does not invent past release dates.

## Unreleased

### Languages and Bilingual Documentation

- Spanish (default) / English selector in Settings > General, persisted per
  configuration and applied after restart without translating/migrating internal states.
- English interface, wizards, notices, hover help and diagnostic presentation.
  User names, paths, links, video titles and playlist names remain literal.
- Filters, visibility, column ordering and verification retain stable identifiers;
  a language-only change does not initiate API checks.
- Linked Spanish/English README, user guide, development, verification, release
  publishing and changelog. Private data remains excluded from GitHub.

### Project Cleanup

- Removed prototypes, screenshots, obsolete packages, build caches and the archived
  version's development environment. Kept complete current distribution, active
  environment, source, tests and documentation.
- Recovered old local test data moved to a private backup outside Git. Active
  AppData configuration, OAuth and sessions remain unchanged.
- Updated folder map; kept launch paths compatible. Historical version stays archived.

### Playback Session Inside the App

- Real Chrome/Edge hosted inside comparison, using a dedicated YouTubeSync profile
  shared with Settings > Playback > Manage session.
- Sign-in in a normal browser window opened from Settings. Passwords are not read,
  personal-profile cookies are not imported and OAuth remains independent.
- Removed inner title bar; closing affects only the owned player window, not the
  entire browser or other session windows.
- Playback document restricted to 127.0.0.1 with random routes and validated events.
  Changing steps or closing requests playback stop and removes the hosted window.
- Confirmation remains explicit; video visibility is not changed. Private playback
  compatibility depends on the authorized account.
- Dedicated Playback settings tab; YouTube fields remain legible in small windows.

### Guided Comparison and Hover Help

- Official YouTube playback inside the comparison step, without automatically
  opening an external browser. Decision becomes available after playback starts
  or the user explicitly opens the candidate in the alternate browser.
- Reload/external browser are auxiliary actions with help. Back, Next, link changes
  and closing remove/mute the player.
- App identification, isolated profile and no OAuth tokens passed to the player.
  Private/restricted videos retain the explicit external alternative. A separate
  startup probe isolates unavailable web components from application startup.
- Web engine loads only when comparing, not on startup. Enter in the URL field
  reloads the candidate without closing the wizard.
- Local playback in the wizard with pause, volume and seeking, followed by the
  YouTube candidate and an explicit same-complete-video/own-channel question.
- Mismatch can be remembered without uploading or followed by a separately
  requested new upload. Rejected candidates are excluded from future matches;
  nothing is deleted on YouTube. New upload still permits one attempt with quota
  and safety controls.
- Close/cancel/navigation stops or pauses local playback to avoid background
  audio. The Windows player remains an alternative.
- Descriptive hover help for buttons, icon-only controls, auxiliary windows and menus.

### Now Actions and Manual Confirmation

- Up to five contextual actions with icons/accessibility names; previous/next
  navigation retains the chosen notice.
- Needs verification offers YouTube, local file, manual confirmation, individual
  ID check and Console. Missing links can be entered without scanning the channel.
- Separate Uploaded (manual) mark requires explicit complete-video/ownership
  confirmation, hashes local content off-thread and prevents reupload without API.
- Manual marks authorize no automatic cleanup and are not cryptographic remote
  proof. They do not replace automatic confirmations and reject an ID linked to
  a present file with different content. Later technical proof may promote them.
- Channel upload limit separated from API quota, with Studio, official help and
  project quota links. No invented remaining count or guaranteed Google reset.
- State-specific retry/open/delete/copy-detail actions redact recognizable secrets.
  Cancellation from a notice only targets its file if still actively transferring.

### Manual Local Deletion

- Trash can delete selected local files in any state, including Pending, Review,
  Processing and Issue. Unconfirmed upload warns about losing the only copy;
  Delete anyway is explicit and Cancel is the default.
- Uploaded files retain Verify and delete plus warned unchecked local deletion.
- Unchecked deletion uses no API and deletes no channel videos. It sets Auto OFF,
  waits for the active transfer and checks file identity/recent modification.
- Unknown-duration review can also lead to the same separate deletion confirmation.
  Automatic cleanup keeps all remote safety checks; this exception is manual only.

### Short Video Cleanup

- Cleanup offers retention cleanup and manual deletion of any local file strictly
  under 30 seconds, Uploaded or Pending, with warnings about possible only copies.
- Background Windows duration analysis without YouTube quota, visible progress
  and count/size/list confirmation.
- Unreadable, recent or changed files stay. Identity/duration are rechecked before
  deletion without API. Retention cleanup keeps remote verification. No automatic
  short-video deletion or channel deletion.
- Short/unknown-duration clips require Review before upload, not Issue, with
  Approve and upload, Open local file, Delete local file and Later.
- Per-file approval persists but is invalidated on changes. Unreviewed requests
  create no upload session and do not override retry protection.
- Cleanup pauses new uploads and waits for active work; transferring files are not deleted.

### Configurable Library

- Settings > Library selects visible columns, drag/arrow ordering and defaults.
- Default File, Size, Created and Status; optional Title, Path, Thumbnail,
  Resolution, Duration and FPS remain available.
- Header icons and state text/color/icons.
- Windows Explorer media metadata and thumbnails loaded for visible rows
  off-thread, without YouTube requests. Metadata sorting completes remaining rows
  through a bounded queue. Identity-keyed bounded cache; unsupported formats show
  unavailable data rather than invented values.
- Numeric sorting for size/resolution/duration/FPS. Hidden/moved columns never
  change row identity, actions or confirmations.
- Column-only settings do not trigger channel verification.

### Stable Notices and Compact Transfer Strip

- Now retains the selected notice through refresh/countdown; routine activity
  does not rotate among unresolved problems.
- Selecting a file displays/preserves its notice; resolving it returns to the
  highest-priority remaining problem.
- Uniform profile grid without redundant text labels, retaining icons, values,
  accessibility names and hover details.
- Third card replaced by a thin strip below the main two panels, visible only
  for active/paused/processing work. Query quota without an upload queue does not
  show it; cancellation, stopped queue or confirmed completion hides it.
- Processing uses an indeterminate indicator, not a fabricated YouTube percentage.
  Byte progress and filename appear only in the strip.

### Interface and Diagnostic Console

- Separate profile fields/icons for channel, folder, visibility, category and
  playlist, fitting paths and connection status.
- Removed duplicated quota explanation from transfer display; Now keeps causes
  and actions while the transfer strip shows only its own state.
- Local Lucide assets replace font symbols/mismatched native icons, with source
  attribution and license. Consistent controls, filters, tables, settings and wizard.
- Console moved out of primary tabs to a reusable window opened from General
  settings or notices. Closing it does not stop capture.
- Bounded log with time/zone, level, source, operation, file and traces when
  available. Search/filter/copy/export UTF-8 with recognizable credential redaction.
- Technical content is plain text, not server HTML. Clearing Console touches
  neither database nor upload confirmations.
- Distribution checks cover SVG/diagnostic assets and missing libraries before delivery.

### Unified State and Guidance

- State/Configuration combined in Channel and folder: account, path, visibility,
  category and playlist. Local refresh no longer replaces Connected with Ready.
- Now panel across tabs explains connection/OAuth/disabled-API/permissions/quota
  problems with concrete actions.
- Persistent per-source notices and navigation; refresh or activity does not hide problems.
- Selected Issue/Needs verification actions target that file, not an older selection.
- Service, Channel, Settings and cleanup failures also appear in Now, with technical
  details in Console/notices. Compact settings tested without added API queries.

### Repeated-Upload Protection

- Fixed a loop that returned unconfirmed attempts to Pending and transferred the
  same file repeatedly during automatic cycles.
- Atomic persistent per-file reservation blocks new transfers after failure,
  cancellation or unexpected exit, including across restart.
- Retry/Upload selected permit one additional attempt; an actively transferring
  file cannot be queued again.
- Remote checks may recover confirmation but cannot release an old attempt merely
  because the video is absent.
- Bounded chunk retries stay inside an existing resumable session; ambiguous
  session-creation failures are not automatically repeated.
- Quota rejection before session creation may retry after the global pause;
  partial transfer requires explicit review.
- New attempts store outcomes/reasons. Attempt history is neither actual quota
  nor a completed-video count.

### Fewer Queries and Permanent Confirmations

- Unchanged confirmed uploads are not rechecked on startup, refresh or timers.
- With no unresolved processing, periodic work does not query the channel. Known
  IDs are batched instead of traversing the entire channel.
- Short persistent cache shared by UI/worker; concurrent requests are coalesced
  without artificially extending expiry.
- Needs verification waits for explicit action, not endless checks without new evidence.
- Temporary limits separated from daily limits, including rateLimitExceeded with
  Video Uploads per day details. Expired pauses discarded, stale notices corrected
  and repeated temporary restrictions use progressive waits.
- Checked local deletion always queries fresh data only for its selected IDs,
  never uses cached authorization.

### GitHub Releases Updates

- Manual latest-stable public Release lookup in Settings with numeric version comparison.
- Direct Windows x64 package download, progress/cancellation, no GitHub OAuth or
  YouTube quota consumption.
- Checks HTTPS origin, size, published SHA-256, ZIP structure and version manifest;
  source archives/partial files are never offered as the application.
- Notes and downloaded-folder access. Installation stays manual to avoid overwriting
  running binaries or user data.
- Central version in `youtube_sync_version.py`; packager checks the real EXE before
  creating complete ZIP/checksum.
- Documented future v1.1 publishing without inventing a release now; version stays 1.0.
- Tests cover metadata, versions, integrity, paths, cancellation, failures, UI and
  packages without personal data.

### First Connection With User-Owned Credentials

- Seven-step wizard: welcome, project, API, credentials, authorization, channel
  confirmation and upload options.
- Existing JSON shortcut; managed copy validates desktop client and official
  authorization/token servers.
- Compatible authorization and quota pauses migrate during JSON import.
- External-browser authorization with explicit PKCE/account selection; channel
  name/image/ID checked before save.
- Provisional token during setup; cancelling leaves the active account unchanged.
  Save commits connection, folder, visibility, playlist and upload mode.
- New setup does not auto-upload by default. Explicit Auto waits for reconciliation;
  configured users retain their normal flow.
- Replaced old JSON wizard with a single Settings entry; search finds the YouTube tab.
- Tests cover import, cancellation, save failures, confirmation/navigation,
  new/existing startup and preservation of prior features.

### Persistence and Safety Review

- Atomic receipt for each new completed transfer: returned ID, local signature,
  full fingerprint, size/date and Processing state, independent of description edits.
- Confirmed unchanged files remain recognized in the folder, after restart and
  after clearing Console; no repeat upload.
- Insufficient-evidence records show Needs verification rather than defective
  files; historical receipts are never invented.
- ID checks verify channel ownership. Removed unused title-only confirmation methods.
- Manual deletion carries the selection's persistent ID; later local failures
  do not erase stored remote identity.
- Upload files close on success, failure and cancellation; transfer-time changes
  block correspondence confirmation.
- At most six thumbnail workers. Final exit stops watchers/timers without new work.
- Atomic validated settings, fixed minimized startup and source-mode Windows startup command.
- Verification protocol plus tests for persistence, identity, channel ownership,
  cancellation, changes and deletion selection.

### API Quota and Local Reads

- Exhaustion is a global pause, not an issue per file. Confirmed states stay;
  blocked attempts wait with a next-attempt countdown.
- Shared persistent request blocking until a planned Google reset or Retry-After,
  preventing repeated failing queries each cycle.
- Upload-specific quotas/channel restrictions separated from general reads;
  API pause does not disable the user's Auto ON intent.
- Reused worker client; catalog cached five minutes, IDs one minute; automatic
  cleanup considered at most every five minutes.
- Last successfully loaded gallery snapshot available with date when offline;
  it cannot confirm current availability or authorize checked deletion.
- Refresh offers official quotas, extension request and explicit retry; retry
  does not reset Google's counter.
- Tests for quota, persistence/recovery/cache/states and Pacific time transitions;
  HTTP 308 transfer test retained.

### Content Verification and State Recovery

- Remote `succeeded` normalized as completed processing, fixing finished videos
  incorrectly left In progress.
- Checks at startup/refresh and periodic unresolved-ID batches of 50 off-thread,
  even with Auto OFF. Retry retains selection/ID after table refresh.
- Configured automatic startup actually starts the worker.
- New uploads include chunk-computed, identity-cached full-file SHA-256. Duration
  is never content identity. Legacy fingerprints also need original name/size.
- Insufficient evidence never produces false Uploaded or deletion.
- Removed path-only association when local signature changed.
- Atomic reconciliation preserves newer retries/uploads; network failures are
  not treated as missing videos.
- State tooltips give reasons; In progress has its own count, not an issue count.
- Tests cover processing, ID reconciliation, retries, equal-metadata false positives
  and content differences outside old sampled segments.

### Chunk Uploads and Processing

- Official Google HTTP transport preserves `308 Resume Incomplete` without Location
  as upload continuation, not redirect; 30-second timeout retained.
- Processing videos are kept despite local error/cancel states; cancellation
  does not delete remote videos based on an inferred incomplete state.
- Processing and confirmed upload stay distinct; only confirmed files enter Uploaded
  and checked local cleanup. Worker library updates are grouped.
- Mocked HTTP 308/201 tests and processing/cancellation retention checks, no real uploads.

### One Active Project

- Development/builds exclusively target Qt.
- Engine extracted into the active project without old-folder/Tkinter/Pillow/pystray
  dependencies. Historical version moved to `archive/youtube-sync-legacy` and
  excluded from active test discovery.
- One root launcher/build entry; preserved configuration, token and SQLite formats/paths.

### Executable Startup

- Fixed unrelated PATH `icuuc.dll` collision preventing QtCore import; Qt package
  uses Windows ICU, with versioned packaging specification retaining the exclusion.
- `--self-test` checks startup/SSL without user configuration, account authorization
  or uploads. Legacy Tk self-test remains historical.
- Launchers target complete `dist`, not incomplete intermediate `build` executables.

### OAuth and HTTPS

- Packaged auxiliary SSL trust data required by some Python runtimes.
- Serialized authorization across checks/scans/uploads to prevent concurrent prompts.
- Refresh network errors no longer discard valid authorization; consent renewal
  only for changed permissions or revoked credentials.
- Atomic token writes, short error cooldown and bounded query/refresh/consent timeouts.
- Connection checks avoid duplicate threads; ON/OFF changes are idempotent.

### Windowed Interface Review

- Corrected old UI container height so tables remain visible.
- Compact header/progress/counters while preserving pending/cleanup/channel actions.
- Separate pending/in-progress/issue counts avoid double-counting.
- Grouped channel controls and fallback scrolling for short windows.
- Removed foreign bright borders from the old dark interface.
- Qt read-only tables, reused Settings window and bounded Console; persistent records kept.
- Bounded event processing gives time back to Qt. Folder sorting tolerates disappearing files.
- Expanded legacy/Qt layout and accessibility tests.

### Other Fixes and Improvements

- Stable thumbnail aspect ratio and undistorted scaling.
- Scrollable sidebar when height is insufficient, including metadata and Play access.
- Metadata reflows when the splitter changes width; compact short-window layout.
- Internal URL column hidden without wasted width.
- Debounced resize; cached image painting without repeated decoding.
- Tests for small/large windows, long content and splitter behavior.
- Repository source/assets/exclusions prepared; user/development/changelog documentation.

## 1.0

Existing functional baseline when the repository was prepared. No unverifiable
historical release dates or versions are reconstructed.

### Included

- PySide6/Qt desktop interface with YouTubeSync identity.
- Folder watching, creation-date titles and YouTube upload.
- Automatic/manual uploads, progress, cancellation and retry.
- Persistent records and checks to reduce duplicate uploads.
- Local library and channel thumbnails/filters.
- Browser playback, visibility changes and sharing links.
- Playlist creation from Settings and reassignment from Channel.
- Channel video deletion and checked local cleanup.
- OAuth wizard, tabbed Settings and setting search.
- Windows startup, tray and confirmed final exit.
- Version 1.0 in Settings, reserved space for future updates.

### Limitations at That Baseline

- Updater did not yet download or install releases (download added under Unreleased).
- Playback was in the external browser (guided comparison added under Unreleased).
- Duplicate detection skipped insufficient metadata.
- Recovery times after some YouTube limits were estimates.
