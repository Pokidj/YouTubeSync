import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from youtube_sync_cleanup import scan_short_videos

ui, ROOT = fixture.ui, fixture.ROOT


class ShortVideoScanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def item(self, name):
        path = self.base / name
        path.write_bytes(b"example")
        return {"path": str(path), "signature": ui.engine.file_signature(path), "title": name,
                "youtube_id": "remote-id", "status": "Subido"}

    def test_duration_limit_is_strict_and_does_not_round_30_seconds(self):
        items = [self.item(f"clip-{i}.mp4") for i in range(4)]
        with patch("youtube_sync_cleanup.windows_media", side_effect=[{"seconds": value} for value in (29.999, 30, 30.001, 5)]):
            progress = Mock()
            result = scan_short_videos(items, progress=progress)
        self.assertEqual([item["seconds"] for item in result["items"]], [29.999, 5])
        self.assertEqual(result["errors"], [])
        self.assertEqual(progress.call_count, 4)
        self.assertTrue(all(Path(item["path"]).exists() for item in items))

    def test_unreadable_zero_negative_and_nonfinite_durations_are_preserved(self):
        items = [self.item(f"clip-{i}.mp4") for i in range(7)]
        with patch("youtube_sync_cleanup.windows_media", side_effect=[{}, {"seconds": 0}, {"seconds": -1},
                {"seconds": float("nan")}, {"seconds": float("inf")}, {"seconds": None}, OSError("codec unavailable")]):
            result = scan_short_videos(items)
        self.assertFalse(result["items"])
        self.assertEqual(len(result["errors"]), 7)
        self.assertTrue(all(Path(item["path"]).exists() for item in items))

    def test_changed_or_missing_file_is_not_a_candidate(self):
        changed, missing = self.item("changed.mp4"), self.item("missing.mp4")
        Path(changed["path"]).write_bytes(b"different-content")
        Path(missing["path"]).unlink()
        with patch("youtube_sync_cleanup.windows_media") as read:
            result = scan_short_videos([changed, missing])
        read.assert_not_called()
        self.assertFalse(result["items"])
        self.assertEqual(len(result["errors"]), 2)

    def test_file_modified_during_duration_read_is_preserved(self):
        item = self.item("changed.mp4")
        def read(path, thumbnail):
            path.write_bytes(b"new-content")
            return {"seconds": 10}
        with patch("youtube_sync_cleanup.windows_media", side_effect=read):
            result = scan_short_videos([item])
        self.assertFalse(result["items"])
        self.assertEqual(len(result["errors"]), 1)

    def test_cancelled_scan_never_offers_a_partial_list_for_deletion(self):
        item = self.item("clip.mp4")
        with patch("youtube_sync_cleanup.windows_media") as read:
            result = scan_short_videos([item], cancelled=lambda: True)
        self.assertTrue(result["cancelled"])
        self.assertFalse(result["items"])
        read.assert_not_called()


class ShortCleanupLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.base = Path(self.temporary.name)
        path = self.base / "clip.mp4"
        path.write_bytes(b"example")
        self.item = {"path": str(path), "signature": ui.engine.file_signature(path), "title": "clip",
                     "youtube_id": "remote-id", "status": "Subido", "seconds": 20.5, "size": 7}

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)
        self.temporary.cleanup()

    def test_cleanup_button_has_both_options_and_scans_all_files(self):
        button = next(button for button in self.window.findChildren(ui.QPushButton) if button.text() == "Limpieza")
        self.assertEqual(len(button.menu().actions()), 2)
        self.window.video_rows = {0: dict(self.item), 1: dict(self.item, status="Pendiente")}
        with patch.object(self.window, "refresh_folder"), patch.object(ui.threading, "Thread") as thread:
            self.window.run_short_video_cleanup()
            self.window.run_short_video_cleanup()
        self.assertEqual(thread.call_count, 1)
        self.assertEqual(thread.call_args.kwargs["args"], ([self.item, dict(self.item, status="Pendiente")],))
        self.assertFalse(self.window.short_cleanup_action.isEnabled())

    def test_confirmation_lists_files_and_cancel_is_default_and_does_not_delete(self):
        dialogs = []
        def show(dialog):
            dialogs.append(dialog)
            return 0
        with patch.object(ui.QMessageBox, "exec", show), patch.object(ui.threading, "Thread") as thread:
            self.window.confirm_short_video_cleanup({"items": [self.item], "errors": []})
        thread.assert_not_called()
        self.assertEqual(dialogs[0].defaultButton().text(), "Cancelar")
        self.assertIn("clip.mp4", dialogs[0].detailedText())
        self.assertIn("20.5 s", dialogs[0].detailedText())
        self.assertTrue(Path(self.item["path"]).exists())

    def test_confirmed_short_cleanup_uses_local_cleanup_and_pauses_automatic_uploads(self):
        def clicked(dialog):
            return next(button for button in dialog.buttons() if button.text() == "Borrar archivos locales")
        with patch.object(ui.QMessageBox, "exec", return_value=0), patch.object(ui.QMessageBox, "clickedButton", clicked), \
                patch.object(ui.threading, "Thread") as thread:
            self.window.confirm_short_video_cleanup({"items": [self.item], "errors": []})
        self.assertEqual(thread.call_args.kwargs["target"], self.window._delete_local_files_thread)
        self.assertEqual(thread.call_args.kwargs["args"], ([self.item], True))
        self.assertFalse(self.window.auto_enabled)
        self.assertTrue(self.window.local_delete_running)

    def test_live_verification_failure_or_unfinished_processing_keeps_local_file(self):
        for response in ((False, "", "identity mismatch", "processed"), (True, "remote-id", "processing", "processing")):
            client = Mock()
            client.verify_local_file.return_value = response
            with patch.object(ui.engine, "YouTubeClient", return_value=client):
                self.window._delete_local_verified_thread([self.item])
            self.assertTrue(Path(self.item["path"]).exists())
            client.uploaded_video_index.assert_called_once_with(force=True, video_ids=["remote-id"])

    def test_quota_failure_cannot_delete_a_short_video(self):
        client = Mock()
        client.uploaded_video_index.side_effect = RuntimeError("quotaExceeded")
        with patch.object(ui.engine, "YouTubeClient", return_value=client):
            self.window._delete_local_verified_thread([self.item])
        self.assertTrue(Path(self.item["path"]).exists())
        client.verify_local_file.assert_not_called()

    def test_confirmed_identity_and_completed_processing_allows_local_deletion(self):
        client = Mock()
        client.verify_local_file.return_value = (True, "remote-id", "confirmed", "processed")
        with patch.object(ui.engine, "YouTubeClient", return_value=client):
            self.window._delete_local_verified_thread([self.item])
        self.assertFalse(Path(self.item["path"]).exists())
        self.window.store.mark_local_deleted.assert_called_once_with(self.item["signature"])
        client.delete_video.assert_not_called()

    def test_no_matches_reenables_action_and_preserves_every_file(self):
        self.window.short_cleanup_scanning = True
        self.window.short_cleanup_action.setEnabled(False)
        with patch.object(ui.QMessageBox, "information") as message, patch.object(ui.threading, "Thread") as thread:
            self.window.confirm_short_video_cleanup({"items": [], "errors": ["Windows cannot read duration"]})
        message.assert_called_once()
        self.assertFalse(self.window.short_cleanup_scanning)
        self.assertTrue(self.window.short_cleanup_action.isEnabled())
        thread.assert_not_called()
        self.assertTrue(Path(self.item["path"]).exists())


if __name__ == "__main__":
    unittest.main()
