"""Windows fullscreen shell notification and Escape for a hosted browser surface."""

import ctypes
from ctypes import wintypes
import os
import uuid


def mark_fullscreen(hwnd, enabled):
    if os.name != "nt":
        return False
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value != os.getpid():
        return False
    ole = ctypes.WinDLL("ole32")
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole.CoInitializeEx.restype = ctypes.c_long
    ole.CoCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                    ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    ole.CoCreateInstance.restype = ctypes.c_long
    initialized = ole.CoInitializeEx(None, 2)
    if initialized < 0 and initialized != -2147417850:  # RPC_E_CHANGED_MODE: Qt initialized COM already.
        return False
    interface = ctypes.c_void_p()
    clsid = ctypes.create_string_buffer(uuid.UUID("56fdf344-fd6d-11d0-958a-006097c9a090").bytes_le)
    iid = ctypes.create_string_buffer(uuid.UUID("602d4995-b13a-429b-a66e-1935e44f4317").bytes_le)
    try:
        if ole.CoCreateInstance(clsid, None, 1, iid, ctypes.byref(interface)) < 0:
            return False
        table = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        initialize = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(table[3])
        mark = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.HWND, wintypes.BOOL)(table[8])
        return initialize(interface) >= 0 and mark(interface, hwnd, bool(enabled)) >= 0
    except OSError:
        return False
    finally:
        if interface:
            table = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(table[2])(interface)
        if initialized in (0, 1):
            ole.CoUninitialize()


def escape_pressed(hwnd):
    if os.name != "nt":
        return False
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user.GetAncestor.restype = wintypes.HWND
    user.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user.GetAsyncKeyState.restype = ctypes.c_short
    # The foreign browser has its own event loop. Only inspect Escape while our
    # fullscreen window (or its hosted child) actually owns the foreground.
    foreground = user.GetForegroundWindow()
    return bool(foreground and user.GetAncestor(foreground, 2) == hwnd
                and user.GetAsyncKeyState(0x1b) & 0x8000)
