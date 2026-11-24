"""Backend for the Qt application: storage, OAuth, YouTube and synchronization."""

import hashlib
import math
from contextlib import closing, contextmanager


from functools import partial


import json


import os


import queue


import re


import sqlite3


import sys


import threading
import traceback


import tempfile


import time


from dataclasses import asdict, dataclass, field
from youtube_sync_library import DEFAULT_LIBRARY_COLUMNS, normalize_library_columns


from datetime import datetime, timedelta, timezone


from email.utils import parsedate_to_datetime


from pathlib import Path


from typing import Callable, Iterable


try:
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload, build_http
except Exception:
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception
    MediaFileUpload = None
    build_http = None
    RefreshError = None
    AuthorizedHttp = None
    httplib2 = None


APP_NAME = "YouTubeSync"


SCOPES = ["https://www.googleapis.com/auth/youtube"]


CATEGORIES = {
    "Cine y animacion": "1",
    "Coches y vehiculos": "2",
    "Musica": "10",
    "Mascotas y animales": "15",
    "Deportes": "17",
    "Viajes y eventos": "19",
    "Videojuegos": "20",
    "Gente y blogs": "22",
    "Comedia": "23",
    "Entretenimiento": "24",
    "Noticias y politica": "25",
    "Consejos y estilo": "26",
    "Educacion": "27",
    "Ciencia y tecnologia": "28",
    "ONG y activismo": "29",
}


CATEGORY_NAMES_BY_ID = {value: key for key, value in CATEGORIES.items()}


PRIVACY_LABELS = {"private": "Privado", "unlisted": "Oculto", "public": "Público"}


PRIVACY_VALUES = {label: value for value, label in PRIVACY_LABELS.items()}


def app_dir() -> Path:
    root = os.environ.get("APPDATA")
    path = Path(root) / APP_NAME if root else Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S")


def describe_error(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        filename = getattr(exc, "filename", "") or getattr(exc, "filename2", "")
        if filename:
            return f"No se encontro la ruta: {filename}"
    return str(exc) or exc.__class__.__name__


def is_youtube_quota_error(exc: Exception) -> bool:
    if isinstance(exc, ApiQuotaUnavailable):
        return True
    if getattr(getattr(exc, "resp", None), "status", None) == 429:
        return True
    text = str(exc).lower()
    return (
        "quota exceeded" in text
        or "quotaexceeded" in text
        or "dailylimitexceeded" in text
        or "cuota diaria de youtube data api agotada" in text
        or "cuota api agotada" in text
        or "videouploads" in text
        or "video uploads per day" in text
        or "ratelimitexceeded" in text
        or "uploadlimitexceeded" in text
        or "exceeded the number of videos" in text
    )


class ApiQuotaUnavailable(RuntimeError):
    def __init__(self, state: dict) -> None:
        self.state = state
        label = "Limite temporal API" if state.get("kind") == "api" else "Cuota API agotada"
        super().__init__(label + ". Proximo intento: " + state["retry_at"])


def api_scope(client_secret_path: str) -> str:
    return hashlib.sha256(os.path.normcase(str(Path(client_secret_path).resolve())).encode("utf-8")).hexdigest()


def is_youtube_channel_upload_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return "uploadlimitexceeded" in text or "exceeded the number of videos" in text


def youtube_error_message(exc: Exception) -> str:
    if is_youtube_channel_upload_limit(exc):
        return (
            "Limite de subidas del canal/cuenta de YouTube agotado. "
            "Cambiar de JSON OAuth no lo evita si autorizas el mismo canal; espera al reinicio del limite "
            "o usa otro canal con permiso real para subir."
        )
    if is_youtube_quota_error(exc):
        if youtube_retry_prediction(exc)[0] == "api":
            return "Limite temporal de peticiones de YouTube. Se reintentara sin modificar los estados de los videos."
        return (
            "Cuota diaria de YouTube Data API agotada para este proyecto de Google. "
            "No es un fallo del video: YouTube no aceptara nuevas peticiones hasta que se renueve la cuota "
            "o aumentes el limite del proyecto."
        )
    return describe_error(exc)


def youtube_retry_prediction(exc: Exception) -> tuple[str, datetime, str]:
    if isinstance(exc, ApiQuotaUnavailable):
        state = exc.state
        return state["kind"], datetime.fromisoformat(state["retry_at"]), state["source"]
    now = datetime.now().astimezone()
    response = getattr(exc, "resp", None)
    retry_after = None
    if response is not None and hasattr(response, "get"):
        retry_after = response.get("retry-after") or response.get("Retry-After")
    if retry_after:
        try:
            seconds = max(60, int(retry_after))
            return "api", now + timedelta(seconds=seconds), "indicado por YouTube"
        except (TypeError, ValueError):
            try:
                parsed = parsedate_to_datetime(str(retry_after))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=now.tzinfo)
                return "api", parsed.astimezone(), "indicado por YouTube"
            except (TypeError, ValueError, OverflowError):
                pass

    if is_youtube_channel_upload_limit(exc):
        return "canal", now + timedelta(hours=24), "ventana estimada de 24 h"

    text = str(exc).lower()
    # Google can report rateLimitExceeded for the daily Video Uploads bucket.
    if any(value in text for value in ("per minute", "per_minute", "perminute", "per second", "per_second", "persecond")):
        return "api", now + timedelta(minutes=1), "reintento conservador tras limite temporal"
    if any(value in text for value in ("per day", "per_day", "perday", "dailylimitexceeded", "quotaexceeded")):
        return "proyecto", next_pacific_midnight(now), "reinicio diario estimado de la cuota del proyecto"

    if "ratelimitexceeded" in text or getattr(response, "status", None) == 429:
        return "api", now + timedelta(minutes=1), "reintento conservador tras limite temporal"

    return "proyecto", next_pacific_midnight(now), "reinicio diario estimado de la cuota del proyecto"


def nth_weekday_of_month(year: int, month: int, weekday: int, occurrence: int) -> datetime:
    first = datetime(year, month, 1)
    day = 1 + (weekday - first.weekday()) % 7 + (occurrence - 1) * 7
    return datetime(year, month, day)


def pacific_offset_at_midnight(local_date) -> int:
    dst_start = nth_weekday_of_month(local_date.year, 3, 6, 2).date()
    dst_end = nth_weekday_of_month(local_date.year, 11, 6, 1).date()
    return -7 if dst_start < local_date <= dst_end else -8


def next_pacific_midnight(now: datetime | None = None) -> datetime:
    current = now or datetime.now().astimezone()
    utc_now = current.astimezone().replace(tzinfo=None) - current.astimezone().utcoffset()
    year = utc_now.year
    dst_start_local = nth_weekday_of_month(year, 3, 6, 2).replace(hour=2)
    dst_end_local = nth_weekday_of_month(year, 11, 6, 1).replace(hour=2)
    dst_start_utc = dst_start_local + timedelta(hours=8)
    dst_end_utc = dst_end_local + timedelta(hours=7)
    current_offset = -7 if dst_start_utc <= utc_now < dst_end_utc else -8
    pacific_now = utc_now + timedelta(hours=current_offset)
    target_date = pacific_now.date() + timedelta(days=1)
    target_offset = pacific_offset_at_midnight(target_date)
    target_utc = datetime.combine(target_date, datetime.min.time()) - timedelta(hours=target_offset)
    return target_utc.replace(tzinfo=timezone.utc).astimezone()


