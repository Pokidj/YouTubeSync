"""Check the packaged applications without loading accounts or starting uploads."""

import json
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for project in ("youtube-sync", "youtube-sync-modern"):
    folder = root / "outputs" / project / "dist/YouTubeSync"
    executable = folder / "YouTubeSync.exe"
    for name in ("python312.dll", "codex-rejected-cas.pem"):
        if not (folder / "_internal" / name).is_file():
            raise RuntimeError(f"{project}: falta {name}")
    if project.endswith("modern") and list((folder / "_internal").rglob("icuuc.dll")):
        raise RuntimeError("La distribucion Qt incluye una ICU ajena a Windows")
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        report = Path(temporary) / "startup.json"
        subprocess.run([str(executable), "--self-test", str(report)], check=True, timeout=30, cwd=root)
        result = json.loads(report.read_text(encoding="utf-8"))
        if not result.get("ok") or not result.get("ssl"):
            raise RuntimeError(f"{project}: fallo de arranque: {result}")
    print(f"{project}: arranque y SSL correctos")
