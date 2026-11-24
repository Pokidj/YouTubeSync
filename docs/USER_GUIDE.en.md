# YouTubeSync User Guide

[Español](GUIA_DE_USO.md) | **English**

## Language

Choose **Español** (default) or **English** in **Settings > General > Language**.
Save and restart YouTubeSync. If closing keeps it in the tray, first choose Exit
there. Language changes do not affect videos, playlists, paths, OAuth or stored
confirmations. Original technical messages from Google may keep their source language.

## What It Does

YouTubeSync watches a Windows folder and uploads videos to your channel. Titles
use file creation date/time, such as `2025-06-18 14:32:05`. Copying between drives
can change that date; review library titles before starting a large batch.

## Installation

Download `YouTubeSync-…-windows-x64-setup.exe` from the
[latest release](https://github.com/Pokidj/YouTubeSync/releases/latest), run it
and open YouTubeSync from Start. Dependencies are included; Python is not needed.
Source code archives are for development. AppData is kept, including on uninstall.
See the [development guide](DEVELOPMENT.en.md) for source builds.

## First Setup

1. First launch opens **Connect my channel**, also available in Settings > YouTube.
   Choose **I already have my OAuth JSON** to skip preparation if applicable.
2. The wizard guides creation of your own Google Cloud project, enabling YouTube
   Data API v3 and creating a Desktop app OAuth client.
3. Select the downloaded JSON. A validated managed copy is kept under
   `%APPDATA%\YouTubeSync\oauth`; the app no longer depends on your Downloads copy.
4. Click **Connect with Google** to authorize in your system browser. You never
   enter your password in YouTubeSync.
5. Check the channel name, image and ID; select **This is my channel**.
   **Choose another account** returns to Google's account selection.
6. Choose folder, subfolders, visibility and playlist. Enable **Upload automatically**
   only if wanted; it is initially unchecked in the wizard.
7. Click **Save and finish**. Authorization and options are remembered. If you
   chose Auto, the channel is checked before the upload worker starts.

Set up later leaves the connection incomplete without starting uploads.
Cancelling never replaces your active account with a provisional one. Existing
configured users keep normal startup. Category, extensions, cleanup and Windows
startup options remain available in Settings.

### Get Your OAuth JSON

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/projectcreate).
2. Enable [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com).
3. Configure consent and account access.
4. Create a **Desktop app** OAuth client and download its JSON.
5. Select it in the app and authorize in the browser.

Google screens can change. If the project is in Testing, check that your account
is allowed to authorize it. Never publish the JSON or access token to GitHub.

## General Controls

| Control | Function |
| --- | --- |
| ON / OFF | Enable or pause automatic mode. |
| Up arrow | Request pending uploads and enable automatic mode. |
| Stop | Request cancellation of the active upload and set Auto OFF. |
| Refresh | Reload settings/folder and check the YouTube connection. |
| Gear | Open Settings. |

Hover over a button for its description. Cancellation may wait for the current
transfer operation/chunk. Cancelling does not automatically delete remote videos.
Before retrying, the app checks the channel; a video still processing is kept.
Doubtful videos can be reviewed and manually deleted from Channel.

## Videos Tab

The table shows files in the configured folder. Defaults are File, Size, Created
and Status, with header/state icons. Click a header to sort; file size uses bytes.

In **Settings > Library**, choose visible columns and reorder them by dragging
or using arrows. **Defaults** restores the initial layout. Save applies and
remembers changes. Title and Path remain available as optional columns.

Thumbnail, Resolution, Duration and FPS are also available. Resolution means
actual pixel dimensions, not an estimated quality grade. Windows Explorer's
provider reads these in the background, on demand and with caching, without
YouTube quota. Sorting by media metadata reads remaining files to sort the
whole library. Unsupported formats/codecs show No thumbnail or Unavailable.
Media metadata is never proof that a file has been uploaded.

