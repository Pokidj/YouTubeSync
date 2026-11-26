import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_layout as fixture
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from fake_youtube_player import FakeYouTubePlayer
import youtube_sync_channel_ui as channel
import youtube_sync_fullscreen as native


class FullscreenPlatformTests(unittest.TestCase):
    def test_non_windows_does_not_call_native_apis(self):
        with patch.object(native.os, "name", "posix"):
            self.assertFalse(native.mark_fullscreen(123, True))
            self.assertFalse(native.escape_pressed(123))

    def test_escape_is_ignored_if_another_application_has_focus(self):
        user = Mock()
        user.GetForegroundWindow.return_value = 10
        user.GetAncestor.return_value = 999
        with patch.object(native.os, "name", "nt"), patch.object(native.ctypes, "WinDLL", return_value=user):
            self.assertFalse(native.escape_pressed(123))
        user.GetAsyncKeyState.assert_not_called()

    def test_only_escape_down_in_our_foreground_tree_is_accepted(self):
        user = Mock()
        user.GetForegroundWindow.return_value = 10
        user.GetAncestor.return_value = 123
        with patch.object(native.os, "name", "nt"), patch.object(native.ctypes, "WinDLL", return_value=user):
            user.GetAsyncKeyState.return_value = 1
            self.assertFalse(native.escape_pressed(123))
            user.GetAsyncKeyState.return_value = -32768
            self.assertTrue(native.escape_pressed(123))
        user.GetAncestor.assert_called_with(10, 2)
        user.GetAsyncKeyState.assert_called_with(0x1b)


class NativeFullscreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def test_windows_fullscreen_covers_taskbar_and_escape_returns_to_panel(self):
        if os.name != "nt" or self.app.platformName() != "windows":
            self.skipTest("Requires the real Windows Qt platform")
        with tempfile.TemporaryDirectory() as folder, patch.object(channel, "EmbeddedYouTubePlayer", FakeYouTubePlayer):
            panel = channel.ChannelPlayback(fixture.ui.PreviewThumbnail(), Path(folder))
            panel.show()
            panel.select_video("aB3_cD6-eF9")
            try:
                panel.open_popup()
                popup = panel.popup
                QTest.qWait(400)
                hwnd = int(popup.winId())
                self.assertTrue(native.mark_fullscreen(hwnd, True))
                self.assertEqual(popup.geometry(), popup.screen().geometry())
                user = ctypes.WinDLL("user32")
                user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
                user.WindowFromPoint.argtypes = [wintypes.POINT]
                user.WindowFromPoint.restype = wintypes.HWND
                user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
                user.GetAncestor.restype = wintypes.HWND
                user.GetForegroundWindow.restype = wintypes.HWND
                rect = wintypes.RECT()
                self.assertTrue(user.GetWindowRect(hwnd, ctypes.byref(rect)))
                point = wintypes.POINT((rect.left + rect.right) // 2, rect.bottom - 24)
                hit = user.WindowFromPoint(point)
                name = ctypes.create_unicode_buffer(128)
                user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
                user.GetClassNameW(hit, name, 128)
                if user.GetAncestor(user.GetForegroundWindow(), 2) != hwnd:
                    self.skipTest("Windows denied foreground activation; use interactive fullscreen QA")
                self.assertEqual(user.GetAncestor(hit, 2), hwnd,
                                 f"Hit {name.value}; foreground={user.GetForegroundWindow()}, player={hwnd}")
                self.assertTrue(popup.transport.isVisible())
                QTest.keyClick(popup.back, Qt.Key_Escape)
                self.assertIsNone(panel.popup)
                self.assertFalse(popup.isVisible())
                self.assertEqual(panel.player.video_id, "aB3_cD6-eF9")
            finally:
                panel.stop()
                panel.close()
                panel.deleteLater()
                self.app.processEvents()
