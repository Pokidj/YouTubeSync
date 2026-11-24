"""A dedicated real-browser session. Never reads cookies or browser credentials."""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess


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


def browser_arguments(base: Path, browser: Path) -> list[str]:
    profile = Path(base).resolve() / "playback-session" / browser.stem.lower()
    profile.mkdir(parents=True, exist_ok=True)
    return [str(browser), "--user-data-dir=" + str(profile), "--no-first-run", "--no-default-browser-check"]


def open_playback_session(base: Path):
    browser = find_browser()
    if browser is None:
        raise OSError("Instala Chrome o Microsoft Edge para gestionar la sesión de reproducción.")
    arguments = browser_arguments(base, browser) + ["--new-window", "https://www.youtube.com/"]
    return subprocess.Popen(arguments, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
                    and self.window_pid(self.hwnd) == self.pid and self.title in self.text(self.hwnd))

    def strip_frame(self):
        if self.owned():
            style = self.get_style(self.hwnd, -16)
            decorations = 0x00C00000 | 0x00040000 | 0x00020000 | 0x00010000 | 0x00080000 | 0x80000000
            self.set_style(self.hwnd, -16, (style & ~decorations) | 0x40000000)
            self.user.SetWindowPos(self.hwnd, None, 0, 0, 0, 0, 0x0037)

    def close(self):
        if self.owned():
            self.user.ShowWindow(self.hwnd, 0)
            self.user.PostMessageW(self.hwnd, 0x0010, 0, 0)
        self.hwnd, self.pid = None, None
