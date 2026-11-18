import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from test_layout import ui, ROOT

engine = ui.engine


class SetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = ui.QApplication.instance() or ui.QApplication([])
        ui.apply_style(cls.app)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        with patch.object(engine, "app_dir", return_value=self.base):
            self.store = engine.Store()
        self.source = self.base / "downloaded.json"
        self.credentials = {"installed": {
            "client_id": "example.apps.googleusercontent.com", "client_secret": "test-only",
            "project_id": "test-project", "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": ["http://localhost"],
        }}
        self.source.write_text(json.dumps(self.credentials), encoding="utf-8")
        self.wizard = None

    def tearDown(self):
        if self.wizard is not None:
            self.wizard.reject()
            self.wizard.deleteLater()
        self.app.processEvents()

    def open_wizard(self, config=None):
        self.wizard = ui.SetupWizard(self.store, config or engine.Config())
        return self.wizard

    def channel_ready(self):
        wizard = self.wizard
        wizard.connection_ready(wizard._generation, {"info": {"id": "test-channel", "title": "Mi canal"},
                                "playlists": [{"id": "test-playlist", "title": "Clips"}], "avatar": b"", "warning": ""})

    def test_import_rejects_web_clients_and_untrusted_google_urls(self):
        for invalid in ({"web": self.credentials["installed"]}, {"type": "service_account"},
                        {"installed": {**self.credentials["installed"], "auth_uri": "https://accounts.google.com.example.invalid/auth"}}):
            with self.subTest(document=invalid):
                self.source.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    self.store.import_oauth_json(self.source)
        self.assertFalse((self.base / "oauth").exists())

    def test_imported_credentials_survive_removing_the_original_download(self):
        managed = self.store.import_oauth_json(self.source)
        self.source.unlink()
        self.assertTrue(managed.is_file())
        self.assertEqual(json.loads(managed.read_text()), self.credentials)
        self.assertFalse(self.store.config_path.exists())

    def test_import_migrates_a_matching_saved_authorization(self):
        config = engine.Config(client_secret_path=str(self.source))
        self.store.save_config(config)
        previous_token = self.store.token_path_for(str(self.source))
        token = {"client_id": self.credentials["installed"]["client_id"], "refresh_token": "test-refresh"}
        previous_token.write_text(json.dumps(token))
        managed = self.store.import_oauth_json(self.source)
        self.assertEqual(json.loads(self.store.token_path_for(str(managed)).read_text()), token)
        self.assertEqual(self.store.load_config().client_secret_path, str(self.source))

    def test_import_does_not_copy_an_unrelated_token(self):
        self.store.token_path_for(str(self.source)).write_text(json.dumps({"client_id": "other", "refresh_token": "test-only"}))
        managed = self.store.import_oauth_json(self.source)
        self.assertFalse(self.store.token_path_for(str(managed)).exists())

    def test_import_preserves_an_active_quota_pause(self):
        pause = {"retry_at": (datetime.now().astimezone() + timedelta(hours=1)).isoformat(), "kind": "proyecto"}
        self.store.save_service_cache(engine.api_scope(str(self.source)), "quota_general", pause)
        managed = self.store.import_oauth_json(self.source)
        self.assertEqual(self.store.api_pause(engine.api_scope(str(managed))), pause)

    def test_welcome_and_channel_confirmation_gate_the_flow(self):
        wizard = self.open_wizard()
        self.assertEqual(wizard.pages.currentIndex(), 0)
        self.assertEqual(wizard.next.text(), "Conectar mi canal")
        wizard.go(4)
        self.assertFalse(wizard.next.isEnabled())
        self.assertTrue(wizard.import_file(self.source))
        self.assertTrue(wizard.next.isEnabled())
        self.channel_ready()
        self.assertEqual(wizard.pages.currentIndex(), 5)
        self.assertFalse(wizard.next.isEnabled())
        wizard.confirm_channel.setChecked(True)
        self.assertTrue(wizard.next.isEnabled())

    def test_finish_requires_a_real_folder_and_a_completed_authorization(self):
        wizard = self.open_wizard()
        wizard.import_file(self.source)
        self.channel_ready()
        wizard.confirm_channel.setChecked(True)
        wizard.folder.setText(str(self.base / "missing-folder"))
        wizard.finish_setup()
        self.assertFalse(self.store.config_path.exists())
        wizard.folder.setText(str(self.base))
        wizard.finish_setup()
        self.assertIn("autorizacion", wizard.message.text())
        self.assertFalse(self.store.config_path.exists())

    def test_finish_saves_only_after_confirming_the_channel_and_options(self):
        wizard = self.open_wizard()
        wizard.import_file(self.source)
        wizard.staged_token.write_text('{"token":"test-only"}')
        self.channel_ready()
        wizard.confirm_channel.setChecked(True)
        wizard.folder.setText(str(self.base))
        wizard.go(6)
        wizard.playlist.setCurrentIndex(1)
        configured = Mock()
        wizard.configured.connect(configured)
        wizard.finish_setup()
        saved = self.store.load_config()
        self.assertEqual(saved.connected_channel_id, "test-channel")
        self.assertEqual(saved.connected_channel_name, "Mi canal")
        self.assertEqual(saved.playlist_id, "test-playlist")
        self.assertFalse(saved.auto_start_enabled)
        self.assertEqual(saved.watch_folder, str(self.base))
        self.assertEqual(self.store.token_path_for(saved.client_secret_path).read_text(), '{"token":"test-only"}')
        configured.assert_called_once()

    def test_cancel_does_not_change_the_active_account_or_configuration(self):
        config = engine.Config(client_secret_path=str(self.source), watch_folder=str(self.base))
        self.store.save_config(config)
        original_token = self.store.token_path_for(str(self.source))
        original_token.write_text(json.dumps({"client_id": self.credentials["installed"]["client_id"], "token": "old-account"}))
        wizard = self.open_wizard(config)
        wizard.staged_token.write_text('{"token":"new-account"}')
        wizard.reject()
        self.assertEqual(self.store.load_config(), config)
        self.assertIn("old-account", original_token.read_text())

    def test_authorization_uses_the_staged_token_and_no_embedded_browser(self):
        wizard = self.open_wizard()
        wizard.import_file(self.source)
        client = Mock()
        client.channel_info.return_value = {"id": "test-channel", "title": "Canal", "thumbnail": ""}
        client.playlists.return_value = []
        with patch.object(engine, "YouTubeClient", return_value=client) as factory:
            wizard.authorize(wizard._generation, True)
        self.assertTrue(factory.call_args.kwargs["force_authorize"])
        self.assertEqual(client.token_path, wizard.staged_token)
        self.assertNotEqual(client.token_path, self.store.token_path_for(wizard.config.client_secret_path))
        self.assertEqual(wizard.channel["id"], "test-channel")

    def test_closed_wizard_does_not_begin_an_authorization(self):
        wizard = self.open_wizard()
        wizard.reject()
        with patch.object(engine, "YouTubeClient") as client:
            wizard.authorize(0, False)
        client.assert_not_called()

    def test_late_results_do_not_replace_a_newer_connection(self):
        wizard = self.open_wizard()
        wizard._generation = 2
        wizard.connection_ready(1, {})
        self.assertIsNone(wizard.channel)

    def test_quota_failure_offers_waiting_without_confirming_a_channel(self):
        wizard = self.open_wizard()
        wizard.connection_failed(0, "Cuota API agotada")
        self.assertIsNone(wizard.channel)
        self.assertIn("cuando se renueve la cuota", wizard.message.text())
        self.assertNotIn("usuario de prueba", wizard.message.text())

    def test_save_failure_restores_the_previous_active_token(self):
        wizard = self.open_wizard()
        wizard.import_file(self.source)
        target = self.store.token_path_for(wizard.config.client_secret_path)
        target.write_text("old-token")
        wizard.staged_token.write_text("new-token")
        self.channel_ready()
        wizard.confirm_channel.setChecked(True)
        wizard.folder.setText(str(self.base))
        with patch.object(self.store, "save_config", side_effect=OSError("disk full")):
            wizard.finish_setup()
        self.assertEqual(target.read_text(), "old-token")
        self.assertFalse(wizard._closed)

    def test_small_window_navigation_remains_visible(self):
        wizard = self.open_wizard()
        wizard.resize(620, 500)
        wizard.show()
        for index in range(7):
            wizard.go(index)
            self.app.processEvents()
            for button in (wizard.next, wizard.back, wizard.later):
                self.assertTrue(wizard.rect().contains(button.geometry()))
