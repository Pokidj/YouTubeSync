"""Build a portable release ZIP after checking the actual packaged executable."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "outputs/youtube-sync-modern/src"))

from youtube_sync_updater import MANIFEST, MAX_UNPACKED, package_name, release_version, validate_package
from youtube_sync_version import APP_VERSION, REPOSITORY


def validate_binary(source: Path, version: str) -> None:
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as temporary:
        report = Path(temporary) / "startup.json"
        subprocess.run([str(source / "YouTubeSync.exe"), "--self-test", str(report)],
                       check=True, timeout=30, cwd=source)
        data = json.loads(report.read_text(encoding="utf-8"))
        if (not data.get("ok") or not data.get("ssl")
                or release_version(data.get("version", "")) != release_version(version)):
            raise RuntimeError("El ejecutable no corresponde a la version indicada o falla el arranque/SSL. Recompila primero.")


def create_package(source: Path, output: Path, version: str) -> tuple[Path, Path]:
    source, output = source.resolve(), output.resolve()
    if output.is_relative_to(source):
        raise ValueError("La carpeta de salida no puede estar dentro de la distribucion.")
    if not (source / "YouTubeSync.exe").is_file() or not list((source / "_internal").glob("python*.dll")):
        raise ValueError("Selecciona la distribucion completa de dist/YouTubeSync, no el EXE intermedio de build.")
    files = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("No se admiten enlaces simbolicos en la distribucion.")
        if not path.is_file():
            continue
        relative, name = path.relative_to(source), path.name.lower()
        if (name == "config.json" or name.startswith(("client_secret", "youtube-token", "credentials", ".env"))
                or path.suffix.lower() in {".sqlite3", ".sqlite", ".db", ".log"}):
            raise ValueError("La distribucion contiene configuracion o datos personales. Recompila en una carpeta limpia.")
        if len(relative.parts) == 1 and name not in {"youtubesync.exe", "release.json"}:
            raise ValueError("Hay archivos ajenos al paquete en la raiz de la distribucion.")
        if relative.as_posix() != "release.json":
            files.append(path)
    if len(files) > 19999 or sum(path.stat().st_size for path in files) > MAX_UNPACKED:
        raise ValueError("La distribucion es demasiado grande.")
    output.mkdir(parents=True, exist_ok=True)
    package = output / package_name(version)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output, suffix=".tmp", delete=False) as staging:
            temporary = Path(staging.name)
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6, strict_timestamps=False) as archive:
            for path in files:
                archive.write(path, "YouTubeSync/" + path.relative_to(source).as_posix())
            archive.writestr(MANIFEST, json.dumps({
                "app": "YouTubeSync", "version": str(release_version(version)), "platform": "windows",
                "architecture": "x64", "generated_at": datetime.now(timezone.utc).isoformat(),
            }, indent=2))
        validate_package(temporary, version)
        temporary.replace(package)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256()
    with package.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = output / "SHA256SUMS.txt"
    checksum.write_text(f"{digest.hexdigest()}  {package.name}\n", encoding="ascii")
    return package, checksum


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "outputs/youtube-sync-modern/dist/YouTubeSync")
    parser.add_argument("--output", type=Path, default=ROOT / "work/releases")
    args = parser.parse_args()
    source = args.dist.resolve()
    validate_binary(source, APP_VERSION)
    package, checksum = create_package(source, args.output, APP_VERSION)
    print(f"ZIP: {package}")
    print(f"SHA256: {checksum}")
    print(f"Publicar ambos como assets de la release v{APP_VERSION} en {REPOSITORY}.")


if __name__ == "__main__":
    main()
