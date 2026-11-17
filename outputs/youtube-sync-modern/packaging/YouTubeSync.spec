from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "src/youtube_sync_modern.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=["youtube_sync_engine"],
    hookspath=[str(root / "build_hooks")],
    hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
# Qt uses the Windows ICU API. A same-named DLL on PATH can expose incompatible exports.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() != "icuuc.dll"]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="YouTubeSync",
    debug=False, strip=False, upx=False, console=False,
    icon=[str(root / "assets/youtube-sync.ico")],
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="YouTubeSync")
