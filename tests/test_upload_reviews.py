import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from youtube_sync_cleanup import delete_short_videos

ui, ROOT = fixture.ui, fixture.ROOT
engine = ui.engine


class UploadReviewSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.path = self.base / "clip.mp4"
        self.path.write_bytes(b"example")
        self.signature = engine.file_signature(self.path)
        with patch.object(engine, "app_dir", return_value=self.base):
            self.store = engine.Store()
        self.config = engine.Config(watch_folder=str(self.base))
        self.events = queue.Queue()
        self.worker = engine.SyncWorker(self.store, lambda: self.config, self.events)

    def test_short_clip_is_blocked_without_api_calls_or_upload_attempts(self):
        self.worker.set_enabled(True)
        with patch.object(engine, "local_video_duration", return_value=29.999) as read, \
                patch.object(self.worker, "available_client") as client, \
                patch.object(self.worker, "is_stable", return_value=True):
            for _ in range(3):
                self.worker.scan_once()
        read.assert_called_once()
        client.assert_not_called()
        self.assertEqual(self.store.daily_upload_attempt_count(), 0)
        self.assertIn(self.signature, self.store.pending_upload_reviews())
        events = []
        while not self.events.empty():
            events.append(self.events.get()[0])
        self.assertEqual(events.count("upload_review"), 1)

    def test_exactly_30_seconds_does_not_require_manual_approval(self):
        with patch.object(engine, "local_video_duration", return_value=30.0):
            self.assertFalse(self.worker.requires_upload_review(self.path))
        self.assertNotIn(self.signature, self.store.pending_upload_reviews())

    def test_pending_review_with_old_youtube_id_does_not_repeat_remote_checks(self):
        self.store.remember_upload(self.signature, self.path, "Video", "old-id", reason="needs_verification")
        with patch.object(engine, "local_video_duration", return_value=10.0):
            self.assertTrue(self.worker.requires_upload_review(self.path))
        self.worker.set_enabled(True)
        with patch.object(self.worker, "available_client") as api, patch.object(self.worker, "is_stable", return_value=True):
            self.worker.scan_once()
            self.worker.scan_once()
        api.assert_not_called()

    def test_unknown_duration_is_fail_closed_until_explicit_review(self):
        with patch.object(engine, "local_video_duration", return_value=None):
            self.assertTrue(self.worker.requires_upload_review(self.path))
            self.store.approve_upload_review(self.path, self.signature)
            self.assertFalse(self.worker.requires_upload_review(self.path))

    def test_approval_survives_restart_but_does_not_apply_to_a_changed_file(self):
        with patch.object(engine, "local_video_duration", return_value=12.0):
            self.assertTrue(self.worker.requires_upload_review(self.path))
            self.store.approve_upload_review(self.path, self.signature)
            with patch.object(engine, "app_dir", return_value=self.base):
                reopened = engine.Store()
            new_worker = engine.SyncWorker(reopened, lambda: self.config, queue.Queue())
            self.assertFalse(new_worker.requires_upload_review(self.path))
            self.path.write_bytes(b"changed-clip")
            self.assertTrue(new_worker.requires_upload_review(self.path))
            with self.assertRaises(OSError):
                reopened.approve_upload_review(self.path, self.signature)

    def test_approved_short_clip_can_upload_and_retry_guard_still_applies(self):
        with patch.object(engine, "local_video_duration", return_value=10.0):
            self.store.review_before_upload(self.path)
            self.store.approve_upload_review(self.path, self.signature)
        client = Mock()
        client.verify_local_file.return_value = (False, "", "missing", "missing")
        client.upload.side_effect = TimeoutError("Interrupted")
        self.worker.handle_file(self.path, client)
        self.worker.handle_file(self.path, client)
        client.upload.assert_called_once()
        self.assertEqual(self.store.daily_upload_attempt_count(), 1)

    def test_direct_upload_path_cannot_bypass_review(self):
        client = Mock()
        client.verify_local_file.return_value = (False, "", "missing", "missing")
        with patch.object(engine, "local_video_duration", return_value=5.0):
            self.worker.handle_file(self.path, client)
        client.upload.assert_not_called()
        self.assertEqual(self.store.daily_upload_attempt_count(), 0)

    def test_already_confirmed_upload_is_not_reclassified_or_reuploaded(self):
        self.store.remember_upload(self.signature, self.path, "Video", "remote-id")
        with patch.object(engine, "local_video_duration") as read:
            self.assertFalse(self.worker.requires_upload_review(self.path))
        read.assert_not_called()
        self.assertTrue(self.store.has_success(self.signature))

    def test_deleted_file_review_is_removed_without_touching_other_reviews(self):
        with patch.object(engine, "local_video_duration", return_value=10.0):
            self.store.review_before_upload(self.path)
        self.store.mark_local_deleted(self.signature)
        self.assertNotIn(self.signature, self.store.pending_upload_reviews())

    def test_short_cleanup_can_delete_a_pending_file_without_youtube(self):
        item = {"path": str(self.path), "signature": self.signature, "status": "Pendiente"}
        with patch("youtube_sync_cleanup.windows_media", return_value={"seconds": 10}), \
                patch.object(engine, "YouTubeClient") as api:
            result = delete_short_videos([item], stable_seconds=0)
        self.assertEqual(result["deleted"], [item])
        self.assertFalse(self.path.exists())
        api.assert_not_called()

    def test_short_cleanup_preserves_changed_unknown_and_30_second_files(self):
        item = {"path": str(self.path), "signature": self.signature}
        for seconds in (None, 0, float("nan"), 30, 30.01):
            with patch("youtube_sync_cleanup.windows_media", return_value={"seconds": seconds}):
                result = delete_short_videos([item], stable_seconds=0)
            self.assertFalse(result["deleted"])
            self.assertTrue(self.path.exists())
        self.path.write_bytes(b"changed")
        with patch("youtube_sync_cleanup.windows_media") as read:
            self.assertFalse(delete_short_videos([item], stable_seconds=0)["deleted"])
        read.assert_not_called()

    def test_short_cleanup_preserves_recent_files_and_cancelled_work(self):
        item = {"path": str(self.path), "signature": self.signature}
        with patch("youtube_sync_cleanup.windows_media") as read:
            self.assertFalse(delete_short_videos([item], stable_seconds=60)["deleted"])
            self.assertFalse(delete_short_videos([item], cancelled=lambda: True, stable_seconds=0)["deleted"])
        read.assert_not_called()
        self.assertTrue(self.path.exists())


class UploadReviewLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.base = Path(self.temporary.name)
        self.path = self.base / "short.mp4"
        self.path.write_bytes(b"short")
        self.signature = engine.file_signature(self.path)
        self.item = {"path": str(self.path), "signature": self.signature, "status": "Revisar", "title": "Short", "youtube_id": "", "error": ""}
        self.window.config.watch_folder = str(self.base)
        self.window.store.pending_upload_reviews.return_value = {self.signature: {"path": str(self.path), "seconds": 12.0, "approved": False}}
        self.window.store.registry_index.return_value = ({}, {})
        self.window.store.upload_status_index.return_value = ({}, {})

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)
        self.temporary.cleanup()

    def test_review_is_visible_with_icon_and_is_not_an_incident_or_transfer_candidate(self):
        self.window.refresh_folder()
        self.assertEqual(self.window.video_table.item(0, 4).text(), "Revisar")
        self.assertFalse(self.window.video_table.item(0, 4).icon().isNull())
        self.assertIn("Incidencias 0", self.window.video_summary.text())
        self.assertEqual(self.window.transfer_candidates, 0)
        self.assertEqual(self.window.guidance_notices["review"].target, str(self.path))

    def test_manual_upload_opens_review_instead_of_starting_worker(self):
        with patch.object(self.window, "review_selected_video") as review, patch.object(self.window, "start_worker") as start:
            self.window.queue_video(self.item)
        review.assert_called_once_with(self.item)
        start.assert_not_called()

    def test_explicit_approval_is_persisted_before_enqueueing(self):
        def clicked(dialog):
            return next(button for button in dialog.buttons() if button.text() == "Autorizar y subir")
        with patch.object(ui.QMessageBox, "exec", return_value=0), patch.object(ui.QMessageBox, "clickedButton", clicked), \
                patch.object(self.window, "refresh_folder"), patch.object(self.window, "queue_video") as queued:
            self.window.review_selected_video(self.item)
        self.window.store.approve_upload_review.assert_called_once_with(self.path, self.signature)
        self.assertEqual(queued.call_args.args[0]["status"], "Pendiente")

    def test_later_does_not_approve_or_upload_and_is_default(self):
        dialogs = []
        def show(dialog):
            dialogs.append(dialog)
            return 0
        with patch.object(ui.QMessageBox, "exec", show), patch.object(self.window, "queue_video") as queued:
            self.window.review_selected_video(self.item)
        self.assertEqual(dialogs[0].defaultButton().text(), "Más tarde")
        self.window.store.approve_upload_review.assert_not_called()
        queued.assert_not_called()

    def test_local_deletion_waits_for_upload_operation_lock(self):
        lock = threading.RLock()
        worker = Mock(operation_lock=lock)
        self.window.worker = worker
        started = threading.Event()
        def delete(*args, **kwargs):
            started.set()
            return {"deleted": [], "errors": []}
        with patch.object(ui, "delete_short_videos", side_effect=delete):
            lock.acquire()
            task = threading.Thread(target=self.window._delete_local_files_thread, args=([self.item], True))
            task.start()
            self.assertFalse(started.wait(0.1))
            lock.release()
            task.join(3)
        self.assertFalse(task.is_alive())
        self.assertTrue(started.is_set())


if __name__ == "__main__":
    unittest.main()