| State | Meaning |
| --- | --- |
| Pending | Needs an upload or additional verification. |
| Review | Short/unknown-duration video needs approval before upload. |
| In progress | Transferring or checking processing. |
| Uploaded | Identity and processing confirmed; last confirmation retained. |
| Uploaded (manual) | Match declared by you; no automatic verification or cleanup permission. |
| Waiting | Quota blocks progress; not a defective file. |
| Needs verification | Insufficient evidence of correspondence with the channel. |
| Issue | A specific error or cancellation was recorded. |

Local Uploaded state is not a live remote check. Retention cleanup and Verify
and delete query YouTube before deleting the local copy. Unchecked manual deletion
requires explicitly accepting its separate warning.

Select a file and use Upload for an individual request. Retry authorizes a new
attempt; Open local file uses the Windows-associated program. Refresh folder
forces a local scan.

Before a new upload the app reads duration locally, without querying YouTube.
Videos **under 30 seconds**, or with unreadable duration, require **Review**.
The notice/Upload action offers **Approve and upload**, **Open local file**,
**Delete local file** or **Later**. Deletion asks separately. Nothing is deleted
or uploaded automatically by this review. Approval survives restart but not file
changes. Already confirmed uploads are not uploaded again or reviewed again.

### Now Actions

Now shows contextual actions for the notice/selected file, up to five buttons,
with previous/next arrows. Tooltips describe icons. File actions target the
notice's file, not an unrelated earlier selection.

For **Needs verification**, actions include **View on YouTube**, **View local file**,
**Confirm match**, **Check this video** and **Console**. If no link exists,
**Assign link** lets you paste it. The individual API check queries that ID,
not the whole channel, and confirms Uploaded only with technical identity evidence
and complete processing. A quota error is neither a file issue nor confirmation.

### Guided Manual Comparison

The comparison has three steps. First the local video plays inside the window
with pause, sound and seeking. **Next: YouTube** pauses it and loads the candidate
in the same window. Correct/reload its link if necessary. Once playback starts,
**I have reviewed it** becomes available; choose **Yes, it matches** or
**No, it is a different video**.

For private videos, open **Settings > Playback > Manage session**. Chrome or
Edge opens with YouTubeSync's dedicated profile. Sign in to an account allowed
to view the video, then close that window. The hosted browser in the comparison
uses the same profile. The app reads no passwords and copies no personal-profile
cookies. Change playback accounts through that same Settings action. This session
does not replace OAuth, change visibility or claim an account is connected before
you check it in the browser.

An explicit browser button remains if YouTube restricts embedding. Without
Chrome/Edge, the earlier embedded fallback is retained. Auto pauses for comparison.
On confirmation, saving waits for the active upload operation, calculates a full
local fingerprint off-thread and stores **Uploaded (manual)** without API calls.
The mark survives restart and prevents reupload while the file is unchanged.
You can edit the link through the notice. One link cannot be assigned to present
files with different content; identical copies can share it.

If it does not match, **Save without uploading** keeps it Pending with Auto OFF.
Alternatively **Upload as a new video** requests one new attempt, not repeated
retries; it consumes quota. The rejected ID is remembered for this local file.
No YouTube video is deleted. Cancelling saves no decision.

Closing the wizard stops integrated playback. Back/Next also removes YouTube
to avoid background audio. Only its owned player window closes, not other browser
windows. If the local server stops responding, the document attempts to stop the
video. The dedicated session is retained across launches. All buttons have help.

A manual mark does not prove current remote state, create a fictional receipt
or authorize automatic cleanup. The trash action retains its warning. A later
API check may provide technical confirmation if the required evidence exists.

### Limits and Quota Actions

For a channel upload limit, **YouTube Studio** and **Channel limits** open management
and official help. **API quota** opens Google Cloud, selecting the JSON's project
when its ID is available. These are different limits. YouTube does not expose
an exact remaining channel-upload counter. Official Cloud metrics can be delayed;
the app does not replace them with a guessed quota or guarantee an unlock time.

