import ctypes
import json
import tempfile
import unittest
from ctypes import wintypes
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from youtube_sync_browser_session import BrowserWindow
from youtube_sync_first_party_player import FirstPartyPlayer, owned_target, media_expression
from youtube_sync_player_controls import command, telemetry, iframe_command
from youtube_sync_transport_ui import TransportControls
from fake_youtube_player import FakeYouTubePlayer

VIDEO = "aB3_dE6-fG9"
DATA = {"position": 20, "duration": 100, "volume": 65, "playing": True, "muted": False}


class PlayerValueTests(unittest.TestCase):
    def test_commands_are_small_validated_values_not_javascript(self):
        for action, value in (("seek", -1), ("seek", float("nan")), ("volume", 101),
                              ("relative", 61), ("volume", True), ("mute", 1), ("execute", "alert(1)")):
            with self.subTest(action=action, value=value), self.assertRaises(ValueError):
                command(action, value)
        self.assertIn("setVolume(65)", iframe_command("volume", 65))
        self.assertIn("getCurrentTime()+-10", iframe_command("relative", -10))

    def test_progress_rejects_infinite_numbers_boolean_times_and_missing_states(self):
        for changed in ({"position": True}, {"duration": float("inf")}, {"volume": -1}, {"playing": 1}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                telemetry(dict(DATA, **changed))
        self.assertEqual(telemetry(DATA), DATA)

    def test_only_our_exact_bootstrap_target_can_be_selected(self):
        bootstrap = "http://127.0.0.1:1111/our-token"
        own = {"type": "page", "targetId": "our-tab", "url": bootstrap}
        self.assertEqual(owned_target([own], bootstrap), "our-tab")
        for targets in ([dict(own, type="browser")], [dict(own, url="https://accounts.google.com")],
                        [own, own], [dict(own, targetId="../other")], {}, ["bad"]):
            self.assertIsNone(owned_target(targets, bootstrap))

    def test_media_script_only_operates_on_selected_youtube_video_without_reading_auth(self):
        script = media_expression(VIDEO, "relative", -10)
        self.assertIn("location.origin!=='https://www.youtube.com'", script)
        self.assertIn("/embed/" + VIDEO, script)
        self.assertIn("p.getCurrentTime()+-10", script)
        self.assertIn("v.readyState===0", script)
        for forbidden in ("document.cookie", "localStorage", "sessionStorage", "fetch(", "password", "access_token"):
            self.assertNotIn(forbidden, script)
        self.assertLess(script.index("ad-showing"), script.index("p.seekTo"))
        self.assertNotIn("v.currentTime=", script)


class TransportWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        self.player = FakeYouTubePlayer()
        self.player.load_video(VIDEO)
        self.controls = TransportControls(self.player)
        self.addCleanup(self.controls.close)
        self.controls.set_active(True)

    def test_controls_wait_for_real_progress_before_enabling(self):
        self.assertFalse(self.controls.isEnabled())
        self.player.telemetry.emit(DATA)
        self.assertTrue(self.controls.isEnabled())
        self.assertEqual(self.controls.seek.value(), 200)
        self.assertEqual(self.controls.volume.value(), 65)
        self.assertEqual(self.controls.time.text(), "0:20 / 1:40")
        self.assertEqual(self.player.commands, [])

    def test_seek_back_forward_pause_and_volume_reach_the_same_player(self):
        self.player.telemetry.emit(DATA)
        self.controls.back.click()
        self.controls.forward.click()
        self.controls.toggle.click()
        self.controls.seek.setValue(500)
        self.controls.commit_seek()
        self.controls.volume.setValue(30)
        self.controls.commit_volume()
        self.controls.mute.click()
        self.assertEqual(self.player.commands, [("relative", -10), ("relative", 10), ("pause", None),
                                                ("seek", 50), ("volume", 30), ("mute", False), ("mute", True)])

    def test_release_disables_controls_and_ignores_stale_progress(self):
        self.player.telemetry.emit(DATA)
        self.controls.set_active(False)
        self.player.telemetry.emit(DATA)
        self.assertFalse(self.controls.isEnabled())
        self.assertIsNone(self.controls.last_data)
        self.assertFalse(self.controls.seek_timer.isActive())


class FirstPartyConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.client = FirstPartyPlayer(Path(self.temporary.name), "http://127.0.0.1:1111/our-random-token", VIDEO)
        self.addCleanup(self.client.release)

    def test_discovery_ignores_other_tabs_and_their_session_pages(self):
        pipe = Mock()
        self.client.targets_finished(pipe, {"result": {"targetInfos": [
            {"type": "page", "url": "https://accounts.google.com/", "targetId": "other"}]}})
        pipe.request.assert_not_called()

    def test_private_media_error_never_becomes_successful_playback(self):
        failure, progress = Mock(), Mock()
        self.client.failed.connect(failure)
        self.client.telemetry.connect(progress)
        self.client.pending[1] = "poll"
        self.client.on_message(json.dumps({"id": 1, "result": {"result": {"value": {"valid": True, "media": False, "error": "Private"}}}}))
        failure.assert_called_once()
        progress.assert_not_called()
        self.assertFalse(self.client.ready)

    def test_invalid_progress_and_advertising_do_not_unlock_controls(self):
        progress, availability = Mock(), Mock()
        self.client.telemetry.connect(progress)
        self.client.available.connect(availability)
        self.client.pending[1] = "poll"
        self.client.on_message(json.dumps({"id": 1, "result": {"result": {"value": dict(DATA, valid=True, media=True, volume=-1)}}}))
        self.assertFalse(self.client.ready)
        self.client.pending[2] = "poll"
        self.client.on_message(json.dumps({"id": 2, "result": {"result": {"value": {"valid": True, "media": False, "advertising": True}}}}))
        progress.assert_not_called()
        availability.assert_called_once_with(False)

    def test_private_pipe_attaches_only_to_our_target_and_uses_the_selected_session(self):
        pipe, messages = Mock(), []
        pipe.alive.return_value = True
        def receive(method, params, callback, session_id=None):
            messages.append((method, params, session_id))
            if method == "Target.getTargets":
                result = {"targetInfos": [{"type": "page", "targetId": "owned", "url": self.client.bootstrap}]}
            elif method == "Target.attachToTarget":
                result = {"sessionId": "our-session"}
            elif method == "Runtime.evaluate":
                result = {"result": {"value": dict(DATA, valid=True, media=True)}}
            else:
                result = {}
            callback({"result": result})
            return True
        pipe.request.side_effect = receive
        with patch("youtube_sync_first_party_player.connections_for", return_value=[pipe]):
            self.client.tick()
            self.client.tick()
        self.assertTrue(self.client.ready)
        navigate = next(item for item in messages if item[0] == "Page.navigate")
        self.assertEqual(navigate[2], "our-session")
        self.assertTrue(navigate[1]["url"].startswith("https://www.youtube.com/embed/" + VIDEO))
        self.assertEqual(navigate[1]["referrer"], "http://127.0.0.1:1111/")
        self.assertTrue(self.client.control("volume", 40))
        self.assertIn("p.setVolume(40)", messages[-1][1]["expression"])
        self.assertTrue(messages[-1][1]["userGesture"])



class CaptionTests(unittest.TestCase):
    def window(self, caption_height, dpi=96):
        window = BrowserWindow.__new__(BrowserWindow)
        window.hwnd = 123
        window.user = Mock()
        window.user.GetDpiForWindow.return_value = dpi
        window.owned = Mock(return_value=True)
        def rect(_hwnd, pointer):
            value = ctypes.cast(pointer, ctypes.POINTER(wintypes.RECT)).contents
            value.left, value.top, value.right, value.bottom = 100, 200, 900, 800
            return True
        def hit(_hwnd, _message, _param, point, _flags, _timeout, pointer):
            offset = (point >> 16 & 0xffff) - 200
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_size_t))[0] = 2 if offset < caption_height else 1
            return True
        window.user.GetWindowRect.side_effect = rect
        window.user.SendMessageTimeoutW.side_effect = hit
        return window

    def test_only_a_confirmed_native_caption_is_cropped_at_each_dpi(self):
        self.assertEqual(self.window(0).caption_height(), 0)
        self.assertEqual(self.window(32).caption_height(), 32)
        self.assertEqual(self.window(48, 144).caption_height(), 48)

    def test_no_caption_query_or_close_on_foreign_window(self):
        window = self.window(32)
        window.owned.return_value = False
        self.assertEqual(window.caption_height(), 0)
        window.user.SendMessageTimeoutW.assert_not_called()

    def test_random_windows_property_pins_ownership_when_the_video_changes_title(self):
        window = self.window(32)
        self.assertTrue(window.pin_identity())
        window.pid = 778
        window.user.IsWindow.return_value = True
        window.window_pid = Mock(return_value=778)
        window.user.GetPropW.return_value = window._property_value
        window.text = Mock(return_value="New YouTube title")
        window.owned = BrowserWindow.owned.__get__(window)
        self.assertTrue(window.owned())
        window.window_pid.return_value = 779
        self.assertFalse(window.owned())
        window.close()
        window.user.PostMessageW.assert_not_called()
