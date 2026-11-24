import http.client
import json
import queue
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

import test_layout as fixture
from youtube_sync_browser_player import NativeBrowserPlayer, PlayerDocument
from youtube_sync_browser_session import BrowserWindow, browser_arguments, open_playback_session
from youtube_sync_youtube_player import EmbeddedYouTubePlayer, player_html

VIDEO = "aB3_dE6-fG9"


class SessionSafetyTests(unittest.TestCase):
    def test_browser_profile_is_private_to_app_and_not_a_personal_chrome_profile(self):
        with tempfile.TemporaryDirectory(dir=fixture.ROOT) as folder:
            browser = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
            arguments = browser_arguments(Path(folder), browser)
            profile = next(arg.split("=", 1)[1] for arg in arguments if arg.startswith("--user-data-dir="))
            self.assertEqual(Path(profile), Path(folder).resolve() / "playback-session/chrome")
            self.assertTrue(Path(profile).is_dir())
            self.assertNotIn("--remote-debugging", " ".join(arguments))
            self.assertNotIn("--disable-web-security", arguments)

    def test_settings_login_and_player_use_the_same_dedicated_profile(self):
        with tempfile.TemporaryDirectory(dir=fixture.ROOT) as folder, patch("youtube_sync_browser_session.find_browser", return_value=Path("chrome.exe")), patch("youtube_sync_browser_session.subprocess.Popen") as launch:
            open_playback_session(Path(folder))
            arguments = launch.call_args.args[0]
            self.assertEqual(arguments[-2:], ["--new-window", "https://www.youtube.com/"])
            self.assertIn("--user-data-dir=" + str(Path(folder).resolve() / "playback-session/chrome"), arguments)
            self.assertFalse(launch.call_args.kwargs.get("shell", False))

    def test_chrome_and_edge_do_not_share_the_same_profile_directory(self):
        with tempfile.TemporaryDirectory(dir=fixture.ROOT) as folder:
            chrome = browser_arguments(Path(folder), Path("chrome.exe"))
            edge = browser_arguments(Path(folder), Path("msedge.exe"))
            self.assertNotEqual(chrome[1], edge[1])

    def test_frame_changes_and_close_only_apply_to_the_owned_window(self):
        window = BrowserWindow.__new__(BrowserWindow)
        window.hwnd, window.pid = 123, 456
        window.user = Mock()
        window.get_style = Mock(return_value=0x90CF0000)
        window.set_style = Mock()
        window.owned = Mock(return_value=True)
        window.strip_frame()
        style = window.set_style.call_args.args[2]
        self.assertTrue(style & 0x40000000)
        self.assertFalse(style & 0x00C00000)
        window.close()
        window.user.PostMessageW.assert_called_once_with(123, 0x0010, 0, 0)
        window.owned.return_value = False
        window.close()
        self.assertEqual(window.user.PostMessageW.call_count, 1)


class LocalDocumentTests(unittest.TestCase):
    def setUp(self):
        self.document = PlayerDocument(VIDEO)
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.document.close(grace=0)
        self.document.thread.join(timeout=3)

    def request(self, method, path, body=None, origin=None, host=None):
        parsed = urlsplit(self.document.origin)
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
        try:
            headers = {"Host": host or self.document.host}
            if origin:
                headers["Origin"] = origin
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            connection.close()

    def test_only_the_token_document_is_served_and_referrer_does_not_leak_the_token(self):
        status, body, headers = self.request("GET", self.document.route)
        self.assertEqual(status, 200)
        self.assertIn(self.document.title.encode(), body)
        self.assertIn(self.document.origin.encode(), body)
        self.assertEqual(headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertNotIn(b"access_token", body)
        self.assertEqual(self.request("GET", "/")[0], 404)
        self.assertEqual(self.request("GET", self.document.route, host="evil.test")[0], 403)

    def test_valid_events_are_queued_but_cross_origin_and_wrong_id_are_rejected(self):
        route = self.document.route + "/event"
        data = {"id": VIDEO, "type": "state", "value": 1}
        self.assertEqual(self.request("POST", route, json.dumps(data), self.document.origin)[0], 204)
        self.assertEqual(self.document.events.get_nowait(), data)
        self.assertEqual(self.request("POST", route, json.dumps(data), "https://evil.test")[0], 403)
        data["id"] = "zY8_xW5-vU2"
        self.assertEqual(self.request("POST", route, json.dumps(data), self.document.origin)[0], 400)
        self.assertTrue(self.document.events.empty())

    def test_invalid_or_oversized_payloads_are_rejected_and_the_queue_is_bounded(self):
        route = self.document.route + "/event"
        for data in (b"x" * 1025, b"[]", b"not json", json.dumps({"id": VIDEO, "type": "state", "value": True}).encode()):
            self.assertEqual(self.request("POST", route, data, self.document.origin)[0], 400)
        self.assertEqual(self.document.events.maxsize, 100)

    def test_close_sends_a_stop_signal_before_server_shutdown(self):
        self.document.close(grace=1)
        status, body, _ = self.request("GET", self.document.route + "/control")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"stop": True, "play": False})
        html = self.document.html.decode()
        self.assertIn("window.player.mute()", html)
        self.assertIn("window.player.stopVideo()", html)
        self.assertIn(".catch(stopPlayback)", html)
        self.assertIn('"autoplay": 0', html)

    def test_template_escapes_title_and_disallows_remote_callback_endpoints(self):
        html = player_html("AAAOPTIONS_", title="<script>no</script>")
        self.assertIn('"AAAOPTIONS_"', html)
        self.assertIn("&lt;script&gt;", html)
        for kwargs in ({"origin": "https://evil.test"}, {"event_route": "https://evil.test"}, {"control_route": "//evil.test"}):
            with self.assertRaises(ValueError):
                player_html(VIDEO, **kwargs)


class NativePlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=fixture.ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.player = NativeBrowserPlayer(Path(self.temporary.name))
        self.addCleanup(self.player.release)
        self.document = Mock(events=queue.Queue(), title="our-token", url="http://127.0.0.1/player")

    def load(self, attached=True):
        with patch("youtube_sync_browser_player.find_browser", return_value=Path("chrome.exe")), \
                patch("youtube_sync_browser_player.PlayerDocument", return_value=self.document), \
                patch("youtube_sync_browser_player.BrowserWindow") as window, \
                patch("youtube_sync_browser_player.subprocess.Popen") as process:
            window.return_value.find.return_value = None
            process.return_value.poll.return_value = None
            self.player.load_video(VIDEO)
        self.player.poll.stop()
        if attached:
            self.player.container = fixture.ui.QWidget(self.player)
            self.player.layout.addWidget(self.player.container)
        return window.return_value, process.return_value

    def test_no_confirmation_event_is_emitted_before_the_browser_is_hosted(self):
        self.load(attached=False)
        played = Mock()
        self.player.reviewed.connect(played)
        self.document.events.put({"id": VIDEO, "type": "state", "value": 1})
        self.player.check()
        played.assert_not_called()
        self.assertFalse(self.document.events.empty())

    def test_ready_does_not_unlock_confirmation_but_playing_does(self):
        self.load()
        played = Mock()
        self.player.reviewed.connect(played)
        self.document.events.put({"id": VIDEO, "type": "ready", "value": 0})
        self.player.check()
        played.assert_not_called()
        self.document.events.put({"id": VIDEO, "type": "state", "value": 1})
        self.player.check()
        played.assert_called_once_with(VIDEO)

    def test_close_removes_our_window_without_killing_the_shared_session_browser(self):
        window, process = self.load()
        self.player.release()
        self.document.close.assert_called_once()
        window.close.assert_called_once()
        process.kill.assert_not_called()
        process.terminate.assert_not_called()
        self.assertFalse(self.player.poll.isActive())

    def test_private_error_requests_session_review_without_marking_a_match(self):
        self.load()
        failed, played = Mock(), Mock()
        self.player.failed.connect(failed)
        self.player.reviewed.connect(played)
        self.document.events.put({"id": VIDEO, "type": "error", "value": 100})
        self.player.check()
        self.assertIn("Ajustes", failed.call_args.args[0])
        played.assert_not_called()

    def test_wrapper_prefers_native_and_never_runs_the_qt_probe_for_that_path(self):
        wrapper = EmbeddedYouTubePlayer()
        wrapper.native_base = Path(self.temporary.name)
        with patch("youtube_sync_browser_session.find_browser", return_value=Path("chrome.exe")), \
                patch.object(NativeBrowserPlayer, "load_video") as load, \
                patch("youtube_sync_youtube_player.QProcess") as process:
            wrapper.load_video(VIDEO)
            self.assertIsNotNone(wrapper.native)
            load.assert_called_once_with(VIDEO)
            process.assert_not_called()
            wrapper.release()

    def test_settings_session_action_uses_the_app_data_directory_not_the_test_profile(self):
        store = Mock(base=Path(self.temporary.name))
        settings = fixture.ui.SettingsDialog(store, fixture.ui.engine.Config())
        try:
            with patch.object(fixture.ui, "open_playback_session") as session:
                settings.playback_login.click()
            session.assert_called_once_with(store.base)
            self.assertNotIn("Conectado", settings.playback_session_status.text())
        finally:
            settings.close()

    def test_settings_at_minimum_size_do_not_squash_the_youtube_fields(self):
        store = Mock(base=Path(self.temporary.name))
        settings = fixture.ui.SettingsDialog(store, fixture.ui.engine.Config())
        try:
            settings.findChild(fixture.ui.QTabWidget).setCurrentIndex(1)
            settings.resize(900, 650)
            settings.show()
            self.app.processEvents()
            for control in (settings.oauth, settings.privacy, settings.category, settings.playlist_combo):
                self.assertGreaterEqual(control.height(), 38)
                self.assertTrue(settings.rect().contains(control.mapTo(settings, control.rect().bottomRight())))
            save = next(button for button in settings.findChildren(fixture.ui.QPushButton) if button.text() == "Guardar")
            self.assertTrue(settings.rect().contains(save.mapTo(settings, save.rect().bottomRight())))
            settings.settings_search.setText("sesión")
            self.app.processEvents()
            self.assertEqual(settings.findChild(fixture.ui.QTabWidget).currentIndex(), 2)
            self.assertTrue(settings.playback_login.isVisible())
        finally:
            settings.close()


if __name__ == "__main__":
    unittest.main()
