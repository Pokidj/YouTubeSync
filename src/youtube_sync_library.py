"""Stable logical column IDs; hiding or moving a column never changes row identity."""

LIBRARY_COLUMNS = (
    ("file", "Archivo", "file-video-camera"),
    ("title", "Título", "file-text"),
    ("size", "Tamaño", "layers"),
    ("created", "Creado", "calendar"),
    ("status", "Estado", "circle-check"),
    ("path", "Ruta", "folder-open"),
    ("resolution", "Resolución", "monitor"),
    ("thumbnail", "Miniatura", "file-video-camera"),
    ("duration", "Duración", "clock"),
    ("fps", "FPS", "play"),
)
DEFAULT_LIBRARY_COLUMNS = ("file", "size", "created", "status")
MEDIA_COLUMNS = frozenset({"resolution", "thumbnail", "duration", "fps"})
STATUS_ICONS = {
    "Pendiente": ("arrow-up", "#3ea6ff"),
    "Subido": ("circle-check", "#22c55e"),
    "Subido (manual)": ("user-round", "#5bd8b7"),
    "Incidencia": ("circle-exclamation-point", "#f59e0b"),
    "En curso": ("refresh-cw", "#c084fc"),
    "En espera": ("clock", "#a7adb8"),
    "Por verificar": ("circle-question-mark", "#eab308"),
    "Revisar": ("circle-question-mark", "#fbbf24"),
}


def normalize_library_columns(value) -> list[str]:
    known = {column[0] for column in LIBRARY_COLUMNS}
    result = []
    if isinstance(value, list):
        for key in value:
            if isinstance(key, str) and key in known and key not in result:
                result.append(key)
    return result or list(DEFAULT_LIBRARY_COLUMNS)


def media_cells(data: dict) -> tuple[tuple[str, float], ...]:
    width, height = data.get("width", 0), data.get("height", 0)
    seconds, fps = data.get("seconds", 0), data.get("fps", 0)
    duration = "No disponible"
    if seconds > 0:
        minutes, second = divmod(round(seconds), 60)
        hours, minute = divmod(minutes, 60)
        duration = f"{hours}:{minute:02}:{second:02}" if hours else f"{minute}:{second:02}"
    return (
        (f"{width} x {height}" if width and height else "No disponible", width * height),
        ("" if data.get("thumbnail") else "Sin miniatura", 0),
        (duration, seconds),
        (f"{fps:g}" if fps > 0 else "No disponible", fps),
    )
