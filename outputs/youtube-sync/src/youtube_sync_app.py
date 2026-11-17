import hashlib
import json
import os
import queue
import re
import shutil
import sqlite3
import sys
import threading
import time
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable, Iterable

import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
except Exception:
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception
    MediaFileUpload = None

try:
    from PIL import Image, ImageTk
    import pystray
except Exception:
    Image = None
    ImageTk = None
    pystray = None


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


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def set_window_icon(window: tk.Tk | tk.Toplevel) -> None:
    icon = resource_path("assets/youtube-sync.ico")
    if icon.exists():
        try:
            window.iconbitmap(str(icon))
        except (AttributeError, tk.TclError):
            pass


class RoundedButton(tk.Canvas):
    STYLE_COLORS = {
        "Success.TButton": ("#2ba640", "#35bc4d", "#1f7f30"),
        "Danger.TButton": ("#c91f37", "#e32a45", "#94152a"),
        "Warning.TButton": ("#b7791f", "#d5962c", "#875815"),
        "Soft.TButton": ("#272727", "#3a3a3a", "#171717"),
        "Accent.TButton": ("#ff0033", "#ff3157", "#bd0026"),
        "HeaderAccentIcon.TButton": ("#ff0033", "#ff3157", "#bd0026"),
        "HeaderIcon.TButton": ("#272727", "#3a3a3a", "#171717"),
    }

    def __init__(self, parent, text: str, command: Callable[[], None], style: str, width: int, height: int = 40) -> None:
        try:
            parent_bg = parent.cget("background")
        except tk.TclError:
            parent_bg = "#0f0f0f"
        super().__init__(parent, width=width, height=height, bg=parent_bg, highlightthickness=0, cursor="hand2")
        self.button_text = text
        self.command = command
        self.style_name = style
        self.button_state = "normal"
        self.hovered = False
        self.pressed = False
        self.bind("<Enter>", lambda _event: self.set_hover(True))
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.draw_button()

    def rounded_rectangle(self, x1: int, y1: int, x2: int, y2: int, radius: int, color: str) -> None:
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=color, outline=color)
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=color, outline=color)
        self.create_oval(x1, y1, x1 + radius * 2, y1 + radius * 2, fill=color, outline=color)
        self.create_oval(x2 - radius * 2, y1, x2, y1 + radius * 2, fill=color, outline=color)
        self.create_oval(x1, y2 - radius * 2, x1 + radius * 2, y2, fill=color, outline=color)
        self.create_oval(x2 - radius * 2, y2 - radius * 2, x2, y2, fill=color, outline=color)

    def draw_button(self) -> None:
        self.delete("all")
        normal, hover, pressed = self.STYLE_COLORS.get(self.style_name, self.STYLE_COLORS["HeaderIcon.TButton"])
        color = "#202020" if self.button_state == "disabled" else (pressed if self.pressed else hover if self.hovered else normal)
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        inset = 2 if self.pressed else 1
        self.rounded_rectangle(inset, inset, width - inset, height - inset, 8, color)
        font_size = 13 if len(self.button_text) <= 2 else 10
        foreground = "#666666" if self.button_state == "disabled" else "#ffffff"
        offset = 1 if self.pressed else 0
        self.create_text(width // 2, height // 2 + offset, text=self.button_text, fill=foreground, font=("Segoe UI", font_size, "bold"))

    def invoke(self, _event=None) -> None:
        if self.button_state != "disabled":
            self.command()

    def on_press(self, _event=None) -> None:
        if self.button_state == "disabled":
            return
        self.pressed = True
        self.draw_button()
        self.update_idletasks()

    def on_release(self, event=None) -> None:
        if self.button_state == "disabled" or not self.pressed:
            return
        inside = event is None or (0 <= event.x < int(self.cget("width")) and 0 <= event.y < int(self.cget("height")))
        if inside:
            self.after(120, self.release_visual)
            self.after(20, self.invoke)
        else:
            self.release_visual()

    def release_visual(self) -> None:
        self.pressed = False
        self.draw_button()

    def on_leave(self, _event=None) -> None:
        self.hovered = False
        if self.pressed:
            self.pressed = False
        self.draw_button()

    def set_hover(self, hovered: bool) -> None:
        self.hovered = hovered and self.button_state != "disabled"
        self.draw_button()

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "text" in kwargs:
            self.button_text = kwargs.pop("text")
        if "style" in kwargs:
            self.style_name = kwargs.pop("style")
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "state" in kwargs:
            self.button_state = kwargs.pop("state")
            self.pressed = False
            super().configure(cursor="arrow" if self.button_state == "disabled" else "hand2")
        result = super().configure(**kwargs) if kwargs else None
        self.draw_button()
        return result

    config = configure


class ToolTip:
    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window = None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _event=None) -> None:
        if self.window:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 6}")
        tk.Label(self.window, text=self.text, bg="#272727", fg="#ffffff", padx=9, pady=5, font=("Segoe UI", 9)).pack()

    def hide(self, _event=None) -> None:
        if self.window:
            self.window.destroy()
            self.window = None


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
    text = str(exc).lower()
    return (
        "quota exceeded" in text
        or "quotaexceeded" in text
        or "videouploads" in text
        or "video uploads per day" in text
        or "ratelimitexceeded" in text
        or "uploadlimitexceeded" in text
        or "exceeded the number of videos" in text
    )


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
        return (
            "Cuota diaria de YouTube Data API agotada para este proyecto de Google. "
            "No es un fallo del video: YouTube no aceptara nuevas peticiones hasta que se renueve la cuota "
            "o aumentes el limite del proyecto."
        )
    return describe_error(exc)


def youtube_retry_prediction(exc: Exception) -> tuple[str, datetime, str]:
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

    if "ratelimitexceeded" in str(exc).lower():
        return "api", now + timedelta(hours=1), "estimacion de 1 h para limite temporal"

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


_fingerprint_cache: dict[tuple[str, int, int], str] = {}


def file_content_fingerprint(path: Path) -> str:
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
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
    value = digest.hexdigest()
    if len(_fingerprint_cache) >= 1000:
        _fingerprint_cache.clear()
    _fingerprint_cache[key] = value
    return value


def human_size(bytes_count: int) -> str:
    size = float(bytes_count)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{bytes_count} B"


def ask_confirmation(
    title: str,
    action: str,
    will_do: list[str],
    will_not_do: list[str] | None = None,
    warning: str = "",
    question: str = "¿Quieres continuar?",
) -> bool:
    lines = [action, "", "Se realizará:"]
    lines.extend(f"• {item}" for item in will_do)
    if will_not_do:
        lines.extend(["", "No se modificará:"])
        lines.extend(f"• {item}" for item in will_not_do)
    if warning:
        lines.extend(["", f"Importante: {warning}"])
    lines.extend(["", question])
    return messagebox.askyesno(title, "\n".join(lines), icon="warning" if warning else "question")


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
        path.write_text(f'@echo off\nstart "" "{exe}"\n', encoding="utf-8")
    elif path.exists():
        path.unlink()


