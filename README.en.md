# YouTubeSync

[Español](README.md) | **English**

Upload videos to YouTube from a Windows folder. See what is pending, processing
or confirmed without uploading unchanged confirmed files again.

![YouTubeSync](assets/youtube-sync-logo.png)

## Download and Install

**[Download YouTubeSync for Windows](https://github.com/Pokidj/YouTubeSync/releases/latest)**

1. Download **YouTubeSync-1.0-windows-x64-setup.exe** from the latest release.
2. Run the installer. It includes the complete application: no separate Python
   or library installation is needed.
3. Open **YouTubeSync** from Start or your chosen desktop shortcut.

Requires 64-bit Windows 10 (1809 or later) or Windows 11. GitHub's **Source code**
archives are for development, not installation. The installer does not yet have
a publisher-owned code-signing certificate; Windows may show an unknown-publisher
warning. Download only from this repository and consult the release's `SHA256SUMS.txt`.

## Connect Your Channel

1. Click **Connect my channel**. The wizard guides you through preparing your own
   Google Cloud project and Desktop app OAuth credentials.
2. Select the downloaded JSON and authorize in Google's browser page.
   YouTubeSync never asks for your password.
3. Confirm your channel's name and image.
4. Choose your folder, visibility and playlist.
5. Upload a selected file or turn **ON** automatic mode.

Each user uses their own project and YouTube quota. Settings and authorization
are remembered. [Complete setup and user guide](docs/USER_GUIDE.en.md).

## Features

- **Library:** sort videos, customize columns and view state, size, duration,
  resolution or local thumbnail.
- **Uploads:** automate, upload one file, cancel, review problems and explicitly retry.
- **Confirmation:** remember confirmed files and compare a local video with its
  YouTube candidate when manual review is needed.
- **Channel:** search, filter, open, share, change visibility, manage playlists
  and review possible duplicates before deciding what to delete.
- **Cleanup:** verify remote uploads before deleting local copies, configure
  retention or review videos under 30 seconds.
- **Settings:** Spanish/English, Windows startup, system tray, columns, playback
  and a separate diagnostic Console.

Manual confirmations never authorize automatic cleanup. API quota and channel
upload limits are different. The app respects pauses without inventing a remaining
quota counter or guaranteed unlock time.

## Update

Open **Settings > General > Check for updates**. When a newer version is available,
download its installer and click **Install update**. After confirmation, the app
closes, updates and reopens. Finish or cancel any active upload or operation first.

Settings, authorization, playback session and upload records are kept. No prior
uninstall or repeated channel authorization is required.

## Help and Data

- [User guide and troubleshooting](docs/USER_GUIDE.en.md).
- [How uploads are verified](docs/UPLOAD_VERIFICATION.en.md).
- [Changelog](CHANGELOG.en.md).
- [Report an issue](https://github.com/Pokidj/YouTubeSync/issues): include version,
  action and error; never attach OAuth JSON or tokens.

Data is stored separately in `%APPDATA%\YouTubeSync`. Uninstalling does not remove
it. Review diagnostic reports before sharing: names, paths and video links may remain.

Contributing to the code: [development documentation](docs/DEVELOPMENT.en.md).
