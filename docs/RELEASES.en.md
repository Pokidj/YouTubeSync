# Publishing GitHub Updates

[Español](RELEASES.md) | **English**

## Update Source

YouTubeSync checks only the latest published stable Release in
`Pokidj/YouTubeSync`. A commit, push or tag without a Release does not offer
an application update. Drafts and pre-releases are skipped. Checking is manual
from **Settings > General > Check for updates**.

The installed version is defined in
`outputs/youtube-sync-modern/src/youtube_sync_version.py`. It remains **1.0**;
these changes do not publish a 1.1 release by themselves.

## Prepare a Version, Such as 1.1

1. Change `APP_VERSION` to `1.1` and update both changelogs.
2. Run tests and build the complete application.
3. Generate the package from the repository root:

```powershell
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File build_exe.ps1
./outputs/youtube-sync-modern/.venv/Scripts/python.exe scripts/create_release.py
```

The final command checks the executable's startup and SSL and requires its
version to match source. It cannot relabel a 1.0 build as 1.1. It generates:

- `work/releases/YouTubeSync-1.1-windows-x64.zip`
- `work/releases/SHA256SUMS.txt`

The ZIP includes the entire `YouTubeSync` folder, `_internal` and the manifest
`YouTubeSync/release.json`. Do not distribute a standalone EXE or GitHub's
automatic Source code ZIP; neither replaces the compiled application package.
The packager rejects common personal/configuration file names, but the contents
must still be inspected before publication.

## Create the Release

1. Commit and push the changes belonging to the version.
2. Open [Releases](https://github.com/Pokidj/YouTubeSync/releases) and create one.
3. Use tag `v1.1`, title `YouTubeSync 1.1` and bilingual release notes.
4. Attach the generated ZIP and `SHA256SUMS.txt` as assets.
5. Publish as a stable latest release, not a draft or pre-release.

The ZIP name must exactly match the version. GitHub must supply a valid
`digest=sha256:...` for that asset. The app will not download a package without
a published valid fingerprint, even if `SHA256SUMS.txt` exists.

## User Experience

Check for updates compares the installed version to the latest stable Release.
A newer version with a compatible package offers Download and Release notes.
Download has progress and cancellation, uses HTTPS and needs no GitHub token,
YouTube authorization or YouTube API quota.

Before finalizing the ZIP, the app verifies size, published SHA-256, archive
paths, included runtime, manifest version and platform. Failed partial downloads
are not offered as completed packages. ZIPs are saved in
`%APPDATA%\YouTubeSync\updates`; Open folder displays that location.

This implementation **downloads but does not install automatically**. Exit
YouTubeSync completely, extract the ZIP and replace the entire program folder.
Settings, OAuth and records remain in AppData. The app neither overwrites a
running executable nor executes downloaded content.

SHA-256 checks integrity against GitHub's digest; it is not a Windows digital
signature and alone does not protect against a compromised publisher account.
Future automatic installation needs signing/verification, coordinated shutdown,
backups and recovery.

## References

- [GitHub Releases API](https://docs.github.com/en/rest/releases/releases#get-the-latest-release)
- [Assets and downloads](https://docs.github.com/en/rest/releases/assets#get-a-release-asset)
