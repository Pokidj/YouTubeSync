# Changelog

[Español](CHANGELOG.md) | **English**

## 1.1 - 2026-11-26

### Navigation and Notices

- **On my computer** and **On YouTube** replace the Videos and Channel tab names.
- Tabs sit above their content. The profile and Notices appear only on On my computer,
  leaving the remote library more room.
- Connection and configuration share one profile: prominent connection and channel,
  folder and visibility, category and playlist, without a redundant title.
- Now becomes **Notices**. Previous/next arrows retain the chosen notice across
  background updates instead of jumping back to the first.
- Notices no longer duplicates commands: video actions live in its sidebar,
  general actions in the toolbar or the header question mark between ON/OFF and
  Settings, without a menu arrow.

### Libraries and Settings

- Matching table editors for columns, order, reset and selection color, with
  independent preferences for each tab.
- On YouTube offers 14 columns: thumbnail, title, duration, visibility, playlists,
  published, link, ID, original file, size, resolution, FPS, quality and processing.
  Showing columns does not add requests per column.
- Green selection by default and alternative colors. Accent-insensitive settings
  search, retention of a matching current tab and an explicit no-results state.
- Retention periods become visually disabled when automatic cleanup is off,
  without losing supported review and stability values.
- New original S logo with safe vector margins, transparent PNG and eight native
  Windows icon sizes, generated from the SVG during builds.

### Previews and Players

- Resizable sidebars appear for a selected row. An arrow hides them without clearing
  selection and remembers each sidebar's width and hide preference during the session.
  Hiding a sidebar stops playback.
- Shared layout: name, path or URL, video, controls and icon-based details.
  Video actions are docked inside the frame at the bottom.
- Local preview with thumbnail, status, size, creation date and duration without API
  calls; seeking, pause, ten-second skips, volume, mute and external-player access.
- On YouTube plays in the sidebar with always-visible controls. Play starts loading,
  replacing the duplicate Play button. Seeking and audio await real player data.
- Private videos use the dedicated Settings > Playback session. OAuth is neither
  passed to the player nor used to log into that session. Failed access offers Settings.
- Custom controls replace the second YouTube control bar; captions start disabled
  and can be toggled in the sidebar and full screen.
- Full screen is available in both players' controls, without a title bar or
  intermediate window. Escape or Return to panel preserves playback.
- Local full screen shares the file and audio with the sidebar, retaining position,
  paused frame and volume. Closing that window stops the video.
- Changing files/tabs or hiding the panel releases playback. Refreshing an unchanged
  file does not restart it; deletion releases the file first.
- Native browser hosting respects Windows scaling without cutting off video controls.
  Full-screen shell notification keeps the taskbar behind the active player.

### On YouTube

- Channel avatar, name and identity, with public/private/unlisted totals based on
  the full catalog rather than the current filter.
- References without metadata are listed separately, not counted as available videos
  or shown in the table, including cached data, without extra requests to sum totals.
- Sharing still confirms changing visibility to **Unlisted** and copying the link.
  Start at is an optional checkbox using the captured real playback position.
- Change one video's playlist in the sidebar or selected videos using the icon beside
  the privacy lock. The permanent destination selector is removed.
- Batch playlist confirmation and partial results; add the destination before
  removing previous memberships and stop further calls on quota exhaustion.
- Search, filters, batch visibility, conservative duplicate review, confirmed remote
  deletion and opening in the browser are retained.

### On My Computer and Safety

- Queue upload, queue cancel, folder, refresh and cleanup sit above the table;
  individual upload, retry, review, checks, locating and deletion live in the sidebar.
- Folder always opens the root configured in Settings. Locate selects the file in
  Explorer without playing it.
- Folder refresh is local; its menu explicitly checks with YouTube. Stop is only
  available with an active queue or transfer.
- Pending files do not offer guided matching. It remains where an existing candidate
  or manual confirmation needs review.
- Muted semantic colors: green for upload/play/confirm, red for delete/stop, blue
  for browse/open and amber for review/cleanup, with descriptive hover help.
- Version 1.0 safeguards remain: identity receipts, no repeated automatic upload
  attempts, verification before deletion, and manual marks that never authorize
  automatic cleanup. Quota exhaustion does not mean a video is missing.

### Installation and Compatibility

- Complete Windows x64 installer, update from 1.0 through Settings, SHA-256 checks
  and product/version validation.
- Settings, authorization, playback session and upload history are preserved.
- User/developer guides, release notes and changelogs in Spanish and English.
- YouTube quotas, private-video permissions and Windows codec requirements still
  apply. The installer has no publisher-owned Authenticode signature.

## 1.0

First complete YouTubeSync release for Windows.

- Complete installer with dependencies, Start menu entry and uninstall that keeps user data.
- GitHub updates from Settings: SHA-256 download, product/version validation,
  explicit confirmation and coordinated shutdown/installation.
- Spanish and English interface, descriptive hover help, tabbed settings and search.
- User-owned credentials wizard, Google authorization and channel confirmation.
- Configurable library, folder watching, manual/automatic uploads, progress,
  cancellation and explicit retries without repeated-transfer loops.
- Persistent receipts/local identity prevent reuploading confirmed unchanged files;
  transfer completion remains distinct from remote processing.
- Guided local/YouTube comparison, independent playback session and manual marks
  separate from technical verification.
- Channel thumbnails, search/filters, playlists, visibility, sharing, conservative
  duplicate detection and confirmed remote deletion.
- Verified local cleanup, configurable retention, warned manual deletion and
  short-video review before uploading or deleting.
- Shared quota pauses, caching and batched ID checks reduce API requests.
- Tray controls, configurable startup, actionable notices and diagnostic Console.
- One active application, separate user/developer documentation, no private data
  or credentials in the repository.

### Known Limits

- YouTube quotas/channel restrictions still apply. Some retry times are estimates.
- Private playback requires an authorized playback account, independent of OAuth;
  embedding compatibility depends on YouTube.
- Manual matching is a human decision and never authorizes automatic cleanup.
- Available media metadata/formats depend on Windows codecs.
- The installer does not yet have a publisher-owned Authenticode certificate.
