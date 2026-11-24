# Publishing Releases

[Español](RELEASES.md) | **English**

## Release Contract

The first public release is **1.0**. Every stable Release includes:

- `YouTubeSync-1.0-windows-x64-setup.exe`: complete installer, not a standalone app EXE.
- `SHA256SUMS.txt`: installer digest.
- Spanish/English notes describing features, changes and relevant limitations.

Names adapt to each version. GitHub's Source code ZIP is not an installer.
Environments, profiles, credentials and local data are never published.

## Local Build

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File build_exe.ps1
.\.venv\Scripts\python.exe scripts/check_distribution.py
.\.venv\Scripts\python.exe scripts/create_release.py
```

Install Inno Setup 7 or point `ISCC` to `ISCC.exe`. Output is saved to `releases`.
The packager checks actual EXE startup/version, rejects personal data, compiles
the installer and validates its product/version resources. It cannot relabel an
older build as a new version.

## Automatic Publication

`.github/workflows/release.yml` validates, builds and publishes when
source, tests or packaging change on `main`, the workflow itself is introduced,
or it is manually dispatched in Actions. Published versions are never overwritten;
increment `APP_VERSION` for a new release.

For 1.1, set `APP_VERSION` to `1.1`, update both changelogs and
`docs/RELEASE_NOTES.md`, then publish source. The workflow creates `v1.1` at that
commit and attaches the checked installer. Failed tests/installation prevent
publication. No YouTube secrets are used.

## Updater Flow

1. Settings checks the latest stable Release, ignoring drafts/pre-releases and
   never offering downgrade or same-version reinstall.
2. Select the exact version's installer, official repository URL and GitHub
   `sha256:` digest.
3. HTTPS download verifies size and SHA-256 before retaining the file, then
   validates PE header, ProductName, ProductVersion and FileDescription.
4. Install update asks confirmation and rechecks off-thread. Active operations
   prevent application shutdown for updating.
5. Start the installer and genuinely exit, not minimize to tray. The installer
   waits for the PID, updates the previous location and relaunches the app.

Installation is per-user without elevation. Other apps are not force-closed and
Windows is never rebooted. `%APPDATA%\YouTubeSync` data survives updates and
uninstall. Windows startup is refreshed by the app if enabled. Downloads live
in `%APPDATA%\YouTubeSync\updates`.

## Security and Maintenance

GitHub digest verification is not Authenticode. Version 1.0 has no publisher-owned
signing certificate; never advertise it as signed. Protect the publisher account
and do not overwrite released assets. Never ask users to disable Windows security.

References: [Inno Setup](https://jrsoftware.org/inno-setup/documentation/),
[installation parameters](https://jrsoftware.org/inno-setup/documentation/topic_setupcmdline.htm),
[GitHub Releases](https://docs.github.com/en/rest/releases/releases).
