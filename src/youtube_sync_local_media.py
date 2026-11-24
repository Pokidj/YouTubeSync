"""Read-only Windows Explorer media properties and thumbnails, off the UI thread."""

import ctypes as ct
import hashlib
import json
import os
import queue
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage


def windows_media(path: Path, thumbnail: Path | None) -> dict:
    if os.name != "nt":
        return {}
    from ctypes import wintypes as wt

    class GUID(ct.Structure):
        _fields_ = [("data", ct.c_ubyte * 16)]

        def __init__(self, value):
            super().__init__()
            self.data[:] = uuid.UUID(value).bytes_le

    class PropertyKey(ct.Structure):
        _fields_ = [("fmtid", GUID), ("pid", wt.DWORD)]

    class Size(ct.Structure):
        _fields_ = [("cx", wt.LONG), ("cy", wt.LONG)]

    class Bitmap(ct.Structure):
        _fields_ = [("type", wt.LONG), ("width", wt.LONG), ("height", wt.LONG),
                    ("stride", wt.LONG), ("planes", wt.WORD), ("bits", wt.WORD), ("data", ct.c_void_p)]

    class BitmapInfo(ct.Structure):
        _fields_ = [("size", wt.DWORD), ("width", wt.LONG), ("height", wt.LONG),
                    ("planes", wt.WORD), ("bits", wt.WORD), ("compression", wt.DWORD),
                    ("image_size", wt.DWORD), ("xppm", wt.LONG), ("yppm", wt.LONG),
                    ("used", wt.DWORD), ("important", wt.DWORD), ("color", wt.DWORD)]

    ole, shell, props, gdi = (ct.WinDLL(name) for name in ("ole32", "shell32", "propsys", "gdi32"))

    def api(dll, name, result, *args):
        fn = getattr(dll, name)
        fn.restype, fn.argtypes = result, args
        return fn

    def method(obj, index, result, *args):
        vtable = ct.cast(obj, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
        return ct.WINFUNCTYPE(result, ct.c_void_p, *args)(vtable[index])

    def release(obj):
        if obj:
            method(obj, 2, wt.ULONG)(obj)

    init = api(ole, "CoInitializeEx", ct.c_long, ct.c_void_p, wt.DWORD)(None, 2)
    if init < 0:
        return {}
    result = {}
    try:
        store = ct.c_void_p()
        iid = GUID("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")
        hr = api(shell, "SHGetPropertyStoreFromParsingName", ct.c_long,
                 wt.LPCWSTR, ct.c_void_p, wt.DWORD, ct.c_void_p, ct.c_void_p)(
                     str(path), None, 0, ct.byref(iid), ct.byref(store))
        if hr >= 0 and store:
            try:
                key_from_name = api(props, "PSGetPropertyKeyFromName", ct.c_long, wt.LPCWSTR, ct.c_void_p)
                convert = api(props, "PropVariantToUInt64", ct.c_long, ct.c_void_p, ct.c_void_p)
                clear = api(ole, "PropVariantClear", ct.c_long, ct.c_void_p)
                get_value = method(store, 5, ct.c_long, ct.c_void_p, ct.c_void_p)
                for key, name, scale in (("width", "System.Video.FrameWidth", 1),
                                         ("height", "System.Video.FrameHeight", 1),
                                         ("seconds", "System.Media.Duration", 10_000_000),
                                         ("fps", "System.Video.FrameRate", 1000)):
                    prop = PropertyKey()
                    if key_from_name(name, ct.byref(prop)) < 0:
                        continue
                    # PROPVARIANT is 24 bytes on Win64; this buffer is also 8-byte aligned.
                    value = (ct.c_uint64 * 3)()
                    try:
                        number = ct.c_uint64()
                        if get_value(store, ct.byref(prop), ct.byref(value)) >= 0 and convert(ct.byref(value), ct.byref(number)) >= 0:
                            result[key] = number.value if scale == 1 else number.value / scale
                    finally:
                        clear(ct.byref(value))
            finally:
                release(store)
        if thumbnail is not None:
            factory, bitmap = ct.c_void_p(), ct.c_void_p()
            iid = GUID("bcc18b79-ba16-442f-80c4-8a59c30c463b")
            hr = api(shell, "SHCreateItemFromParsingName", ct.c_long,
                     wt.LPCWSTR, ct.c_void_p, ct.c_void_p, ct.c_void_p)(str(path), None, ct.byref(iid), ct.byref(factory))
            try:
                if hr >= 0 and factory and method(factory, 3, ct.c_long, Size, wt.DWORD, ct.c_void_p)(
                        factory, Size(256, 144), 8, ct.byref(bitmap)) >= 0 and bitmap:
                    bm = Bitmap()
                    get_object = api(gdi, "GetObjectW", ct.c_int, ct.c_void_p, ct.c_int, ct.c_void_p)
                    if get_object(bitmap, ct.sizeof(bm), ct.byref(bm)) and 0 < bm.width <= 1024 and 0 < bm.height <= 1024:
                        dc = api(gdi, "CreateCompatibleDC", ct.c_void_p, ct.c_void_p)(None)
                        try:
                            info = BitmapInfo()
                            info.size = 40
                            info.width, info.height, info.planes, info.bits = bm.width, -bm.height, 1, 32
                            pixels = ct.create_string_buffer(bm.width * bm.height * 4)
                            rows = api(gdi, "GetDIBits", ct.c_int, ct.c_void_p, ct.c_void_p,
                                       wt.UINT, wt.UINT, ct.c_void_p, ct.c_void_p, wt.UINT)(
                                           dc, bitmap, 0, bm.height, pixels, ct.byref(info), 0)
                            if rows == bm.height:
                                image = QImage(pixels.raw, bm.width, bm.height, bm.width * 4, QImage.Format_RGB32).copy()
                                if image.save(str(thumbnail), "PNG"):
                                    result["thumbnail"] = True
                        finally:
                            if dc:
                                api(gdi, "DeleteDC", wt.BOOL, ct.c_void_p)(dc)
            finally:
                if bitmap:
                    api(gdi, "DeleteObject", wt.BOOL, ct.c_void_p)(bitmap)
                release(factory)
    finally:
        api(ole, "CoUninitialize", None)()
    return result


class LocalMediaLoader(QObject):
    ready = Signal(str, str, object)

    def __init__(self, cache: Path, parent=None):
        super().__init__(parent)
        self.cache = cache
        self.jobs = queue.Queue(maxsize=32)
        self.pending = set()
        self.memory = OrderedDict()
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.started = False
        self.writes = 0

    def request(self, path: str, signature: str, thumbnail: bool) -> dict | None:
        key = (signature, thumbnail)
        with self.lock:
            if key in self.memory:
                self.memory.move_to_end(key)
                return self.memory[key]
            if self.stopped.is_set() or signature in self.pending:
                return None
            try:
                self.jobs.put_nowait((path, signature, thumbnail))
            except queue.Full:
                return None
            self.pending.add(signature)
            if not self.started:
                self.started = True
                for _ in range(2):
                    threading.Thread(target=self.run, daemon=True, name="local-media").start()
        return None

    def shutdown(self):
        self.stopped.set()

    def run(self):
        while not self.stopped.is_set():
            try:
                path, signature, thumbnail = self.jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                data = self.load(Path(path), signature, thumbnail)
            except Exception:
                data = {}
            data["thumbnail_checked"] = thumbnail
            with self.lock:
                self.pending.discard(signature)
                self.memory[(signature, thumbnail)] = data
                if thumbnail:
                    self.memory[(signature, False)] = data
                while len(self.memory) > 256:
                    self.memory.popitem(last=False)
            if not self.stopped.is_set():
                try:
                    self.ready.emit(path, signature, data)
                except RuntimeError:
                    return

    def load(self, path: Path, signature: str, thumbnail: bool) -> dict:
        from youtube_sync_engine import file_signature

        if file_signature(path) != signature:
            return {}
        key = hashlib.sha256(signature.encode("utf-8")).hexdigest()
        metadata, image = self.cache / f"{key}.json", self.cache / f"{key}.png"
        data = {}
        try:
            saved = json.loads(metadata.read_text(encoding="utf-8"))
            if saved.get("version") == 1:
                data = {k: v for k, v in saved.items() if k in {"width", "height", "seconds", "fps"}
                        and type(v) in (int, float) and 0 <= v < 1e12}
                empty_expired = (not any(data.values()) or (thumbnail and not saved.get("thumbnail"))) and time.time() - saved.get("checked_at", 0) > 86400
                if not empty_expired and (not thumbnail or (saved.get("thumbnail_checked") and (not saved.get("thumbnail") or image.exists()))):
                    if saved.get("thumbnail") and image.exists():
                        data["thumbnail"] = str(image)
                    return data
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        self.cache.mkdir(parents=True, exist_ok=True)
        temporary = image.with_suffix(".tmp.png")
        try:
            data = windows_media(path, temporary if thumbnail else None)
            if file_signature(path) != signature:
                return {}
            if data.get("thumbnail"):
                temporary.replace(image)
            saved = dict(data, version=1, thumbnail_checked=thumbnail, checked_at=time.time())
            temp_meta = metadata.with_suffix(".tmp")
            try:
                temp_meta.write_text(json.dumps(saved), encoding="utf-8")
                temp_meta.replace(metadata)
            finally:
                temp_meta.unlink(missing_ok=True)
            if data.get("thumbnail"):
                data["thumbnail"] = str(image)
            # Bound persistent cache size without doing directory work on the GUI thread.
            try:
                self.writes += 1
                if self.writes % 32 == 1:
                    entries = sorted(self.cache.glob("*.json"), key=lambda p: p.stat().st_mtime)
                    for old in entries[:-512]:
                        old.unlink(missing_ok=True)
                        old.with_suffix(".png").unlink(missing_ok=True)
            except OSError:
                pass
            return data
        finally:
            temporary.unlink(missing_ok=True)