References: [channel limit](https://support.google.com/youtube/answer/10383400?hl=en),
[API quota](https://developers.google.com/youtube/data/getting-started),
[metric latency](https://docs.cloud.google.com/monitoring/api/v3/latency-n-retention).

### Local Cleanup

The Videos trash button can delete the selected local file in any state. If its
upload is unconfirmed, the warning explains the risk of losing the only copy and
requires **Delete anyway**; Cancel is the initial choice. Uploaded files offer
**Verify and delete** (fresh YouTube check) or **Delete anyway** (no API). Unchecked
deletion permanently removes only the local file, sets Auto OFF and waits for
the active transfer. Recently modified/changed files are kept.

Automatic and retention cleanup still require remote verification; manual deletion
does not weaken those rules or delete channel videos.

**Cleanup** offers **By retention period** and **Videos under 30 seconds**. The
latter scans all local files off-thread, including Pending ones, then shows count,
size, states and a full list before confirmation. It warns about possible only
copies. **Delete local files** sets Auto OFF and waits for the active operation.
Identity and duration are rechecked just before deletion. Exactly 30-second videos,
recent/changed files and unreadable durations are kept. Short-video cleanup is
manual, uses no API and deletes nothing from the channel.

If identity or remote processing cannot be confirmed for checked cleanup, or
local content changed, the file is kept with a reason. Review the result: a batch
may contain both deleted and retained files. Settings > Cleanup can configure
automatic deletion and retention in minutes, hours or days after upload; allow
enough time to review your videos.

## Channel Tab

Opening the tab requests loading; Load channel also refreshes it. Loading requires
connectivity and can take time for large channels.

- Search by title, playlist or link.
- Filter visibility, playlist and date. Date searches title or publication date;
  examples: `2026`, `2026-06`.
- Select a row for thumbnail, duration, visibility, publication and playlists.
- Drag the splitter to resize the sidebar; scroll it when height is limited.

| Action | Result |
| --- | --- |
| Open / Play | Open the selected video in your browser. |
| YouTube | Open YouTube's home page. |
| Share | After confirmation, set the first selected video to Unlisted and copy its link. |
| Visibility | Change visibility of selected channel videos. |
| Move to playlist | Change one selected video's playlist; single selection required. |
| Duplicates | Find groups with sufficient fingerprints or original-file metadata. |
| Delete | Delete selected YouTube videos after confirmation. |

Use Ctrl or Shift for multiple selection. Check selection before channel deletion.
Private videos use the browser session's permissions; the app's OAuth grant does
not log that browser in. Duplicate detection does not accept equal date/duration
alone and can omit videos without sufficient metadata. Review candidates before
deleting; editing a filter returns to the normal filtered list.

## Settings

| Tab | Options |
| --- | --- |
| General | Version, language, updates, Console, folder, extensions and subfolders. |
| YouTube | OAuth JSON, wizard, visibility, category and playlist creation/selection. |
| Playback | Dedicated Chrome/Edge session for private-video comparison. |
| Automation | Auto on startup, minimized startup, tray close, Windows startup, scan/stability intervals. |
| Cleanup | Automatic deletion and retention value/unit. |
| Library | Visible columns, ordering and defaults. |

Search finds sections by keywords. Save applies changes; language applies after restart.

### Updates

General > Check for updates queries the latest stable `Pokidj/YouTubeSync` Release,
not repository commits. A newer Windows x64 package offers notes and download
with progress/cancellation. This uses neither OAuth nor YouTube quota.

Only matching size, published SHA-256, product and version complete a download.
Click **Install update** and confirm: the app exits, the installer waits for it,
updates the program and reopens it. Finish or cancel active work first. Windows
is not rebooted and other applications are not force-closed. Settings, authorization,
session and records stay; no uninstall or manual extraction is needed. Drafts,
pre-releases and Source code ZIPs are not offered as installers.

## Tray and Exit

The tray menu provides Show, Auto, pending uploads, cancellation, refresh, Settings
and Exit. With tray-close enabled, X hides the window while work continues.
Exit asks for confirmation and closes completely. If tray-close is disabled,
X also asks for final-exit confirmation.

## Console and Local Data

Open the separate Console from Settings > General, or a notice. It records the
session even while closed, with time/zone, severity and source. Upload failures
include operation, file and technical detail when available.

Search/filter by source or severity, copy warnings/errors or the full report,
or export UTF-8 `.log`. Recognizable tokens, OAuth secrets and authorization
fields are redacted before display/copy. Always review reports before sharing:
paths, file names and video links can remain. The temporary log holds up to 2,000
entries. Clearing it never removes upload records. Persistent settings,
authorization and database are under `%APPDATA%\YouTubeSync`.

## Troubleshooting

Channel and folder combines your connected profile and active options. Now explains
current work or problems and offers actionable buttons. Arrows retain your selected
notice while it remains relevant; countdowns and checks do not reset selection.
Routine activity does not rotate alongside unresolved problems. Quota pauses take
priority; table refresh does not erase their explanation.

Select an Issue or Needs verification video for actions targeting that file.
Retry still permits only one attempt and keeps anti-repeat protections. Console
retains technical details. The thin transfer strip appears below the two main
panels only for active, paused or processing work. It disappears when finished
or stopped; a quota notice without uploads does not show it. Processing is not
Uploaded and has no fabricated percentage. Profile details remain in tooltips.

The [verification protocol](UPLOAD_VERIFICATION.en.md) explains why unchanged
confirmed files are not reuploaded, what works offline and which checks deletion needs.

### API Quota Exhausted

This is not a file failure. Confirmed Uploaded records stay confirmed and blocked
attempts wait. The countdown is the planned next check, not guaranteed renewed
quota. Auto ON may resume after the pause; OFF stays OFF.

A temporary API limit is not daily exhaustion. The app respects Retry-After and
increases waiting after repeated temporary limits. An explicitly daily limit is
scheduled for the next daily reset even if its reason is rateLimitExceeded.
Ending a pause permits retry; it does not announce restored quota without a new
server response.

Confirmed unchanged files are not polled. Needs verification waits for manual
review/retry rather than continuous automatic queries. Do not delete the database
to solve quota trouble: it contains associations that prevent duplicate uploads.

Refresh offers View quota, Request more quota and Retry connection. Retry only
queries Google; it does not reset/increase quota. Google provides an
[audit and extension request](https://support.google.com/youtube/contact/yt_api_form).

Daily project quota resets at Pacific midnight, normally 09:00 in mainland Spain,
or 08:00 during the US/European daylight-saving mismatch. The app computes the
next reset instant rather than waiting a fixed 24 hours.
[Official quota reference](https://developers.google.com/youtube/data/determine_quota_cost).

Without API you can inspect local files, open browser links and view a previously
successfully loaded saved gallery. Its date is shown. It is not current channel
verification, particularly for private videos, and never authorizes checked
deletion. YouTube Studio remains available with your authorized account.

### Other Problems

After a failed, cancelled or interrupted transfer, that file does not start again
on its own. Review the channel and click Retry for one new attempt. Folder refresh,
restart and Auto do not remove this protection. If YouTube confirms identity,
the app may recognize Uploaded without another transfer.

Video Uploads per day differs from Queries per day. A small current folder does
not reveal daily attempts: failed attempts, other folders or project applications
may have consumed quota. Local attempt history is not Google's official counter.

| Problem | Action |
| --- | --- |
| File not detected | Check folder/extensions/subfolders; refresh folder and wait for file stability. |
| OAuth disconnected | Check JSON and authorize the correct account. |
| Error/cancellation | Read Console, check connection and use Retry when appropriate. |
| Quota/upload limit | Respect the pause. Some times are estimates; retry cannot remove limits. |
| Cannot delete | Check for missing remote confirmation, pending processing or changed local content. |
| Private video inaccessible | Sign in with an authorized account in the browser/profile used for playback. |

When reporting an issue, include version, action and error message. Never share
tokens, OAuth JSON or reports containing private information.