@dataclass
class Config:
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

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as db:
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
        cleaned = {key: value for key, value in data.items() if key in defaults}
        config = Config(**{**defaults, **cleaned})
        profile_version = int(data.get("timing_profile_version", 0) or 0)
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
        self.config_path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")

    def has_success(self, signature: str) -> bool:
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT 1 FROM upload_registry WHERE signature = ?",
                (signature,),
            ).fetchone()
            return row is not None

    def remember_upload(self, signature: str, path: Path, title: str, youtube_id: str = "", reason: str = "uploaded") -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        with sqlite3.connect(self.db_path) as db:
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

    def update_registry_youtube_id(self, signature: str, youtube_id: str) -> None:
        if not youtube_id:
            return
        stamp = datetime.now().isoformat(timespec="seconds")
        with sqlite3.connect(self.db_path) as db:
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
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE upload_registry SET youtube_id = ?, reason = ?, updated_at = ? WHERE signature = ?",
                (youtube_id, reason, stamp, signature),
            )
            db.execute(
                "UPDATE uploads SET youtube_id = ?, status = ?, updated_at = ?, error = '' WHERE signature = ?",
                (youtube_id, reason, stamp, signature),
            )

    def forget_registry(self, signature: str) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM upload_registry WHERE signature = ?", (signature,))

    def clear_upload_incident(self, signature: str) -> None:
        """Clear a transient upload state without touching the duplicate registry."""
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM uploads WHERE signature = ?", (signature,))

    def upload_status(self, signature: str) -> str:
        with sqlite3.connect(self.db_path) as db:
            row = db.execute("SELECT status FROM uploads WHERE signature = ?", (signature,)).fetchone()
        return str(row[0]) if row else ""

    def upload_identity(self, signature: str) -> tuple[str, str]:
        with sqlite3.connect(self.db_path) as db:
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

    def record_upload_attempt(self, signature: str, path: Path, title: str) -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO upload_attempts(signature, title, path, created_at) VALUES(?,?,?,?)",
                (signature, title, str(path), stamp),
            )

    def daily_upload_attempt_count(self, day: datetime | None = None) -> int:
        selected = day or datetime.now()
        start = selected.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        with sqlite3.connect(self.db_path) as db:
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
        with sqlite3.connect(self.db_path) as db:
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
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT kind, detected_at, retry_at, source, message FROM upload_limit_state WHERE id = 1"
            ).fetchone()
        if not row:
            return None
        return {"kind": row[0], "detected_at": row[1], "retry_at": row[2], "source": row[3], "message": row[4]}

    def clear_upload_limit(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM upload_limit_state WHERE id = 1")

    def upsert(self, signature: str, path: Path, title: str, status: str, youtube_id: str = "", error: str = "") -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        size = path.stat().st_size if path.exists() else 0
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                INSERT INTO uploads(signature, path, title, youtube_id, status, size, created_at, updated_at, error)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(signature) DO UPDATE SET
                    path=excluded.path,
                    title=excluded.title,
                    youtube_id=excluded.youtube_id,
                    status=excluded.status,
                    size=excluded.size,
                    updated_at=excluded.updated_at,
                    error=excluded.error
                """,
                (signature, str(path), title, youtube_id, status, size, stamp, stamp, error),
            )

    def mark_local_deleted(self, signature: str) -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE uploads SET status = 'local_deleted', updated_at = ?, error = '' WHERE signature = ?",
                (stamp, signature),
            )
            db.execute("UPDATE upload_registry SET reason = 'local_deleted', updated_at = ? WHERE signature = ?", (stamp, signature))

    def registry_index(self) -> tuple[dict[str, tuple], dict[str, tuple]]:
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                "SELECT signature, title, path, youtube_id, reason, updated_at FROM upload_registry"
            ).fetchall()
        by_signature = {row[0]: row for row in rows}
        by_path = {str(Path(row[2])): row for row in rows}
        return by_signature, by_path

    def upload_status_index(self) -> tuple[dict[str, tuple], dict[str, tuple]]:
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                "SELECT signature, title, path, status, error, updated_at FROM uploads ORDER BY updated_at DESC"
            ).fetchall()
        by_signature = {row[0]: row for row in rows}
        by_path = {str(Path(row[2])): row for row in rows}
        return by_signature, by_path

    def uploaded_before(self, older_than: datetime, limit: int = 500) -> list[tuple]:
        with sqlite3.connect(self.db_path) as db:
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


class YouTubeClient:
    def __init__(self, store: Store, config: Config, log: Callable[[str], None], client_secret_path: str = "", label: str = "principal") -> None:
        self.store = store
        self.config = config
        self.log = log
        self.client_secret_path = client_secret_path or config.client_secret_path
        self.label = label
        self.token_path = store.token_path_for(self.client_secret_path)
        self._service = None
        self._known_titles: set[str] | None = None
        self._known_video_ids: set[str] | None = None
        self._known_title_ids: dict[str, str] | None = None
        self._known_all_title_ids: dict[str, str] | None = None
        self._known_title_candidates: dict[str, list[str]] | None = None
        self._known_video_states: dict[str, str] | None = None
        self._known_video_metadata: dict[str, dict] | None = None

    def available(self) -> bool:
        return all([Request, Credentials, InstalledAppFlow, build, MediaFileUpload])

    def service(self):
        if not self.available():
            raise RuntimeError("Faltan dependencias. Instala requirements.txt antes de ejecutar la app.")
        if self._service:
            return self._service

        creds = None
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception:
                creds = None
        missing_scopes = bool(creds and hasattr(creds, "has_scopes") and not creds.has_scopes(SCOPES))
        if missing_scopes:
            self.log("Los permisos de YouTube cambiaron. Se pedira autorizacion de nuevo.")
            creds = None
            try:
                self.token_path.unlink(missing_ok=True)
            except OSError:
                pass
        if not creds or not creds.valid or missing_scopes:
            if creds and creds.expired and creds.refresh_token and not missing_scopes:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            else:
                creds = None
            if not creds:
                if not self.client_secret_path or not Path(self.client_secret_path).exists():
                    raise RuntimeError("Selecciona el archivo client_secret.json en Configuracion.")
                self.log(f"Autorizando credencial OAuth {self.label}.")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0, prompt="consent")
            self.token_path.write_text(creds.to_json(), encoding="utf-8")

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def channel_info(self) -> dict:
        response = self.service().channels().list(part="snippet,contentDetails", mine=True).execute()
        items = response.get("items", [])
        if not items:
            raise RuntimeError("La cuenta conectada no devuelve ningun canal de YouTube.")
        item = items[0]
        snippet = item.get("snippet", {})
        uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
        return {
            "title": snippet.get("title", "Canal sin nombre"),
            "id": item.get("id", ""),
            "uploads": uploads,
            "description": snippet.get("description", ""),
        }

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

    def remove_incomplete_upload(self, path: Path, title: str) -> tuple[bool, str]:
        self.uploaded_video_index(force=True)
        matches, video_id, _reason, state = self.verify_local_file(path, title)
        if not matches or not video_id or state not in {"uploaded", "processing"}:
            return False, ""
        try:
            self.delete_video(video_id)
        except HttpError as exc:
            if getattr(exc.resp, "status", 0) != 404:
                raise
        self._known_titles = None
        self._known_video_ids = None
        self._known_title_ids = None
        self._known_all_title_ids = None
        self._known_title_candidates = None
        self._known_video_states = None
        self._known_video_metadata = None
        return True, video_id

    def uploaded_titles(self, force: bool = False) -> set[str]:
        titles, _video_ids = self.uploaded_video_index(force=force)
        return titles

    def uploaded_video_index(self, force: bool = False) -> tuple[set[str], set[str]]:
        if self._known_titles is not None and self._known_video_ids is not None and not force:
            return self._known_titles, self._known_video_ids

        service = self.service()
        title_candidates: dict[str, list[str]] = {}
        info = self.channel_info()
        uploads = info["uploads"]
        page_token = None
        while True:
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
        all_video_ids = list(dict.fromkeys(video_id for values in title_candidates.values() for video_id in values))
        for offset in range(0, len(all_video_ids), 50):
            batch = all_video_ids[offset : offset + 50]
            response = service.videos().list(
                part="snippet,status,processingDetails,fileDetails,contentDetails",
                id=",".join(batch),
                maxResults=50,
            ).execute()
            for item in response.get("items", []):
                video_id = item.get("id", "")
                upload_status = item.get("status", {}).get("uploadStatus", "")
                processing_status = item.get("processingDetails", {}).get("processingStatus", "")
                state = upload_status or processing_status or "unknown"
                if upload_status == "uploaded" and processing_status:
                    state = processing_status
                if video_id:
                    video_states[video_id] = state
                    snippet = item.get("snippet", {})
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
        all_title_ids = {title: candidates[0] for title, candidates in title_candidates.items() if candidates}
        titles = set(title_ids)
        video_ids = set(ready_ids)
        self._known_titles = titles
        self._known_video_ids = video_ids
        self._known_title_ids = title_ids
        self._known_all_title_ids = all_title_ids
        self._known_title_candidates = title_candidates
        self._known_video_states = video_states
        self._known_video_metadata = video_metadata
        processing = sum(1 for state in video_states.values() if state in {"uploaded", "processing"})
        self.log(f"Comprobados {len(titles)} videos procesados en YouTube" + (f" y {processing} procesando." if processing else "."))
        return titles, video_ids

    def uploaded_title_ids(self, force: bool = False) -> dict[str, str]:
        if self._known_title_ids is None or force:
            self.uploaded_video_index(force=force)
        return self._known_title_ids or {}

    def resolve_video_state(self, title: str, youtube_id: str = "") -> tuple[str, str]:
        if self._known_video_states is None or self._known_all_title_ids is None:
            self.uploaded_video_index()
        resolved_id = youtube_id if youtube_id in (self._known_video_states or {}) else (self._known_all_title_ids or {}).get(title, "")
        return resolved_id, (self._known_video_states or {}).get(resolved_id, "missing")

    def verify_local_file(self, path: Path, title: str, youtube_id: str = "") -> tuple[bool, str, str, str]:
        self.uploaded_video_index()
        candidates = []
        if youtube_id and youtube_id in (self._known_video_states or {}):
            candidates.append(youtube_id)
        candidates.extend(
            video_id for video_id in (self._known_title_candidates or {}).get(title, []) if video_id not in candidates
        )
        if not candidates:
            return False, "", "el video no aparece en el canal", "missing"
        local_size = path.stat().st_size
        local_name = path.name.casefold()
        local_fingerprint = ""
        mismatch_reasons = []
        for candidate in candidates:
            state = (self._known_video_states or {}).get(candidate, "missing")
            metadata = (self._known_video_metadata or {}).get(candidate, {})
            marker = metadata.get("fingerprint", "")
            if marker:
                if not local_fingerprint:
                    local_fingerprint = file_content_fingerprint(path)
                if marker == local_fingerprint:
                    return True, candidate, "huella de contenido confirmada", state
                mismatch_reasons.append(f"{candidate}: la huella de contenido no coincide")
                continue
            remote_size = int(metadata.get("size", 0) or 0)
            remote_name = str(metadata.get("filename", "")).casefold()
            if remote_size and remote_name and remote_size == local_size and remote_name == local_name:
                return True, candidate, "nombre original y tamaño confirmados", state
            reasons = []
            if remote_size and remote_size != local_size:
                reasons.append("tamaño distinto")
            if remote_name and remote_name != local_name:
                reasons.append("nombre original distinto")
            if not remote_size or not remote_name:
                reasons.append("faltan metadatos para confirmar el contenido")
            mismatch_reasons.append(f"{candidate}: {', '.join(reasons)}")
        first = candidates[0]
        state = (self._known_video_states or {}).get(first, "missing")
        return False, first, "; ".join(mismatch_reasons[:3]), state

    def verify_video_on_channel(self, title: str, youtube_id: str = "") -> tuple[bool, str, str]:
        self.uploaded_video_index()
        resolved_id, state = self.resolve_video_state(title, youtube_id)
        if state == "processed":
            return True, resolved_id, "procesado y confirmado en el canal"
        if state in {"uploaded", "processing"}:
            return False, resolved_id, "el video sigue procesandose en YouTube"
        if resolved_id:
            return False, resolved_id, f"YouTube indica estado {state}"
        return False, "", "el video no aparece en el canal"

    def upload(self, path: Path, title: str, cancel_event: threading.Event, progress: Callable[[int, str], None]) -> str:
        fingerprint = file_content_fingerprint(path)
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
        request = self.service().videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        progress(0, path.name)
        while response is None:
            if cancel_event.is_set():
                raise UploadCancelled("Subida cancelada por el usuario.")
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                progress(percent, path.name)
                self.log(f"Subiendo {path.name}: {percent}%")
        video_id = response["id"]
        progress(100, path.name)
        if self._known_all_title_ids is not None:
            self._known_all_title_ids[title] = video_id
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
        self.manual_uploads: queue.Queue[Path] = queue.Queue()
        self.last_cleanup_warning_key = ""

    def log(self, text: str) -> None:
        self.events.put(("log", f"[{now_text()}] {text}"))

    def progress(self, percent: int, filename: str) -> None:
        self.events.put(("progress", {"percent": percent, "filename": filename}))

    def pause_for_youtube_limit(self, exc: Exception) -> tuple[str, dict]:
        message = youtube_error_message(exc)
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
        return YouTubeClient(self.store, config, self.log, path)

    def refresh(self) -> None:
        self.wake_event.set()

    def upload_path(self, path: Path) -> None:
        self.manual_uploads.put(path)
        self.wake_event.set()

    def set_enabled(self, enabled: bool) -> None:
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
                self.scan_once(manual_path)
                if self.enabled_event.is_set():
                    self.auto_cleanup_once()
            except Exception as exc:
                self.log(f"Error: {describe_error(exc)}")
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
            self.log("Configura una carpeta valida para empezar.")
            return

        self.events.put(("busy", True))
        self.cancel_upload_event.clear()
        client = self.available_client(config)
        if not client:
            self.log("No hay credenciales OAuth disponibles. Configura el JSON OAuth.")
            return
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

        self.log(f"Encontrados {len(pending)} video(s) candidato(s).")
        try:
            client.uploaded_titles()
        except HttpError as exc:
            if is_youtube_quota_error(exc):
                self.pause_for_youtube_limit(exc)
            else:
                self.log(f"No se pudo comprobar YouTube antes de subir: {youtube_error_message(exc)}")
            return
        except Exception as exc:
            self.log(f"No se pudo comprobar YouTube antes de subir: {describe_error(exc)}")
            return
        for path in pending:
            if self.stop_event.is_set() or self.cancel_upload_event.is_set():
                return
            self.handle_file(path, client)

    def auto_cleanup_once(self) -> None:
        config = self.get_config()
        if not config.auto_delete_uploaded:
            return
        older_than = datetime.now() - config.auto_delete_delay
        rows = self.store.uploaded_before(older_than)
        if not rows:
            return
        try:
            verifier = YouTubeClient(self.store, config, self.log)
            verifier.uploaded_video_index(force=True)
        except Exception as exc:
            self.log(f"Limpieza automatica cancelada: no se pudo comprobar YouTube ({exc}).")
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
        try:
            iterator = folder.glob(pattern)
            for path in iterator:
                try:
                    if not path.is_file() or path.suffix.lower() not in extensions:
                        continue
                    signature = file_signature(path)
                    if not self.store.has_success(signature) and self.is_stable(path, config.stable_wait_seconds):
                        yield path
                except OSError as exc:
                    self.log(f"No puedo leer {path}: {describe_error(exc)}")
        except OSError as exc:
            self.log(f"No se pudo revisar la carpeta {folder}: {describe_error(exc)}")

    def is_stable(self, path: Path, wait_seconds: int) -> bool:
        stat = path.stat()
        age_seconds = time.time() - stat.st_mtime
        return age_seconds >= max(1, int(wait_seconds))

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
        previous_status = self.store.upload_status(signature)
        content_matches, youtube_id, match_reason, remote_state = client.verify_local_file(path, title)
        if remote_state == "processed" and content_matches:
            self.store.upsert(signature, path, title, "skipped", youtube_id=youtube_id, error="Ya existe en YouTube un video con ese titulo.")
            self.store.remember_upload(signature, path, title, youtube_id=youtube_id, reason="youtube_title_exists")
            self.log(f"Omitido {path.name}: contenido confirmado en YouTube ({match_reason}).")
            self.events.put(("folder_refresh", False))
            return
        if remote_state == "processed" and not content_matches:
            self.log(f"El titulo {title} existe, pero no corresponde a {path.name}: {match_reason}. Se subira el archivo correcto.")
        if remote_state in {"uploaded", "processing"} and content_matches:
            if previous_status in {"cancelled", "error", "uploading"}:
                try:
                    client.delete_video(youtube_id)
                    self.log(f"Eliminado de YouTube el intento incompleto {youtube_id} antes de reintentar.")
                    youtube_id, remote_state = "", "missing"
                except Exception as exc:
                    message = f"No se pudo retirar la subida incompleta de YouTube: {describe_error(exc)}"
                    self.store.upsert(signature, path, title, "error", youtube_id=youtube_id, error=message)
                    self.log(message)
                    self.events.put(("folder_refresh", False))
                    return
            else:
                self.store.upsert(signature, path, title, "processing", youtube_id=youtube_id)
                self.store.remember_upload(signature, path, title, youtube_id=youtube_id, reason="processing")
                self.log(f"Recuperada una subida que YouTube todavia esta procesando: https://youtu.be/{youtube_id}")
                self.events.put(("folder_refresh", False))
                return
        if remote_state in {"failed", "rejected", "terminated"} and youtube_id and content_matches:
            try:
                client.delete_video(youtube_id)
                self.log(f"Eliminado de YouTube el intento fallido {youtube_id}; se iniciara una subida limpia.")
            except Exception as exc:
                message = f"No se pudo retirar de YouTube el intento fallido: {describe_error(exc)}"
                self.store.upsert(signature, path, title, "error", youtube_id=youtube_id, error=message)
                self.log(message)
                self.events.put(("folder_refresh", False))
                return
        self.store.upsert(signature, path, title, "uploading")
        self.events.put(("folder_refresh", False))
        self.log(f"Subiendo {path.name} como '{title}'.")
        limit_before_upload = self.store.get_upload_limit()
        try:
            self.store.record_upload_attempt(signature, path, title)
            video_id = client.upload(path, title, self.cancel_upload_event, self.progress)
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
            message = str(exc)
            try:
                removed, incomplete_id = client.remove_incomplete_upload(path, title)
                if removed:
                    message += f" Se elimino de YouTube el intento incompleto {incomplete_id}."
            except Exception as cleanup_error:
                message += f" La limpieza remota queda pendiente: {describe_error(cleanup_error)}"
            self.store.upsert(signature, path, title, "cancelled", error=message)
            self.log(message)
            self.events.put(("folder_refresh", False))
            return
        except HttpError as exc:
            message = youtube_error_message(exc)
            if is_youtube_quota_error(exc):
                message, _state = self.pause_for_youtube_limit(exc)
            else:
                self.log(f"Error de YouTube subiendo {path.name}: {message}")
            self.store.upsert(signature, path, title, "error", error=message)
            self.events.put(("folder_refresh", False))
            return
        except Exception as upload_error:
            try:
                self.store.upsert(signature, path, title, "error", error=describe_error(upload_error))
            except OSError as store_error:
                self.log(f"No se pudo guardar el error de {path}: {describe_error(store_error)}")
            self.log(f"Error subiendo {path.name}: {describe_error(upload_error)}")
            self.events.put(("folder_refresh", False))
            return


class OAuthGuideDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, on_json_selected: Callable[[str], None] | None = None) -> None:
        super().__init__(parent)
        self.on_json_selected = on_json_selected
        self.step = 0
        self.steps = [
            {
                "title": "Paso 1 de 4 - Crea un proyecto en Google",
                "body": (
                    "Necesitamos acceso a la API de YouTube. Google lo gestiona mediante un proyecto en su consola de desarrolladores.\n\n"
                    "1. Haz clic en el boton de abajo para abrir Google Cloud Console.\n"
                    "2. Inicia sesion con la cuenta de Google de tu canal de YouTube.\n"
                    "3. Haz clic en 'Seleccionar proyecto' y luego en 'Nuevo proyecto'.\n"
                    "4. Ponle cualquier nombre, por ejemplo 'MiYouTubeSync', y haz clic en 'Crear'.\n\n"
                    "Cuando hayas creado el proyecto, pulsa Siguiente."
                ),
                "button": "Abrir Google Cloud Console ->",
                "url": "https://console.cloud.google.com/",
            },
            {
                "title": "Paso 2 de 4 - Activa la API de YouTube",
                "body": (
                    "Ahora hay que activar la API de YouTube para tu proyecto.\n\n"
                    "1. Haz clic abajo para ir directamente a la pagina de la API.\n"
                    "2. Asegurate de que tu proyecto recien creado esta seleccionado arriba.\n"
                    "3. Haz clic en el boton azul 'Habilitar'.\n\n"
                    "Cuando lo hayas activado, pulsa Siguiente."
                ),
                "button": "Activar YouTube Data API v3 ->",
                "url": "https://console.cloud.google.com/apis/library/youtube.googleapis.com",
            },
            {
                "title": "Paso 3 de 4 - Crea las credenciales",
                "body": (
                    "Ahora crearemos las credenciales para que la app pueda subir videos.\n\n"
                    "1. Haz clic abajo para ir a 'Crear credenciales'.\n"
                    "2. Elige 'ID de cliente de OAuth'.\n"
                    "3. Si te pide configurar la pantalla de consentimiento, haz clic en ese boton:\n"
                    "   - Tipo de usuario: Externo -> Crear.\n"
                    "   - Nombre de la app: el que quieras -> Guarda y continua.\n"
                    "   - En 'Usuarios de prueba', anade tu email de Google -> Guarda.\n"
                    "4. Vuelve a Credenciales -> Crear credenciales -> ID de cliente OAuth.\n"
                    "5. Tipo de aplicacion: Aplicacion de escritorio.\n"
                    "6. Descarga el archivo JSON."
                ),
                "button": "Ir a Crear Credenciales ->",
                "url": "https://console.cloud.google.com/apis/credentials",
            },
            {
                "title": "Paso 4 de 4 - Selecciona el archivo descargado",
                "body": (
                    "Ya tienes el archivo JSON con tus credenciales.\n\n"
                    "Haz clic en el boton de abajo para seleccionarlo. Lo copiaremos automaticamente a la carpeta de la app.\n\n"
                    "Despues de seleccionarlo, la app estara lista para usarse. La primera vez que pulses 'Autenticar' o compruebes YouTube, "
                    "se abrira el navegador para que des permiso a la app. Es normal y solo ocurre una vez."
                ),
                "button": "Seleccionar archivo JSON ->",
                "url": "",
            },
        ]

        self.title("Configuracion inicial - YouTubeSync")
        self.configure(bg="#181818")
        self.geometry("620x520")
        self.minsize(560, 500)
        set_window_icon(self)
        self.transient(parent)
        self.grab_set()

        self.header = tk.Frame(self, bg="#ff0033", height=58)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        tk.Label(self.header, text="Asistente de configuracion", bg="#ff0033", fg="#ffffff", font=("Segoe UI", 14, "bold")).pack(expand=True)

        self.body = tk.Frame(self, bg="#181818", padx=22, pady=16)
        self.body.pack(fill="both", expand=True)
        self.step_label = tk.Label(self.body, bg="#181818", fg="#cbd5e1", font=("Segoe UI", 10))
        self.step_label.pack(pady=(0, 12))
        self.dots = tk.Canvas(self.body, width=90, height=16, bg="#181818", highlightthickness=0)
        self.dots.pack(pady=(0, 18))

        self.panel = tk.Frame(self.body, bg="#222222", padx=14, pady=14)
        self.panel.pack(fill="both", expand=True)
        self.title_label = tk.Label(self.panel, bg="#222222", fg="#ffffff", font=("Segoe UI", 11, "bold"), wraplength=520, justify="center")
        self.title_label.pack(anchor="center", pady=(0, 16))
        self.body_label = tk.Label(self.panel, bg="#222222", fg="#ffffff", font=("Segoe UI", 9), wraplength=520, justify="left")
        self.body_label.pack(anchor="w", fill="both", expand=True)

        self.main_button = RoundedButton(self.body, "", self.perform_step_action, "Accent.TButton", width=250, height=42)
        self.main_button.pack(pady=(14, 12))

        nav = tk.Frame(self.body, bg="#181818")
        nav.pack()
        self.prev_button = RoundedButton(nav, "← Anterior", self.previous_step, "Soft.TButton", width=110, height=38)
        self.prev_button.pack(side="left", padx=6)
        self.next_button = RoundedButton(nav, "Siguiente →", self.next_step, "Soft.TButton", width=110, height=38)
        self.next_button.pack(side="left", padx=6)
        RoundedButton(nav, "Omitir", self.destroy, "Soft.TButton", width=90, height=38).pack(side="left", padx=6)

        self.render_step()

    def render_step(self) -> None:
        data = self.steps[self.step]
        self.step_label.configure(text=f"Paso {self.step + 1} de {len(self.steps)}")
        self.title_label.configure(text=data["title"])
        self.body_label.configure(text=data["body"])
        self.main_button.configure(text=data["button"])
        self.prev_button.configure(state="normal" if self.step else "disabled")
        self.next_button.configure(text="Finalizar" if self.step == len(self.steps) - 1 else "Siguiente →")
        self.dots.delete("all")
        for index in range(len(self.steps)):
            color = "#ef4444" if index == self.step else "#4b5563"
            self.dots.create_oval(10 + index * 20, 5, 16 + index * 20, 11, fill=color, outline="")

    def previous_step(self) -> None:
        if self.step > 0:
            self.step -= 1
            self.render_step()

    def next_step(self) -> None:
        if self.step < len(self.steps) - 1:
            self.step += 1
            self.render_step()
        else:
            self.destroy()

    def perform_step_action(self) -> None:
        data = self.steps[self.step]
        if data["url"]:
            webbrowser.open(data["url"])
            return
        self.select_json()

    def select_json(self) -> None:
        value = filedialog.askopenfilename(title="Selecciona client_secret.json", filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if not value:
            return
        source = Path(value)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not ("installed" in data or "web" in data):
                raise ValueError("El JSON no parece ser un archivo OAuth de Google.")
            target = app_dir() / "client_secret.json"
            shutil.copy2(source, target)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"No se pudo usar ese JSON:\n{describe_error(exc)}")
            return
        if self.on_json_selected:
            self.on_json_selected(str(target))
        messagebox.showinfo(APP_NAME, "JSON guardado y seleccionado correctamente.")
        self.destroy()


class ConfigDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, config: Config, first_run: bool = False) -> None:
        super().__init__(parent)
        self.title("Asistente de configuracion" if first_run else "Configuracion")
        self.configure(bg="#0f0f0f")
        self.geometry("900x720")
        self.minsize(820, 620)
        set_window_icon(self)
        self.result: Config | None = None
        self.playlists_by_label = {config.playlist_name or "Ninguna": config.playlist_id}
        category_name = CATEGORY_NAMES_BY_ID.get(config.category_id, "Gente y blogs")
        self.vars = {
            "watch_folder": tk.StringVar(value=config.watch_folder),
            "client_secret_path": tk.StringVar(value=config.client_secret_path),
            "privacy_status": tk.StringVar(value=PRIVACY_LABELS.get(config.privacy_status, "Privado")),
            "category_name": tk.StringVar(value=category_name),
            "playlist_label": tk.StringVar(value=config.playlist_name or "Ninguna"),
            "recursive": tk.BooleanVar(value=config.recursive),
            "scan_interval_seconds": tk.IntVar(value=config.scan_interval_seconds),
            "stable_wait_seconds": tk.IntVar(value=config.stable_wait_seconds),
            "extensions": tk.StringVar(value=config.extensions),
            "start_minimized": tk.BooleanVar(value=config.start_minimized),
            "run_at_startup": tk.BooleanVar(value=config.run_at_startup),
            "auto_start_enabled": tk.StringVar(value="Auto ON" if config.auto_start_enabled else "Auto OFF"),
            "auto_delete_uploaded": tk.BooleanVar(value=config.auto_delete_uploaded),
            "auto_delete_after_hours": tk.IntVar(value=config.auto_delete_after_hours),
            "auto_delete_after_unit": tk.StringVar(value=config.auto_delete_after_unit),
        }
        self.build(first_run)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def build(self, first_run: bool) -> None:
        header = ttk.Frame(self, padding=(20, 14), style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Primer arranque" if first_run else "Ajustes", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="Configura carpeta, YouTube y automatizacion", style="Header.TLabel").pack(side="left", padx=(24, 0))

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        canvas = tk.Canvas(body, bg="#0f0f0f", highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas)
        content.columnconfigure(0, weight=1)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        self.folder_section(content).grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.youtube_section(content).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.automation_section(content).grid(row=2, column=0, sticky="ew")

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(18, 0))
        RoundedButton(buttons, "Asistente JSON", self.open_oauth_wizard, "Soft.TButton", width=130, height=38).pack(side="left")
        RoundedButton(buttons, "Guardar", self.save, "Accent.TButton", width=92, height=38).pack(side="right")
        RoundedButton(buttons, "Cancelar", self.cancel, "Soft.TButton", width=92, height=38).pack(side="right", padx=(0, 8))

    def section(self, parent: ttk.Frame, title: str) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=(10, 10), style="Panel.TFrame")
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=title, style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        return frame

    def folder_section(self, parent: ttk.Frame) -> ttk.Frame:
        frame = self.section(parent, "Carpeta")
        self.path_row(frame, 1, "Videos", "watch_folder", self.pick_folder)
        self.field_row(frame, 2, "Extensiones", ttk.Entry(frame, textvariable=self.vars["extensions"]))
        ttk.Checkbutton(frame, text="Incluir subcarpetas", variable=self.vars["recursive"]).grid(row=3, column=1, sticky="w", pady=(8, 0))
        return frame

    def youtube_section(self, parent: ttk.Frame) -> ttk.Frame:
        frame = self.section(parent, "YouTube")
        self.path_row(frame, 1, "JSON OAuth", "client_secret_path", self.pick_json)
        RoundedButton(frame, "Asistente", self.open_oauth_wizard, "Soft.TButton", width=92, height=34).grid(row=1, column=3, padx=(8, 0))
        self.field_row(frame, 2, "Privacidad", ttk.Combobox(
            frame, textvariable=self.vars["privacy_status"], values=list(PRIVACY_VALUES), state="readonly"
        ))
        self.field_row(frame, 3, "Categoria", ttk.Combobox(frame, textvariable=self.vars["category_name"], values=list(CATEGORIES.keys()), state="readonly"))
        self.playlist_combo = ttk.Combobox(frame, textvariable=self.vars["playlist_label"], values=list(self.playlists_by_label.keys()), state="readonly")
        self.field_row(frame, 4, "Lista", self.playlist_combo)
        playlist_buttons = ttk.Frame(frame)
        playlist_buttons.grid(row=4, column=2, columnspan=2, padx=(8, 0), sticky="ew")
        RoundedButton(playlist_buttons, "Cargar", self.load_playlists, "Soft.TButton", width=78, height=34).pack(side="left", padx=(0, 6))
        RoundedButton(playlist_buttons, "Crear", self.create_playlist, "Accent.TButton", width=78, height=34).pack(side="left")
        return frame

    def automation_section(self, parent: ttk.Frame) -> ttk.Frame:
        frame = self.section(parent, "Automatizacion")
        self.field_row(frame, 1, "Revisar cada", ttk.Spinbox(frame, from_=2, to=3600, textvariable=self.vars["scan_interval_seconds"], width=8), "segundos")
        self.field_row(frame, 2, "Esperar estabilidad", ttk.Spinbox(frame, from_=2, to=600, textvariable=self.vars["stable_wait_seconds"], width=8), "segundos")
        self.field_row(
            frame, 3, "Al abrir la app",
            ttk.Combobox(frame, textvariable=self.vars["auto_start_enabled"], values=["Auto ON", "Auto OFF"], state="readonly"),
        )
        ttk.Checkbutton(frame, text="Arrancar minimizada", variable=self.vars["start_minimized"]).grid(row=4, column=1, sticky="w", pady=(8, 0))
        ttk.Checkbutton(frame, text="Iniciar con Windows", variable=self.vars["run_at_startup"]).grid(row=5, column=1, sticky="w", pady=(8, 0))
        ttk.Checkbutton(frame, text="Borrar automaticamente archivos locales ya subidos", variable=self.vars["auto_delete_uploaded"]).grid(
            row=6, column=1, sticky="w", pady=(8, 0)
        )
        ttk.Label(frame, text="Borrar tras", style="PanelMuted.TLabel").grid(row=7, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Spinbox(frame, from_=1, to=525600, textvariable=self.vars["auto_delete_after_hours"], width=8).grid(row=7, column=1, sticky="ew", pady=5)
        ttk.Combobox(
            frame,
            textvariable=self.vars["auto_delete_after_unit"],
            values=["minutos", "horas", "dias"],
            state="readonly",
            width=10,
        ).grid(row=7, column=2, sticky="w", pady=5, padx=(8, 0))
        return frame

    def field_row(self, frame: ttk.Frame, row: int, label: str, widget, suffix: str = "") -> None:
        ttk.Label(frame, text=label, style="PanelMuted.TLabel").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 14))
        widget.grid(row=row, column=1, sticky="ew", pady=5)
        if suffix:
            ttk.Label(frame, text=suffix, style="PanelMuted.TLabel").grid(row=row, column=2, sticky="w", pady=5, padx=(8, 0))

    def path_row(self, frame: ttk.Frame, row: int, label: str, key: str, command: Callable[[], None]) -> None:
        ttk.Label(frame, text=label, style="PanelMuted.TLabel").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(frame, textvariable=self.vars[key]).grid(row=row, column=1, sticky="ew", pady=5)
        RoundedButton(frame, "Elegir", command, "Soft.TButton", width=78, height=34).grid(row=row, column=2, padx=(8, 0), pady=5)

    def pick_folder(self) -> None:
        value = filedialog.askdirectory(title="Carpeta de videos")
        if value:
            self.vars["watch_folder"].set(value)

    def pick_json(self) -> None:
        value = filedialog.askopenfilename(title="Archivo client_secret.json", filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if value:
            self.vars["client_secret_path"].set(value)

    def open_oauth_wizard(self) -> None:
        OAuthGuideDialog(self, self.set_client_secret_path)

    def set_client_secret_path(self, value: str) -> None:
        self.vars["client_secret_path"].set(value)

    def temp_config(self) -> Config:
        return Config(
            watch_folder=self.vars["watch_folder"].get().strip(),
            client_secret_path=self.vars["client_secret_path"].get().strip(),
            privacy_status=PRIVACY_VALUES.get(self.vars["privacy_status"].get(), "private"),
            category_id=CATEGORIES.get(self.vars["category_name"].get(), "22"),
        )

    def load_playlists(self) -> None:
        try:
            client = YouTubeClient(self.master.store, self.temp_config(), lambda _text: None)
            playlists = client.playlists()
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"No se pudieron cargar las listas:\n{exc}")
            return
        self.set_playlist_options(playlists)

    def set_playlist_options(self, playlists: list[dict], selected_id: str = "") -> None:
        labels: list[str] = []
        self.playlists_by_label = {}
        for item in playlists:
            label = item["title"]
            if label in self.playlists_by_label:
                label = f"{label} ({item['id']})"
            labels.append(label)
            self.playlists_by_label[label] = item["id"]
        self.playlist_combo.configure(values=labels)
        if selected_id:
            for label, playlist_id in self.playlists_by_label.items():
                if playlist_id == selected_id:
                    self.vars["playlist_label"].set(label)
                    return
        if self.vars["playlist_label"].get() not in self.playlists_by_label:
            self.vars["playlist_label"].set(labels[0] if labels else "Ninguna")

    def create_playlist(self) -> None:
        name = simpledialog.askstring(APP_NAME, "Nombre de la nueva lista de reproduccion:", parent=self)
        if not name:
            return
        try:
            client = YouTubeClient(self.master.store, self.temp_config(), lambda _text: None)
            created = client.create_playlist(name, PRIVACY_VALUES.get(self.vars["privacy_status"].get(), "private"))
            playlists = client.playlists()
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"No se pudo crear la lista:\n{exc}")
            return
        self.set_playlist_options(playlists, selected_id=created["id"])
        messagebox.showinfo(APP_NAME, f"Lista creada y seleccionada:\n{created['title']}")

    def save(self) -> None:
        if not self.vars["watch_folder"].get().strip():
            messagebox.showerror(APP_NAME, "Selecciona la carpeta de videos.")
            return
        if not self.vars["client_secret_path"].get().strip():
            messagebox.showerror(APP_NAME, "Selecciona el archivo de credenciales OAuth.")
            return
        try:
            cleanup_value = int(self.vars["auto_delete_after_hours"].get())
            scan_interval = int(self.vars["scan_interval_seconds"].get())
            stable_wait = int(self.vars["stable_wait_seconds"].get())
        except (tk.TclError, ValueError):
            messagebox.showerror(APP_NAME, "Revisa los tiempos: deben ser números enteros válidos.")
            return
        if cleanup_value < 1:
            messagebox.showerror(APP_NAME, "El plazo de borrado debe ser como minimo 1.")
            return
        if scan_interval < 2 or stable_wait < 2:
            messagebox.showerror(APP_NAME, "Los tiempos de revisión y estabilidad deben ser de al menos 2 segundos.")
            return
        playlist_label = self.vars["playlist_label"].get()
        self.result = Config(
            watch_folder=self.vars["watch_folder"].get().strip(),
            client_secret_path=self.vars["client_secret_path"].get().strip(),
            privacy_status=PRIVACY_VALUES.get(self.vars["privacy_status"].get(), "private"),
            category_id=CATEGORIES.get(self.vars["category_name"].get(), "22"),
            playlist_id=self.playlists_by_label.get(playlist_label, ""),
            playlist_name=playlist_label or "Ninguna",
            recursive=self.vars["recursive"].get(),
            scan_interval_seconds=scan_interval,
            stable_wait_seconds=stable_wait,
            extensions=self.vars["extensions"].get().strip(),
            start_minimized=self.vars["start_minimized"].get(),
            run_at_startup=self.vars["run_at_startup"].get(),
            auto_start_enabled=self.vars["auto_start_enabled"].get() == "Auto ON",
            auto_delete_uploaded=self.vars["auto_delete_uploaded"].get(),
            auto_delete_after_hours=cleanup_value,
            auto_delete_after_unit=self.vars["auto_delete_after_unit"].get(),
        )
        self.destroy()

    def cancel(self) -> None:
        self.destroy()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.store = Store()
        self.config = self.store.load_config()
        self.events: queue.Queue = queue.Queue()
        self.worker: SyncWorker | None = None
        self.tray_icon = None
        self.logo_image = None
        self.busy = False
        self.folder_refresh_running = False
        self.folder_refresh_pending = False
        self.folder_refresh_verify_pending = False
        self.processing_check_after_id = None
        self.gallery_loading = False
        self.gallery_loaded = False
        self.gallery_all_videos: list[dict] = []
        self.gallery_rows_by_id: dict[str, dict] = {}
        self.gallery_playlists_by_label: dict[str, str] = {"Ninguna": ""}
        self.gallery_filter_playlists_by_label: dict[str, str | None] = {"Todas": None, "Sin lista": ""}
        self.gallery_duplicate_ids: set[str] = set()
        self.gallery_duplicate_groups = 0
        self.gallery_duplicates_only = False
        self.gallery_find_duplicates_pending = False
        self.gallery_action_widgets: list[tk.Widget] = []
        self.gallery_loading_progress: ttk.Progressbar | None = None
        self.gallery_loading_var = tk.StringVar(value="")
        self.upload_limit_state = self.store.get_upload_limit()
        if self.upload_limit_state:
            try:
                retry_at = datetime.fromisoformat(self.upload_limit_state["retry_at"])
                if retry_at <= datetime.now().astimezone():
                    self.store.clear_upload_limit()
                    self.upload_limit_state = None
            except (TypeError, ValueError):
                self.store.clear_upload_limit()
                self.upload_limit_state = None
        self.auto_enabled = self.config.auto_start_enabled and self.upload_limit_state is None

        self.title(APP_NAME)
        self.geometry("1120x740")
        self.minsize(760, 520)
        self.window_geometry_before_tray = "1120x740"
        self.window_state_before_tray = "normal"
        self.restoring_window = False
        self.configure(bg="#0f0f0f")
        set_window_icon(self)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.bind("<Configure>", self.remember_window_geometry, add="+")
        self.bind("<Map>", lambda _event: self.after(80, self.refresh_visible_layout), add="+")

        self.configure_styles()
        self.build_ui()
        self.load_logo()
        self.after(100, self.ensure_tray)
        self.after(100, self.process_events)
        self.after(300, self.update_upload_limit_countdown)

        first_run = not self.store.config_path.exists()
        if first_run:
            self.after(250, lambda: self.open_config(first_run=True))
        else:
            self.start_worker()
            self.after(250, self.check_youtube_connection)
            if self.config.start_minimized:
                self.after(500, self.hide_to_tray)

    def configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        bg = "#0f0f0f"
        panel = "#181818"
        panel2 = "#272727"
        text = "#f9f9f9"
        muted = "#aaaaaa"
        accent = "#ff0033"
        blue = "#3ea6ff"
        style.configure(".", background=bg, foreground=text, fieldbackground=panel, font=("Segoe UI", 10))
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel, borderwidth=0, relief="flat")
        style.configure("PanelInner.TFrame", background=panel, borderwidth=0)
        style.configure("Toolbar.TFrame", background="#141414")
        style.configure("Header.TFrame", background=accent)
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("Muted.TLabel", background=bg, foreground=muted)
        style.configure("Panel.TLabel", background=panel, foreground=text)
        style.configure("PanelMuted.TLabel", background=panel, foreground=muted)
        style.configure("Header.TLabel", background=accent, foreground="#ffffff", font=("Segoe UI", 12, "bold"))
        style.configure("Title.TLabel", background=bg, foreground=text, font=("Segoe UI", 18, "bold"))
        style.configure("DialogTitle.TLabel", background=panel, foreground=text, font=("Segoe UI", 20, "bold"))
        style.configure("Section.TLabel", background=bg, foreground="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("Big.TLabel", background=panel, foreground=text, font=("Segoe UI", 12, "bold"))
        style.configure("Status.TLabel", background=panel, foreground="#d1d5db", font=("Segoe UI", 10, "bold"))
        style.configure("CardTitle.TLabel", background=panel, foreground=muted, font=("Segoe UI", 9, "bold"))
        style.configure("CardMain.TLabel", background=panel, foreground=text, font=("Segoe UI", 12, "bold"))
        style.configure("CardDetail.TLabel", background=panel, foreground=muted, font=("Segoe UI", 9))
        style.configure("StatLabel.TLabel", background=panel, foreground=muted, font=("Segoe UI", 9, "bold"))
        style.configure("StatTotal.TLabel", background=panel, foreground=text, font=("Segoe UI", 18, "bold"))
        style.configure("StatPending.TLabel", background=panel, foreground=blue, font=("Segoe UI", 18, "bold"))
        style.configure("StatActive.TLabel", background=panel, foreground="#c084fc", font=("Segoe UI", 18, "bold"))
        style.configure("StatUploaded.TLabel", background=panel, foreground="#2ba640", font=("Segoe UI", 18, "bold"))
        style.configure("StatIssue.TLabel", background=panel, foreground="#f6b73c", font=("Segoe UI", 18, "bold"))
        style.configure("TLabelFrame", background=bg, foreground=text, bordercolor=panel2)
        style.configure("TLabelFrame.Label", background=bg, foreground=muted)
        style.configure("TNotebook", background=bg, borderwidth=0, bordercolor=bg, lightcolor=bg, darkcolor=bg, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", background="#181818", foreground=muted, padding=(16, 8), borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#272727")], foreground=[("selected", accent)])
        style.configure("TNotebook.Tab", bordercolor="#303030", lightcolor="#303030", darkcolor="#303030")
        style.configure("TButton", background=panel2, foreground=text, borderwidth=0, padding=(14, 9), font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[("active", "#3a3a3a")])
        style.configure("Accent.TButton", background=accent, foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#dc2626")])
        style.configure("Success.TButton", background="#16a34a", foreground="#ffffff")
        style.map("Success.TButton", background=[("active", "#15803d")])
        style.configure("Soft.TButton", background="#272727", foreground="#f9f9f9")
        style.map("Soft.TButton", background=[("active", "#3f3f3f")])
        style.configure("Blue.TButton", background=blue, foreground="#0f0f0f")
        style.map("Blue.TButton", background=[("active", "#65b8ff")])
        style.configure("Danger.TButton", background="#991b1b", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#7f1d1d")])
        style.configure("Icon.TButton", background="#2b2b2b", foreground="#f3f4f6", borderwidth=0, padding=(12, 9), font=("Segoe UI", 10, "bold"))
        style.map("Icon.TButton", background=[("active", "#383838")])
        style.configure("HeaderIcon.TButton", background="#2b2b2b", foreground="#f3f4f6", borderwidth=0, padding=(12, 7), font=("Segoe UI", 14, "bold"))
        style.map("HeaderIcon.TButton", background=[("active", "#383838")])
        style.configure("HeaderAccentIcon.TButton", background=accent, foreground="#ffffff", borderwidth=0, padding=(12, 7), font=("Segoe UI", 14, "bold"))
        style.map("HeaderAccentIcon.TButton", background=[("active", "#dc2626")])
        style.configure("TCheckbutton", background=panel, foreground=text, focuscolor=panel)
        style.map("TCheckbutton", background=[("active", panel)], foreground=[("active", text)])
        style.configure("TEntry", fieldbackground="#101010", foreground=text, insertcolor=text, bordercolor=panel2)
        style.configure("TSpinbox", fieldbackground="#101010", foreground=text, insertcolor=text, bordercolor=panel2)
        style.configure("TCombobox", fieldbackground="#101010", foreground=text, bordercolor=panel2, arrowcolor=text, selectbackground="#101010", selectforeground=text)
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#101010"), ("disabled", "#101010")],
            foreground=[("readonly", text), ("disabled", text)],
            selectbackground=[("readonly", "#101010")],
            selectforeground=[("readonly", text)],
        )
        style.configure("Treeview", background="#141414", foreground=text, fieldbackground="#141414", borderwidth=0, bordercolor="#272727", lightcolor="#272727", darkcolor="#272727", rowheight=32, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#272727", foreground="#ffffff", borderwidth=0, padding=(8, 8), font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#3b1b22")], foreground=[("selected", "#ffffff")])
        style.configure("Horizontal.TProgressbar", troughcolor="#272727", background=accent, bordercolor="#272727", lightcolor=accent, darkcolor=accent, thickness=9)

    def build_ui(self) -> None:
        viewport = ttk.Frame(self)
        viewport.pack(fill="both", expand=True)
        viewport.rowconfigure(0, weight=1)
        viewport.columnconfigure(0, weight=1)
        self.main_canvas = tk.Canvas(viewport, bg="#0f0f0f", highlightthickness=0)
        self.main_canvas.grid(row=0, column=0, sticky="nsew")

        root = ttk.Frame(self.main_canvas, padding=12)
        self.main_root = root
        self.main_window = self.main_canvas.create_window((0, 0), window=root, anchor="nw")
        root.bind("<Configure>", lambda _event: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.bind("<Configure>", self.resize_main_content)
        self.bind_all("<MouseWheel>", self.scroll_main_content, add="+")

        header = ttk.Frame(root)
        self.header_frame = header
        header.pack(fill="x", pady=(0, 8))
        self.logo_label = ttk.Label(header)
        self.logo_label.pack(side="left", padx=(0, 14))
        title_area = ttk.Frame(header)
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(title_area, text="YouTubeSync", style="Title.TLabel").pack(anchor="w")
        self.status_var = tk.StringVar(value="Preparado")
        status_row = ttk.Frame(title_area)
        status_row.pack(anchor="w", pady=(4, 0))
        self.health_canvas = tk.Canvas(status_row, width=14, height=14, bg="#0f0f0f", highlightthickness=0)
        self.health_canvas.pack(side="left", padx=(0, 8))
        self.health_dot = self.health_canvas.create_oval(2, 2, 12, 12, fill="#f59e0b", outline="")
        self.header_status = ttk.Label(status_row, textvariable=self.status_var, style="Muted.TLabel", wraplength=440)
        self.header_status.pack(side="left", fill="x", expand=True)

        actions = ttk.Frame(header)
        actions.pack(side="right")
        auto_text = "Auto ON" if self.auto_enabled else "Auto OFF"
        auto_style = "Success.TButton" if self.auto_enabled else "Danger.TButton"
        self.auto_button = RoundedButton(actions, auto_text, self.toggle_auto_mode, auto_style, width=94)
        self.auto_button.grid(row=0, column=0, padx=4)
        upload_button = RoundedButton(actions, "↑", self.upload_pending_now, "HeaderAccentIcon.TButton", width=44)
        upload_button.grid(row=0, column=1, padx=4)
        refresh_button = RoundedButton(actions, "↻", self.refresh_all, "HeaderIcon.TButton", width=44)
        refresh_button.grid(row=0, column=2, padx=4)
        settings_button = RoundedButton(actions, "⚙", lambda: self.open_config(False), "HeaderIcon.TButton", width=44)
        settings_button.grid(row=0, column=3, padx=4)
        ToolTip(upload_button, "Subir pendientes")
        ToolTip(refresh_button, "Actualizar")
        ToolTip(settings_button, "Ajustes")

        cards = ttk.Frame(root)
        self.cards_frame = cards
        cards.pack(fill="x", pady=(0, 8))
        cards.rowconfigure(0, weight=1)
        for column in range(3):
            cards.columnconfigure(column, weight=1, uniform="header_cards")
        self.youtube_card = self.card(cards, "Estado", "Sin comprobar")
        self.youtube_card["frame"].grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.folder_card = self.card(cards, "Configuracion", "Sin configurar")
        self.folder_card["frame"].grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        self.progress_card = self.card(cards, "Subida actual", "Sin actividad")
        self.progress_card["frame"].grid(row=0, column=2, sticky="nsew")

        self.progress_var = tk.IntVar(value=0)
        progress_panel = ttk.Frame(root, padding=(10, 6), style="Panel.TFrame")
        progress_panel.pack(fill="x", pady=(0, 8))
        ttk.Label(progress_panel, text="Subida", style="PanelMuted.TLabel").pack(side="left", padx=(0, 10))
        ttk.Progressbar(progress_panel, variable=self.progress_var, maximum=100).pack(side="left", fill="x", expand=True)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self.videos_tab = ttk.Frame(self.notebook, padding=8)
        self.gallery_tab = ttk.Frame(self.notebook, padding=8)
        self.console_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.videos_tab, text="Vídeos")
        self.notebook.add(self.gallery_tab, text="Canal")
        self.notebook.add(self.console_tab, text="Consola")

        self.build_videos_tab()
        self.build_gallery_tab()
        self.build_console_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self.on_main_tab_changed)
        self.refresh_config_text()
        self.refresh_folder_contents(verify_youtube=False)

    def resize_main_content(self, event) -> None:
        # A canvas window otherwise keeps its requested height, even when the app shrinks.
        self.main_canvas.itemconfigure(self.main_window, width=max(1, event.width), height=max(640, event.height))
        if hasattr(self, "header_status"):
            self.header_status.configure(wraplength=max(180, event.width - 420))
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        if event.height >= 640:
            self.main_canvas.yview_moveto(0)

    def scroll_main_content(self, event) -> None:
        widget = event.widget
        if isinstance(widget, (ttk.Treeview, tk.Text, ttk.Combobox, ttk.Spinbox)):
            return
        bounds = self.main_canvas.bbox("all")
        if bounds and bounds[3] > self.main_canvas.winfo_height():
            self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def card(self, parent: ttk.Frame, title: str, value: str) -> dict:
        frame = ttk.Frame(parent, padding=(10, 6), style="Panel.TFrame")
        ttk.Label(frame, text=title.upper(), style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        var = tk.StringVar(value=value)
        detail_var = tk.StringVar(value="")
        icon = tk.Label(frame, text="●", bg="#181818", fg="#aaaaaa", font=("Segoe UI", 16, "bold"), width=2)
        icon.grid(row=1, column=0, rowspan=2, sticky="nw", pady=(3, 0), padx=(0, 8))
        main_label = ttk.Label(frame, textvariable=var, style="CardMain.TLabel", wraplength=260)
        detail_label = ttk.Label(frame, textvariable=detail_var, style="CardDetail.TLabel", wraplength=260)
        main_label.grid(row=1, column=1, sticky="ew", pady=(3, 0))
        detail_label.grid(row=2, column=1, sticky="ew", pady=(2, 0))
        frame.columnconfigure(1, weight=1)
        frame.bind("<Configure>", lambda event: self.resize_card_text(event, main_label, detail_label))
        return {"frame": frame, "var": var, "detail": detail_var, "icon": icon}

    def resize_card_text(self, event, main_label: ttk.Label, detail_label: ttk.Label) -> None:
        wrap = max(100, event.width - 72)
        main_label.configure(wraplength=wrap)
        detail_label.configure(wraplength=wrap)

    def set_card(self, card: dict, main: str, detail: str = "", color: str = "#9ca3af", icon: str = "●") -> None:
        card["var"].set(main)
        card["detail"].set(detail)
        card["icon"].configure(text=icon, fg=color)

    def set_health(self, state: str, text: str) -> None:
        colors = {"ok": "#22c55e", "warn": "#f59e0b", "error": "#ef4444"}
        self.health_canvas.itemconfigure(self.health_dot, fill=colors.get(state, "#f59e0b"))
        self.status_var.set(text)

    def update_upload_limit_countdown(self) -> None:
        state = self.upload_limit_state
        if state:
            try:
                retry_at = datetime.fromisoformat(state["retry_at"])
                now = datetime.now().astimezone()
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=now.tzinfo)
                if retry_at > now:
                    labels = {"canal": "Limite del canal", "proyecto": "Cuota del proyecto", "api": "Limite de YouTube"}
                    remaining = remaining_text(retry_at, now)
                    label = labels.get(state.get("kind", ""), "Limite de YouTube")
                    self.set_card(self.progress_card, label, f"Reintento en {remaining}", "#ef4444", "!")
                    if hasattr(self, "quota_summary_var"):
                        self.quota_summary_var.set(
                            f"{label} | Reintento: {retry_at.astimezone().strftime('%d/%m %H:%M')} | Faltan {remaining} | {state.get('source', 'estimado')}"
                        )
                    self.set_health("error", f"{label}: reintento en {remaining}")
                else:
                    self.store.clear_upload_limit()
                    self.upload_limit_state = None
                    self.auto_enabled = True
                    self.auto_button.configure(text="Auto ON", style="Success.TButton")
                    self.set_card(self.progress_card, "Reintentando", "Comprobando disponibilidad real", "#f59e0b", "↻")
                    self.log("Ha terminado la espera estimada. Probando de nuevo con YouTube.")
                    self.start_worker()
            except (TypeError, ValueError):
                self.store.clear_upload_limit()
                self.upload_limit_state = None
        self.after(1000, self.update_upload_limit_countdown)

    def build_videos_tab(self) -> None:
        top = ttk.Frame(self.videos_tab)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Biblioteca de vídeos", style="Title.TLabel").pack(side="left")
        self.folder_summary_var = tk.StringVar(value="Sin revisar")
        self.quota_summary_var = tk.StringVar(value="YouTube: sin comprobar")
        videos_refresh_button = RoundedButton(top, "↻", self.refresh_folder_contents, "HeaderIcon.TButton", width=42, height=36)
        videos_refresh_button.pack(side="right")
        ToolTip(videos_refresh_button, "Actualizar videos")

        summary = ttk.Frame(self.videos_tab, padding=(10, 3), style="Panel.TFrame")
        summary.pack(fill="x", pady=(0, 6))
        self.total_count_var = tk.StringVar(value="0")
        self.pending_count_var = tk.StringVar(value="0")
        self.active_count_var = tk.StringVar(value="0")
        self.uploaded_count_var = tk.StringVar(value="0")
        self.issue_count_var = tk.StringVar(value="0")
        stats = [
            ("TOTAL", self.total_count_var, "StatTotal.TLabel"),
            ("PENDIENTES", self.pending_count_var, "StatPending.TLabel"),
            ("EN CURSO", self.active_count_var, "StatActive.TLabel"),
            ("SUBIDOS", self.uploaded_count_var, "StatUploaded.TLabel"),
            ("INCIDENCIAS", self.issue_count_var, "StatIssue.TLabel"),
        ]
        for column, (label, variable, value_style) in enumerate(stats):
            summary.columnconfigure(column, weight=1, uniform="video_stats")
            cell = ttk.Frame(summary, style="PanelInner.TFrame", padding=(6, 2))
            cell.grid(row=0, column=column, sticky="ew")
            ttk.Label(cell, textvariable=variable, style=value_style).pack(side="left", padx=(0, 6))
            ttk.Label(cell, text=label, style="StatLabel.TLabel").pack(side="left")
        summary_status = ttk.Frame(summary, style="PanelInner.TFrame")
        summary_status.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(2, 0))
        ttk.Label(summary_status, textvariable=self.folder_summary_var, style="PanelMuted.TLabel").pack(side="left")
        ttk.Label(summary_status, textvariable=self.quota_summary_var, style="PanelMuted.TLabel").pack(side="right")

        self.videos_notebook = ttk.Notebook(self.videos_tab)
        self.videos_notebook.pack(fill="both", expand=True)
        self.pending_tab = ttk.Frame(self.videos_notebook, padding=8)
        self.uploaded_tab = ttk.Frame(self.videos_notebook, padding=8)
        self.videos_notebook.add(self.pending_tab, text="Pendientes")
        self.videos_notebook.add(self.uploaded_tab, text="Ya subidos")

        pending_top = ttk.Frame(self.pending_tab)
        pending_top.pack(fill="x", pady=(0, 8))
        self.pending_summary_var = tk.StringVar(value="Videos que faltan por subir")
        ttk.Label(pending_top, textvariable=self.pending_summary_var, style="Muted.TLabel").pack(anchor="w")
        self.incident_help_var = tk.StringVar(value="")
        self.incident_help_label = ttk.Label(pending_top, textvariable=self.incident_help_var, style="Muted.TLabel", wraplength=600)
        self.incident_help_var.trace_add("write", self.toggle_incident_help)
        pending_actions = ttk.Frame(pending_top)
        self.pending_actions = pending_actions
        pending_actions.pack(fill="x")
        retry_button = RoundedButton(pending_actions, "↻ Reintentar", self.retry_selected_incident, "HeaderAccentIcon.TButton", width=112, height=36)
        reset_button = RoundedButton(pending_actions, "✓ Pendiente", self.reset_selected_incident, "Soft.TButton", width=112, height=36)
        cancel_button = RoundedButton(pending_actions, "■ Cancelar", self.cancel_selected_incident, "Danger.TButton", width=104, height=36)
        open_pending_button = RoundedButton(pending_actions, "▣", self.open_folder_selection, "Soft.TButton", width=42, height=36)
        copy_pending_button = RoundedButton(pending_actions, "⧉", self.copy_selected_incident, "Soft.TButton", width=42, height=36)
        selected_upload_button = RoundedButton(pending_actions, "↑1", self.upload_selected_pending, "HeaderAccentIcon.TButton", width=48, height=36)
        pending_upload_button = RoundedButton(pending_actions, "↑", self.upload_pending_now, "HeaderAccentIcon.TButton", width=42, height=36)
        retry_button.pack(side="left", padx=(0, 7))
        reset_button.pack(side="left", padx=(0, 7))
        cancel_button.pack(side="left")
        pending_upload_button.pack(side="right")
        selected_upload_button.pack(side="right", padx=(0, 7))
        copy_pending_button.pack(side="right", padx=(0, 7))
        open_pending_button.pack(side="right", padx=(0, 7))
        ToolTip(retry_button, "Reintentar o volver a comprobar")
        ToolTip(reset_button, "Quitar el error y dejar el video pendiente")
        ToolTip(cancel_button, "Cancelar la subida activa")
        ToolTip(open_pending_button, "Abrir archivo local")
        ToolTip(copy_pending_button, "Copiar detalle del estado")
        ToolTip(selected_upload_button, "Subir solo el video seleccionado")
        ToolTip(pending_upload_button, "Subir pendientes")

        pending_list = ttk.Frame(self.pending_tab)
        pending_list.pack(fill="both", expand=True)
        columns = ("nombre", "tamano", "creado", "estado", "detalle", "ruta")
        self.pending_table = ttk.Treeview(pending_list, columns=columns, show="headings", height=5)
        for key, label, width in [
            ("nombre", "Archivo pendiente", 280),
            ("tamano", "Tamaño", 90),
            ("creado", "Creado", 145),
            ("estado", "Estado", 120),
            ("detalle", "Que ha pasado", 360),
            ("ruta", "Ruta", 420),
        ]:
            self.pending_table.heading(key, text=label)
            self.pending_table.column(key, width=width, anchor="w")
        self.enable_tree_sorting(self.pending_table)
        pending_list.rowconfigure(0, weight=1)
        pending_list.columnconfigure(0, weight=1)
        self.pending_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(pending_list, orient="vertical", command=self.pending_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        xscrollbar = ttk.Scrollbar(pending_list, orient="horizontal", command=self.pending_table.xview)
        xscrollbar.grid(row=1, column=0, sticky="ew")
        self.pending_table.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)
        self.pending_table.tag_configure("pending", foreground="#e5e7eb")
        self.pending_table.tag_configure("error", foreground="#ff5c68")
        self.pending_table.tag_configure("cancelled", foreground="#f6b73c")
        self.pending_table.tag_configure("uploading", foreground="#3ea6ff")
        self.pending_table.tag_configure("processing", foreground="#c084fc")
        self.pending_table.tag_configure("missing", foreground="#fb7185")
        self.pending_table.bind("<Double-1>", self.open_folder_selection)
        self.pending_table.bind("<<TreeviewSelect>>", self.update_incident_help)

        uploaded_top = ttk.Frame(self.uploaded_tab)
        uploaded_top.pack(fill="x", pady=(0, 8))
        self.uploaded_summary_var = tk.StringVar(value="Videos subidos o detectados en YouTube")
        ttk.Label(uploaded_top, textvariable=self.uploaded_summary_var, style="Muted.TLabel").pack(anchor="w", pady=(0, 7))
        uploaded_actions = ttk.Frame(uploaded_top)
        uploaded_actions.pack(fill="x")
        cleanup_button = RoundedButton(uploaded_actions, "⌫", self.run_configured_cleanup, "Soft.TButton", width=42, height=36)
        delete_one_button = RoundedButton(uploaded_actions, "−", self.delete_selected_uploaded_file, "Danger.TButton", width=42, height=36)
        delete_all_button = RoundedButton(uploaded_actions, "×", self.delete_all_uploaded_files, "Danger.TButton", width=42, height=36)
        open_local_button = RoundedButton(uploaded_actions, "▣", self.open_selected_cleanup_local, "Soft.TButton", width=42, height=36)
        open_youtube_button = RoundedButton(uploaded_actions, "▶", self.open_selected_cleanup_youtube, "HeaderAccentIcon.TButton", width=42, height=36)
        for button in (cleanup_button, delete_one_button, delete_all_button):
            button.pack(side="left", padx=(0, 7))
        open_local_button.pack(side="right", padx=(7, 0))
        open_youtube_button.pack(side="right")
        ToolTip(cleanup_button, "Ejecutar limpieza configurada")
        ToolTip(delete_one_button, "Borrar archivo local seleccionado")
        ToolTip(delete_all_button, "Borrar todos los archivos locales verificados")
        ToolTip(open_local_button, "Abrir archivo local")
        ToolTip(open_youtube_button, "Abrir en YouTube")

        cleanup_list = ttk.Frame(self.uploaded_tab)
        cleanup_list.pack(fill="both", expand=True)
        columns = ("fecha", "titulo", "archivo", "tamano", "youtube")
        self.cleanup_table = ttk.Treeview(cleanup_list, columns=columns, show="headings", height=5)
        for key, label, width in [
            ("fecha", "Subido", 150),
            ("titulo", "Titulo", 190),
            ("archivo", "Archivo local", 430),
            ("tamano", "Tamaño", 100),
            ("youtube", "YouTube", 220),
        ]:
            self.cleanup_table.heading(key, text=label)
            self.cleanup_table.column(key, width=width, anchor="w")
        self.enable_tree_sorting(self.cleanup_table)
        cleanup_list.rowconfigure(0, weight=1)
        cleanup_list.columnconfigure(0, weight=1)
        self.cleanup_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(cleanup_list, orient="vertical", command=self.cleanup_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        xscrollbar = ttk.Scrollbar(cleanup_list, orient="horizontal", command=self.cleanup_table.xview)
        xscrollbar.grid(row=1, column=0, sticky="ew")
        self.cleanup_table.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)
        self.cleanup_table.tag_configure("uploaded", foreground="#64d879")
        self.cleanup_table.bind("<Double-1>", self.open_cleanup_selection)

    def toggle_incident_help(self, *_args) -> None:
        if self.incident_help_var.get():
            self.incident_help_label.pack(anchor="w", fill="x", pady=(0, 4), before=self.pending_actions)
        else:
            self.incident_help_label.pack_forget()

    def build_gallery_tab(self) -> None:
        top = ttk.Frame(self.gallery_tab)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Vídeos del canal", style="Title.TLabel").pack(side="left")
        self.gallery_summary_var = tk.StringVar(value="Abre esta pestaña para cargar el canal")
        gallery_refresh = RoundedButton(top, "↻", lambda: self.refresh_channel_gallery(True), "HeaderIcon.TButton", width=42, height=36)
        gallery_refresh.pack(side="right")
        duplicate_button = RoundedButton(top, "≋", self.find_channel_duplicates, "HeaderIcon.TButton", width=42, height=36)
        duplicate_button.pack(side="right", padx=(0, 7))
        ToolTip(gallery_refresh, "Actualizar canal")
        ToolTip(duplicate_button, "Buscar duplicados por título")

        actions = ttk.Frame(self.gallery_tab)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Label(actions, textvariable=self.gallery_summary_var, style="Muted.TLabel").pack(side="left")
        open_button = RoundedButton(actions, "▶", self.open_gallery_video, "HeaderAccentIcon.TButton", width=42, height=36)
        studio_button = RoundedButton(actions, "↓", self.open_gallery_download, "Soft.TButton", width=42, height=36)
        share_button = RoundedButton(actions, "↗", self.share_gallery_video, "Soft.TButton", width=42, height=36)
        delete_button = RoundedButton(actions, "×", self.delete_gallery_video, "Danger.TButton", width=42, height=36)
        open_button.pack(side="right")
        studio_button.pack(side="right", padx=(0, 7))
        share_button.pack(side="right", padx=(0, 7))
        delete_button.pack(side="right", padx=(0, 7))
        ToolTip(open_button, "Abrir vídeo")
        ToolTip(studio_button, "Abrir en YouTube Studio para descargar")
        ToolTip(share_button, "Poner como Oculto y copiar enlace")
        ToolTip(delete_button, "Borrar vídeo de YouTube")
        self.gallery_action_widgets.extend(
            [gallery_refresh, duplicate_button, open_button, studio_button, share_button, delete_button]
        )

        filters = ttk.Frame(self.gallery_tab)
        filters.pack(fill="x", pady=(0, 8))
        ttk.Label(filters, text="Buscar", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.gallery_search_var = tk.StringVar()
        search_entry = ttk.Entry(filters, textvariable=self.gallery_search_var, width=18)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.gallery_privacy_filter_var = tk.StringVar(value="Todas")
        privacy_filter = ttk.Combobox(
            filters,
            textvariable=self.gallery_privacy_filter_var,
            values=("Todas", "Público", "Oculto", "Privado"),
            state="readonly",
            width=12,
        )
        privacy_filter.pack(side="left", padx=(0, 8))
        self.gallery_playlist_filter_var = tk.StringVar(value="Todas")
        self.gallery_playlist_filter_combo = ttk.Combobox(
            filters, textvariable=self.gallery_playlist_filter_var, values=("Todas", "Sin lista"),
            state="readonly", width=16,
        )
        self.gallery_playlist_filter_combo.pack(side="left", padx=(0, 8))
        clear_filters = RoundedButton(filters, "×", self.clear_gallery_filters, "Soft.TButton", width=38, height=32)
        clear_filters.pack(side="left")
        ToolTip(search_entry, "Buscar por título, identificador o lista")
        ToolTip(privacy_filter, "Filtrar por privacidad")
        ToolTip(self.gallery_playlist_filter_combo, "Filtrar por lista de reproducción")
        ToolTip(clear_filters, "Quitar filtros")
        self.gallery_search_var.trace_add("write", self.filter_gallery_rows)
        privacy_filter.bind("<<ComboboxSelected>>", self.filter_gallery_rows)
        self.gallery_playlist_filter_combo.bind("<<ComboboxSelected>>", self.filter_gallery_rows)
        self.gallery_action_widgets.extend([search_entry, privacy_filter, self.gallery_playlist_filter_combo, clear_filters])

        date_filters = ttk.Frame(self.gallery_tab)
        date_filters.pack(fill="x", pady=(0, 8))
        ttk.Label(date_filters, text="Fecha", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.gallery_date_filter_var = tk.StringVar()
        date_entry = ttk.Entry(date_filters, textvariable=self.gallery_date_filter_var, width=18)
        date_entry.pack(side="left", padx=(0, 8))
        self.gallery_date_source_var = tk.StringVar(value="Título o publicación")
        date_source = ttk.Combobox(
            date_filters,
            textvariable=self.gallery_date_source_var,
            values=("Título o publicación", "Título", "Publicado"),
            state="readonly",
            width=21,
        )
        date_source.pack(side="left")
        ToolTip(date_entry, "Filtrar por año, mes o fecha completa")
        ToolTip(date_source, "Elegir dónde buscar la fecha")
        self.gallery_date_filter_var.trace_add("write", self.filter_gallery_rows)
        date_source.bind("<<ComboboxSelected>>", self.filter_gallery_rows)
        self.gallery_action_widgets.extend([date_entry, date_source])

        playlist_bar = ttk.Frame(self.gallery_tab)
        playlist_bar.pack(fill="x", pady=(0, 8))
        ttk.Label(playlist_bar, text="Lista", style="Muted.TLabel").pack(side="left", padx=(0, 10))
        self.gallery_playlist_var = tk.StringVar(value="Ninguna")
        self.gallery_playlist_combo = ttk.Combobox(
            playlist_bar, textvariable=self.gallery_playlist_var, values=["Ninguna"], state="readonly", width=18
        )
        self.gallery_playlist_combo.pack(side="left")
        move_button = RoundedButton(playlist_bar, "≡", self.change_gallery_playlist, "Soft.TButton", width=42, height=34)
        move_button.pack(side="left", padx=(7, 0))
        ToolTip(move_button, "Cambiar la lista del vídeo seleccionado")
        self.gallery_action_widgets.extend([self.gallery_playlist_combo, move_button])

        privacy_bar = playlist_bar
        ttk.Label(privacy_bar, text="Privacidad", style="Muted.TLabel").pack(side="left", padx=(18, 8))
        self.gallery_privacy_var = tk.StringVar(value="Oculto")
        gallery_privacy_combo = ttk.Combobox(
            privacy_bar,
            textvariable=self.gallery_privacy_var,
            values=("Privado", "Oculto", "Público"),
            state="readonly",
            width=14,
        )
        gallery_privacy_combo.pack(side="left")
        privacy_button = RoundedButton(
            privacy_bar, "✓", self.change_gallery_privacy, "HeaderAccentIcon.TButton", width=42, height=34
        )
        privacy_button.pack(side="left", padx=(7, 0))
        ToolTip(gallery_privacy_combo, "Privacidad para los vídeos seleccionados")
        ToolTip(privacy_button, "Aplicar privacidad a la selección")
        self.gallery_action_widgets.extend([gallery_privacy_combo, privacy_button])

        loading_frame = ttk.Frame(self.gallery_tab, padding=(12, 9), style="Panel.TFrame")
        loading_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(loading_frame, textvariable=self.gallery_loading_var, style="PanelMuted.TLabel").pack(side="left")
        self.gallery_loading_progress = ttk.Progressbar(loading_frame, mode="indeterminate", length=180)
        self.gallery_loading_progress.pack(side="right", fill="x", expand=True, padx=(12, 0))
        loading_frame.pack_forget()
        self.gallery_loading_frame = loading_frame

        table_frame = ttk.Frame(self.gallery_tab)
        table_frame.pack(fill="both", expand=True)
        columns = ("titulo", "duracion", "privacidad", "listas", "fecha", "youtube")
        self.gallery_table = ttk.Treeview(table_frame, columns=columns, show="headings", height=5, selectmode="extended")
        for key, label, width in [
            ("titulo", "Título", 330),
            ("duracion", "Duración", 90),
            ("privacidad", "Privacidad", 105),
            ("listas", "Listas", 280),
            ("fecha", "Publicado", 115),
            ("youtube", "YouTube", 220),
        ]:
            self.gallery_table.heading(key, text=label)
            self.gallery_table.column(key, width=width, anchor="w")
        self.enable_tree_sorting(self.gallery_table)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.gallery_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.gallery_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        xscrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.gallery_table.xview)
        xscrollbar.grid(row=1, column=0, sticky="ew")
        self.gallery_table.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)
        self.gallery_table.tag_configure("public", foreground="#64d879")
        self.gallery_table.tag_configure("unlisted", foreground="#3ea6ff")
        self.gallery_table.tag_configure("private", foreground="#f6b73c")
        self.gallery_table.tag_configure("duplicate", background="#351515")
        self.gallery_table.tag_configure("loading", foreground="#f6b73c")
        self.gallery_table.bind("<Double-1>", lambda _event: self.open_gallery_video())
        self.gallery_table.bind("<<TreeviewSelect>>", self.on_gallery_selection)

    def enable_tree_sorting(self, tree: ttk.Treeview) -> None:
        tree.sort_reverse = {}
        tree.sort_active_column = None
        tree.sort_labels = {column: tree.heading(column, "text") for column in tree["columns"]}
        for column in tree["columns"]:
            tree.heading(column, anchor="center", command=lambda selected=column, target=tree: self.sort_treeview(target, selected))
            tree.column(column, anchor="center", stretch=False)
        tree.bind("<Configure>", lambda event, target=tree: self.resize_treeview_columns(target, event.width), add="+")
        self.fit_treeview_columns(tree)

    def fit_treeview_columns(self, tree: ttk.Treeview) -> None:
        font = tkfont.nametofont("TkDefaultFont")
        maximums = {
            "titulo": 360, "nombre": 320, "archivo": 340, "ruta": 340, "detalle": 360,
            "listas": 280, "youtube": 230, "fecha": 150, "creado": 160,
            "privacidad": 120, "duracion": 105, "tamano": 115, "estado": 135,
        }
        rows = tree.get_children("")[:500]
        natural_widths = {}
        for column in tree["columns"]:
            label = getattr(tree, "sort_labels", {}).get(column, tree.heading(column, "text"))
            measured = font.measure(label) + 30
            for item_id in rows:
                measured = max(measured, font.measure(str(tree.set(item_id, column))) + 24)
            width = min(maximums.get(column, 240), max(72, measured))
            natural_widths[column] = width
        tree.natural_column_widths = natural_widths
        self.resize_treeview_columns(tree)

    def resize_treeview_columns(self, tree: ttk.Treeview, container_width: int | None = None) -> None:
        available = (container_width if container_width is not None else tree.winfo_width()) - 4
        if available < 100:
            return
        columns = list(tree["columns"])
        natural = getattr(tree, "natural_column_widths", {})
        if not columns or not natural:
            return
        wide_columns = {"titulo", "nombre", "archivo", "ruta", "detalle", "listas", "youtube"}
        minimum = {column: 110 if column in wide_columns else 72 for column in columns}
        minimum_total = sum(minimum.values())
        natural_total = sum(natural.get(column, minimum[column]) for column in columns)
        if available <= minimum_total:
            widths = minimum.copy()
        elif available < natural_total:
            ratio = (available - minimum_total) / max(1, natural_total - minimum_total)
            widths = {
                column: round(minimum[column] + (natural.get(column, minimum[column]) - minimum[column]) * ratio)
                for column in columns
            }
        else:
            extra = available - natural_total
            widths = {
                column: natural.get(column, minimum[column]) + round(extra * natural.get(column, 1) / natural_total)
                for column in columns
            }
        widths[columns[-1]] += available - sum(widths.values())
        for column in columns:
            tree.column(
                column, width=max(minimum[column], widths[column]), minwidth=minimum[column],
                anchor="center", stretch=False,
            )

    def sort_treeview(self, tree: ttk.Treeview, column: str, descending: bool | None = None) -> None:
        if descending is None:
            descending = not tree.sort_reverse.get(column, True)
        tree.sort_reverse[column] = descending
        tree.sort_active_column = column

        def sort_key(item_id: str):
            value = tree.set(item_id, column)
            if column == "tamano":
                return size_value(value)
            if column == "duracion":
                return duration_value(value)
            return value.casefold()

        rows = sorted(tree.get_children(""), key=sort_key, reverse=descending)
        for index, item_id in enumerate(rows):
            tree.move(item_id, "", index)
        for heading in tree["columns"]:
            label = tree.sort_labels[heading]
            if heading == column:
                label += " ▼" if descending else " ▲"
            tree.heading(heading, text=label)

    def reapply_tree_sort(self, tree: ttk.Treeview) -> None:
        column = getattr(tree, "sort_active_column", None)
        if column:
            self.sort_treeview(tree, column, tree.sort_reverse.get(column, False))

    def build_console_tab(self) -> None:
        toolbar = ttk.Frame(self.console_tab)
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Label(toolbar, text="Consola", style="Title.TLabel").pack(side="left")
        clear_console_button = RoundedButton(toolbar, "⌫", self.clear_console, "HeaderIcon.TButton", width=42, height=36)
        clear_console_button.pack(side="right")
        ToolTip(clear_console_button, "Limpiar consola")
        self.log_box = tk.Text(
            self.console_tab,
            height=12,
            wrap="word",
            state="disabled",
            bg="#0b0b0b",
            fg="#d7d7d7",
            insertbackground="#ffffff",
            selectbackground="#5a1b27",
            relief="flat",
            padx=16,
            pady=14,
            font=("Cascadia Mono", 9),
        )
        self.log_box.pack(fill="both", expand=True)

    def clear_console(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.status_var.set("Consola limpiada")

    def on_main_tab_changed(self, _event=None) -> None:
        if self.notebook.select() == str(self.gallery_tab) and not self.gallery_loaded and not self.gallery_loading:
            self.refresh_channel_gallery()

    def set_gallery_loading(self, loading: bool, message: str = "") -> None:
        self.gallery_loading = loading
        self.configure(cursor="watch" if loading else "")
        if loading:
            self.gallery_loading_var.set(message or "Cargando canal...")
            if hasattr(self, "gallery_loading_frame") and not self.gallery_loading_frame.winfo_ismapped():
                self.gallery_loading_frame.pack(fill="x", pady=(0, 8), before=self.gallery_table.master)
            if self.gallery_loading_progress:
                self.gallery_loading_progress.start(12)
            if hasattr(self, "gallery_table"):
                for item in self.gallery_table.get_children():
                    self.gallery_table.delete(item)
                self.gallery_rows_by_id = {}
                self.gallery_table.insert(
                    "", "end", iid="gallery:loading",
                    values=("Cargando canal...", "—", "—", "—", "—", "—"),
                    tags=("loading",),
                )
        else:
            if self.gallery_loading_progress:
                self.gallery_loading_progress.stop()
            if hasattr(self, "gallery_loading_frame") and self.gallery_loading_frame.winfo_ismapped():
                self.gallery_loading_frame.pack_forget()
            if hasattr(self, "gallery_table") and self.gallery_table.exists("gallery:loading"):
                self.gallery_table.delete("gallery:loading")
        for widget in getattr(self, "gallery_action_widgets", []):
            try:
                if isinstance(widget, RoundedButton):
                    widget.configure(state="disabled" if loading else "normal")
                elif isinstance(widget, ttk.Combobox):
                    widget.configure(state="disabled" if loading else "readonly")
                elif isinstance(widget, ttk.Entry):
                    widget.configure(state="disabled" if loading else "normal")
            except tk.TclError:
                pass
        self.update_idletasks()

    def refresh_channel_gallery(self, force: bool = False) -> None:
        if self.gallery_loading:
            return
        if self.youtube_requests_blocked_by_quota():
            self.gallery_summary_var.set("Canal en espera hasta que se renueve la cuota de YouTube")
            return
        if not self.config.client_secret_path or not Path(self.config.client_secret_path).exists():
            messagebox.showerror(APP_NAME, "Configura primero el JSON OAuth de YouTube.")
            return
        self.gallery_summary_var.set("Cargando vídeos y listas del canal...")
        self.set_health("warn", "Cargando canal de YouTube...")
        self.set_gallery_loading(True, "Consultando YouTube...")
        threading.Thread(target=self._refresh_channel_gallery_thread, daemon=True).start()

    def _refresh_channel_gallery_thread(self) -> None:
        try:
            client = YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", f"[{now_text()}] {text}")))
            videos, playlists = client.channel_gallery()
            self.events.put(("gallery_rows", {"videos": videos, "playlists": playlists}))
        except Exception as exc:
            self.events.put(("gallery_error", f"No se pudo cargar el canal: {describe_error(exc)}"))

    def apply_gallery_rows(self, payload: dict) -> None:
        self.gallery_all_videos = list(payload.get("videos", []))
        self.gallery_playlists_by_label = {"Ninguna": ""}
        self.gallery_playlist_labels_by_id = {"": "Ninguna"}
        self.gallery_filter_playlists_by_label = {"Todas": None, "Sin lista": ""}
        used_labels = {"Ninguna"}
        for playlist in payload.get("playlists", []):
            playlist_id = playlist.get("id", "")
            if not playlist_id:
                continue
            base_label = playlist.get("title", "Lista sin nombre")
            label = base_label
            if label in used_labels:
                label = f"{base_label} · {playlist_id[-6:]}"
            used_labels.add(label)
            self.gallery_playlists_by_label[label] = playlist_id
            self.gallery_playlist_labels_by_id[playlist_id] = label
            self.gallery_filter_playlists_by_label[label] = playlist_id
        self.gallery_playlist_combo.configure(values=list(self.gallery_playlists_by_label.keys()))
        self.gallery_playlist_filter_combo.configure(values=list(self.gallery_filter_playlists_by_label.keys()))
        if self.gallery_playlist_filter_var.get() not in self.gallery_filter_playlists_by_label:
            self.gallery_playlist_filter_var.set("Todas")
        self.gallery_loaded = True
        self.set_gallery_loading(False)
        if self.gallery_find_duplicates_pending or self.gallery_duplicates_only:
            self.gallery_find_duplicates_pending = False
            self.gallery_duplicates_only = False
            self.find_channel_duplicates()
        else:
            self.filter_gallery_rows()
        self.set_health("ok", f"Canal cargado: {len(self.gallery_all_videos)} vídeo(s)")

    def render_gallery_rows(self, videos: list[dict]) -> None:
        for item in self.gallery_table.get_children():
            self.gallery_table.delete(item)
        self.gallery_rows_by_id = {}
        privacy_labels = {"public": "Público", "unlisted": "Oculto", "private": "Privado"}
        for video in videos:
            video_id = video["id"]
            memberships = video.get("memberships", [])
            playlist_text = ", ".join(item.get("playlist_title", "") for item in memberships if item.get("playlist_title")) or "Sin lista"
            privacy = video.get("privacy", "desconocido")
            published = video.get("published_at", "")[:10]
            item_id = f"gallery:{video_id}"
            self.gallery_table.insert(
                "", "end", iid=item_id,
                values=(
                    video.get("title", "Sin título"), video.get("duration", "—"),
                    privacy_labels.get(privacy, privacy), playlist_text, published,
                    f"https://youtu.be/{video_id}",
                ),
                tags=tuple(
                    tag for tag in (
                        privacy if privacy in {"public", "unlisted", "private"} else "",
                        "duplicate" if video_id in self.gallery_duplicate_ids else "",
                    ) if tag
                ),
            )
            self.gallery_rows_by_id[item_id] = video
        self.fit_treeview_columns(self.gallery_table)
        self.reapply_tree_sort(self.gallery_table)

    def filter_gallery_rows(self, *_args) -> None:
        if not hasattr(self, "gallery_table"):
            return
        query = self.gallery_search_var.get().strip().casefold()
        date_query = self.normalize_gallery_date(self.gallery_date_filter_var.get())
        date_source = self.gallery_date_source_var.get()
        privacy = {
            "Público": "public", "Oculto": "unlisted", "Privado": "private",
        }.get(self.gallery_privacy_filter_var.get())
        playlist = self.gallery_filter_playlists_by_label.get(self.gallery_playlist_filter_var.get())
        filtered = []
        for video in self.gallery_all_videos:
            memberships = video.get("memberships", [])
            playlist_ids = {item.get("playlist_id", "") for item in memberships}
            searchable = " ".join([
                video.get("title", ""), video.get("id", ""),
                *(item.get("playlist_title", "") for item in memberships),
            ]).casefold()
            if query and query not in searchable:
                continue
            if self.gallery_duplicates_only and video.get("id") not in self.gallery_duplicate_ids:
                continue
            if date_query:
                title_date = self.normalize_gallery_date(video.get("title", ""))
                published_date = self.normalize_gallery_date(video.get("published_at", ""))
                if date_source == "Título" and date_query not in title_date:
                    continue
                if date_source == "Publicado" and date_query not in published_date:
                    continue
                if date_source == "Título o publicación" and date_query not in title_date and date_query not in published_date:
                    continue
            if privacy and video.get("privacy") != privacy:
                continue
            if playlist == "" and memberships:
                continue
            if playlist not in (None, "") and playlist not in playlist_ids:
                continue
            filtered.append(video)
        self.render_gallery_rows(filtered)
        if self.gallery_duplicates_only:
            self.gallery_summary_var.set(
                f"{len(filtered)} vídeo(s) en {self.gallery_duplicate_groups} grupo(s) duplicado(s)"
            )
        else:
            self.gallery_summary_var.set(f"{len(filtered)} de {len(self.gallery_all_videos)} vídeo(s)")

    def find_channel_duplicates(self) -> None:
        if self.gallery_loading:
            self.gallery_find_duplicates_pending = True
            return
        if not self.gallery_loaded:
            self.gallery_find_duplicates_pending = True
            self.refresh_channel_gallery(True)
            return
        if self.gallery_duplicates_only:
            self.gallery_duplicates_only = False
            self.gallery_duplicate_ids.clear()
            self.gallery_duplicate_groups = 0
            self.filter_gallery_rows()
            return
        self.update_gallery_duplicate_index()
        if not self.gallery_duplicate_ids:
            self.gallery_duplicates_only = False
            messagebox.showinfo("Buscar duplicados", "No se encontraron vídeos con el mismo título en el canal.")
            self.filter_gallery_rows()
            return
        self.gallery_duplicates_only = True
        self.filter_gallery_rows()

    def update_gallery_duplicate_index(self) -> None:
        groups: dict[str, list[dict]] = {}
        for video in self.gallery_all_videos:
            normalized_title = re.sub(r"\s+", " ", video.get("title", "").strip()).casefold()
            if normalized_title:
                groups.setdefault(normalized_title, []).append(video)
        duplicate_groups = [videos for videos in groups.values() if len(videos) > 1]
        self.gallery_duplicate_ids = {
            video["id"] for videos in duplicate_groups for video in videos if video.get("id")
        }
        self.gallery_duplicate_groups = len(duplicate_groups)

    @staticmethod
    def normalize_gallery_date(value: str) -> str:
        return value.strip().casefold().replace(".", "-").replace("/", "-").replace("_", "-")

    def clear_gallery_filters(self) -> None:
        self.gallery_search_var.set("")
        self.gallery_privacy_filter_var.set("Todas")
        self.gallery_playlist_filter_var.set("Todas")
        self.gallery_date_filter_var.set("")
        self.gallery_date_source_var.set("Título o publicación")
        self.gallery_duplicates_only = False
        self.gallery_duplicate_ids.clear()
        self.gallery_duplicate_groups = 0
        self.filter_gallery_rows()

    def selected_gallery_video(self) -> dict | None:
        videos = self.selected_gallery_videos()
        return videos[0] if videos else None

    def selected_gallery_videos(self) -> list[dict]:
        return [
            self.gallery_rows_by_id[item_id]
            for item_id in self.gallery_table.selection()
            if item_id in self.gallery_rows_by_id
        ]

    def on_gallery_selection(self, _event=None) -> None:
        video = self.selected_gallery_video()
        if not video:
            return
        memberships = video.get("memberships", [])
        if len(memberships) == 1:
            playlist_id = memberships[0].get("playlist_id", "")
            self.gallery_playlist_var.set(self.gallery_playlist_labels_by_id.get(playlist_id, "Ninguna"))
        else:
            self.gallery_playlist_var.set("Ninguna")

    def open_gallery_video(self) -> None:
        video = self.selected_gallery_video()
        if not video:
            messagebox.showinfo(APP_NAME, "Selecciona primero un vídeo del canal.")
            return
        webbrowser.open(f"https://youtu.be/{video['id']}")

    def open_gallery_download(self) -> None:
        video = self.selected_gallery_video()
        if not video:
            messagebox.showinfo(APP_NAME, "Selecciona primero un vídeo del canal.")
            return
        webbrowser.open(f"https://studio.youtube.com/video/{video['id']}/edit")

    def share_gallery_video(self) -> None:
        video = self.selected_gallery_video()
        if not video:
            messagebox.showinfo(APP_NAME, "Selecciona primero un vídeo del canal.")
            return
        if not ask_confirmation(
            "Compartir vídeo",
            "Vas a preparar este vídeo para compartirlo.",
            [f"Cambiar '{video['title']}' a Oculto", "Copiar su enlace al portapapeles"],
            ["El título y las listas de reproducción"],
        ):
            return
        self.gallery_summary_var.set("Actualizando privacidad...")
        threading.Thread(target=self._share_gallery_video_thread, args=(video,), daemon=True).start()

    def _share_gallery_video_thread(self, video: dict) -> None:
        try:
            client = YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", f"[{now_text()}] {text}")))
            client.set_video_unlisted(video["id"])
            self.events.put(("gallery_shared", video))
        except Exception as exc:
            self.events.put(("gallery_error", f"No se pudo compartir el vídeo: {describe_error(exc)}"))

    def change_gallery_privacy(self) -> None:
        videos = self.selected_gallery_videos()
        if not videos:
            messagebox.showinfo(APP_NAME, "Selecciona uno o varios vídeos del canal.")
            return
        label = self.gallery_privacy_var.get()
        privacy = PRIVACY_VALUES.get(label)
        if not privacy:
            messagebox.showerror(APP_NAME, "Selecciona una privacidad válida.")
            return
        if not ask_confirmation(
            "Cambiar privacidad",
            "Vas a cambiar la visibilidad de los vídeos seleccionados.",
            [f"Aplicar {label} a {len(videos)} vídeo(s)"],
            ["Los títulos y las listas de reproducción"],
        ):
            return
        self.gallery_summary_var.set(f"Actualizando privacidad de {len(videos)} vídeo(s)...")
        threading.Thread(
            target=self._change_gallery_privacy_thread, args=(videos, privacy), daemon=True
        ).start()

    def _change_gallery_privacy_thread(self, videos: list[dict], privacy: str) -> None:
        updated = []
        errors = []
        try:
            client = YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", f"[{now_text()}] {text}")))
        except Exception as exc:
            self.events.put(("gallery_error", f"No se pudo iniciar el cambio de privacidad: {describe_error(exc)}"))
            return
        for video in videos:
            try:
                client.set_video_privacy(video["id"], privacy)
                updated.append(video)
            except Exception as exc:
                errors.append(f"{video.get('title', video.get('id', 'Vídeo'))}: {describe_error(exc)}")
        self.events.put(("gallery_privacy_changed", {"updated": updated, "privacy": privacy, "errors": errors}))

    def delete_gallery_video(self) -> None:
        videos = self.selected_gallery_videos()
        if not videos:
            messagebox.showinfo(APP_NAME, "Selecciona uno o varios vídeos del canal.")
            return
        delete_details = [f"Eliminar definitivamente {len(videos)} vídeo(s) de YouTube"]
        delete_details.extend(f"{video['title']}" for video in videos[:5])
        if len(videos) > 5:
            delete_details.append(f"Y {len(videos) - 5} vídeo(s) más")
        if not ask_confirmation(
            "Eliminar vídeos de YouTube",
            "Vas a borrar los vídeos seleccionados del canal.",
            delete_details,
            warning="Esta acción no se puede deshacer.",
            question="¿Eliminar los vídeos seleccionados?",
        ):
            return
        self.gallery_summary_var.set(f"Borrando {len(videos)} vídeo(s) de YouTube...")
        threading.Thread(target=self._delete_gallery_video_thread, args=(videos,), daemon=True).start()

    def _delete_gallery_video_thread(self, videos: list[dict]) -> None:
        deleted = []
        errors = []
        try:
            client = YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", f"[{now_text()}] {text}")))
        except Exception as exc:
            self.events.put(("gallery_error", f"No se pudo iniciar el borrado: {describe_error(exc)}"))
            return
        for video in videos:
            try:
                client.delete_video(video["id"])
                deleted.append(video)
            except Exception as exc:
                errors.append(f"{video.get('title', video.get('id', 'Vídeo'))}: {describe_error(exc)}")
        self.events.put(("gallery_deleted", {"deleted": deleted, "errors": errors}))

    def change_gallery_playlist(self) -> None:
        video = self.selected_gallery_video()
        if not video:
            messagebox.showinfo(APP_NAME, "Selecciona primero un vídeo del canal.")
            return
        label = self.gallery_playlist_var.get()
        target_id = self.gallery_playlists_by_label.get(label, "")
        if not ask_confirmation(
            "Cambiar lista de reproducción",
            "Vas a cambiar la organización de este vídeo.",
            [f"Quitar sus listas actuales", f"Asignar '{video['title']}' a: {label}"],
            ["La privacidad y el título"],
        ):
            return
        self.gallery_summary_var.set("Actualizando lista de reproducción...")
        threading.Thread(target=self._change_gallery_playlist_thread, args=(video, target_id), daemon=True).start()

    def _change_gallery_playlist_thread(self, video: dict, target_id: str) -> None:
        try:
            client = YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", f"[{now_text()}] {text}")))
            client.replace_video_playlist(video["id"], video.get("memberships", []), target_id)
            self.events.put(("gallery_playlist_changed", "Lista actualizada correctamente."))
        except Exception as exc:
            self.events.put(("gallery_error", f"No se pudo cambiar la lista: {describe_error(exc)}"))

    def load_logo(self) -> None:
        logo = resource_path("assets/youtube-sync-logo.png")
        if Image and ImageTk and logo.exists():
            image = Image.open(logo)
            image.thumbnail((52, 52))
            self.logo_image = ImageTk.PhotoImage(image)
            self.logo_label.configure(image=self.logo_image)

    def refresh_config_text(self) -> None:
        folder = self.config.watch_folder or "Sin configurar"
        folder_label = compact_path(folder)
        category = CATEGORY_NAMES_BY_ID.get(self.config.category_id, self.config.category_id)
        playlist = self.config.playlist_name if self.config.playlist_id else "Sin lista"
        cleanup = f"Limpieza auto: {self.config.auto_delete_delay_label}" if self.config.auto_delete_uploaded else "Limpieza auto: no"
        oauth_ok = bool(self.config.client_secret_path.strip())
        folder_ok = bool(self.config.watch_folder and Path(self.config.watch_folder).exists())
        if folder_ok and oauth_ok:
            color, icon, main = "#22c55e", "✓", "Listo"
        elif folder_ok:
            color, icon, main = "#f59e0b", "!", "Falta OAuth"
        else:
            color, icon, main = "#ef4444", "!", "Falta carpeta"
        self.set_card(self.folder_card, main, f"{folder_label} · {category} · {playlist} · {cleanup}", color, icon)
        if not self.config.watch_folder or not Path(self.config.watch_folder).exists():
            self.set_health("error", "Falta configurar una carpeta valida")

    def open_config(self, first_run: bool = False) -> None:
        dialog = ConfigDialog(self, self.config, first_run=first_run)
        self.wait_window(dialog)
        if dialog.result:
            self.config = dialog.result
            self.store.save_config(self.config)
            if first_run:
                self.auto_enabled = self.config.auto_start_enabled and self.upload_limit_state is None
                self.auto_button.configure(
                    text="Auto ON" if self.auto_enabled else "Auto OFF",
                    style="Success.TButton" if self.auto_enabled else "Danger.TButton",
                )
            try:
                set_run_at_startup(self.config.run_at_startup)
            except OSError as exc:
                messagebox.showwarning(APP_NAME, f"No se pudo actualizar el inicio con Windows:\n{exc}")
            self.refresh_config_text()
            self.start_worker()
            self.log("Configuracion guardada.")
            self.check_youtube_connection()
            self.refresh_folder_contents()
            if self.auto_enabled:
                self.scan_now()

    def start_worker(self) -> None:
        if self.worker and self.worker.is_alive():
            self.worker.set_enabled(self.auto_enabled)
            self.worker.refresh()
            return
        self.worker = SyncWorker(self.store, lambda: self.config, self.events)
        self.worker.start()
        self.worker.set_enabled(self.auto_enabled)

    def toggle_auto_mode(self) -> None:
        if not self.auto_enabled and self.youtube_requests_blocked_by_quota():
            return
        self.auto_enabled = not self.auto_enabled
        self.start_worker()
        if self.worker:
            self.worker.set_enabled(self.auto_enabled)
        if self.auto_enabled:
            self.auto_button.configure(text="Auto ON", style="Success.TButton")
            self.set_health("warn", "Modo automatico activo")
            self.log("Modo automatico activado.")
            self.scan_now()
        else:
            self.auto_button.configure(text="Auto OFF", style="Danger.TButton")
            self.set_card(self.progress_card, "Pausado", "Auto OFF", "#f59e0b", "⏸")
            self.set_health("warn", "Modo automatico pausado")
            self.log("Modo automatico pausado.")

    def refresh_all(self) -> None:
        self.check_youtube_connection()
        self.refresh_folder_contents()
        if self.auto_enabled:
            self.scan_now()
        else:
            self.log("Actualizado YouTube y carpeta. Auto esta pausado; no se subiran videos.")

    def scan_now(self) -> None:
        if not self.auto_enabled:
            self.log("Auto esta pausado. No se escanea ni se sube hasta activarlo.")
            self.set_health("warn", "Modo automatico pausado")
            return
        self.start_worker()
        if self.worker:
            self.worker.refresh()
        self.log("Recarga de carpeta solicitada.")
        self.set_health("warn", "Revisando carpeta...")

    def upload_pending_now(self) -> None:
        if self.youtube_requests_blocked_by_quota():
            return
        if not self.auto_enabled:
            self.auto_enabled = True
            self.auto_button.configure(text="Auto ON", style="Success.TButton")
            self.set_health("warn", "Modo automatico activo")
        self.start_worker()
        if self.worker:
            self.worker.set_enabled(True)
            self.worker.refresh()
        self.refresh_folder_contents()
        self.log("Subida de pendientes solicitada.")

    def upload_selected_pending(self) -> None:
        if self.youtube_requests_blocked_by_quota():
            return
        item = self.selected_incident()
        if not item:
            messagebox.showinfo(APP_NAME, "Selecciona primero un video pendiente.")
            return
        if item["status"] in {"Subiendo", "Procesando"}:
            messagebox.showinfo(APP_NAME, "Este video ya se esta subiendo o procesando en YouTube.")
            return
        path = Path(item["path"])
        if not path.exists():
            messagebox.showwarning(APP_NAME, "El archivo seleccionado ya no existe.")
            return
        if self.store.has_success(item["signature"]):
            messagebox.showinfo(APP_NAME, "Este video ya esta protegido por el registro permanente. Se comprobara YouTube.")
            self.refresh_folder_contents(verify_youtube=True)
            return
        self.start_worker()
        if self.worker:
            self.worker.upload_path(path)
        self.set_card(self.progress_card, "En cola", compact_path(path.name, 34), "#3b82f6", "↑")
        self.set_health("warn", "Subida manual preparada")
        self.log(f"Subida manual solicitada solo para {path.name}.")

    def youtube_requests_blocked_by_quota(self) -> bool:
        if not self.upload_limit_state:
            return False
        try:
            retry_at = datetime.fromisoformat(self.upload_limit_state["retry_at"])
            if retry_at <= datetime.now().astimezone():
                return False
            remaining = remaining_text(retry_at)
            messagebox.showwarning(
                "Cuota de YouTube agotada",
                f"YouTube no acepta nuevas peticiones para este proyecto.\n\n"
                f"Reintento automático estimado: {retry_at.astimezone().strftime('%d/%m/%Y %H:%M')}\n"
                f"Tiempo restante: {remaining}",
            )
            return True
        except (KeyError, TypeError, ValueError):
            return False

    def cancel_upload(self) -> None:
        self.auto_enabled = False
        self.auto_button.configure(text="Auto OFF", style="Danger.TButton")
        if self.worker:
            self.worker.cancel_upload()
            self.worker.set_enabled(False)
        self.set_card(self.progress_card, "Cancelando", "Deteniendo subida", "#ef4444", "!")
        self.set_health("warn", "Subida cancelada · Auto OFF")
        self.log("Auto se ha pausado para impedir que el video cancelado vuelva a subirse automaticamente.")

    def check_youtube_connection(self) -> None:
        if self.upload_limit_state:
            self.set_card(self.youtube_card, "En espera", "Cuota del proyecto", "#f59e0b", "!")
            return
        self.set_card(self.youtube_card, "Comprobando", "YouTube", "#f59e0b", "●")
        self.set_health("warn", "Comprobando conexion con YouTube...")
        threading.Thread(target=self._check_youtube_connection_thread, daemon=True).start()

    def _check_youtube_connection_thread(self) -> None:
        path = self.config.client_secret_path.strip()
        if not path:
            self.events.put(("youtube_error", "No hay JSON OAuth configurado."))
            return
        if not Path(path).exists():
            self.events.put(("youtube_error", "No existe el JSON OAuth configurado."))
            return
        try:
            client = YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", f"[{now_text()}] {text}")), path)
            info = client.channel_info()
            self.events.put(("youtube", info))
        except Exception as exc:
            self.events.put(("youtube_error", describe_error(exc)))

    def log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{now_text()}] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.status_var.set(text)

    def process_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.log_box.configure(state="normal")
                    self.log_box.insert("end", value + "\n")
                    self.log_box.see("end")
                    self.log_box.configure(state="disabled")
                    self.status_var.set(value.split("] ", 1)[-1])
                elif kind == "progress":
                    self.progress_var.set(value["percent"])
                    filename = value["filename"] or "Sin actividad"
                    if value["filename"]:
                        self.set_card(self.progress_card, f"{value['percent']}%", compact_path(filename, 34), "#3b82f6", "↑")
                    else:
                        self.set_card(self.progress_card, "Sin actividad", "Esperando videos", "#9ca3af", "●")
                elif kind == "busy":
                    self.busy = bool(value)
                elif kind == "upload_completed":
                    if value.get("quota_cleared"):
                        self.upload_limit_state = None
                    self.refresh_folder_contents(verify_youtube=False)
                elif kind == "folder_refresh":
                    self.refresh_folder_contents(verify_youtube=bool(value))
                elif kind == "cleanup_warning":
                    if ask_confirmation(
                        "Revisar limpieza",
                        value,
                        ["Abrir la lista de vídeos ya subidos para revisarla"],
                        question="¿Abrir la revisión ahora?",
                    ):
                        self.notebook.select(self.videos_tab)
                        self.videos_notebook.select(self.uploaded_tab)
                        self.refresh_folder_contents()
                elif kind == "gallery_rows":
                    self.apply_gallery_rows(value)
                elif kind == "gallery_shared":
                    url = f"https://youtu.be/{value['id']}"
                    self.clipboard_clear()
                    self.clipboard_append(url)
                    value["privacy"] = "unlisted"
                    item_id = f"gallery:{value['id']}"
                    if self.gallery_table.exists(item_id):
                        self.gallery_table.set(item_id, "privacidad", "Oculto")
                        self.gallery_table.item(item_id, tags=("unlisted",))
                    self.gallery_summary_var.set("Vídeo en Oculto · enlace copiado")
                elif kind == "gallery_playlist_changed":
                    messagebox.showinfo(APP_NAME, value)
                    self.gallery_loaded = False
                    self.refresh_channel_gallery(True)
                elif kind == "gallery_privacy_changed":
                    privacy = value["privacy"]
                    label = PRIVACY_LABELS.get(privacy, privacy)
                    for video in value["updated"]:
                        video["privacy"] = privacy
                    self.filter_gallery_rows()
                    changed = len(value["updated"])
                    failed = len(value["errors"])
                    self.gallery_summary_var.set(f"{changed} vídeo(s) actualizado(s) a {label}")
                    if failed:
                        details = "\n".join(value["errors"][:5])
                        messagebox.showwarning(
                            APP_NAME,
                            f"Se actualizaron {changed} vídeo(s), pero fallaron {failed}:\n\n{details}",
                        )
                    else:
                        messagebox.showinfo(APP_NAME, f"Privacidad actualizada a {label} en {changed} vídeo(s).")
                elif kind == "gallery_deleted":
                    deleted_ids = {video.get("id") for video in value["deleted"]}
                    self.gallery_all_videos = [
                        video for video in self.gallery_all_videos if video.get("id") not in deleted_ids
                    ]
                    if self.gallery_duplicates_only:
                        self.update_gallery_duplicate_index()
                        if not self.gallery_duplicate_ids:
                            self.gallery_duplicates_only = False
                    self.filter_gallery_rows()
                    deleted = len(value["deleted"])
                    failed = len(value["errors"])
                    self.gallery_summary_var.set(f"{deleted} vídeo(s) eliminado(s) del canal")
                    if failed:
                        details = "\n".join(value["errors"][:5])
                        messagebox.showwarning(
                            APP_NAME,
                            f"Se eliminaron {deleted} vídeo(s), pero fallaron {failed}:\n\n{details}",
                        )
                    else:
                        messagebox.showinfo(APP_NAME, f"Se eliminaron {deleted} vídeo(s) del canal.")
                elif kind == "gallery_error":
                    self.set_gallery_loading(False)
                    self.gallery_summary_var.set(value)
                    self.set_health("error", "No se pudo cargar el canal")
                    messagebox.showerror(APP_NAME, value)
                elif kind == "incident_reset":
                    self.log(value)
                    messagebox.showinfo(APP_NAME, value)
                    self.refresh_folder_contents(verify_youtube=True)
                elif kind == "incident_error":
                    self.log(value)
                    messagebox.showerror(APP_NAME, value)
                elif kind == "upload_limited":
                    self.upload_limit_state = value
                    self.auto_enabled = False
                    self.auto_button.configure(text="Auto OFF", style="Danger.TButton")
                    retry_at = datetime.fromisoformat(value["retry_at"])
                    remaining = remaining_text(retry_at)
                    self.set_card(self.progress_card, "Limite de YouTube", f"Reintento en {remaining}", "#ef4444", "!")
                    self.log(f"{value['message']} Reintento {value['source']}: {retry_at.astimezone().strftime('%d/%m/%Y %H:%M')}.")
                    self.set_health("error", f"Limite de YouTube: reintento en {remaining}")
                elif kind == "youtube_quota_detected":
                    self.upload_limit_state = value
                    self.auto_enabled = False
                    self.auto_button.configure(text="Auto OFF", style="Danger.TButton")
                    if self.worker:
                        self.worker.pause_after_current()
                    retry_at = datetime.fromisoformat(value["retry_at"])
                    remaining = remaining_text(retry_at)
                    self.set_card(self.progress_card, "Cuota del proyecto", f"Reintento en {remaining}", "#ef4444", "!")
                    self.set_health("error", f"Cuota del proyecto: reintento en {remaining}")
                elif kind == "folder_rows":
                    self.apply_folder_rows(value)
                    self.folder_refresh_running = False
                    if self.folder_refresh_pending:
                        verify = self.folder_refresh_verify_pending
                        self.folder_refresh_pending = False
                        self.folder_refresh_verify_pending = False
                        self.after_idle(lambda verify=verify: self.refresh_folder_contents(verify_youtube=verify))
                elif kind == "youtube":
                    category = CATEGORY_NAMES_BY_ID.get(self.config.category_id, self.config.category_id)
                    playlist = self.config.playlist_name if self.config.playlist_id else "Sin lista"
                    self.set_card(self.youtube_card, "Conectado", f"{value['title']} · {playlist}", "#22c55e", "✓")
                    self.log(f"YouTube conectado: canal {value['title']} ({value['id']}), lista {playlist}, categoria {category}.")
                    if self.config.watch_folder and Path(self.config.watch_folder).exists():
                        self.set_health("ok", "Todo funcionando correctamente")
                    else:
                        self.set_health("error", "YouTube OK, pero la carpeta no es valida")
                elif kind == "youtube_error":
                    self.set_card(self.youtube_card, "Sin conexion", "Revisa OAuth", "#ef4444", "!")
                    self.log(f"No se pudo comprobar YouTube: {value}")
                    self.set_health("error", "YouTube no conectado")
        except queue.Empty:
            pass
        except Exception as exc:
            try:
                self.log(f"La interfaz recuperó un error interno: {describe_error(exc)}")
            except Exception:
                pass
        finally:
            try:
                self.after(75, self.process_events)
            except tk.TclError:
                pass

    def refresh_folder_contents(self, verify_youtube: bool = True) -> None:
        if (self.busy or self.upload_limit_state) and verify_youtube:
            verify_youtube = False
        if self.folder_refresh_running:
            self.folder_refresh_pending = True
            self.folder_refresh_verify_pending = self.folder_refresh_verify_pending or verify_youtube
            return
        self.folder_refresh_running = True
        self.folder_summary_var.set("Revisando carpeta...")
        threading.Thread(target=self._refresh_folder_contents_thread, args=(verify_youtube,), daemon=True).start()

    def _refresh_folder_contents_thread(self, verify_youtube: bool = True) -> None:
        folder = Path(self.config.watch_folder) if self.config.watch_folder else None
        if not folder or not folder.exists():
            self.events.put(
                (
                    "folder_rows",
                    {
                        "pending_rows": [],
                        "uploaded_rows": [],
                        "other_rows": [],
                        "total": 0,
                        "uploaded": 0,
                        "pending": 0,
                        "active": 0,
                        "other": 0,
                        "error": "Carpeta no valida",
                    },
                )
            )
            return

        pattern = "**/*" if self.config.recursive else "*"
        extensions = self.config.extension_set
        registry_by_signature, registry_by_path = self.store.registry_index()
        activity_by_signature, activity_by_path = self.store.upload_status_index()
        youtube_checked = False
        youtube_verifier = None
        if verify_youtube and self.config.client_secret_path and Path(self.config.client_secret_path).exists():
            try:
                verifier = YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", f"[{now_text()}] {text}")))
                verifier.uploaded_video_index(force=True)
                youtube_verifier = verifier
                youtube_checked = True
            except Exception as exc:
                if is_youtube_quota_error(exc):
                    message = youtube_error_message(exc)
                    kind, retry_at, source = youtube_retry_prediction(exc)
                    state = self.store.set_upload_limit(kind, retry_at, source, message)
                    self.events.put(("youtube_quota_detected", state))
                    self.events.put((
                        "log",
                        f"[{now_text()}] Cuota diaria del proyecto agotada. Se omiten nuevas comprobaciones "
                        f"hasta {retry_at.astimezone().strftime('%d/%m/%Y %H:%M')}; la subida activa no se cancela.",
                    ))
                else:
                    self.events.put(("log", f"[{now_text()}] No se pudo validar la lista de subidos con YouTube: {describe_error(exc)}"))
        pending_rows = []
        uploaded_rows = []
        other_rows = []
        restored_pending = 0
        filled_links = 0
        total = 0
        uploaded = 0
        pending = 0
        active = 0
        other = 0
        max_rows = 2000
        try:
            for path in folder.glob(pattern):
                if not path.is_file() or path.suffix.lower() not in extensions:
                    continue
                total += 1
                stat = path.stat()
                title = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                size_label = human_size(stat.st_size)
                created_label = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                try:
                    signature = file_signature(path)
                except OSError:
                    signature = hashlib.sha256(str(path).encode("utf-8", errors="replace")).hexdigest()
                registry_row = registry_by_signature.get(signature) or registry_by_path.get(str(path))
                activity_row = activity_by_signature.get(signature) or activity_by_path.get(str(path))
                status = registry_row[4] if registry_row else "Pendiente"
                youtube_processing = False
                youtube_failure = ""
                if registry_row and youtube_checked and status in {"uploaded", "processing", "local_deleted", "youtube_title_exists", "skipped"}:
                    registry_signature = registry_row[0]
                    registry_title = registry_row[1]
                    youtube_id = registry_row[3] or ""
                    content_matches, found_id, match_reason, remote_state = (
                        youtube_verifier.verify_local_file(path, registry_title, youtube_id)
                        if youtube_verifier else (False, "", "sin verificacion", "missing")
                    )
                    if remote_state == "processed" and content_matches:
                        if found_id != youtube_id or status == "processing":
                            self.store.update_registry_state(registry_signature, found_id, "uploaded")
                            registry_row = (registry_row[0], registry_row[1], registry_row[2], found_id, "uploaded", registry_row[5])
                            status = "uploaded"
                            filled_links += 1
                    elif remote_state == "processed" and not content_matches:
                        youtube_failure = f"El video enlazado no corresponde al archivo local: {match_reason}."
                        self.store.forget_registry(registry_signature)
                        self.store.upsert(signature, path, title, "error", youtube_id=found_id, error=youtube_failure)
                        registry_row = None
                        status = "Error"
                    elif remote_state in {"uploaded", "processing"} and content_matches:
                        youtube_processing = True
                        if found_id and (found_id != youtube_id or status != "processing"):
                            self.store.update_registry_state(registry_signature, found_id, "processing")
                            registry_row = (registry_row[0], registry_row[1], registry_row[2], found_id, "processing", registry_row[5])
                            status = "processing"
                    elif remote_state in {"uploaded", "processing"} and not content_matches:
                        youtube_failure = f"La subida asociada no corresponde al archivo local: {match_reason}."
                        self.store.forget_registry(registry_signature)
                        self.store.upsert(signature, path, title, "error", youtube_id=found_id, error=youtube_failure)
                        registry_row = None
                        status = "Error"
                    elif remote_state in {"failed", "rejected", "terminated", "deleted"}:
                        youtube_failure = f"YouTube indica que el procesamiento termino con estado: {remote_state}."
                        if content_matches and found_id and remote_state != "deleted" and youtube_verifier:
                            try:
                                youtube_verifier.delete_video(found_id)
                                youtube_failure += " El elemento fallido se elimino del canal."
                                self.events.put(("log", f"[{now_text()}] Eliminado de YouTube el video fallido {found_id}."))
                            except Exception as exc:
                                youtube_failure += f" No se pudo eliminar automaticamente: {describe_error(exc)}"
                        self.store.forget_registry(registry_signature)
                        self.store.upsert(signature, path, title, "error", youtube_id=found_id, error=youtube_failure)
                        registry_row = None
                        status = "Error"
                    else:
                        self.store.forget_registry(registry_signature)
                        registry_row = None
                        status = "Pendiente"
                        restored_pending += 1
                missing_youtube_link = bool(
                    registry_row
                    and status in {"uploaded", "processing", "local_deleted", "youtube_title_exists", "skipped"}
                    and not (registry_row[3] or "")
                )
                if youtube_failure:
                    other += 1
                    display_status = "Error YouTube"
                    status_detail = youtube_failure
                elif youtube_processing:
                    active += 1
                    display_status = "Procesando"
                    status_detail = "YouTube recibio el archivo, pero todavia no confirma que este listo."
                elif missing_youtube_link:
                    other += 1
                    display_status = "Sin enlace"
                    status_detail = "Falta verificar el ID del video con YouTube. Pulsa Actualizar para repararlo."
                elif registry_row and status in {"uploaded", "local_deleted", "youtube_title_exists", "skipped"}:
                    uploaded += 1
                    display_status = "Existe en YouTube" if status == "youtube_title_exists" else "Subido"
                    status_detail = ""
                elif registry_row and status == "processing":
                    active += 1
                    display_status = "Procesando"
                    status_detail = "YouTube recibio el archivo, pero todavia no confirma que este listo."
                elif activity_row and activity_row[3] in {"error", "cancelled", "uploading", "processing"}:
                    if activity_row[3] in {"uploading", "processing"}:
                        active += 1
                    else:
                        other += 1
                    labels = {"error": "Error", "cancelled": "Cancelado", "uploading": "Subiendo", "processing": "Procesando"}
                    display_status = labels[activity_row[3]]
                    status_detail = activity_row[4] or ""
                elif status == "Pendiente":
                    pending += 1
                    display_status = "Pendiente"
                    status_detail = ""
                else:
                    other += 1
                    display_status = status
                    status_detail = activity_row[4] if activity_row else ""
                if display_status == "Pendiente" and len(pending_rows) < max_rows:
                    pending_rows.append((signature, path.name, size_label, created_label, "Pendiente", "", str(path)))
                elif display_status in {"Subido", "Existe en YouTube"} and len(uploaded_rows) < max_rows:
                    registry_signature = registry_row[0] if registry_row else signature
                    registry_title = registry_row[1] if registry_row else title
                    youtube_id = registry_row[3] if registry_row else ""
                    updated_at = registry_row[5] if registry_row else ""
                    uploaded_rows.append(
                        (
                            registry_signature,
                            updated_at,
                            registry_title,
                            str(path),
                            size_label,
                            f"https://youtu.be/{youtube_id}" if youtube_id else "",
                            youtube_id,
                        )
                    )
                elif len(other_rows) < max_rows:
                    incident_signature = registry_row[0] if display_status == "Sin enlace" and registry_row else signature
                    other_rows.append((incident_signature, path.name, size_label, created_label, display_status, status_detail, str(path)))
        except OSError as exc:
            self.events.put(
                (
                    "folder_rows",
                    {
                        "pending_rows": pending_rows,
                        "uploaded_rows": uploaded_rows,
                        "other_rows": other_rows,
                        "total": total,
                        "uploaded": uploaded,
                        "pending": pending,
                        "active": active,
                        "other": other,
                        "error": str(exc),
                    },
                )
            )
            return
        self.events.put(
            (
                "folder_rows",
                {
                    "pending_rows": pending_rows,
                    "uploaded_rows": uploaded_rows,
                    "other_rows": other_rows,
                    "total": total,
                    "uploaded": uploaded,
                    "pending": pending,
                    "active": active,
                    "other": other,
                    "error": "",
                    "youtube_checked": youtube_checked,
                    "restored_pending": restored_pending,
                    "filled_links": filled_links,
                },
            )
        )

    def apply_folder_rows(self, payload: dict) -> None:
        for item in self.pending_table.get_children():
            self.pending_table.delete(item)
        for item in self.cleanup_table.get_children():
            self.cleanup_table.delete(item)
        self.cleanup_rows_by_id = {}
        self.incident_rows_by_id = {}
        queue_rows = list(payload.get("pending_rows", [])) + list(payload.get("other_rows", []))
        status_order = {"Error": 0, "Error YouTube": 0, "Sin enlace": 0, "Cancelado": 1, "Procesando": 2, "Subiendo": 2, "Pendiente": 3}
        queue_rows.sort(key=lambda row: (status_order.get(row[4], 2), row[3], row[1]))
        for index, row in enumerate(queue_rows):
            signature, name, size_label, created_label, status, detail, path = row
            status_tag = {
                "Pendiente": "pending", "Error": "error", "Error YouTube": "error", "Sin enlace": "missing",
                "Cancelado": "cancelled", "Subiendo": "uploading", "Procesando": "processing",
            }.get(status, "")
            item_id = f"queue:{index}:{signature}"
            self.pending_table.insert(
                "", "end", iid=item_id, values=(name, size_label, created_label, status, detail, path),
                tags=(status_tag,) if status_tag else (),
            )
            self.incident_rows_by_id[item_id] = {
                "signature": signature,
                "name": name,
                "status": status,
                "detail": detail,
                "path": path,
            }
        for row in payload.get("uploaded_rows", []):
            signature, updated_at, title, path, size_label, youtube, youtube_id = row
            item_id = f"cleanup:{signature}"
            self.cleanup_table.insert("", "end", iid=item_id, values=(updated_at, title, path, size_label, youtube), tags=("uploaded",))
            size = Path(path).stat().st_size if Path(path).exists() else 0
            self.cleanup_rows_by_id[signature] = (signature, updated_at, "uploaded", title, path, youtube_id, "", size)
        self.reapply_tree_sort(self.pending_table)
        self.reapply_tree_sort(self.cleanup_table)
        self.fit_treeview_columns(self.pending_table)
        self.fit_treeview_columns(self.cleanup_table)
        used = self.store.daily_upload_attempt_count()
        active = payload.get("active", 0)
        self.total_count_var.set(str(payload["total"]))
        self.pending_count_var.set(str(payload["pending"]))
        self.active_count_var.set(str(active))
        self.uploaded_count_var.set(str(payload["uploaded"]))
        self.issue_count_var.set(str(payload["other"]))
        if payload["error"]:
            self.folder_summary_var.set(payload["error"])
        else:
            details = []
            if payload.get("youtube_checked"):
                if payload.get("filled_links"):
                    details.append(f"{payload['filled_links']} enlace(s) recuperado(s)")
                if payload.get("restored_pending"):
                    details.append(f"{payload['restored_pending']} vuelto(s) a pendientes")
            if payload.get("youtube_checked"):
                self.folder_summary_var.set(f"Canal comprobado · {', '.join(details) if details else 'sin cambios'}")
            else:
                self.folder_summary_var.set("Vista local actualizada")
        self.pending_summary_var.set(
            f"{payload['pending'] + active + payload['other']} por resolver · "
            f"{payload['pending']} listo(s) · {active} en curso · {payload['other']} con incidencia"
        )
        self.uploaded_summary_var.set(f"{payload['uploaded']} video(s) de esta carpeta ya subido(s) o detectado(s) en YouTube")
        if not self.upload_limit_state:
            self.quota_summary_var.set(f"Intentos registrados hoy: {used}")
        has_processing = any(row[4] == "Procesando" for row in payload.get("other_rows", []))
        if has_processing:
            self.schedule_processing_check()
        elif self.processing_check_after_id is not None:
            self.after_cancel(self.processing_check_after_id)
            self.processing_check_after_id = None

    def schedule_processing_check(self) -> None:
        if self.processing_check_after_id is None:
            self.processing_check_after_id = self.after(30000, self.run_processing_check)

    def run_processing_check(self) -> None:
        self.processing_check_after_id = None
        self.refresh_folder_contents(verify_youtube=True)

    def open_folder_selection(self, _event=None) -> None:
        item = self.selected_incident()
        if not item:
            return
        path = Path(item["path"])
        if path.exists():
            os.startfile(path)
        else:
            messagebox.showwarning(APP_NAME, "El archivo local ya no existe.")

    def selected_incident(self) -> dict | None:
        selected = self.pending_table.selection()
        if not selected:
            return None
        item_id = selected[0]
        if not item_id.startswith("queue:"):
            return None
        return getattr(self, "incident_rows_by_id", {}).get(item_id)

    def update_incident_help(self, _event=None) -> None:
        incident = self.selected_incident()
        if not incident:
            self.incident_help_var.set("")
            return
        status = incident["status"]
        detail = incident["detail"].lower()
        if status == "Pendiente":
            suggestion = "Listo para subir. Usa la flecha de subida o activa el modo automatico."
        elif status == "Subiendo":
            suggestion = "La subida esta activa. Puedes cancelarla o esperar a que termine."
        elif status == "Procesando":
            suggestion = "Pulsa Reintentar para comprobarlo o Pendiente para retirar una subida incompleta y liberarlo."
        elif status == "Sin enlace":
            suggestion = "Pulsa Reintentar para comprobar YouTube y recuperar el enlace antes de hacer otra subida."
        elif "quota" in detail or "limit" in detail or "429" in detail:
            suggestion = "YouTube ha limitado las subidas. Espera al contador y despues pulsa Reintentar."
        elif "oauth" in detail or "credential" in detail or "scope" in detail:
            suggestion = "Revisa el JSON OAuth en Ajustes y despues pulsa Reintentar."
        elif "no such file" in detail or "no existe" in detail:
            suggestion = "El archivo no esta disponible. Comprueba la ruta o devuelve el elemento a Pendientes."
        elif status == "Cancelado":
            suggestion = "La subida fue cancelada. Puedes reintentarlo ahora o devolverlo a Pendientes."
        else:
            suggestion = "Puedes reintentar ahora; si vuelve a fallar, copia el detalle para revisarlo en Consola."
        self.incident_help_var.set(suggestion)

    def retry_selected_incident(self) -> None:
        incident = self.selected_incident()
        if not incident:
            messagebox.showinfo(APP_NAME, "Selecciona primero un video pendiente.")
            return
        if incident["status"] == "Pendiente":
            self.upload_pending_now()
            return
        if incident["status"] == "Subiendo" and self.busy:
            messagebox.showinfo(APP_NAME, "Este video ya se esta subiendo.")
            return
        if incident["status"] in {"Sin enlace", "Procesando"}:
            self.incident_help_var.set("Comprobando el canal y recuperando el enlace...")
            self.log(f"Comprobacion manual del enlace solicitada: {incident['name']}.")
            self.refresh_folder_contents(verify_youtube=True)
            return
        path = Path(incident["path"])
        if not path.exists():
            messagebox.showwarning(APP_NAME, "No se puede reintentar porque el archivo local no existe.")
            return
        if self.store.has_success(incident["signature"]):
            messagebox.showinfo(APP_NAME, "El registro permanente indica que este video ya fue subido. Se actualizara la vista.")
            self.refresh_folder_contents()
            return
        self.log(f"Reintento manual solicitado: {incident['name']}.")
        self.upload_pending_now()
        self.refresh_folder_contents(verify_youtube=False)

    def reset_selected_incident(self) -> None:
        incident = self.selected_incident()
        if not incident:
            messagebox.showinfo(APP_NAME, "Selecciona primero un video pendiente.")
            return
        if incident["status"] == "Pendiente":
            messagebox.showinfo(APP_NAME, "Este video ya esta pendiente y listo para subir.")
            return
        if incident["status"] == "Subiendo" and self.busy:
            messagebox.showinfo(APP_NAME, "Cancela primero la subida activa.")
            return
        if incident["status"] == "Procesando":
            confirmed = ask_confirmation(
                "Revisar subida incompleta",
                "Vas a comprobar el estado real de este vídeo en YouTube.",
                ["Conservarlo como subido si terminó correctamente", "Retirarlo de YouTube si sigue incompleto", "Devolver el archivo local a Pendientes si se retira"],
                ["El archivo local"],
                question="¿Comprobar la subida ahora?",
            )
            if confirmed:
                self.incident_help_var.set("Comprobando y retirando la subida incompleta...")
                threading.Thread(target=self._reset_processing_incident_thread, args=(incident,), daemon=True).start()
            return
        if incident["status"] == "Sin enlace":
            confirmed = ask_confirmation(
                "Restablecer vídeo sin enlace",
                "El registro local no tiene un enlace de YouTube verificable.",
                ["Retirar la referencia del registro", "Devolver el vídeo a Pendientes"],
                ["El archivo local", "Cualquier vídeo que sí exista en YouTube"],
                question="¿Restablecer este vídeo?",
            )
            if not confirmed:
                return
            self.store.forget_registry(incident["signature"])
        self.store.clear_upload_incident(incident["signature"])
        self.log(f"Incidencia restablecida a pendiente: {incident['name']}.")
        self.refresh_folder_contents(verify_youtube=False)

    def _reset_processing_incident_thread(self, incident: dict) -> None:
        signature = incident["signature"]
        title, saved_id = self.store.upload_identity(signature)
        path = Path(incident["path"])
        if not title and path.exists():
            try:
                title = creation_title(path)
            except OSError:
                title = ""
        try:
            client = YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", f"[{now_text()}] {text}")))
            client.uploaded_video_index(force=True)
            content_matches, resolved_id, match_reason, remote_state = client.verify_local_file(path, title, saved_id)
            if remote_state == "processed" and content_matches:
                if path.exists():
                    self.store.upsert(signature, path, title, "uploaded", youtube_id=resolved_id)
                    self.store.remember_upload(signature, path, title, youtube_id=resolved_id, reason="uploaded")
                else:
                    self.store.update_registry_state(signature, resolved_id, "uploaded")
                self.events.put(("incident_reset", f"{incident['name']} termino correctamente en YouTube y se mantiene como subido."))
                return
            if content_matches and resolved_id and remote_state in {"uploaded", "processing"}:
                try:
                    client.delete_video(resolved_id)
                except HttpError as exc:
                    if getattr(exc.resp, "status", 0) != 404:
                        raise
            self.store.forget_registry(signature)
            self.store.clear_upload_incident(signature)
            detail = ""
            if resolved_id and not content_matches:
                detail = f" El enlace anterior no correspondia al archivo local ({match_reason})."
            self.events.put(("incident_reset", f"Subida incompleta retirada. {incident['name']} vuelve a Pendientes.{detail}"))
        except Exception as exc:
            self.events.put(("incident_error", f"No se pudo liberar {incident['name']}: {describe_error(exc)}"))

    def cancel_selected_incident(self) -> None:
        if not self.busy:
            messagebox.showinfo(APP_NAME, "No hay ninguna subida activa para cancelar.")
            return
        self.cancel_upload()

    def copy_selected_incident(self) -> None:
        incident = self.selected_incident()
        if not incident:
            messagebox.showinfo(APP_NAME, "Selecciona primero un video pendiente.")
            return
        text = f"{incident['name']}\nEstado: {incident['status']}\n{incident['detail']}\n{incident['path']}"
        self.clipboard_clear()
        self.clipboard_append(text)
        self.incident_help_var.set("Detalle copiado al portapapeles.")

    def open_cleanup_selection(self, _event=None) -> None:
        selected = self.cleanup_table.selection()
        if not selected:
            return
        values = self.cleanup_table.item(selected[0], "values")
        youtube = values[4]
        path = values[2]
        if youtube.startswith("https://"):
            webbrowser.open(youtube)
        elif path and Path(path).exists():
            os.startfile(path)

    def open_selected_cleanup_youtube(self) -> None:
        selected = self.cleanup_table.selection()
        if not selected:
            messagebox.showinfo(APP_NAME, "Selecciona primero un video subido.")
            return
        values = self.cleanup_table.item(selected[0], "values")
        youtube = values[4]
        if youtube.startswith("https://"):
            webbrowser.open(youtube)
        else:
            messagebox.showinfo(APP_NAME, "Este registro no tiene enlace confirmado de YouTube. Actualiza la carpeta para revalidarlo.")

    def open_selected_cleanup_local(self) -> None:
        selected = self.cleanup_table.selection()
        if not selected:
            messagebox.showinfo(APP_NAME, "Selecciona primero un video subido.")
            return
        values = self.cleanup_table.item(selected[0], "values")
        path = values[2]
        if path and Path(path).exists():
            os.startfile(path)
        else:
            messagebox.showinfo(APP_NAME, "El archivo local ya no existe.")

    def selected_cleanup_signature(self) -> str | None:
        selected = self.cleanup_table.selection()
        if not selected:
            return None
        return selected[0].split(":", 1)[1]

    def delete_selected_uploaded_file(self) -> None:
        signature = self.selected_cleanup_signature()
        if not signature:
            messagebox.showinfo(APP_NAME, "Selecciona primero un video subido.")
            return
        row = getattr(self, "cleanup_rows_by_id", {}).get(signature)
        if row:
            self.delete_uploaded_paths([row])

    def delete_all_uploaded_files(self) -> None:
        rows = [row for row in getattr(self, "cleanup_rows_by_id", {}).values() if Path(row[4]).exists()]
        if not rows:
            messagebox.showinfo(APP_NAME, "No hay archivos locales subidos para borrar.")
            return
        self.delete_uploaded_paths(rows)

    def run_configured_cleanup(self) -> None:
        older_than = datetime.now() - self.config.auto_delete_delay
        rows = [row for row in self.store.uploaded_before(older_than, 2000) if Path(row[4]).exists()]
        if not rows:
            messagebox.showinfo(APP_NAME, f"No hay archivos locales subidos con mas de {self.config.auto_delete_delay_label}.")
            return
        self.delete_uploaded_paths(rows)

    def delete_uploaded_paths(self, rows: list[tuple]) -> None:
        existing = [row for row in rows if Path(row[4]).exists()]
        if not existing:
            messagebox.showinfo(APP_NAME, "El archivo local ya no existe.")
            return
        try:
            verifier = YouTubeClient(self.store, self.config, self.log)
            verifier.uploaded_video_index(force=True)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"No se pudo comprobar YouTube. No se borrara ningun archivo.\n\n{exc}")
            return

        confirmed_rows = []
        mismatches = []
        for row in existing:
            signature, _updated_at, _status, title, path, youtube_id, _error, _size = row
            target = Path(path)
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
                continue
            if not youtube_id and resolved_id:
                self.store.update_registry_youtube_id(signature, resolved_id)
            confirmed_rows.append(row)

        mismatch_preview = "\n".join(f"- {filename}: {reason}" for filename, reason in mismatches[:10])
        if not confirmed_rows:
            detail = f"\n\n{mismatch_preview}" if mismatch_preview else ""
            messagebox.showwarning(APP_NAME, f"No se borrara ningun archivo: ninguno quedo confirmado con seguridad en el canal de YouTube.{detail}")
            return

        total = sum(Path(row[4]).stat().st_size for row in confirmed_rows)
        conserved = [f"{len(mismatches)} archivo(s) con discrepancias"]
        conserved.extend(f"{filename}: {reason}" for filename, reason in mismatches[:10])
        if len(mismatches) > 10:
            conserved.append(f"Y {len(mismatches) - 10} discrepancia(s) más")
        if not ask_confirmation(
            "Confirmar limpieza local",
            "La comprobación de seguridad en YouTube ha terminado.",
            [f"Borrar {len(confirmed_rows)} archivo(s) local(es) confirmados ({human_size(total)})"],
            conserved,
            "Los archivos locales confirmados se eliminarán de forma permanente.",
            "¿Borrar únicamente los archivos confirmados?",
        ):
            self.log("Limpieza cancelada por el usuario despues de la comprobacion de YouTube.")
            return

        deleted = 0
        failed = 0
        for signature, _updated_at, _status, _title, path, _youtube_id, _error, _size in confirmed_rows:
            try:
                Path(path).unlink()
                self.store.mark_local_deleted(signature)
                deleted += 1
            except OSError as exc:
                failed += 1
                self.log(f"No se pudo borrar {path}: {exc}")
        self.log(f"Limpieza completada: {deleted} borrado(s), {len(mismatches)} conservado(s) por discrepancias, {failed} error(es).")
        self.refresh_folder_contents(verify_youtube=False)

    def hide_to_tray(self) -> None:
        current_state = self.state()
        if current_state in {"normal", "zoomed"}:
            self.window_state_before_tray = current_state
        if current_state == "normal":
            self.window_geometry_before_tray = self.geometry()
        if pystray and Image:
            self.withdraw()
            self.ensure_tray()
        else:
            self.iconify()

    def ensure_tray(self) -> None:
        if self.tray_icon or not pystray or not Image:
            return
        logo = resource_path("assets/youtube-sync-logo.png")
        if logo.exists():
            with Image.open(logo) as source:
                image = source.convert("RGBA")
                image.thumbnail((64, 64), Image.Resampling.LANCZOS)
        else:
            image = Image.new("RGBA", (64, 64), (255, 0, 51, 255))
        menu = pystray.Menu(
            pystray.MenuItem("Mostrar", lambda: self.after(0, self.show_from_tray), default=True),
            pystray.MenuItem("Auto ON/OFF", lambda: self.after(0, self.toggle_auto_mode)),
            pystray.MenuItem("Actualizar", lambda: self.after(0, self.refresh_all)),
            pystray.MenuItem("Salir", lambda: self.after(0, self.quit_app)),
        )
        self.tray_icon = pystray.Icon(APP_NAME, image, APP_NAME, menu)
        threading.Thread(target=self.run_tray_icon, daemon=True).start()

    def run_tray_icon(self) -> None:
        try:
            self.tray_icon.run()
        except Exception as exc:
            self.tray_icon = None
            self.events.put(("log", f"[{now_text()}] No se pudo iniciar el icono de bandeja: {describe_error(exc)}"))

    def show_from_tray(self) -> None:
        self.restoring_window = True
        self.deiconify()
        self.state("normal")
        if self.window_geometry_before_tray:
            self.geometry(self.window_geometry_before_tray)
        if self.window_state_before_tray == "zoomed":
            self.state("zoomed")
        self.update_idletasks()
        self.after(80, self.refresh_visible_layout)
        self.after(180, lambda: setattr(self, "restoring_window", False))
        self.lift()
        self.focus_force()

    def refresh_visible_layout(self) -> None:
        if not self.winfo_viewable():
            return
        try:
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
            self.resize_treeview_columns(self.pending_table)
            self.resize_treeview_columns(self.cleanup_table)
            self.resize_treeview_columns(self.gallery_table)
            self.update_idletasks()
        except tk.TclError:
            pass

    def remember_window_geometry(self, event=None) -> None:
        if self.restoring_window:
            return
        if event is not None and event.widget is not self:
            return
        try:
            if self.state() == "normal" and self.winfo_viewable() and self.winfo_width() >= 760 and self.winfo_height() >= 520:
                self.window_geometry_before_tray = self.geometry()
        except tk.TclError:
            pass

    def quit_app(self) -> None:
        if self.worker:
            self.worker.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
