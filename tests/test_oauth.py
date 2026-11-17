import queue
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from test_layout import ui

engine = ui.engine


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.folder = Path(self.directory.name)
        self.token = self.folder / "token.json"
        self.secret = self.folder / "client.json"
        self.secret.write_text("{}", encoding="utf-8")
        self.store = Mock()
        self.store.token_path_for.return_value = self.token
        self.config = engine.Config(client_secret_path=str(self.secret))
        self.creds = Mock(valid=True, expired=False, refresh_token="test-only")
        self.creds.has_scopes.return_value = True
        self.creds.to_json.return_value = '{"token": "test-only"}'
        engine._oauth_retry_after.clear()

    def tearDown(self):
        engine._oauth_retry_after.clear()
        self.directory.cleanup()

    def client(self):
        return engine.YouTubeClient(self.store, self.config, Mock())

    def test_concurrent_clients_only_authorize_once(self):
        flow = Mock()
        started = threading.Event()
        release = threading.Event()

        def consent(**kwargs):
            started.set()
            release.wait(2)
            return self.creds

        flow.run_local_server.side_effect = consent
        with patch.object(engine.InstalledAppFlow, "from_client_secrets_file", return_value=flow), \
                patch.object(engine.Credentials, "from_authorized_user_file", return_value=self.creds), \
                patch.object(engine, "build"), patch.object(engine, "AuthorizedHttp"), \
                patch.object(engine.httplib2, "Http"):
            with ThreadPoolExecutor(max_workers=3) as pool:
                first = pool.submit(self.client().service)
                self.assertTrue(started.wait(2))
                second = pool.submit(self.client().service)
                third = pool.submit(self.client().service)
                release.set()
                for future in (first, second, third):
                    future.result(timeout=5)
        flow.run_local_server.assert_called_once()
        self.assertEqual(flow.run_local_server.call_args.kwargs["timeout_seconds"], 180)
        self.assertTrue(self.token.exists())
        self.assertEqual(list(self.folder.glob("*.tmp")), [])

    def test_refresh_network_failure_keeps_token_and_does_not_open_browser(self):
        self.token.write_text("original-token", encoding="utf-8")
        self.creds.valid = False
        self.creds.expired = True
        self.creds.refresh.side_effect = ConnectionError("offline")
        with patch.object(engine.Credentials, "from_authorized_user_file", return_value=self.creds), \
                patch.object(engine.InstalledAppFlow, "from_client_secrets_file") as browser:
            with self.assertRaises(ConnectionError):
                self.client().service()
            with self.assertRaisesRegex(RuntimeError, "espera breve"):
                self.client().service()
        browser.assert_not_called()
        self.assertEqual(self.token.read_text(), "original-token")
        self.creds.refresh.assert_called_once()

    def test_revoked_token_requests_new_consent(self):
        self.token.write_text("original-token", encoding="utf-8")
        expired = Mock(valid=False, expired=True, refresh_token="test-only")
        expired.has_scopes.return_value = True
        expired.refresh.side_effect = engine.RefreshError("invalid_grant")
        flow = Mock()
        flow.run_local_server.return_value = self.creds
        with patch.object(engine.Credentials, "from_authorized_user_file", return_value=expired), \
                patch.object(engine.InstalledAppFlow, "from_client_secrets_file", return_value=flow), \
                patch.object(engine, "build"), patch.object(engine, "AuthorizedHttp"), \
                patch.object(engine.httplib2, "Http"):
            self.client().service()
        flow.run_local_server.assert_called_once()
        self.assertEqual(self.token.read_text(), self.creds.to_json())

    def test_repeated_mode_does_not_log_or_wake_again(self):
        events = queue.Queue()
        worker = engine.SyncWorker(self.store, lambda: self.config, events)
        worker.set_enabled(True)
        worker.wake_event.clear()
        worker.set_enabled(True)
        self.assertFalse(worker.wake_event.is_set())
        self.assertEqual(events.qsize(), 1)


if __name__ == "__main__":
    unittest.main()
