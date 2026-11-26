"""Persistent channel presentation; never changes remote video identity."""

CHANNEL_COLUMNS = (
    ("thumbnail", "Miniatura", "file-video-camera"), ("title", "Título", "file-text"),
    ("duration", "Duración", "clock"), ("privacy", "Privacidad", "lock"),
    ("playlists", "Listas", "list-video"), ("published", "Publicado", "calendar"),
    ("url", "YouTube", "external-link"), ("id", "ID del vídeo", "tag"),
    ("filename", "Archivo original", "file-video-camera"), ("size", "Tamaño", "layers"),
    ("resolution", "Resolución", "monitor"), ("fps", "FPS", "play"),
    ("quality", "Calidad", "monitor"), ("processing", "Procesamiento", "refresh-cw"),
)
DEFAULT_CHANNEL_COLUMNS = tuple(key for key, _, _ in CHANNEL_COLUMNS[:6])
SELECTION_COLORS = {"green": ("Verde", "#15803d"), "blue": ("Azul", "#1765b3"),
                    "red": ("Rojo", "#b91c39"), "violet": ("Violeta", "#713cac")}


def normalize_channel_columns(value):
    known = {key for key, _, _ in CHANNEL_COLUMNS}
    result = []
    for key in value if isinstance(value, (list, tuple)) else ():
        if isinstance(key, str) and key in known and key not in result:
            result.append(key)
    return result or list(DEFAULT_CHANNEL_COLUMNS)


def selection_color(value):
    return value if isinstance(value, str) and value in SELECTION_COLORS else "green"


def duration_sort_value(value):
    parts = str(value).split(":")
    if len(parts) not in (2, 3) or not all(part.isdecimal() for part in parts):
        return -1
    result = 0
    for part in parts:
        result = result * 60 + int(part)
    return result
