import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_layout import ui

engine = ui.engine


class EngineCompatibilityTests(unittest.TestCase):
    def test_registry_config_and_token_identity_survive_reopening(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            base = Path(temporary)
            with patch.object(engine, "app_dir", return_value=base):
                store = engine.Store()
                config = engine.Config(watch_folder="C:/Videos", client_secret_path="C:/oauth/client.json")
                store.save_config(config)
                store.remember_upload("test-signature", base / "video.mp4", "Video", "test-video-id")
                token = store.token_path_for(config.client_secret_path)
                token.write_text("test-token", encoding="utf-8")
                reopened = engine.Store()
                self.assertEqual(reopened.load_config().watch_folder, config.watch_folder)
                self.assertEqual(reopened.load_config().client_secret_path, config.client_secret_path)
                self.assertTrue(reopened.has_success("test-signature"))
                self.assertEqual(reopened.token_path_for(config.client_secret_path).read_text(), "test-token")

    def test_active_backend_has_no_old_ui(self):
        self.assertEqual(engine.APP_NAME, "YouTubeSync")
        self.assertFalse(hasattr(engine, "App"))
        self.assertFalse(hasattr(engine, "tk"))


if __name__ == "__main__":
    unittest.main()
