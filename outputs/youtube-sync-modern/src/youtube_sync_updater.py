"""Read public GitHub releases and download verified portable packages."""

import hashlib
import json
import re
import stat
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from packaging.version import InvalidVersion, Version

from youtube_sync_version import APP_VERSION, REPOSITORY

RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
LATEST_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MAX_DOWNLOAD = 1024 * 1024 * 1024
MAX_UNPACKED = 2 * 1024 * 1024 * 1024
MANIFEST = "YouTubeSync/release.json"


class UpdateError(RuntimeError):
    pass


class DownloadCancelled(UpdateError):
    pass


def release_version(value: str) -> Version:
    try:
        version = Version(value)
    except (InvalidVersion, TypeError) as exc:
        raise UpdateError("La release no tiene una version valida.") from exc
    if version.is_prerelease or version.is_devrelease or version.local is not None:
        raise UpdateError("Solo se admiten versiones estables publicadas.")
    return version


def package_name(version: str) -> str:
    return f"YouTubeSync-{release_version(version)}-windows-x64.zip"


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    notes: str
    url: str
    asset: ReleaseAsset | None

    def is_newer(self, current: str = APP_VERSION) -> bool:
        return release_version(self.version) > release_version(current)


class GitHubRedirects(urllib.request.HTTPRedirectHandler):
    HOSTS = {"api.github.com", "github.com", "release-assets.githubusercontent.com",
             "objects.githubusercontent.com", "github-releases.githubusercontent.com"}

    @classmethod
    def validate(cls, url: str) -> None:
        try:
            parsed = urllib.parse.urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise UpdateError("GitHub ha devuelto una direccion de descarga no valida.") from exc
        if (parsed.scheme != "https" or parsed.hostname not in cls.HOSTS
                or parsed.username or parsed.password or port not in {None, 443}):
            raise UpdateError("La descarga redirige fuera de los servidores HTTPS de GitHub permitidos.")

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.validate(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def parse_release(data: dict) -> Release | None:
    if not isinstance(data, dict):
        raise UpdateError("GitHub ha devuelto una respuesta de release no valida.")
    if data.get("draft") or data.get("prerelease"):
        return None
    tag = data.get("tag_name", "")
    version = str(release_version(tag))
    url = data.get("html_url", "")
    expected_url = RELEASES_URL + "/tag/" + urllib.parse.quote(tag, safe="")
    if url != expected_url:
        raise UpdateError("La release no pertenece al repositorio esperado.")
    expected_name = package_name(version)
    published_assets = data.get("assets", [])
    if not isinstance(published_assets, list):
        raise UpdateError("GitHub no ha devuelto una lista valida de paquetes.")
    assets = [item for item in published_assets if isinstance(item, dict) and item.get("name") == expected_name]
    if len(assets) > 1:
        raise UpdateError("La release contiene paquetes duplicados con el mismo nombre.")
    asset = None
    if assets:
        item = assets[0]
        expected_download = RELEASES_URL + "/download/" + urllib.parse.quote(tag, safe="") + "/" + expected_name
        size, digest = item.get("size"), item.get("digest", "")
        if item.get("state") != "uploaded" or item.get("browser_download_url") != expected_download:
            raise UpdateError("El paquete no esta publicado correctamente en el repositorio esperado.")
        if type(size) is not int or not 0 < size <= MAX_DOWNLOAD:
            raise UpdateError("El tamano del paquete no es valido.")
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise UpdateError("GitHub no proporciona una huella SHA-256 valida para este paquete.")
        asset = ReleaseAsset(expected_name, expected_download, size, digest[7:].lower())
    notes = data.get("body") or "Sin notas de version."
    if not isinstance(notes, str):
        raise UpdateError("Las notas de version no son validas.")
    return Release(version, tag, notes[:100000], url, asset)


def validate_package(path: Path, version: str) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 20000 or sum(item.file_size for item in entries) > MAX_UNPACKED:
                raise UpdateError("El paquete supera los limites de seguridad de descompresion.")
            names = set()
            for item in entries:
                name = item.filename.replace("\\", "/")
                parts = PurePosixPath(name)
                if (parts.is_absolute() or ".." in parts.parts or ":" in name
                        or not name.startswith("YouTubeSync/") or stat.S_ISLNK(item.external_attr >> 16)
                        or item.flag_bits & 1):
                    raise UpdateError("El paquete contiene rutas no permitidas.")
                if name in names:
                    raise UpdateError("El paquete contiene archivos duplicados.")
                names.add(name)
            if "YouTubeSync/YouTubeSync.exe" not in names or not any(
                    re.fullmatch(r"YouTubeSync/_internal/python\d+\.dll", name) for name in names):
                raise UpdateError("Falta el ejecutable o su runtime. No es una distribucion completa.")
            if MANIFEST not in names or archive.getinfo(MANIFEST).file_size > 16384:
                raise UpdateError("El paquete no incluye un manifiesto de version valido.")
            manifest = json.loads(archive.read(MANIFEST))
            if (not isinstance(manifest, dict) or manifest.get("app") != "YouTubeSync"
                    or release_version(manifest.get("version", "")) != release_version(version)
                    or manifest.get("platform") != "windows" or manifest.get("architecture") != "x64"):
                raise UpdateError("El contenido del paquete no corresponde a esta version de Windows.")
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateError("No se puede validar el archivo ZIP descargado.") from exc


class ReleaseClient:
    def __init__(self, opener=None) -> None:
        self.opener = opener or urllib.request.build_opener(GitHubRedirects())

    def open(self, url: str, binary: bool = False):
        GitHubRedirects.validate(url)
        request = urllib.request.Request(url, headers={
            "User-Agent": f"YouTubeSync/{APP_VERSION}",
            "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        })
        try:
            return self.opener.open(request, timeout=30)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, OSError) as exc:
            raise UpdateError("No se pudo conectar con GitHub. Comprueba tu conexion e intentalo de nuevo.") from exc

    def latest(self) -> Release | None:
        try:
            with self.open(LATEST_URL) as response:
                data = response.read(2 * 1024 * 1024 + 1)
                if len(data) > 2 * 1024 * 1024:
                    raise UpdateError("La respuesta de GitHub es demasiado grande.")
                return parse_release(json.loads(data))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in {403, 429}:
                raise UpdateError("GitHub ha limitado las consultas. Espera unos minutos y vuelve a intentarlo.") from exc
            raise UpdateError(f"GitHub no pudo consultar la release (HTTP {exc.code}).") from exc
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise UpdateError("GitHub no ha devuelto metadatos de version validos.") from exc

    def download(self, release: Release, folder: Path, cancel: threading.Event,
                 progress: Callable[[int, int], None]) -> Path:
        asset = release.asset
        if asset is None:
            raise UpdateError("Esta release no incluye un paquete Windows x64 compatible.")
        expected_url = RELEASES_URL + "/download/" + urllib.parse.quote(release.tag, safe="") + "/" + package_name(release.version)
        if asset.name != package_name(release.version) or asset.url != expected_url:
            raise UpdateError("El nombre o la procedencia del paquete no coinciden con la release.")
        if cancel.is_set():
            raise DownloadCancelled("Descarga cancelada.")
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / asset.name
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=folder, prefix="download-", suffix=".part", delete=False) as output:
                temporary = Path(output.name)
                digest, received = hashlib.sha256(), 0
                with self.open(asset.url, binary=True) as response:
                    while True:
                        if cancel.is_set():
                            raise DownloadCancelled("Descarga cancelada.")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        received += len(chunk)
                        if received > asset.size:
                            raise UpdateError("La descarga supera el tamano publicado por GitHub.")
                        output.write(chunk)
                        digest.update(chunk)
                        progress(received, asset.size)
            if cancel.is_set():
                raise DownloadCancelled("Descarga cancelada.")
            if received != asset.size or digest.hexdigest() != asset.sha256:
                raise UpdateError("La descarga esta incompleta o no coincide con la huella SHA-256 publicada.")
            validate_package(temporary, release.version)
            if cancel.is_set():
                raise DownloadCancelled("Descarga cancelada.")
            temporary.replace(destination)
            return destination
        except urllib.error.HTTPError as exc:
            raise UpdateError(f"GitHub no pudo descargar el paquete (HTTP {exc.code}).") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise UpdateError("No se pudo completar la descarga. Comprueba la conexion y el espacio disponible.") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
