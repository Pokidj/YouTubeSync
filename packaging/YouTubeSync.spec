from pathlib import Path
from importlib.metadata import distributions
from PySide6.QtCore import QLibraryInfo
import sys
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

root = Path(SPECPATH).parent
sys.path.insert(0, str(root / "src"))
from youtube_sync_version import APP_VERSION
numbers = tuple(map(int, APP_VERSION.split('.')))
numbers += (0,) * (4 - len(numbers))
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904b0', [StringStruct('ProductName', 'YouTubeSync'),
          StringStruct('FileDescription', 'YouTubeSync'), StringStruct('FileVersion', APP_VERSION),
          StringStruct('ProductVersion', APP_VERSION), StringStruct('OriginalFilename', 'YouTubeSync.exe')])]),
          VarFileInfo([VarStruct('Translation', [1033, 1200])])],
)
license_data = []
for dependency in distributions():
    for file in dependency.files or ():
        if '.dist-info/' in str(file) and file.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE')):
            source = Path(dependency.locate_file(file))
            if source.is_file():
                license_data.append((str(source), 'licenses/' + dependency.metadata['Name']))

a = Analysis(
    [str(root / "src/youtube_sync_app.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=license_data + [(str(root / "assets"), "assets"),
           (str(Path(QLibraryInfo.path(QLibraryInfo.TranslationsPath)) / "qtbase_es.qm"), "PySide6/translations")],
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
    version=version_info,
    icon=[str(root / "assets/youtube-sync.ico")],
    manifest=str(root / "packaging/YouTubeSync.manifest"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="YouTubeSync")
