# Changelog

[Español](CHANGELOG.md) | **English**

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
