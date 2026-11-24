"""YouTube links and official quota destinations; no network requests."""

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


def youtube_video_id(value: str) -> str:
    text = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise ValueError("Introduce un enlace de vídeo de YouTube o su ID de 11 caracteres.")
    parts = parsed.path.strip("/").split("/")
    host = (parsed.hostname or "").lower()
    if host in {"youtu.be", "www.youtu.be"} and len(parts) == 1:
        candidate = parts[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed"}:
            candidate = parts[1]
        else:
            candidate = ""
    else:
        candidate = ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        raise ValueError("El enlace no contiene un ID de vídeo de YouTube válido.")
    return candidate


def quota_console_url(client_secret_path: str) -> str:
    base = "https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas"
    try:
        path = Path(client_secret_path)
        if path.stat().st_size > 1024 * 1024:
            return base
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        project = data.get("installed", {}).get("project_id", "")
        if isinstance(project, str) and project and len(project) <= 128:
            return base + "?" + urlencode({"project": project})
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return base
