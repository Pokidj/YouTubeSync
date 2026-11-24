"""Verify the official installer and prepare a coordinated, user-approved update."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import struct
import subprocess

from packaging.version import Version


def installer_identity(path: Path) -> tuple[str, str, str]:
    if os.name != "nt":
        raise OSError("La instalación solo está disponible en Windows.")
    api = ctypes.WinDLL("version", use_last_error=True, winmode=0x800)
    api.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    api.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    api.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    api.GetFileVersionInfoW.restype = wintypes.BOOL
    api.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
    api.VerQueryValueW.restype = wintypes.BOOL
    size = api.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        raise ValueError("El instalador no contiene información de versión válida.")
    data = ctypes.create_string_buffer(size)
    if not api.GetFileVersionInfoW(str(path), 0, size, data):
        raise ctypes.WinError(ctypes.get_last_error())
    pointer, length = ctypes.c_void_p(), wintypes.UINT()
    if not api.VerQueryValueW(data, "\\VarFileInfo\\Translation", ctypes.byref(pointer), ctypes.byref(length)) or length.value < 4:
        raise ValueError("El instalador no contiene información del producto.")
    translation = ctypes.string_at(pointer, length.value)
    language, page = struct.unpack_from("<HH", translation)

    def query(name):
        key = f"\\StringFileInfo\\{language:04x}{page:04x}\\{name}"
        if not api.VerQueryValueW(data, key, ctypes.byref(pointer), ctypes.byref(length)) or not length.value:
            return ""
        return ctypes.wstring_at(pointer, length.value).rstrip("\0 ")

    return query("ProductName"), query("ProductVersion"), query("FileDescription")


def validate_installer(path: Path, version: str) -> None:
    with path.open("rb") as source:
        header = source.read(64)
        if len(header) < 64 or header[:2] != b"MZ":
            raise ValueError("El archivo descargado no es un instalador de Windows.")
        offset = struct.unpack_from("<I", header, 60)[0]
        if not 64 <= offset <= min(path.stat().st_size - 6, 1024 * 1024):
            raise ValueError("La cabecera del instalador no es válida.")
        source.seek(offset)
        if source.read(4) != b"PE\0\0":
            raise ValueError("La cabecera del instalador no es válida.")
    product, actual_version, description = installer_identity(path)
    if product != "YouTubeSync" or description != "YouTubeSync Installer" or Version(actual_version) != Version(version):
        raise ValueError("El instalador no corresponde a YouTubeSync o a la versión solicitada.")


@dataclass(frozen=True)
class InstallPlan:
    path: Path
    version: str
    size: int
    modified_ns: int
    file_id: int


def prepare_install(path: Path, release) -> InstallPlan:
    path = path.resolve(strict=True)
    asset = release.asset
    if asset is None or path.name != asset.name or not release.is_newer():
        raise ValueError("No hay una actualización válida para instalar.")
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    validate_installer(path, release.version)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError("El instalador ha cambiado durante la comprobación.")
    if after.st_size != asset.size or digest.hexdigest() != asset.sha256:
        raise ValueError("La descarga no coincide con la huella publicada. Descárgala de nuevo.")
    return InstallPlan(path, release.version, after.st_size, after.st_mtime_ns, after.st_ino)


def launch_installer(plan: InstallPlan, language: str, pid: int | None = None):
    if os.name != "nt":
        raise OSError("La instalación solo está disponible en Windows.")
    stat = plan.path.stat()
    if (stat.st_size, stat.st_mtime_ns, stat.st_ino) != (plan.size, plan.modified_ns, plan.file_id):
        raise ValueError("El instalador ha cambiado. Descárgalo de nuevo.")
    arguments = [str(plan.path), "/SILENT", "/SP-", "/NORESTART", "/NOCLOSEAPPLICATIONS",
                 "/NORESTARTAPPLICATIONS", f"/UPDATEPID={pid or os.getpid()}", "/RELAUNCH=1",
                 "/LANG=" + ("english" if language == "en" else "spanish")]
    return subprocess.Popen(arguments, cwd=plan.path.parent, close_fds=True,
                            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
