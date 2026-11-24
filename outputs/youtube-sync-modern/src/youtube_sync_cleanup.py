"""Local file cleanup and short-clip discovery; duration is never upload evidence."""

import math
import time
from pathlib import Path

from youtube_sync_engine import file_signature
from youtube_sync_local_media import windows_media


def scan_short_videos(items: list[dict], cancelled=lambda: False, progress=lambda done, total: None) -> dict:
    matches, errors = [], []
    for done, item in enumerate(items, 1):
        if cancelled():
            return {"items": [], "errors": errors, "cancelled": True}
        path = Path(item["path"])
        try:
            if file_signature(path) != item["signature"]:
                raise ValueError("El archivo ha cambiado; se conserva.")
            seconds = float(windows_media(path, None).get("seconds", 0))
            if not math.isfinite(seconds) or seconds <= 0:
                raise ValueError("Windows no ha podido leer la duración; se conserva.")
            if file_signature(path) != item["signature"]:
                raise ValueError("El archivo ha cambiado durante la lectura; se conserva.")
            if seconds < 30:
                matches.append(dict(item, seconds=seconds, size=path.stat().st_size))
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
        progress(done, len(items))
    return {"items": matches, "errors": errors, "cancelled": False}


def delete_local_files(items: list[dict], cancelled=lambda: False, stable_seconds: int = 5,
                       max_seconds: float | None = None) -> dict:
    deleted, errors = [], []
    for item in items:
        if cancelled():
            break
        path = Path(item["path"])
        try:
            if file_signature(path) != item["signature"]:
                raise ValueError("El archivo ha cambiado desde la revisión; se conserva.")
            if time.time() - path.stat().st_mtime < stable_seconds:
                raise ValueError("El archivo se ha modificado hace poco; espera a que termine de guardarse.")
            if max_seconds is not None:
                seconds = float(windows_media(path, None).get("seconds", 0))
                if not math.isfinite(seconds) or not 0 < seconds < max_seconds:
                    raise ValueError(f"No se confirma una duración inferior a {max_seconds:g} segundos; se conserva.")
            if cancelled():
                break
            if file_signature(path) != item["signature"]:
                raise ValueError("El archivo ha cambiado durante la comprobación; se conserva.")
            path.unlink()
            deleted.append(item)
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
    return {"deleted": deleted, "errors": errors}


def delete_short_videos(items: list[dict], cancelled=lambda: False, stable_seconds: int = 5) -> dict:
    return delete_local_files(items, cancelled=cancelled, stable_seconds=stable_seconds, max_seconds=30)
