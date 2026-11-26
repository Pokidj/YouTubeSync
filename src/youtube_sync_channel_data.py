"""Separate channel metadata from unavailable playlist references, without deleting anything."""


def split_gallery_rows(videos):
    available, unavailable = {}, set()
    for video in videos:
        if not isinstance(video, dict) or not video.get("id"):
            continue
        video_id = video["id"]
        legacy_placeholder = (
            "metadata_available" not in video
            and video.get("title") in {"Sin titulo", "Sin título"}
            and video.get("privacy") not in {"public", "private", "unlisted"}
            and not any(video.get(key) for key in
                        ("published_at", "thumbnail", "raw_duration", "filename", "size", "fingerprint"))
        )
        if video.get("metadata_available") is False or legacy_placeholder:
            unavailable.add(video_id)
        else:
            available[video_id] = video
    return list(available.values()), sorted(unavailable - available.keys())