def remaining_text(until: datetime, now: datetime | None = None) -> str:
    current = now or datetime.now().astimezone()
    if until.tzinfo is None:
        until = until.replace(tzinfo=current.tzinfo)
    seconds = max(0, int((until - current).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min {seconds:02d} s"
    return f"{seconds} s"


def creation_title(path: Path) -> str:
    created = datetime.fromtimestamp(path.stat().st_ctime)
    return created.strftime("%Y-%m-%d %H:%M:%S")


def file_signature(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}|{stat.st_size}|{stat.st_ctime_ns}|{stat.st_mtime_ns}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def local_video_duration(path: Path) -> float | None:
    from youtube_sync_local_media import windows_media
    try:
        seconds = float(windows_media(path, None).get("seconds", 0))
        return seconds if math.isfinite(seconds) and seconds > 0 else None
    except Exception:
        return None


_fingerprint_cache: dict[tuple, str] = {}


def file_content_fingerprint(path: Path) -> str:
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    cached = _fingerprint_cache.get(key)
    if cached:
        return cached
    digest = hashlib.sha256()
    digest.update(str(stat.st_size).encode("ascii"))
    sample_size = 1024 * 1024
    offsets = sorted({0, max(0, stat.st_size // 2 - sample_size // 2), max(0, stat.st_size - sample_size)})
    with path.open("rb") as source:
        for offset in offsets:
            source.seek(offset)
            digest.update(offset.to_bytes(8, "big"))
            digest.update(source.read(sample_size))
    after = path.stat()
    if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise OSError("El archivo ha cambiado durante la comprobacion")
    value = digest.hexdigest()
    if len(_fingerprint_cache) >= 1000:
        _fingerprint_cache.clear()
    _fingerprint_cache[key] = value
    return value


_full_fingerprint_cache: dict[tuple, str] = {}


def full_content_fingerprint(path: Path, cancelled: Callable[[], bool] | None = None) -> str:
    if cancelled and cancelled():
        raise OSError("Operación cancelada")
    before = path.stat()
    key = (str(path.resolve()), before.st_size, before.st_mtime_ns, before.st_ctime_ns)
    if key in _full_fingerprint_cache:
        return _full_fingerprint_cache[key]
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            if cancelled and cancelled():
                raise OSError("Operación cancelada")
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise OSError("El archivo ha cambiado durante la comprobacion")
    value = "sha256:" + digest.hexdigest()
    if len(_full_fingerprint_cache) >= 1000:
        _full_fingerprint_cache.clear()
    _full_fingerprint_cache[key] = value
    return value


def remote_video_state(item: dict) -> str:
    upload = item.get("status", {}).get("uploadStatus", "")
    processing = item.get("processingDetails", {}).get("processingStatus", "")
    if upload in {"failed", "rejected", "deleted"}:
        return upload
    if processing in {"failed", "terminated"}:
        return processing
    if upload == "processed" or processing == "succeeded":
        return "processed"
    if upload == "uploaded" or processing == "processing":
        return "processing"
    return "unknown"


def human_size(bytes_count: int) -> str:
    size = float(bytes_count)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{bytes_count} B"


def size_value(label: str) -> float:
    parts = str(label).strip().upper().replace(",", ".").split()
    if not parts:
        return 0.0
    try:
        value = float(parts[0])
    except ValueError:
        return 0.0
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    return value * multipliers.get(parts[1] if len(parts) > 1 else "B", 1)


def format_iso_duration(value: str) -> str:
    match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return "—"
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    total_hours = days * 24 + hours
    return f"{total_hours}:{minutes:02d}:{seconds:02d}" if total_hours else f"{minutes}:{seconds:02d}"


def duration_value(label: str) -> int:
    try:
        parts = [int(part) for part in str(label).split(":")]
    except ValueError:
        return 0
    total = 0
    for part in parts:
        total = total * 60 + part
    return total


def compact_path(value: str, max_chars: int = 48) -> str:
    if not value or len(value) <= max_chars:
        return value
    path = Path(value)
    parts = path.parts
    if len(parts) >= 3:
        candidate = str(Path(parts[0], "...", parts[-2], parts[-1]))
        if len(candidate) <= max_chars:
            return candidate
    return value[: max_chars // 2 - 2] + "..." + value[-max_chars // 2 :]


def startup_script_path() -> Path:
    root = os.environ.get("APPDATA")
    if not root:
        return app_dir() / f"{APP_NAME}.cmd"
    return Path(root) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{APP_NAME}.cmd"


def set_run_at_startup(enabled: bool) -> None:
    path = startup_script_path()
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        exe = Path(sys.executable).resolve()
        argument = "" if getattr(sys, "frozen", False) else f' "{Path(__file__).with_name("youtube_sync_app.py")}"'
        path.write_text(f'@echo off\nstart "" "{exe}"{argument}\n', encoding="utf-8")
    elif path.exists():
        path.unlink()


@dataclass
class Config:
    language: str = "es"
    watch_folder: str = ""
    client_secret_path: str = ""
    privacy_status: str = "private"
    category_id: str = "22"
    playlist_id: str = ""
    playlist_name: str = "Ninguna"
    recursive: bool = False
    scan_interval_seconds: int = 5
    stable_wait_seconds: int = 5
    timing_profile_version: int = 2
    extensions: str = ".mp4,.mov,.mkv,.avi,.m4v,.webm,.wmv"
    start_minimized: bool = False
    close_to_tray: bool = True
    run_at_startup: bool = False
    auto_start_enabled: bool = True
    auto_delete_uploaded: bool = False
    auto_delete_after_hours: int = 24
    auto_delete_after_unit: str = "horas"
    connected_channel_id: str = ""
    connected_channel_name: str = ""
    library_columns: list[str] = field(default_factory=lambda: list(DEFAULT_LIBRARY_COLUMNS))

    @property
    def extension_set(self) -> set[str]:
        return {item.strip().lower() for item in self.extensions.split(",") if item.strip()}

    @property
    def auto_delete_delay(self) -> timedelta:
        value = max(1, int(self.auto_delete_after_hours))
        unit = self.auto_delete_after_unit if self.auto_delete_after_unit in {"minutos", "horas", "dias"} else "horas"
        if unit == "minutos":
            return timedelta(minutes=value)
        if unit == "dias":
            return timedelta(days=value)
        return timedelta(hours=value)

    @property
    def auto_delete_delay_label(self) -> str:
        value = max(1, int(self.auto_delete_after_hours))
        unit = self.auto_delete_after_unit if self.auto_delete_after_unit in {"minutos", "horas", "dias"} else "horas"
        singular = {"minutos": "minuto", "horas": "hora", "dias": "dia"}[unit]
        return f"{value} {singular if value == 1 else unit}"


class Store:
    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(self.db_path)) as connection:
            with connection:
                yield connection

    def __init__(self) -> None:
        self.base = app_dir()
        self.config_path = self.base / "config.json"
        self.db_path = self.base / "state.sqlite3"
        self.token_path = self.base / "youtube-token.json"
        self._init_db()

    def token_path_for(self, client_secret_path: str) -> Path:
        if not client_secret_path:
            return self.token_path
        digest = hashlib.sha256(str(Path(client_secret_path)).lower().encode("utf-8", errors="replace")).hexdigest()[:12]
        return self.base / f"youtube-token-{digest}.json"

    def import_oauth_json(self, source: Path) -> Path:
        try:
            if source.stat().st_size > 1024 * 1024:
                raise ValueError("El archivo es demasiado grande para ser un JSON OAuth de escritorio.")
            data = json.loads(source.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("No se puede leer el JSON. Selecciona el archivo descargado de Google Cloud.") from exc
        installed = data.get("installed") if isinstance(data, dict) else None
        if not isinstance(installed, dict) or "web" in data:
            raise ValueError("Selecciona credenciales OAuth de tipo Aplicacion de escritorio, no web ni cuenta de servicio.")
        client_id = installed.get("client_id", "")
        if not isinstance(client_id, str) or not client_id.endswith(".apps.googleusercontent.com"):
            raise ValueError("El JSON no contiene un ID de cliente de Google valido.")
        if installed.get("auth_uri") not in {"https://accounts.google.com/o/oauth2/auth", "https://accounts.google.com/o/oauth2/v2/auth"}:
            raise ValueError("El enlace de autorizacion del JSON no es un enlace oficial de Google.")
        if installed.get("token_uri") not in {"https://oauth2.googleapis.com/token", "https://accounts.google.com/o/oauth2/token", "https://www.googleapis.com/oauth2/v4/token"}:
            raise ValueError("El servidor de tokens del JSON no es un servidor oficial de Google.")
        digest = hashlib.sha256(client_id.encode("utf-8")).hexdigest()[:16]
        folder = self.base / "oauth"
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f"client-{digest}.json"
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder, suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                json.dump({"installed": installed}, output, indent=2)
            temporary.replace(destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        target_token = self.token_path_for(str(destination))
        if not target_token.exists():
            previous = self.load_config().client_secret_path
            for candidate in (self.token_path_for(str(source)), self.token_path_for(previous), self.token_path):
                try:
                    token = json.loads(candidate.read_text(encoding="utf-8"))
                    if isinstance(token, dict) and token.get("client_id") == client_id:
                        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.base, suffix=".tmp", delete=False) as output:
                            temporary = Path(output.name)
                            json.dump(token, output)
                        temporary.replace(target_token)
                        break
                except (OSError, UnicodeError, json.JSONDecodeError):
                    continue
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        for bucket in ("general", "upload"):
            pause = self.api_pause(api_scope(str(source)), bucket)
            if pause and not self.api_pause(api_scope(str(destination)), bucket):
                self.save_service_cache(api_scope(str(destination)), "quota_" + bucket, pause)
        return destination

    def _init_db(self) -> None:
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS service_cache (
                       scope TEXT NOT NULL, name TEXT NOT NULL, payload TEXT NOT NULL,
                       checked_at TEXT NOT NULL, PRIMARY KEY(scope, name))""")
            db.execute("""CREATE TABLE IF NOT EXISTS upload_receipts (
                       signature TEXT NOT NULL, youtube_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
                       size INTEGER NOT NULL, received_at TEXT NOT NULL, confirmed_at TEXT,
                       PRIMARY KEY(signature, youtube_id))""")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS uploads (
                    signature TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    youtube_id TEXT,
                    status TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error TEXT
                )
                """
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_uploads_title ON uploads(title)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status)")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS upload_registry (
                    signature TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL,
                    youtube_id TEXT,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS upload_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signature TEXT NOT NULL,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_upload_attempts_created ON upload_attempts(created_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_upload_attempts_signature ON upload_attempts(signature)")
            columns = {row[1] for row in db.execute("PRAGMA table_info(upload_attempts)")}
            for name in ("outcome", "detail"):
                if name not in columns:
                    db.execute(f"ALTER TABLE upload_attempts ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
            db.execute("""CREATE TABLE IF NOT EXISTS upload_retry_permissions (
                       signature TEXT PRIMARY KEY, after_attempt_id INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS manual_confirmations (
                       signature TEXT PRIMARY KEY, youtube_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
                       size INTEGER NOT NULL, channel_id TEXT NOT NULL, confirmed_at TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_manual_youtube ON manual_confirmations(youtube_id)")
            db.execute("""CREATE TABLE IF NOT EXISTS rejected_matches (
                       signature TEXT NOT NULL, youtube_id TEXT NOT NULL, rejected_at TEXT NOT NULL,
                       PRIMARY KEY(signature,youtube_id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS fresh_upload_permissions (
                       signature TEXT PRIMARY KEY, after_attempt_id INTEGER NOT NULL)""")
            db.execute("""UPDATE uploads SET status='error',
                       error='Intento anterior sin confirmar. Revisa el canal y pulsa Reintentar.'
                       WHERE status='pending' AND signature IN (
                           SELECT a.signature FROM upload_attempts a
                           LEFT JOIN upload_retry_permissions p ON p.signature=a.signature
                           GROUP BY a.signature HAVING MAX(a.id)>COALESCE(MAX(p.after_attempt_id),0))""")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS upload_limit_state (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    kind TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    retry_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )
            db.execute("DROP INDEX IF EXISTS idx_registry_title")
            db.execute("CREATE INDEX IF NOT EXISTS idx_registry_title_lookup ON upload_registry(title)")
            db.execute(
                """
                INSERT OR IGNORE INTO upload_registry(signature, title, path, youtube_id, reason, created_at, updated_at)
                SELECT signature, title, path, youtube_id, status, created_at, updated_at
                FROM uploads
                WHERE status IN ('uploaded','skipped','local_deleted')
                  AND youtube_id IS NOT NULL
                  AND youtube_id <> ''
                """
            )

    def save_service_cache(self, scope: str, name: str, payload) -> None:
        with self._connection() as db:
            db.execute("""INSERT INTO service_cache(scope, name, payload, checked_at) VALUES(?,?,?,?)
                       ON CONFLICT(scope,name) DO UPDATE SET payload=excluded.payload, checked_at=excluded.checked_at""",
                       (scope, name, json.dumps(payload), datetime.now().astimezone().isoformat()))

    def review_before_upload(self, path: Path) -> dict:
        signature = file_signature(path)
        saved = self.service_cache("upload_review", signature)
        if saved and isinstance(saved["data"], dict) and type(saved["data"].get("approved")) is bool:
            seconds = saved["data"].get("seconds")
            if seconds is None or (type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0):
                return dict(saved["data"], signature=signature)
        seconds = local_video_duration(path)
        if file_signature(path) != signature:
            raise OSError("El archivo ha cambiado al leer su duración")
        review = {"path": str(path), "seconds": seconds, "approved": seconds is not None and seconds >= 30}
        self.save_service_cache("upload_review", signature, review)
        return dict(review, signature=signature)

    def pending_upload_reviews(self) -> dict:
        with self._connection() as db:
            rows = db.execute("SELECT name,payload FROM service_cache WHERE scope='upload_review'").fetchall()
        result = {}
        for signature, payload in rows:
            try:
                data = json.loads(payload)
                if isinstance(data, dict) and data.get("approved") is not True:
                    result[signature] = data
            except (ValueError, TypeError):
                continue
        return result

    def approve_upload_review(self, path: Path, signature: str) -> None:
        if file_signature(path) != signature:
            raise OSError("El archivo ha cambiado. Revisa la nueva versión antes de autorizarla.")
        review = self.review_before_upload(path)
        if review["signature"] != signature:
            raise OSError("La revisión ya no corresponde al archivo actual")
        self.save_service_cache("upload_review", signature,
                                {"path": str(path), "seconds": review.get("seconds"), "approved": True})

    def service_cache(self, scope: str, name: str) -> dict | None:
        with self._connection() as db:
            row = db.execute("SELECT payload, checked_at FROM service_cache WHERE scope=? AND name=?", (scope, name)).fetchone()
        if not row:
            return None
        return {"data": json.loads(row[0]), "checked_at": row[1]}

    def fresh_service_cache(self, scope: str, name: str, seconds: int):
        cached = self.service_cache(scope, name)
        if cached:
            try:
                age = (datetime.now().astimezone() - datetime.fromisoformat(cached["checked_at"])).total_seconds()
                if 0 <= age < seconds:
                    return cached["data"]
            except (ValueError, TypeError):
                pass
        return None

    def api_pause(self, scope: str, bucket: str = "general") -> dict | None:
        cached = self.service_cache(scope, "quota_" + bucket)
        if not cached:
            return None
        state = cached["data"]
        try:
            if datetime.fromisoformat(state["retry_at"]) > datetime.now().astimezone():
                return state
        except (KeyError, ValueError, TypeError):
            pass
        with self._connection() as db:
            db.execute("DELETE FROM service_cache WHERE scope=? AND name=? AND payload=?",
                       (scope, "quota_" + bucket, json.dumps(state)))
        return None

    def defer_api(self, scope: str, exc: Exception, bucket: str = "general") -> dict:
        if isinstance(exc, ApiQuotaUnavailable):
            return exc.state
        kind, retry_at, source = youtube_retry_prediction(exc)
        now = datetime.now().astimezone()
        attempts = 1
        previous = self.service_cache(scope, "last_limit_" + bucket)
        if kind == "api" and source != "indicado por YouTube" and previous:
            try:
                data = previous["data"]
                age = (now - datetime.fromisoformat(data["observed_at"])).total_seconds()
                if data.get("kind") == "api" and 0 <= age < 3600:
                    attempts = min(5, int(data.get("attempts", 1)) + 1)
                    retry_at = now + timedelta(seconds=min(900, 60 * 2 ** (attempts - 1)))
            except (KeyError, ValueError, TypeError):
                pass
        state = {"kind": kind, "retry_at": retry_at.isoformat(), "source": source, "bucket": bucket,
                 "observed_at": now.isoformat(), "attempts": attempts}
        try:
            details = json.loads(exc.content).get("error", {}).get("errors", [])
            state["reason"] = ", ".join(str(item.get("reason", "")) for item in details)[:200]
        except (AttributeError, ValueError, TypeError):
            state["reason"] = ""
        self.save_service_cache(scope, "quota_" + bucket, state)
        self.save_service_cache(scope, "last_limit_" + bucket, state)
        return state

    def clear_api_pause(self, scope: str) -> None:
        with self._connection() as db:
            db.execute("DELETE FROM service_cache WHERE scope=? AND name IN ('quota_general','quota_upload')", (scope,))

    def load_config(self) -> Config:
        if not self.config_path.exists():
            return Config()
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("La configuración no contiene un objeto JSON.")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            backup = self.base / f"config-invalid-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            try:
                self.config_path.replace(backup)
            except OSError:
                pass
            return Config()
        defaults = asdict(Config())
        cleaned = {}
        for key, default in defaults.items():
            value = data.get(key, default)
            if type(default) is int:
                try:
                    value = int(value) if not isinstance(value, bool) else default
                except (TypeError, ValueError, OverflowError):
                    value = default
            elif not isinstance(value, type(default)):
                value = default
            cleaned[key] = value
        config = Config(**cleaned)
        if config.language not in {"es", "en"}:
            config.language = "es"
        config.library_columns = normalize_library_columns(config.library_columns)
        config.scan_interval_seconds = max(2, min(86400, config.scan_interval_seconds))
        config.stable_wait_seconds = max(1, min(86400, config.stable_wait_seconds))
        config.auto_delete_after_hours = max(1, config.auto_delete_after_hours)
        if config.privacy_status not in PRIVACY_LABELS:
            config.privacy_status = "private"
        profile_version = config.timing_profile_version if "timing_profile_version" in data else 0
        if profile_version < 1:
            config.scan_interval_seconds = min(max(2, int(config.scan_interval_seconds)), 10)
            config.stable_wait_seconds = min(max(2, int(config.stable_wait_seconds)), 10)
            config.timing_profile_version = 1
            self.save_config(config)
        if profile_version < 2:
            if int(config.scan_interval_seconds) == 10:
                config.scan_interval_seconds = 5
            if int(config.stable_wait_seconds) == 10:
                config.stable_wait_seconds = 5
            config.timing_profile_version = 2
            self.save_config(config)
        if config.auto_delete_after_unit not in {"minutos", "horas", "dias"}:
            config.auto_delete_after_unit = "horas"
        return config

    def save_config(self, config: Config) -> None:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.base,
                                             prefix="config-", suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                json.dump(asdict(config), output, indent=2)
            temporary.replace(self.config_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def has_success(self, signature: str) -> bool:
        with self._connection() as db:
            row = db.execute(
                "SELECT 1 FROM upload_registry WHERE signature = ? AND youtube_id != '' "
                "AND reason IN ('uploaded', 'youtube_title_exists', 'manual_confirmed')",
                (signature,),
            ).fetchone()
            return row is not None

    def remember_receipt(self, signature: str, path: Path, youtube_id: str, fingerprint: str) -> None:
        if not youtube_id or not fingerprint.startswith("sha256:"):
            raise ValueError("Falta el ID o la huella completa del recibo de subida")
        stamp = datetime.now().astimezone().isoformat()
        title, size = creation_title(path), path.stat().st_size
        with self._connection() as db:
            db.execute("""INSERT OR IGNORE INTO upload_receipts
                       (signature,youtube_id,fingerprint,size,received_at) VALUES(?,?,?,?,?)""",
                       (signature, youtube_id, fingerprint, size, stamp))
            db.execute("""INSERT INTO upload_registry(signature,title,path,youtube_id,reason,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?) ON CONFLICT(signature) DO UPDATE SET
                       youtube_id=excluded.youtube_id, reason=excluded.reason, updated_at=excluded.updated_at""",
                       (signature, title, str(path), youtube_id, "processing", stamp, stamp))
            db.execute("""INSERT INTO uploads(signature,path,title,youtube_id,status,size,created_at,updated_at,error)
                       VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(signature) DO UPDATE SET
                       youtube_id=excluded.youtube_id, status=excluded.status, updated_at=excluded.updated_at, error=''""",
                       (signature, str(path), title, youtube_id, "processing", size, stamp, stamp, ""))

    def receipt(self, youtube_id: str) -> tuple | None:
        with self._connection() as db:
            return db.execute("SELECT fingerprint,size FROM upload_receipts WHERE youtube_id=?", (youtube_id,)).fetchone()

    def remember_upload(self, signature: str, path: Path, title: str, youtube_id: str = "", reason: str = "uploaded") -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        with self._connection() as db:
            db.execute(
                """
                INSERT INTO upload_registry(signature, title, path, youtube_id, reason, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(signature) DO UPDATE SET
                    title=excluded.title,
                    path=excluded.path,
                    youtube_id=excluded.youtube_id,
                    reason=excluded.reason,
                    updated_at=excluded.updated_at
                """,
                (signature, title, str(path), youtube_id, reason, stamp, stamp),
            )

    def confirm_manual_match(self, path: Path, signature: str, youtube_id: str, channel_id: str = "",
                             acknowledged: bool = False, cancelled: Callable[[], bool] = lambda: False) -> None:
        from youtube_sync_manual import youtube_video_id
        video_id = youtube_video_id(youtube_id)
        if acknowledged is not True:
            raise ValueError("Debes confirmar que has comparado ambos vídeos completos.")
        if file_signature(path) != signature:
            raise OSError("El archivo ha cambiado. Vuelve a comparar su contenido antes de confirmar.")
        fingerprint = full_content_fingerprint(path, cancelled=cancelled)
        size, title = path.stat().st_size, creation_title(path)
        if cancelled() or file_signature(path) != signature:
            raise OSError("Confirmación cancelada o archivo modificado; no se ha guardado.")
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connection() as db:
            existing = db.execute("SELECT reason FROM upload_registry WHERE signature=?", (signature,)).fetchone()
            if existing and existing[0] in {"uploaded", "youtube_title_exists"}:
                raise ValueError("Este archivo ya tiene una confirmación automática; no se sustituye por una manual.")
            conflicts = db.execute("""SELECT r.path FROM manual_confirmations m
                                   JOIN upload_registry r ON r.signature=m.signature
                                   WHERE m.youtube_id=? AND m.fingerprint<>? AND m.signature<>?
                                   AND r.reason='manual_confirmed'""", (video_id, fingerprint, signature)).fetchall()
            conflicts += db.execute("""SELECT r.path FROM upload_receipts u
                                    JOIN upload_registry r ON r.signature=u.signature
                                    WHERE u.youtube_id=? AND u.fingerprint<>? AND u.signature<>?
                                    AND r.reason<>'local_deleted'""", (video_id, fingerprint, signature)).fetchall()
            if any(Path(row[0]).exists() for row in conflicts):
                raise ValueError("Ese vídeo ya está asignado manualmente a otro archivo de contenido distinto. Revisa el enlace.")
            if cancelled() or file_signature(path) != signature:
                raise OSError("El archivo ha cambiado o la operación se ha cancelado.")
            db.execute("""INSERT INTO manual_confirmations(signature,youtube_id,fingerprint,size,channel_id,confirmed_at) VALUES(?,?,?,?,?,?)
                       ON CONFLICT(signature) DO UPDATE SET youtube_id=excluded.youtube_id,
                       fingerprint=excluded.fingerprint,size=excluded.size,channel_id=excluded.channel_id,
                       confirmed_at=excluded.confirmed_at""", (signature, video_id, fingerprint, size, channel_id, stamp))
            db.execute("""INSERT INTO upload_registry(signature,title,path,youtube_id,reason,created_at,updated_at)
                       VALUES(?,?,?,?, 'manual_confirmed',?,?) ON CONFLICT(signature) DO UPDATE SET
                       title=excluded.title,path=excluded.path,youtube_id=excluded.youtube_id,
                       reason=excluded.reason,updated_at=excluded.updated_at""", (signature, title, str(path), video_id, stamp, stamp))
            db.execute("""INSERT INTO uploads(signature,path,title,youtube_id,status,size,created_at,updated_at,error)
                       VALUES(?,?,?,?, 'manual_confirmed',?,?,?,'') ON CONFLICT(signature) DO UPDATE SET
                       path=excluded.path,title=excluded.title,youtube_id=excluded.youtube_id,
                       status=excluded.status,size=excluded.size,updated_at=excluded.updated_at,error=''""",
                       (signature, str(path), title, video_id, size, stamp, stamp))
            db.execute("DELETE FROM service_cache WHERE scope='upload_review' AND name=?", (signature,))
            db.execute("DELETE FROM rejected_matches WHERE signature=? AND youtube_id=?", (signature, video_id))
            db.execute("DELETE FROM fresh_upload_permissions WHERE signature=?", (signature,))

    def rejected_video_ids(self, signature: str) -> set[str]:
        with self._connection() as db:
            return {row[0] for row in db.execute("SELECT youtube_id FROM rejected_matches WHERE signature=?", (signature,))}

    def reject_manual_match(self, path: Path, signature: str, youtube_id: str, upload_requested: bool = False) -> None:
        from youtube_sync_manual import youtube_video_id
        video_id = youtube_video_id(youtube_id)
        if file_signature(path) != signature:
            raise OSError("El archivo ha cambiado desde la comparación. No se modifica su estado.")
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connection() as db:
            existing = db.execute("SELECT youtube_id,reason FROM upload_registry WHERE signature=?", (signature,)).fetchone()
            if existing and existing[1] in {"uploaded", "youtube_title_exists"}:
                raise ValueError("El archivo tiene una confirmación automática; no se descarta desde la comparación manual.")
            if existing and existing[0] and existing[0] != video_id:
                raise ValueError("El enlace asociado ha cambiado durante la comparación. Revisa la nueva asociación.")
            db.execute("INSERT OR REPLACE INTO rejected_matches VALUES(?,?,?)", (signature, video_id, stamp))
            db.execute("DELETE FROM manual_confirmations WHERE signature=?", (signature,))
            db.execute("UPDATE upload_registry SET youtube_id='',reason='manual_rejected',updated_at=? WHERE signature=?", (stamp, signature))
            db.execute("UPDATE uploads SET youtube_id='',status='pending',updated_at=?,error='' WHERE signature=?", (stamp, signature))
            if upload_requested:
                last = db.execute("SELECT COALESCE(MAX(id),0) FROM upload_attempts WHERE signature=?", (signature,)).fetchone()[0]
                db.execute("INSERT OR REPLACE INTO fresh_upload_permissions VALUES(?,?)", (signature, last))
            else:
                db.execute("DELETE FROM fresh_upload_permissions WHERE signature=?", (signature,))

    def fresh_upload_authorized(self, signature: str) -> bool:
        with self._connection() as db:
            row = db.execute("""SELECT p.after_attempt_id >= COALESCE((SELECT MAX(id) FROM upload_attempts WHERE signature=p.signature),0)
                             FROM fresh_upload_permissions p WHERE p.signature=?""", (signature,)).fetchone()
        return bool(row and row[0])

    def update_registry_youtube_id(self, signature: str, youtube_id: str) -> None:
        if not youtube_id:
            return
        stamp = datetime.now().isoformat(timespec="seconds")
        with self._connection() as db:
            db.execute(
                "UPDATE upload_registry SET youtube_id = ?, updated_at = ? WHERE signature = ?",
                (youtube_id, stamp, signature),
            )
            db.execute(
                "UPDATE uploads SET youtube_id = ?, updated_at = ? WHERE signature = ?",
                (youtube_id, stamp, signature),
            )

    def update_registry_state(self, signature: str, youtube_id: str, reason: str) -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        with self._connection() as db:
            db.execute(
                "UPDATE upload_registry SET youtube_id = ?, reason = ?, updated_at = ? WHERE signature = ?",
                (youtube_id, reason, stamp, signature),
            )
            db.execute(
                "UPDATE uploads SET youtube_id = ?, status = ?, updated_at = ?, error = '' WHERE signature = ?",
                (youtube_id, reason, stamp, signature),
            )

    def clear_upload_incident(self, signature: str) -> None:
        """Clear a transient upload state without touching the duplicate registry."""
        self.authorize_upload_retry(signature)
        with self._connection() as db:
            db.execute("UPDATE uploads SET status = 'pending', error = '' WHERE signature = ?", (signature,))

    def authorize_upload_retry(self, signature: str, after_attempt_id: int | None = None) -> None:
        with self._connection() as db:
            if after_attempt_id is None:
                after_attempt_id = db.execute("SELECT COALESCE(MAX(id),0) FROM upload_attempts WHERE signature=?",
                                             (signature,)).fetchone()[0]
            db.execute("""INSERT INTO upload_retry_permissions(signature,after_attempt_id) VALUES(?,?)
                       ON CONFLICT(signature) DO UPDATE SET
                       after_attempt_id=MAX(after_attempt_id,excluded.after_attempt_id)""",
                       (signature, after_attempt_id))

    def retry_required_signatures(self) -> set[str]:
        with self._connection() as db:
            rows = db.execute("""SELECT a.signature FROM upload_attempts a
                              LEFT JOIN upload_retry_permissions p ON p.signature=a.signature
                              GROUP BY a.signature HAVING MAX(a.id)>COALESCE(MAX(p.after_attempt_id),0)""").fetchall()
        return {row[0] for row in rows}

    def upload_status(self, signature: str) -> str:
        with self._connection() as db:
            row = db.execute("SELECT status FROM uploads WHERE signature = ?", (signature,)).fetchone()
        return str(row[0]) if row else ""

    def upload_identity(self, signature: str) -> tuple[str, str]:
        with self._connection() as db:
            row = db.execute(
                "SELECT title, COALESCE(youtube_id, '') FROM upload_registry WHERE signature = ?",
                (signature,),
            ).fetchone()
            if not row:
                row = db.execute(
                    "SELECT title, COALESCE(youtube_id, '') FROM uploads WHERE signature = ?",
                    (signature,),
                ).fetchone()
        return (str(row[0]), str(row[1])) if row else ("", "")

    def record_upload_attempt(self, signature: str, path: Path, title: str) -> int | None:
        """Atomically claim one transfer; failures never implicitly authorize a new one."""
        stamp = datetime.now().isoformat(timespec="seconds")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            latest = db.execute("SELECT COALESCE(MAX(id),0) FROM upload_attempts WHERE signature=?", (signature,)).fetchone()[0]
            permission = db.execute("SELECT after_attempt_id FROM upload_retry_permissions WHERE signature=?", (signature,)).fetchone()
            if latest > (permission[0] if permission else 0):
                return None
            cursor = db.execute(
                "INSERT INTO upload_attempts(signature, title, path, created_at, outcome) VALUES(?,?,?,?, 'started')",
                (signature, title, str(path), stamp),
            )
            return cursor.lastrowid

    def finish_upload_attempt(self, attempt_id: int, outcome: str, detail: str = "") -> None:
        with self._connection() as db:
            db.execute("UPDATE upload_attempts SET outcome=?,detail=? WHERE id=?", (outcome, detail, attempt_id))

    def daily_upload_attempt_count(self, day: datetime | None = None) -> int:
        selected = day or datetime.now()
        start = selected.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        with self._connection() as db:
            row = db.execute(
                "SELECT COUNT(*) FROM upload_attempts WHERE created_at >= ? AND created_at < ?",
                (start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")),
            ).fetchone()
            return int(row[0] if row else 0)

    def set_upload_limit(self, kind: str, retry_at: datetime, source: str, message: str) -> dict:
        detected_at = datetime.now().astimezone()
        state = {
            "kind": kind,
            "detected_at": detected_at.isoformat(timespec="seconds"),
            "retry_at": retry_at.isoformat(timespec="seconds"),
            "source": source,
            "message": message,
        }
        with self._connection() as db:
            db.execute(
                """
                INSERT INTO upload_limit_state(id, kind, detected_at, retry_at, source, message)
                VALUES(1,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind,
                    detected_at=excluded.detected_at,
                    retry_at=excluded.retry_at,
                    source=excluded.source,
                    message=excluded.message
                """,
                (kind, state["detected_at"], state["retry_at"], source, message),
            )
        return state

    def get_upload_limit(self) -> dict | None:
        with self._connection() as db:
            row = db.execute(
                "SELECT kind, detected_at, retry_at, source, message FROM upload_limit_state WHERE id = 1"
            ).fetchone()
        if not row:
            return None
        return {"kind": row[0], "detected_at": row[1], "retry_at": row[2], "source": row[3], "message": row[4]}

    def clear_upload_limit(self) -> None:
        with self._connection() as db:
            db.execute("DELETE FROM upload_limit_state WHERE id = 1")

    def upsert(self, signature: str, path: Path, title: str, status: str, youtube_id: str = "", error: str = "") -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        size = path.stat().st_size if path.exists() else 0
        with self._connection() as db:
            db.execute(
                """
                INSERT INTO uploads(signature, path, title, youtube_id, status, size, created_at, updated_at, error)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(signature) DO UPDATE SET
                    path=excluded.path,
                    title=excluded.title,
                    youtube_id=CASE WHEN excluded.youtube_id = '' THEN uploads.youtube_id ELSE excluded.youtube_id END,
                    status=excluded.status,
                    size=excluded.size,
                    updated_at=excluded.updated_at,
                    error=excluded.error
                """,
                (signature, str(path), title, youtube_id, status, size, stamp, stamp, error),
            )

    def apply_reconciliation(self, signature: str, path: Path, title: str, youtube_id: str,
                             status: str, reason: str, error: str,
                             expected_registry: tuple | None, expected_status: tuple | None) -> bool:
        stamp = datetime.now().isoformat(timespec="seconds")
        size = path.stat().st_size
        with self._connection() as db:
            # Do not overwrite a retry or an upload that changed since the API snapshot.
            db.execute("BEGIN IMMEDIATE")
            current_registry = db.execute(
                "SELECT signature, title, path, youtube_id, reason, updated_at FROM upload_registry WHERE signature = ?",
                (signature,),
            ).fetchone()
            current_status = db.execute(
                "SELECT signature, title, path, status, error, updated_at FROM uploads WHERE signature = ?",
                (signature,),
            ).fetchone()
            if current_registry != expected_registry or current_status != expected_status:
                return False
            db.execute(
                """INSERT INTO upload_registry(signature, title, path, youtube_id, reason, created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?) ON CONFLICT(signature) DO UPDATE SET
                   youtube_id=excluded.youtube_id, reason=excluded.reason, updated_at=excluded.updated_at""",
                (signature, title, str(path), youtube_id, reason, stamp, stamp),
            )
            db.execute(
                """INSERT INTO uploads(signature, path, title, youtube_id, status, size, created_at, updated_at, error)
                   VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(signature) DO UPDATE SET
                   youtube_id=excluded.youtube_id, status=excluded.status, updated_at=excluded.updated_at, error=excluded.error""",
                (signature, str(path), title, youtube_id, status, size, stamp, stamp, error),
            )
            if status == "uploaded":
                db.execute("UPDATE upload_receipts SET confirmed_at=? WHERE signature=? AND youtube_id=?",
                           (stamp, signature, youtube_id))
        return True

    def mark_local_deleted(self, signature: str) -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        with self._connection() as db:
            db.execute(
                "UPDATE uploads SET status = 'local_deleted', updated_at = ?, error = '' WHERE signature = ?",
                (stamp, signature),
            )
            db.execute("UPDATE upload_registry SET reason = 'local_deleted', updated_at = ? WHERE signature = ?", (stamp, signature))
            db.execute("DELETE FROM service_cache WHERE scope='upload_review' AND name=?", (signature,))
            db.execute("DELETE FROM fresh_upload_permissions WHERE signature=?", (signature,))

    def registry_index(self) -> tuple[dict[str, tuple], dict[str, tuple]]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT signature, title, path, youtube_id, reason, updated_at FROM upload_registry"
            ).fetchall()
        by_signature = {row[0]: row for row in rows}
        by_path = {str(Path(row[2])): row for row in rows}
        return by_signature, by_path

    def upload_status_index(self) -> tuple[dict[str, tuple], dict[str, tuple]]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT signature, title, path, status, error, updated_at FROM uploads ORDER BY updated_at DESC"
            ).fetchall()
        by_signature = {row[0]: row for row in rows}
        by_path = {str(Path(row[2])): row for row in rows}
        return by_signature, by_path

    def uploaded_before(self, older_than: datetime, limit: int = 500) -> list[tuple]:
        with self._connection() as db:
            return db.execute(
                """
                SELECT signature, updated_at, status, title, path, youtube_id, error, size
                FROM uploads
                WHERE status = 'uploaded' AND updated_at <= ?
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (older_than.isoformat(timespec="seconds"), limit),
            ).fetchall()


class UploadCancelled(Exception):
    pass


_oauth_lock = threading.Lock()
_verification_lock = threading.Lock()


_oauth_retry_after: dict[str, tuple[float, str]] = {}


class QuotaAwareHttp:
    def __init__(self, transport, store: Store, scope: str) -> None:
        self.transport, self.store, self.scope = transport, store, scope

    def __getattr__(self, name):
        return getattr(self.transport, name)

    def request(self, uri, method="GET", **kwargs):
        uploading = "/upload/" in uri or "upload_id=" in uri
        pause = self.store.api_pause(self.scope)
        if not pause and uploading:
            pause = self.store.api_pause(self.scope, "upload")
        if pause:
            raise ApiQuotaUnavailable(pause)
        response, content = self.transport.request(uri, method=method, **kwargs)
        if int(response.status) in {403, 429}:
            error = HttpError(response, content, uri=uri)
            if (is_youtube_quota_error(error) or int(response.status) == 429) and not is_youtube_channel_upload_limit(error):
                # Granular upload quotas do not block read requests.
                text = str(error).lower()
                bucket = "upload" if "video uploads" in text or "videouploads" in text else "general"
                self.store.defer_api(self.scope, error, bucket)
        return response, content


class YouTubeClient:
    def __init__(self, store: Store, config: Config, log: Callable[[str], None], client_secret_path: str = "", label: str = "principal", force_authorize: bool = False) -> None:
        self.store = store
        self.config = config
        self.log = log
        self.client_secret_path = client_secret_path or config.client_secret_path
        self.label = label
        self.force_authorize = force_authorize
        self.token_path = store.token_path_for(self.client_secret_path)
        self.scope = api_scope(self.client_secret_path)
        self._service = None
        self._known_titles: set[str] | None = None
        self._known_video_ids: set[str] | None = None
        self._known_title_candidates: dict[str, list[str]] | None = None
        self._known_video_states: dict[str, str] | None = None
        self._known_video_metadata: dict[str, dict] | None = None
        self._index_checked_at = 0.0
        self._index_requested_ids: set[str] | None = None
        self._index_identity: str | None = None
        self._channel_info: dict | None = None

    def available(self) -> bool:
        return all([Request, Credentials, InstalledAppFlow, build, MediaFileUpload, AuthorizedHttp, httplib2])

    def service(self):
        if not self.available():
            raise RuntimeError("Faltan dependencias. Instala requirements.txt antes de ejecutar la app.")
        pause = self.store.api_pause(self.scope)
        if pause:
            raise ApiQuotaUnavailable(pause)
        if self._service:
            return self._service

        # UI checks, scanning and uploads may request authorization concurrently.
        with _oauth_lock:
            retry_key = str(self.token_path.resolve())
            retry_at, previous_error = _oauth_retry_after.get(retry_key, (0, ""))
            if time.monotonic() < retry_at:
                raise RuntimeError(f"OAuth en espera breve tras un error: {previous_error}. Reintenta en 30 segundos.")
            try:
                creds = self._authorize()
            except Exception as exc:
                _oauth_retry_after[retry_key] = (time.monotonic() + 30, describe_error(exc))
                raise
            _oauth_retry_after.pop(retry_key, None)

        # Google's factory leaves resumable-upload HTTP 308 responses to next_chunk().
        http = build_http()
        http.timeout = 30
        transport = QuotaAwareHttp(AuthorizedHttp(creds, http=http), self.store, self.scope)
        self._service = build("youtube", "v3", http=transport, cache_discovery=False)
        return self._service

    def _authorize(self):
        creds = None
        if self.token_path.exists() and not self.force_authorize:
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception:
                creds = None
        missing_scopes = bool(creds and hasattr(creds, "has_scopes") and not creds.has_scopes(SCOPES))
        if missing_scopes:
            self.log("Los permisos de YouTube cambiaron. Se pedira autorizacion de nuevo.")
            creds = None
        if not creds or not creds.valid or missing_scopes:
            if creds and creds.refresh_token and not missing_scopes:
                try:
                    creds.refresh(partial(Request(), timeout=30))
                except RefreshError as exc:
                    if any(reason in str(exc).lower() for reason in ("invalid_grant", "invalid_scope", "unauthorized_client")):
                        self.log("Google solicita renovar la autorizacion del canal.")
                        creds = None
                    else:
                        raise
            else:
                creds = None
            if not creds:
                if not self.client_secret_path or not Path(self.client_secret_path).exists():
                    raise RuntimeError("Selecciona el archivo client_secret.json en Configuracion.")
                self.log(f"Autorizando credencial OAuth {self.label}.")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, SCOPES, autogenerate_code_verifier=True)
                flow.fetch_token = partial(flow.fetch_token, timeout=30)
                creds = flow.run_local_server(
                    port=0, prompt="consent select_account", timeout_seconds=180,
                    authorization_prompt_message="",
                )
            if not creds or not creds.valid:
                raise RuntimeError("La autorizacion no termino correctamente. Vuelve a conectar YouTube.")
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.token_path.parent,
                                                 prefix=self.token_path.stem, suffix=".tmp", delete=False) as output:
                    temporary = Path(output.name)
                    output.write(creds.to_json())
                temporary.replace(self.token_path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return creds

    def channel_info(self) -> dict:
        if self._channel_info is not None:
            return self._channel_info
        response = self.service().channels().list(part="snippet,contentDetails", mine=True).execute()
        items = response.get("items", [])
        if not items:
            raise RuntimeError("La cuenta conectada no devuelve ningun canal de YouTube.")
        item = items[0]
        snippet = item.get("snippet", {})
        uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
        self._channel_info = {
            "title": snippet.get("title", "Canal sin nombre"),
            "id": item.get("id", ""),
            "uploads": uploads,
            "description": snippet.get("description", ""),
            "thumbnail": (snippet.get("thumbnails", {}).get("high", {}).get("url")
                          or snippet.get("thumbnails", {}).get("default", {}).get("url") or ""),
        }
        return self._channel_info

    def playlists(self) -> list[dict]:
        service = self.service()
        playlists: list[dict] = [{"id": "", "title": "Ninguna"}]
        page_token = None
        while True:
            response = service.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=page_token).execute()
            for item in response.get("items", []):
                playlists.append({"id": item.get("id", ""), "title": item.get("snippet", {}).get("title", "Lista sin nombre")})
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return playlists

    def create_playlist(self, title: str, privacy_status: str) -> dict:
        title = title.strip()
        if not title:
            raise ValueError("El nombre de la lista no puede estar vacio.")
        response = self.service().playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": f"Lista creada desde {APP_NAME}.",
                },
                "status": {"privacyStatus": privacy_status},
            },
        ).execute()
        return {"id": response.get("id", ""), "title": response.get("snippet", {}).get("title", title)}

    def channel_gallery(self) -> tuple[list[dict], list[dict]]:
        self.uploaded_video_index(force=True)
        playlists = self.playlists()
        memberships: dict[str, list[dict]] = {}
        service = self.service()
        for playlist in playlists:
            playlist_id = playlist.get("id", "")
            if not playlist_id:
                continue
            page_token = None
            while True:
                response = service.playlistItems().list(
                    part="contentDetails",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                ).execute()
                for item in response.get("items", []):
                    video_id = item.get("contentDetails", {}).get("videoId", "")
                    if video_id:
                        memberships.setdefault(video_id, []).append(
                            {
                                "playlist_id": playlist_id,
                                "playlist_title": playlist.get("title", ""),
                                "item_id": item.get("id", ""),
                            }
                        )
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        videos = []
        all_ids = list(dict.fromkeys(video_id for values in (self._known_title_candidates or {}).values() for video_id in values))
        for video_id in all_ids:
            metadata = (self._known_video_metadata or {}).get(video_id, {})
            videos.append(
                {
                    "id": video_id,
                    "title": metadata.get("title", "") or "Sin titulo",
                    "duration": format_iso_duration(metadata.get("duration", "")),
                    "privacy": metadata.get("privacy", "") or "desconocido",
                    "published_at": metadata.get("published_at", ""),
                    "thumbnail": metadata.get("thumbnail", ""),
                    "filename": metadata.get("filename", ""),
                    "size": metadata.get("size", 0),
                    "fingerprint": metadata.get("fingerprint", ""),
                    "raw_duration": metadata.get("duration", ""),
                    "memberships": memberships.get(video_id, []),
                }
            )
        videos.sort(key=lambda item: item["published_at"], reverse=True)
        self.store.save_service_cache(self.scope, "gallery", {"videos": videos, "playlists": playlists})
        return videos, playlists

    def set_video_privacy(self, video_id: str, privacy_status: str) -> None:
        if privacy_status not in {"private", "unlisted", "public"}:
            raise ValueError("Privacidad de YouTube no válida.")
        self.service().videos().update(
            part="status",
            body={"id": video_id, "status": {"privacyStatus": privacy_status}},
        ).execute()
        if self._known_video_metadata is not None and video_id in self._known_video_metadata:
            self._known_video_metadata[video_id]["privacy"] = privacy_status

    def set_video_unlisted(self, video_id: str) -> None:
        self.set_video_privacy(video_id, "unlisted")

    def replace_video_playlist(self, video_id: str, memberships: list[dict], target_playlist_id: str) -> None:
        service = self.service()
        already_in_target = False
        for membership in memberships:
            playlist_id = membership.get("playlist_id", "")
            item_id = membership.get("item_id", "")
            if playlist_id == target_playlist_id:
                already_in_target = True
                continue
            if item_id:
                service.playlistItems().delete(id=item_id).execute()
        if target_playlist_id and not already_in_target:
            service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": target_playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()

    def delete_video(self, video_id: str) -> None:
        if not video_id:
            raise ValueError("No hay ID de YouTube para eliminar el video.")
        self.service().videos().delete(id=video_id).execute()

    def uploaded_titles(self, force: bool = False) -> set[str]:
        titles, _video_ids = self.uploaded_video_index(force=force)
        return titles

    def _verification_scope(self) -> str:
        try:
            token_version = str(self.token_path.stat().st_mtime_ns)
        except FileNotFoundError:
            token_version = "no-token"
        identity = f"{self.config.connected_channel_id}|{token_version}"
        return self.scope + ":" + hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def uploaded_video_index(self, force: bool = False, video_ids: list[str] | None = None) -> tuple[set[str], set[str]]:
        with _verification_lock:
            return self._uploaded_video_index(force, video_ids)

    def _uploaded_video_index(self, force: bool, video_ids: list[str] | None) -> tuple[set[str], set[str]]:
        requested_ids = None if video_ids is None else set(video_ids)
        identity = self._verification_scope()
        pause = self.store.api_pause(self.scope)
        if pause:
            raise ApiQuotaUnavailable(pause)
        if video_ids is None:
            cache_covers_request = self._index_requested_ids is None
        else:
            known = self._index_requested_ids if self._index_requested_ids is not None else set(self._known_video_states or {})
            cache_covers_request = set(video_ids).issubset(known)
        if (self._known_titles is not None and self._known_video_ids is not None and not force
                and self._index_identity == identity
                and time.monotonic() - self._index_checked_at < (300 if video_ids is None else 60) and cache_covers_request):
            return self._known_titles, self._known_video_ids

        # Share short-lived checks across the UI and worker; destructive actions bypass this.
        if not force and (self._known_titles is None or self._index_identity != identity):
            for name, ttl in (("verification_ids", 60), ("verification_full", 300 if requested_ids is None else 60)):
                cached = self.store.fresh_service_cache(self.scope, name, ttl)
                if not cached or cached.get("identity") != identity:
                    continue
                covered = cached["requested_ids"]
                if ((requested_ids is None and covered is not None)
                        or (requested_ids is not None and not requested_ids.issubset(
                            set(covered) if covered is not None else set(cached["states"])))):
                    continue
                self._known_video_states = cached["states"]
                self._known_video_metadata = cached["metadata"]
                self._known_title_candidates = cached["candidates"]
                self._known_video_ids = {key for key, state in cached["states"].items() if state == "processed"}
                self._known_titles = {title for title, ids in cached["candidates"].items()
                                      if any(video_id in self._known_video_ids for video_id in ids)}
                self._index_requested_ids = None if covered is None else set(covered)
                self._index_identity = identity
                # Keep the persisted expiry; do not renew it each time it is read.
                age = (datetime.now().astimezone() - datetime.fromisoformat(cached["checked_at"])).total_seconds()
                self._index_checked_at = time.monotonic() - max(0, age)
                return self._known_titles, self._known_video_ids

        service = self.service()
        title_candidates: dict[str, list[str]] = {}
        uploads = self.channel_info()["uploads"] if video_ids is None else ""
        page_token = None
        while video_ids is None:
            response = service.playlistItems().list(
                part="snippet",
                playlistId=uploads,
                maxResults=50,
                pageToken=page_token,
            ).execute()
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                title = snippet.get("title")
                video_id = snippet.get("resourceId", {}).get("videoId")
                if title:
                    if video_id:
                        title_candidates.setdefault(title, []).append(video_id)
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        video_states: dict[str, str] = {}
        video_metadata: dict[str, dict] = {}
        owner_id = self.channel_info().get("id", "") if requested_ids is not None else ""
        all_video_ids = list(dict.fromkeys(video_ids if video_ids is not None else
                                         (video_id for values in title_candidates.values() for video_id in values)))
        for offset in range(0, len(all_video_ids), 50):
            batch = all_video_ids[offset : offset + 50]
            response = service.videos().list(
                part="snippet,status,processingDetails,fileDetails,contentDetails",
                id=",".join(batch),
                maxResults=50,
            ).execute()
            for item in response.get("items", []):
                video_id = item.get("id", "")
                if owner_id and item.get("snippet", {}).get("channelId") != owner_id:
                    continue
                state = remote_video_state(item)
                if video_id:
                    video_states[video_id] = state
                    snippet = item.get("snippet", {})
                    if snippet.get("title") and video_id not in title_candidates.get(snippet["title"], []):
                        title_candidates.setdefault(snippet["title"], []).append(video_id)
                    file_details = item.get("fileDetails", {})
                    description = snippet.get("description", "") or ""
                    marker = ""
                    for line in description.splitlines():
                        if line.startswith("YouTubeSync-Fingerprint: "):
                            marker = line.split(": ", 1)[1].strip()
                            break
                    try:
                        remote_size = int(file_details.get("fileSize", 0) or 0)
                    except (TypeError, ValueError):
                        remote_size = 0
                    video_metadata[video_id] = {
                        "title": snippet.get("title", ""),
                        "channel_id": snippet.get("channelId", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "thumbnail": (
                            snippet.get("thumbnails", {}).get("medium", {}).get("url")
                            or snippet.get("thumbnails", {}).get("default", {}).get("url")
                            or snippet.get("thumbnails", {}).get("high", {}).get("url")
                            or ""
                        ),
                        "duration": item.get("contentDetails", {}).get("duration", ""),
                        "privacy": item.get("status", {}).get("privacyStatus", ""),
                        "filename": Path(file_details.get("fileName", "") or "").name,
                        "size": remote_size,
                        "fingerprint": marker,
                    }
        ready_ids = {video_id for video_id, state in video_states.items() if state == "processed"}
        title_ids = {
            title: next((video_id for video_id in candidates if video_id in ready_ids), "")
            for title, candidates in title_candidates.items()
        }
        title_ids = {title: video_id for title, video_id in title_ids.items() if video_id}
        titles = set(title_ids)
        video_ids = set(ready_ids)
        self._known_titles = titles
        self._known_video_ids = video_ids
        self._known_title_candidates = title_candidates
        self._known_video_states = video_states
        self._known_video_metadata = video_metadata
        self._index_checked_at = time.monotonic()
        self._index_requested_ids = requested_ids
        self._index_identity = self._verification_scope()
        self.store.save_service_cache(self.scope, "verification_full" if requested_ids is None else "verification_ids", {
            "identity": self._index_identity,
            "requested_ids": None if requested_ids is None else sorted(requested_ids),
            "states": video_states, "metadata": video_metadata, "candidates": title_candidates,
            "checked_at": datetime.now().astimezone().isoformat(),
        })
        processing = sum(1 for state in video_states.values() if state in {"uploaded", "processing"})
        self.log(f"Comprobados {len(titles)} videos procesados en YouTube" + (f" y {processing} procesando." if processing else "."))
        return titles, video_ids

    def verify_local_file(self, path: Path, title: str, youtube_id: str = "") -> tuple[bool, str, str, str]:
        if self._known_video_states is None:
            self.uploaded_video_index()
        candidates = []
        if youtube_id and youtube_id in (self._known_video_states or {}):
            candidates.append(youtube_id)
        candidates.extend(
            video_id for video_id in (self._known_title_candidates or {}).get(title, []) if video_id not in candidates
        )
        rejected = self.store.rejected_video_ids(file_signature(path))
        if isinstance(rejected, set):
            candidates = [candidate for candidate in candidates if candidate not in rejected]
        if not candidates:
            return False, "", "el video no aparece en el canal", "missing"
        local_size = path.stat().st_size
        local_name = path.name.casefold()
        local_fingerprints = {}
        mismatch_reasons = []
        uncertain = []
        candidates.sort(key=lambda candidate: ((self._known_video_states or {}).get(candidate) != "processed", candidate != youtube_id))
        for candidate in candidates:
            state = (self._known_video_states or {}).get(candidate, "missing")
            metadata = (self._known_video_metadata or {}).get(candidate, {})
            marker = metadata.get("fingerprint", "")
            receipt = self.store.receipt(candidate)
            if not marker and receipt:
                if "full" not in local_fingerprints:
                    local_fingerprints["full"] = full_content_fingerprint(path)
                remote_size = int(metadata.get("size", 0) or 0)
                if (receipt[0] == local_fingerprints["full"] and receipt[1] == local_size
                        and (not remote_size or remote_size == local_size)):
                    return True, candidate, "ID de recepcion y huella local persistente confirmados", state
            if marker:
                algorithm = "full" if marker.startswith("sha256:") else "legacy"
                if algorithm not in local_fingerprints:
                    local_fingerprints[algorithm] = full_content_fingerprint(path) if algorithm == "full" else file_content_fingerprint(path)
                if marker == local_fingerprints[algorithm]:
                    remote_size = int(metadata.get("size", 0) or 0)
                    if remote_size and remote_size != local_size:
                        mismatch_reasons.append(f"{candidate}: huella declarada coincidente pero tamaño recibido distinto")
                        continue
                    if algorithm == "legacy":
                        remote_name = str(metadata.get("filename", "")).casefold()
                        if not remote_size or not remote_name:
                            uncertain.append(candidate)
                            continue
                        if remote_name != local_name:
                            mismatch_reasons.append(f"{candidate}: nombre original distinto")
                            continue
                    return True, candidate, "huella de contenido confirmada", state
                mismatch_reasons.append(f"{candidate}: la huella de contenido no coincide")
                continue
            remote_size = int(metadata.get("size", 0) or 0)
            remote_name = str(metadata.get("filename", "")).casefold()
            if (not remote_size or remote_size == local_size) and (not remote_name or remote_name == local_name):
                uncertain.append(candidate)
            reasons = []
            if remote_size and remote_size != local_size:
                reasons.append("tamaño distinto")
            if remote_name and remote_name != local_name:
                reasons.append("nombre original distinto")
            if not remote_size or not remote_name:
                reasons.append("faltan metadatos para confirmar el contenido")
            mismatch_reasons.append(f"{candidate}: {', '.join(reasons)}")
        if uncertain:
            return False, uncertain[0], "No hay datos suficientes para confirmar el contenido; revisa el video en Canal", "unverified"
        first = candidates[0]
        state = (self._known_video_states or {}).get(first, "missing")
        return False, first, "; ".join(mismatch_reasons[:3]), state

    def upload(self, path: Path, title: str, cancel_event: threading.Event, progress: Callable[[int, str], None]) -> str:
        signature = file_signature(path)
        fingerprint = full_content_fingerprint(path)
        body = {
            "snippet": {
                "title": title,
                "description": (
                    f"Subido automaticamente por {APP_NAME}.\n"
                    f"Archivo original: {path.name}\n"
                    f"YouTubeSync-Fingerprint: {fingerprint}"
                ),
                "categoryId": self.config.category_id,
            },
            "status": {"privacyStatus": self.config.privacy_status},
        }
        media = MediaFileUpload(str(path), chunksize=8 * 1024 * 1024, resumable=True)
        request = None
        try:
            request = self.service().videos().insert(part="snippet,status", body=body, media_body=media)
            response = None
            progress(0, path.name)
            while response is None:
                if cancel_event.is_set():
                    raise UploadCancelled("Subida cancelada por el usuario.")
                status, response = request.next_chunk(num_retries=3 if request.resumable_uri else 0)
                if status:
                    percent = int(status.progress() * 100)
                    progress(percent, path.name)
                    self.log(f"Subiendo {path.name}: {percent}%")
        except Exception as exc:
            exc.upload_session_started = bool(request is not None and request.resumable_uri)
            raise
        finally:
            media.stream().close()
        video_id = response["id"]
        if file_signature(path) != signature:
            self.store.upsert(signature, path, title, "error", youtube_id=video_id,
                              error="El archivo cambio durante la transferencia; revisa el video recibido en Canal")
            raise RuntimeError("El archivo cambio durante la transferencia; no se confirma su contenido")
        self.store.remember_receipt(signature, path, video_id, fingerprint)
        progress(100, path.name)
        if self._known_title_candidates is not None:
            self._known_title_candidates.setdefault(title, []).insert(0, video_id)
        if self._known_video_states is not None:
            self._known_video_states[video_id] = "processing"
        if self._known_video_metadata is not None:
            self._known_video_metadata[video_id] = {
                "title": title,
                "published_at": "",
                "duration": "",
                "privacy": self.config.privacy_status,
                "filename": path.name,
                "size": path.stat().st_size,
                "fingerprint": fingerprint,
            }
        try:
            self.add_to_playlist(video_id)
        except Exception as exc:
            self.log(f"El video se subio, pero no se pudo anadir a la lista: {exc}")
        return video_id

    def add_to_playlist(self, video_id: str) -> None:
        if not self.config.playlist_id:
            return
        self.service().playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": self.config.playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()
        self.log(f"Anadido a la lista: {self.config.playlist_name or self.config.playlist_id}")


def reconcile_local_uploads(store: Store, config: Config, client: YouTubeClient,
                            full: bool = False, is_active: Callable[[Path], bool] | None = None) -> int:
    """Reconcile persisted identities without uploading or deleting any video."""
    if not config.watch_folder:
        return 0
    folder = Path(config.watch_folder).resolve()
    registry, _ = store.registry_index()
    statuses, _ = store.upload_status_index()
    retry_required = store.retry_required_signatures()
    candidates = {}
    for signature, row in {**registry, **statuses}.items():
        path = Path(row[2]).resolve()
        if not path.is_relative_to(folder) or (not config.recursive and path.parent != folder):
            continue
        record = registry.get(signature)
        status = statuses.get(signature)
        if record and record[3] and record[4] in {"uploaded", "youtube_title_exists", "manual_confirmed", "local_deleted"}:
            continue
        if is_active and is_active(path):
            continue
        try:
            if not path.is_file() or file_signature(path) != signature:
                continue
        except OSError:
            continue
        video_id = record[3] if record else ""
        if not video_id:
            _title, video_id = store.upload_identity(signature)
        if full or (record and record[4] == "processing") or (status and status[3] in {"uploading", "processing", "waiting_quota"}):
            candidates[signature] = (path, record[1] if record else row[1], video_id)
    if not candidates:
        return 0
    if full and any(not item[2] for item in candidates.values()):
        client.uploaded_video_index(force=True)
    elif any(item[2] for item in candidates.values()):
        client.uploaded_video_index(video_ids=list({item[2] for item in candidates.values() if item[2]}))
    changed = 0
    for signature, (path, title, video_id) in candidates.items():
        if is_active and is_active(path):
            continue
        try:
            if not path.is_file() or file_signature(path) != signature:
                continue
            # An ID-less failed attempt needs the full channel scan before retrying.
            if not full and not video_id:
                if statuses.get(signature, (None,) * 4)[3] != "uploading":
                    continue
                confirmed, resolved_id, reason, state = False, "", "Subida interrumpida; puedes reintentar", "missing"
            else:
                confirmed, resolved_id, reason, state = client.verify_local_file(path, title, video_id)
            if is_active and is_active(path):
                continue
            if file_signature(path) != signature:
                continue
            if confirmed and state == "processed":
                new_status, registry_reason, error = "uploaded", "uploaded", ""
            elif confirmed and state == "processing":
                new_status, registry_reason, error = "processing", "processing", ""
            elif state == "missing":
                new_status, registry_reason, error = "pending", "remote_missing", reason
                if signature in retry_required:
                    new_status = "error"
                    error = "Intento anterior sin confirmar. Revisa el canal y pulsa Reintentar."
            else:
                new_status, registry_reason = (("verification_pending", "needs_verification") if state == "unverified"
                                              else ("error", "unverified"))
                error = reason if not confirmed else f"YouTube indica {state}. Revisa el video en Canal antes de reintentar."
            previous = statuses.get(signature)
            record = registry.get(signature)
            if (previous and previous[3] == new_status and previous[4] == error
                    and record and record[3] == resolved_id and record[4] == registry_reason):
                continue
            if store.apply_reconciliation(signature, path, title, resolved_id or video_id,
                                          new_status, registry_reason, error, record, previous):
                changed += 1
        except OSError as exc:
            client.log(f"No se pudo comprobar {path.name}: {describe_error(exc)}")
    return changed


class SyncWorker(threading.Thread):
    def __init__(self, store: Store, get_config: Callable[[], Config], events: queue.Queue) -> None:
        super().__init__(daemon=True)
        self.store = store
        self.get_config = get_config
        self.events = events
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.cancel_upload_event = threading.Event()
        self.enabled_event = threading.Event()
        self.busy_event = threading.Event()
        self.manual_uploads: queue.Queue[Path] = queue.Queue()
        self.last_cleanup_warning_key = ""
        self.active_path: Path | None = None
        self._client: YouTubeClient | None = None
        self._id_client: YouTubeClient | None = None
        self._client_config: str = ""
        self._last_cleanup_at = 0.0
        self.operation_lock = threading.RLock()
        self._announced_reviews: set[str] = set()

    def log(self, text: str) -> None:
        self.events.put(("log", f"[{now_text()}] {text}"))

    def problem(self, message: str, path: Path | None = None, source: str = "upload",
                error: Exception | None = None, operation: str = "") -> None:
        diagnostic = "".join(traceback.format_exception(type(error), error, error.__traceback__)) if error else ""
        self.events.put(("problem", {"message": message, "path": str(path) if path else "", "source": source,
                                     "operation": operation, "diagnostic": diagnostic}))

    def progress(self, percent: int, filename: str) -> None:
        self.events.put(("progress", {"percent": percent, "filename": filename}))

    def pause_for_youtube_limit(self, exc: Exception) -> tuple[str, dict]:
        message = youtube_error_message(exc)
        if not isinstance(exc, ApiQuotaUnavailable):
            self.log(f"Rechazo de YouTube: {describe_error(exc)}")
        if not is_youtube_channel_upload_limit(exc):
            config = self.get_config()
            scope = api_scope(config.client_secret_path)
            state = exc.state if isinstance(exc, ApiQuotaUnavailable) else (
                self.store.api_pause(scope) or self.store.api_pause(scope, "upload") or self.store.defer_api(scope, exc))
            self.cancel_upload_event.set()
            self.events.put(("api_quota", state))
            self.log(f"{message} Proximo intento: {state['retry_at']} ({state['source']}).")
            return message, state
        kind, retry_at, source = youtube_retry_prediction(exc)
        state = self.store.set_upload_limit(kind, retry_at, source, message)
        self.enabled_event.clear()
        self.cancel_upload_event.set()
        self.events.put(("upload_limited", state))
        return message, state

    def available_client(self, config: Config) -> YouTubeClient | None:
        path = config.client_secret_path.strip()
        if not path:
            return None
        if not Path(path).exists():
            self.log("OAuth omitido: no existe el JSON configurado.")
            return None
        key = json.dumps(asdict(config), sort_keys=True)
        if self._client is None or self._client_config != key:
            self._client = YouTubeClient(self.store, config, self.log, path)
            self._id_client = None
            self._client_config = key
        return self._client

    def refresh(self) -> None:
        self.wake_event.set()

    def upload_path(self, path: Path) -> None:
        self.manual_uploads.put(path)
        self.wake_event.set()

    def set_enabled(self, enabled: bool) -> None:
        if self.enabled_event.is_set() == enabled:
            return
        if enabled:
            self.enabled_event.set()
            self.cancel_upload_event.clear()
            self.wake_event.set()
            self.log("Modo automatico activado.")
        else:
            self.enabled_event.clear()
            self.cancel_upload_event.set()
            self.wake_event.set()
            self.log("Modo automatico pausado.")

    def pause_after_current(self) -> None:
        self.enabled_event.clear()
        queued = 0
        while True:
            try:
                self.manual_uploads.get_nowait()
                queued += 1
            except queue.Empty:
                break
        if queued:
            self.log(f"Subidas manuales en cola retiradas antes del borrado local: {queued}.")
        self.wake_event.set()
        self.log("Modo automatico pausado para no iniciar mas subidas; la subida actual continuara.")

    def cancel_upload(self) -> None:
        self.cancel_upload_event.set()
        self.log("Cancelacion solicitada. Se detendra al terminar el bloque actual.")

    def stop(self) -> None:
        self.stop_event.set()
        self.cancel_upload_event.set()
        self.wake_event.set()

    def run(self) -> None:
        self.log("Servicio en segundo plano iniciado.")
        while not self.stop_event.is_set():
            try:
                manual_path = self.manual_uploads.get_nowait()
            except queue.Empty:
                manual_path = None
            if not self.enabled_event.is_set() and manual_path is None:
                self.events.put(("busy", False))
                self.wake_event.wait(1)
                self.wake_event.clear()
                continue
            try:
                with self.operation_lock:
                    if self.stop_event.is_set():
                        break
                    self.busy_event.set()
                    self.scan_once(manual_path)
                    if self.enabled_event.is_set():
                        self.auto_cleanup_once()
            except Exception as exc:
                self.problem(describe_error(exc), error=exc, operation="Servicio de sincronizacion")
            finally:
                self.busy_event.clear()
            self.events.put(("busy", False))
            config = self.get_config()
            self.wake_event.wait(max(2, int(config.scan_interval_seconds)))
            self.wake_event.clear()
        self.log("Servicio detenido.")

    def scan_once(self, manual_path: Path | None = None) -> None:
        config = self.get_config()
        folder = Path(config.watch_folder) if config.watch_folder else None
        if not self.enabled_event.is_set() and manual_path is None:
            return
        if not folder or not folder.exists():
            self.problem("La carpeta configurada no existe. Elige una carpeta valida.", source="configuration")
            return

        self.events.put(("busy", True))
        self.cancel_upload_event.clear()
        if manual_path is not None:
            if not manual_path.exists() or manual_path.suffix.lower() not in config.extension_set:
                self.log(f"No se puede subir el archivo seleccionado: {manual_path.name} ya no esta disponible.")
                return
            pending = [manual_path]
            self.log(f"Subida manual seleccionada: {manual_path.name}.")
        else:
            pending = list(self.iter_videos(folder, config))
        if not pending:
            self.log("No hay videos pendientes.")
            self.events.put(("progress", {"percent": 0, "filename": ""}))
            return

        eligible = []
        awaiting_review = self.store.pending_upload_reviews()
        if not isinstance(awaiting_review, dict):
            awaiting_review = {}
        for path in pending:
            try:
                signature = file_signature(path)
                known_id = self.store.upload_identity(signature)[1]
                if (known_id and signature not in awaiting_review) or not self.requires_upload_review(path):
                    eligible.append(path)
            except OSError as exc:
                self.log(f"Se conserva {path.name}: {describe_error(exc)}")
        pending = eligible
        if not pending:
            self.progress(0, "")
            return
        client = self.available_client(config)
        if not client:
            self.problem("No hay credenciales OAuth disponibles. Configura el JSON OAuth.", source="connection")
            return
        pause = self.store.api_pause(client.scope) or self.store.api_pause(client.scope, "upload")
        if pause:
            self.events.put(("api_quota", pause))
            return

        self.log(f"Encontrados {len(pending)} video(s) candidato(s).")
        try:
            identities = [self.store.upload_identity(file_signature(path))[1] for path in pending]
            if not all(identities):
                client.uploaded_titles(force=manual_path is not None)
            if any(identities):
                if self._id_client is None:
                    self._id_client = YouTubeClient(self.store, config, self.log)
                self._id_client.uploaded_video_index(
                    force=manual_path is not None,
                    video_ids=list(dict.fromkeys(video_id for video_id in identities if video_id)))
        except HttpError as exc:
            if is_youtube_quota_error(exc):
                self.pause_for_youtube_limit(exc)
            else:
                self.problem(f"No se pudo comprobar YouTube antes de subir: {youtube_error_message(exc)}", error=exc, operation="Verificacion previa a la subida")
            return
        except Exception as exc:
            if is_youtube_quota_error(exc):
                self.pause_for_youtube_limit(exc)
                return
            self.problem(f"No se pudo comprobar YouTube antes de subir: {describe_error(exc)}", error=exc, operation="Verificacion previa a la subida")
            return
        for path, video_id in zip(pending, identities):
            if self.stop_event.is_set() or self.cancel_upload_event.is_set():
                return
            if manual_path is None and not self.enabled_event.is_set():
                return
            self.active_path = path
            try:
                self.handle_file(path, self._id_client if video_id else client)
            finally:
                self.active_path = None

    def auto_cleanup_once(self) -> None:
        config = self.get_config()
        if not config.auto_delete_uploaded:
            return
        if time.monotonic() - self._last_cleanup_at < 300:
            return
        self._last_cleanup_at = time.monotonic()
        older_than = datetime.now() - config.auto_delete_delay
        rows = [row for row in self.store.uploaded_before(older_than) if Path(row[4]).is_file()]
        if not rows:
            return
        try:
            verifier = YouTubeClient(self.store, config, self.log)
            verifier.uploaded_video_index(force=True, video_ids=list({row[5] for row in rows if row[5]}))
        except Exception as exc:
            self.problem(f"Limpieza automatica cancelada: no se pudo comprobar YouTube ({exc}).", source="cleanup", error=exc, operation="Verificacion antes de borrar")
            return
        confirmed_rows = []
        mismatches = []
        for signature, _updated_at, _status, title, path, youtube_id, _error, _size in rows:
            if self.stop_event.is_set():
                return
            target = Path(path)
            if not target.exists():
                self.store.mark_local_deleted(signature)
                continue
            try:
                if file_signature(target) != signature:
                    mismatches.append((target.name, "el archivo local ha cambiado desde la subida"))
                    continue
            except OSError as exc:
                mismatches.append((target.name, f"no se pudo comprobar el archivo local: {describe_error(exc)}"))
                continue
            confirmed, resolved_id, reason, remote_state = verifier.verify_local_file(target, title, youtube_id)
            confirmed = confirmed and remote_state == "processed"
            if not confirmed:
                mismatches.append((target.name, reason))
            else:
                if not youtube_id and resolved_id:
                    self.store.update_registry_youtube_id(signature, resolved_id)
                confirmed_rows.append((signature, target))

        if mismatches:
            for filename, reason in mismatches:
                self.log(f"Limpieza automatica cancelada para {filename}: {reason}.")
            warning_key = "|".join(sorted(filename for filename, _reason in mismatches))
            if warning_key != self.last_cleanup_warning_key:
                self.last_cleanup_warning_key = warning_key
                preview = "\n".join(f"- {filename}: {reason}" for filename, reason in mismatches[:8])
                self.events.put(
                    (
                        "cleanup_warning",
                        f"Limpieza automatica cancelada. No se ha borrado ningun archivo porque {len(mismatches)} video(s) no se confirmaron en el canal:\n\n{preview}\n\nRevisa la pestana Ya subidos y usa el borrado manual para confirmar.",
                    )
                )
            return

        self.last_cleanup_warning_key = ""
        deleted = 0
        for signature, target in confirmed_rows:
            try:
                if file_signature(target) != signature:
                    self.log(f"Limpieza automatica: se conserva {target.name} porque ha cambiado durante la comprobacion.")
                    continue
                target.unlink()
                self.store.mark_local_deleted(signature)
                deleted += 1
            except OSError as exc:
                self.log(f"Limpieza automatica: no se pudo borrar {target}: {exc}")
        if deleted:
            self.log(f"Limpieza automatica: {deleted} archivo(s) local(es) borrado(s).")
            self.events.put(("folder_refresh", False))

    def iter_videos(self, folder: Path, config: Config) -> Iterable[Path]:
        pattern = "**/*" if config.recursive else "*"
        extensions = config.extension_set
        registry, _ = self.store.registry_index()
        statuses, _ = self.store.upload_status_index()
        retry_required = self.store.retry_required_signatures()
        confirmed = {signature for signature, row in registry.items()
                     if row[3] and row[4] in {"uploaded", "youtube_title_exists", "manual_confirmed"}}
        try:
            iterator = folder.glob(pattern)
            for path in iterator:
                try:
                    if not path.is_file() or path.suffix.lower() not in extensions:
                        continue
                    signature = file_signature(path)
                    if statuses.get(signature, (None,) * 4)[3] == "verification_pending":
                        continue
                    if (signature in retry_required
                            and statuses.get(signature, (None,) * 4)[3] not in {"uploading", "processing"}
                            and registry.get(signature, (None,) * 5)[4] != "processing"):
                        continue
                    if signature not in confirmed and self.is_stable(path, config.stable_wait_seconds):
                        yield path
                except OSError as exc:
                    self.log(f"No puedo leer {path}: {describe_error(exc)}")
        except OSError as exc:
            self.log(f"No se pudo revisar la carpeta {folder}: {describe_error(exc)}")

    def is_stable(self, path: Path, wait_seconds: int) -> bool:
        stat = path.stat()
        age_seconds = time.time() - stat.st_mtime
        return age_seconds >= max(1, int(wait_seconds))

    def requires_upload_review(self, path: Path) -> bool:
        if self.store.has_success(file_signature(path)):
            return False
        review = self.store.review_before_upload(path)
        if review.get("approved") is True:
            return False
        signature = review["signature"]
        if signature not in self._announced_reviews:
            self._announced_reviews.add(signature)
            self.log(f"Revisión necesaria antes de subir {path.name}: " +
                     (f"dura {review['seconds']} s." if review.get("seconds") is not None else "duración desconocida."))
            self.events.put(("upload_review", review))
            self.events.put(("folder_refresh", False))
        return True

    def handle_file(self, path: Path, client: YouTubeClient) -> None:
        try:
            if not path.exists():
                self.log(f"Omitido {path}: ya no existe.")
                return
            signature = file_signature(path)
            title = creation_title(path)
        except OSError as exc:
            self.log(f"Omitido {path}: {describe_error(exc)}")
            return
        if self.store.has_success(signature):
            self.log(f"Omitido {path.name}: ya esta en el registro permanente.")
            return
        saved_title, saved_id = self.store.upload_identity(signature)
        content_matches, youtube_id, match_reason, remote_state = client.verify_local_file(path, saved_title or title, saved_id)
        fresh = self.store.fresh_upload_authorized(signature) is True
        if (remote_state == "unverified" or (content_matches and remote_state == "unknown")) and not fresh:
            self.store.update_registry_state(signature, youtube_id, "needs_verification")
            self.store.upsert(signature, path, title, "verification_pending", youtube_id=youtube_id, error=match_reason)
            self.log(f"No se sube ni se borra {path.name}: {match_reason}.")
            self.events.put(("folder_refresh", False))
            return
        if remote_state == "processed" and content_matches:
            self.store.upsert(signature, path, title, "uploaded", youtube_id=youtube_id)
            self.store.remember_upload(signature, path, title, youtube_id=youtube_id, reason="youtube_title_exists")
            self.log(f"Omitido {path.name}: contenido confirmado en YouTube ({match_reason}).")
            self.events.put(("folder_refresh", False))
            return
        if remote_state == "processed" and not content_matches:
            self.log(f"El titulo {title} existe, pero no corresponde a {path.name}: {match_reason}. Se subira el archivo correcto.")
        if remote_state in {"uploaded", "processing"} and content_matches:
            self.store.upsert(signature, path, title, "processing", youtube_id=youtube_id)
            self.store.remember_upload(signature, path, title, youtube_id=youtube_id, reason="processing")
            self.log(f"YouTube aun esta procesando https://youtu.be/{youtube_id}; se conserva y se comprobara de nuevo. Puedes revisarlo en Canal.")
            self.events.put(("folder_refresh", False))
            return
        if self.requires_upload_review(path):
            return
        if file_signature(path) != signature:
            self.log(f"Se conserva {path.name}: el archivo ha cambiado antes de autorizar la transferencia.")
            self.events.put(("folder_refresh", False))
            return
        attempt_id = self.store.record_upload_attempt(signature, path, title)
        if not attempt_id:
            message = "Intento anterior sin confirmar. Revisa el canal y pulsa Reintentar; no se inicia otra subida automaticamente."
            self.store.upsert(signature, path, title, "error", error=message)
            self.problem(f"Se conserva {path.name}: {message}", path)
            self.events.put(("folder_refresh", False))
            return
        if remote_state in {"failed", "rejected", "terminated"} and youtube_id and content_matches:
            try:
                client.delete_video(youtube_id)
                self.log(f"Eliminado de YouTube el intento fallido {youtube_id}; se iniciara una subida limpia.")
            except Exception as exc:
                message = f"No se pudo retirar de YouTube el intento fallido: {describe_error(exc)}"
                self.store.upsert(signature, path, title, "error", youtube_id=youtube_id, error=message)
                self.store.finish_upload_attempt(attempt_id, "error", message)
                self.problem(message, path, error=exc, operation="Retirar intento fallido de YouTube")
                self.events.put(("folder_refresh", False))
                return
        self.store.upsert(signature, path, title, "uploading")
        self.events.put(("folder_refresh", False))
        self.log(f"Subiendo {path.name} como '{title}'.")
        limit_before_upload = self.store.get_upload_limit()
        try:
            if file_signature(path) != signature:
                raise UploadCancelled("El archivo ha cambiado antes de iniciar la transferencia.")
            video_id = client.upload(path, title, self.cancel_upload_event, self.progress)
            self.store.finish_upload_attempt(attempt_id, "received")
            self.store.upsert(signature, path, title, "processing", youtube_id=video_id)
            self.store.remember_upload(signature, path, title, youtube_id=video_id, reason="processing")
            quota_cleared = bool(limit_before_upload)
            if quota_cleared:
                self.store.clear_upload_limit()
            self.log(f"Archivo recibido por YouTube y pendiente de procesamiento: https://youtu.be/{video_id}")
            self.events.put(("upload_completed", {
                "path": str(path), "title": title, "youtube_id": video_id, "quota_cleared": quota_cleared,
            }))
            return

        except UploadCancelled as exc:
            message = str(exc) + " Se comprobara el canal antes de reintentar; no se borra ningun video automaticamente por esta cancelacion."
            self.store.upsert(signature, path, title, "cancelled", error=message)
            self.store.finish_upload_attempt(attempt_id, "cancelled", message)
            self.problem(message, path, operation="Cancelar transferencia")
            self.events.put(("folder_refresh", False))
            return
        except HttpError as exc:
            message = youtube_error_message(exc)
            self.store.finish_upload_attempt(attempt_id, "quota" if is_youtube_quota_error(exc) else "error", describe_error(exc))
            if is_youtube_quota_error(exc):
                message, _state = self.pause_for_youtube_limit(exc)
                if getattr(exc, "upload_session_started", None) is False:
                    self.store.authorize_upload_retry(signature, attempt_id)
            else:
                self.problem(f"Error de YouTube subiendo {path.name}: {message}", path, error=exc, operation="Transferir video a YouTube")
            self.store.upsert(signature, path, title, "waiting_quota" if is_youtube_quota_error(exc) else "error", error=message)
            self.events.put(("folder_refresh", False))
            return
        except Exception as upload_error:
            self.store.finish_upload_attempt(attempt_id, "quota" if is_youtube_quota_error(upload_error) else "error", describe_error(upload_error))
            if is_youtube_quota_error(upload_error):
                message, _state = self.pause_for_youtube_limit(upload_error)
                if getattr(upload_error, "upload_session_started", None) is False:
                    self.store.authorize_upload_retry(signature, attempt_id)
                self.store.upsert(signature, path, title, "waiting_quota", error=message)
                self.events.put(("folder_refresh", False))
                return
            try:
                self.store.upsert(signature, path, title, "error", error=describe_error(upload_error))
            except OSError as store_error:
                self.log(f"No se pudo guardar el error de {path}: {describe_error(store_error)}")
            self.problem(f"Error subiendo {path.name}: {describe_error(upload_error)}", path, error=upload_error, operation="Transferir video a YouTube")
            self.events.put(("folder_refresh", False))
            return
