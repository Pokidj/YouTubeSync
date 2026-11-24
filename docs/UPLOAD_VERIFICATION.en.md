# How Uploads Are Recognized

[Español](VERIFICACION_DE_SUBIDAS.md) | **English**

## Two Different Checks

1. **Local records** remember confirmed uploads so unchanged files are not
   uploaded again, even if they stay in the folder. No API is needed.
2. **Remote verification** checks that the video still belongs to the channel
   and has finished processing. It needs the API and is mandatory for retention
   cleanup and Verify and delete, not for an explicitly confirmed manual discard.

Reading a record is not a live YouTube check. When quota is exhausted, previous
confirmations are kept; a new one is not invented, and disconnection is not
interpreted as a deleted video.

Once Uploaded is confirmed, startup, folder refresh and timers do not query it
again. Its persistent ID and local identity remain stored. Only unresolved
processing is followed. Therefore deleting a confirmed video in YouTube Studio
is not detected automatically. Retention cleanup and Verify and delete perform
a fresh check and keep the file if the video is missing. Delete anyway is a
warned manual exception: it does not query YouTube and can delete the only copy.

## File Identity

A local signature combines path, size, creation time and modification time.
It allows fast record lookup without rereading the full file. An unchanged
signature is recognized after restart; reading the file does not change it.

Content identity is checked separately using full-file SHA-256. Equal duration,
title and date cannot prove two clips are identical. Old sampled fingerprints
also need consistent original metadata and are not full checksums.

Modifying, replacing, renaming or moving a file can change its signature. An old
confirmation is not reused simply because a path matches: the new association
needs verification. This prevents assigning another clip's upload to the file.

## User-Confirmed Matches

Now lets you open the local file and YouTube link, correct the URL and explicitly
declare that both complete videos match and belong to your channel.
**Uploaded (manual)** is saved in a separate table with local signature, video
ID, full local fingerprint, size, declared channel and date. No API query is
made for this decision, and it does not claim Google verified identity or processing.

The guided comparison plays local and YouTube candidates inside the same window,
then asks for an explicit Yes/No decision. The hosted real browser reuses the
dedicated profile opened through Settings > Playback > Manage session. Sign in
with the account authorized to view the private video. Personal-profile cookies
are not copied or read by Python. An explicit external-browser option remains
available if YouTube restricts embedding.

The player receives no OAuth credentials and never changes video visibility.
Playback does not automatically confirm a match. A rejection is remembered by
local signature and ID, excluding that candidate from future associations for
the same file. Rejecting a candidate neither deletes remote videos nor creates
a receipt. Upload as new is an additional choice: it authorizes one attempt,
not a retry loop, and keeps quota protections.

The manual mark prevents reuploading an unchanged file but creates no transfer
receipt, and `verify_local_file` does not accept it as remote evidence. Manual
records are excluded from automatic and retention cleanup. Only later technical
verification with real evidence and processed state can promote them to automatic
Uploaded. A manual mark never downgrades an existing automatic confirmation or
replaces its receipts.

Saving rejects changes during comparison/fingerprinting and an ID already linked
to another present file with different content. This remains a human decision,
not a byte comparison against a remote video. Unchecked local deletion requires
its own separate confirmation.

## Persistent Upload Receipts

When the final upload response returns a video ID, the app atomically stores
a SQLite receipt: ID, local signature, full SHA-256, size and date, together
with Processing state. It survives restarting and clearing Console.

The file is not yet marked Uploaded: receiving bytes does not mean processing
has finished. Cancellation before the final response creates no receipt. A file
changed during transfer cannot have its correspondence confirmed either.

The receipt links that transfer's returned ID to the local content. It can be
verified even if the video description is later edited. Description markers
remain useful for recovering older matches. YouTube returns no independent
SHA-256 of the original bytes; the checksum is calculated by YouTubeSync.

## API Verification

Known IDs are queried directly in batches of up to 50, without loading the entire
channel. UI and service share a 60-second cache. Full searches for unknown
identities may be reused for five minutes; reading caches does not extend expiry.
Deletion checks bypass these caches.

Needs verification cases are not polled continuously by automatic mode: they
require review or an explicit retry. They are never promoted merely to save
quota. With no candidates, the timer does not query the channel.

The app verifies channel ownership and requests status, processing and metadata.
Only `uploadStatus=processed` or `processingStatus=succeeded` counts as complete,
excluding failed, rejected or errored results. `uploaded` alone is not proof of
finished processing.

Linking to a local file requires a consistent fingerprint or persistent receipt
for the same ID. Another video's ID, a repeated title or similar duration is not
enough. A genuine missing result returns to Pending; a network/quota error does
not count as absence.

Reference: [YouTube video states](https://developers.google.com/youtube/data/reference/rest/v3/videos).

## States and Safety

| State | Meaning |
| --- | --- |
| Pending | No confirmed upload for this file. |
| Review | Short video or unknown duration awaiting upload approval. |
| In progress | Active upload or received file still processing. |
| Uploaded | Identity and processing confirmed; permanent record kept. |
| Uploaded (manual) | User-declared match; not evidence for automatic cleanup. |
| Waiting | Quota blocks the next attempt; not a defective file. |
| Needs verification | Candidate exists but evidence is insufficient. |
| Issue | A specific failure or mismatch requires review. |

Old records without evidence are not converted into invented receipts. A missing
historical transfer ID cannot be reliably reconstructed if it was never stored.

## Unconfirmed Attempts

Every transfer atomically reserves an attempt before starting. Failure,
cancellation or interruption prevents another automatic transfer. Even a remote
check that cannot find the video does not release this reservation: review the
channel and explicitly click Retry. This permits only one additional attempt.
Old-attempt protections are retained at startup.

Bounded chunk retries within the same resumable session are allowed. A quota
rejection before session creation may resume after the global pause, but that
exception does not apply to partial sessions or ambiguous outcomes. New outcomes
are stored with the local attempt; older missing outcomes are not fabricated.
Local attempts do not measure actual Google quota.

Retention cleanup and Verify and delete query YouTube, verify content/final state
and check that the local file has not changed. A saved gallery or history cannot
replace this fresh verification.

Delete anyway requires accepting the risk of losing the only copy. Like manual
short-video cleanup, it does not query the API or delete channel videos. It pauses
new uploads, waits for the active operation to release the file and checks local
signature and stability immediately before deletion.
