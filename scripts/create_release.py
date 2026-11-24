"""Build the complete Windows installer after checking the packaged application."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from youtube_sync_updater import MAX_DOWNLOAD, package_name, release_version, validate_package
from youtube_sync_version import APP_VERSION, REPOSITORY


def validate_binary(source: Path, version: str) -> None:
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as temporary:
        report = Path(temporary) / "startup.json"
        subprocess.run([str(source / "YouTubeSync.exe"), "--self-test", str(report)],
                       check=True, timeout=30, cwd=source, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        data = json.loads(report.read_text(encoding="utf-8"))
        if (not data.get("ok") or not data.get("ssl")
                or release_version(data.get("version", "")) != release_version(version)):
            raise RuntimeError("El ejecutable no corresponde a la version indicada o falla el arranque/SSL. Recompila primero.")


def find_compiler() -> Path:
    candidates = [os.environ.get("ISCC", ""), shutil.which("ISCC.exe") or "",
                  str(ROOT / ".tools/inno/ISCC.exe"),
                  "C:/Program Files/Inno Setup 7/ISCC.exe", "C:/Program Files (x86)/Inno Setup 7/ISCC.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise RuntimeError("Instala Inno Setup 7 o configura ISCC con la ruta de ISCC.exe.")


def create_installer(source: Path, output: Path, version: str, compiler: Path | None = None) -> tuple[Path, Path]:
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
        if len(relative.parts) == 1 and name != "youtubesync.exe":
            raise ValueError("Hay archivos ajenos al paquete en la raiz de la distribucion.")
        files.append(path)
    if len(files) > 20000 or sum(path.stat().st_size for path in files) > 2 * MAX_DOWNLOAD:
        raise ValueError("La distribucion es demasiado grande.")
    output.mkdir(parents=True, exist_ok=True)
    package = output / package_name(version)
    parsed = release_version(version)
    if len(parsed.release) > 4 or any(part > 65535 for part in parsed.release):
        raise ValueError("La versión no se puede representar en un instalador Windows.")
    numbers = parsed.release + (0,) * (4 - len(parsed.release))
    subprocess.run([str(compiler or find_compiler()), "/Qp", f"/DAppVersion={parsed}",
                    "/DAppFileVersion=" + ".".join(map(str, numbers)),
                    f"/DAppVersionMS={(numbers[0] << 16) | numbers[1]}",
                    f"/DAppVersionLS={(numbers[2] << 16) | numbers[3]}",
                    f"/DDistDir={source}", f"/DOutputDir={output}", str(ROOT / "packaging/YouTubeSync.iss")],
                   check=True, timeout=900, cwd=ROOT)
    validate_package(package, version)
    if package.stat().st_size > MAX_DOWNLOAD:
        raise ValueError("El instalador supera el tamaño máximo de descarga.")
    digest = hashlib.sha256()
    with package.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = output / "SHA256SUMS.txt"
    checksum.write_text(f"{digest.hexdigest()}  {package.name}\n", encoding="ascii")
    return package, checksum


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist/YouTubeSync")
    parser.add_argument("--output", type=Path, default=ROOT / "releases")
    parser.add_argument("--compiler", type=Path)
    args = parser.parse_args()
    source = args.dist.resolve()
    validate_binary(source, APP_VERSION)
    package, checksum = create_installer(source, args.output, APP_VERSION, args.compiler)
    print(f"Instalador / Installer: {package}")
    print(f"SHA256: {checksum}")
    print(f"Publicar ambos como assets de la release v{APP_VERSION} en {REPOSITORY}.")


if __name__ == "__main__":
    main()
