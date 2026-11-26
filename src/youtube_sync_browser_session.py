"""A dedicated real-browser session. Never reads cookies or browser credentials."""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import secrets


def find_browser() -> Path | None:
    if os.name != "nt":
        return None
    roots = [Path(os.environ.get("PROGRAMFILES", "C:/Program Files")),
             Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))]
    local = os.environ.get("LOCALAPPDATA")
    candidates = [root / "Google/Chrome/Application/chrome.exe" for root in roots]
    if local:
        candidates.append(Path(local) / "Google/Chrome/Application/chrome.exe")
    candidates += [root / "Microsoft/Edge/Application/msedge.exe" for root in roots]
    return next((path for path in candidates if path.is_file()), None)


def playback_profile(base: Path, browser: Path) -> Path:
    profile = Path(base).resolve() / "playback-session" / browser.stem.lower()
    profile.mkdir(parents=True, exist_ok=True)
    return profile


def browser_arguments(base: Path, browser: Path) -> list[str]:
    profile = playback_profile(base, browser)
    return [str(browser), "--user-data-dir=" + str(profile), "--no-first-run", "--no-default-browser-check"]


def start_browser(base: Path, browser: Path, options):
    from youtube_sync_browser_pipe import launch_browser
    return launch_browser(browser_arguments(base, browser) + list(options), playback_profile(base, browser))


def open_playback_session(base: Path):
    browser = find_browser()
    if browser is None:
        raise OSError("Instala Chrome o Microsoft Edge para gestionar la sesión de reproducción.")
    return start_browser(base, browser, ["--new-window", "https://www.youtube.com/"])


class BrowserWindow:
    def __init__(self, title: str, browser: Path):
        self.title, self.browser = title, Path(browser).resolve()
        self.hwnd, self.pid = None, None
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = [self.callback_type, wintypes.LPARAM]
        self.user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.IsWindow.argtypes = [wintypes.HWND]
        self.user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.get_style = getattr(self.user, "GetWindowLongPtrW", self.user.GetWindowLongW)
        self.set_style = getattr(self.user, "SetWindowLongPtrW", self.user.SetWindowLongW)
        self.get_style.argtypes, self.get_style.restype = [wintypes.HWND, ctypes.c_int], ctypes.c_ssize_t
        self.set_style.argtypes, self.set_style.restype = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t], ctypes.c_ssize_t
        self.user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.user.SetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
        self.user.GetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user.GetPropW.restype = wintypes.HANDLE
        self.user.RemovePropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.GetDpiForWindow.argtypes = [wintypes.HWND]
        self.user.GetDpiForWindow.restype = wintypes.UINT
        self.user.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                                 wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
        self._property_name = None

    def text(self, hwnd):
        text = ctypes.create_unicode_buffer(self.user.GetWindowTextLengthW(hwnd) + 1)
        self.user.GetWindowTextW(hwnd, text, len(text))
        return text.value

    def window_pid(self, hwnd):
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value

    def find(self):
        matches = []
        @self.callback_type
        def visit(hwnd, _):
            if self.title not in self.text(hwnd):
                return True
            name = ctypes.create_unicode_buffer(128)
            self.user.GetClassNameW(hwnd, name, len(name))
            if name.value != "Chrome_WidgetWin_1":
                return True
            pid = self.window_pid(hwnd)
            process = self.kernel.OpenProcess(0x1000, False, pid)
            if process:
                try:
                    path, size = ctypes.create_unicode_buffer(32768), wintypes.DWORD(32768)
                    if self.kernel.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)) and Path(path.value).resolve() == self.browser:
                        matches.append((hwnd, pid))
                finally:
                    self.kernel.CloseHandle(process)
            return True
        self.user.EnumWindows(visit, 0)
        if matches:
            self.hwnd, self.pid = matches[0]
        return self.hwnd

    def owned(self):
        return bool(self.hwnd and self.user.IsWindow(self.hwnd)
                    and self.window_pid(self.hwnd) == self.pid
                    and (self.user.GetPropW(self.hwnd, self._property_name) == self._property_value
                         if self._property_name else self.title in self.text(self.hwnd)))

    def pin_identity(self):
        if not self.owned():
            return False
        name, value = "YouTubeSync." + secrets.token_hex(16), secrets.randbelow(0x7ffffffe) + 1
        if not self.user.SetPropW(self.hwnd, name, value):
            return False
        self._property_name, self._property_value = name, value
        return True

    def strip_frame(self):
        if self.owned():
            style = self.get_style(self.hwnd, -16)
            decorations = 0x00C00000 | 0x00040000 | 0x00020000 | 0x00010000 | 0x00080000 | 0x80000000
            wanted = (style & ~decorations) | 0x40000000
            if style != wanted:
                self.set_style(self.hwnd, -16, wanted)
                self.user.SetWindowPos(self.hwnd, None, 0, 0, 0, 0, 0x0037)

    def caption_height(self):
        if not self.owned():
            return 0
        rect = wintypes.RECT()
        if not self.user.GetWindowRect(self.hwnd, ctypes.byref(rect)):
            return 0
        x = (rect.left + rect.right) // 2
        # Crop only a caption confirmed by Windows, never the YouTube controls.
        def hit_at(offset):
            hit = ctypes.c_size_t()
            point = ((rect.top + offset) & 0xffff) << 16 | (x & 0xffff)
            if not self.user.SendMessageTimeoutW(self.hwnd, 0x0084, 0, point, 2, 15, ctypes.byref(hit)):
                return None
            return hit.value
        dpi = self.user.GetDpiForWindow(self.hwnd) or 96
        scale = dpi / 96
        start, end = round(8 * scale), round(80 * scale)
        if hit_at(start) != 2 or hit_at(end) in (None, 2):
            return 0
        low, high = start, end
        while high - low > 1:
            middle = (low + high) // 2
            hit = hit_at(middle)
            if hit is None:
                return 0
            if hit == 2:
                low = middle
            else:
                high = middle
        return high

    def close(self):
        if self.owned():
            if getattr(self, "_property_name", None):
                self.user.RemovePropW(self.hwnd, self._property_name)
                self._property_name = None
            self.user.ShowWindow(self.hwnd, 0)
            self.user.PostMessageW(self.hwnd, 0x0010, 0, 0)
        self.hwnd, self.pid = None, None
