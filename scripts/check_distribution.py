"""Check the packaged applications without loading accounts or starting uploads."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for project in ("YouTubeSync",):
    folder = root / "dist/YouTubeSync"
    executable = folder / "YouTubeSync.exe"
    # The SSL self-test covers trust data specific to the Python build vendor.
    for name in ("python312.dll",):
        if not (folder / "_internal" / name).is_file():
            raise RuntimeError(f"{project}: falta {name}")
    if list((folder / "_internal").rglob("icuuc.dll")):
        raise RuntimeError("La distribucion Qt incluye una ICU ajena a Windows")
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        for language in ("es", "en"):
            report = Path(temporary) / f"startup-{language}.json"
            fixture = root / "tests/fixtures/local-preview.mp4"
            env = dict(os.environ, YOUTUBESYNC_SELF_TEST_LANGUAGE=language)
            subprocess.run([str(executable), "--self-test", str(report), str(fixture)], check=True, timeout=30, cwd=root, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            result = json.loads(report.read_text(encoding="utf-8"))
            required = ("ok", "ssl", "icons", "diagnostics", "library", "manual", "media",
                        "playback", "embedded", "native", "translations")
            if any(not result.get(key) for key in required) or result.get("language") != language:
                raise RuntimeError(f"{project}: comprobacion de distribucion ({language}) fallida: {result}")
    print(f"{project}: arranque, SSL, reproduccion local e idiomas ES/EN correctos / startup, SSL, local playback and ES/EN languages passed")
