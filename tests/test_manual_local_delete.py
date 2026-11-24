import os
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from youtube_sync_cleanup import delete_local_files

ui, ROOT = fixture.ui, fixture.ROOT


class ManualLocalDeleteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "video.mp4"
        self.path.write_bytes(b"video")
        self.item = {"path": str(self.path), "signature": ui.engine.file_signature(self.path), "status": "Pendiente"}

    def test_unuploaded_file_can_be_deleted_without_duration_or_youtube(self):
        with patch("youtube_sync_cleanup.windows_media") as media, patch.object(ui.engine, "YouTubeClient") as api:
            result = delete_local_files([self.item], stable_seconds=0)
        self.assertEqual(result["deleted"], [self.item])
        self.assertFalse(self.path.exists())
        media.assert_not_called()
        api.assert_not_called()

    def test_changed_or_recent_file_is_preserved(self):
        self.assertFalse(delete_local_files([self.item], stable_seconds=60)["deleted"])
        self.path.write_bytes(b"different-file")
        result = delete_local_files([self.item], stable_seconds=0)
        self.assertFalse(result["deleted"])
        self.assertTrue(self.path.exists())
        self.assertTrue(result["errors"])

    def test_cancel_does_not_delete(self):
        self.assertFalse(delete_local_files([self.item], cancelled=lambda: True, stable_seconds=0)["deleted"])
        self.assertTrue(self.path.exists())

    def test_last_signature_check_preserves_file_changed_during_operation(self):
        with patch("youtube_sync_cleanup.file_signature", side_effect=[self.item["signature"], "changed"]):
            result = delete_local_files([self.item], stable_seconds=0)
        self.assertFalse(result["deleted"])
        self.assertTrue(self.path.exists())

    def test_pause_for_deletion_removes_queued_uploads_without_cancelling_current_transfer(self):
        worker = ui.engine.SyncWorker(Mock(), ui.engine.Config, queue.Queue())
        worker.enabled_event.set()
        worker.active_path = self.path
        worker.upload_path(self.path)
        worker.upload_path(self.path.parent / "other.mp4")
        worker.pause_after_current()
        self.assertFalse(worker.enabled_event.is_set())
        self.assertTrue(worker.manual_uploads.empty())
        self.assertFalse(worker.cancel_upload_event.is_set())
        self.assertEqual(worker.active_path, self.path)


class ManualDeleteLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.path = Path(self.temporary.name) / "video.mp4"
        self.path.write_bytes(b"video")
        old = time.time() - 30
        os.utime(self.path, (old, old))
        self.item = {"path": str(self.path), "signature": ui.engine.file_signature(self.path), "status": "Pendiente",
                     "youtube_id": "", "title": "Video", "error": ""}

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)
        self.temporary.cleanup()

    def test_unconfirmed_statuses_show_warning_cancel_default_and_allow_override(self):
        for status in ("Pendiente", "Revisar", "Incidencia", "Por verificar", "En espera", "En curso"):
            dialogs = []
            def show(dialog):
                dialogs.append(dialog)
                return 0
            with patch.object(ui.QMessageBox, "exec", show), patch.object(self.window, "begin_local_deletion") as delete:
                self.window.delete_selected_local_video(dict(self.item, status=status))
            dialog = dialogs[0]
            self.assertEqual(dialog.defaultButton().text(), "Cancelar")
            self.assertIn("única copia", dialog.informativeText())
            self.assertIn("Borrar de todos modos", [button.text() for button in dialog.buttons()])
            self.assertNotIn("Comprobar y borrar", [button.text() for button in dialog.buttons()])
            delete.assert_not_called()
            self.assertTrue(self.path.exists())

    def test_explicit_override_routes_to_local_deletion_only(self):
        def clicked(dialog):
            return next(button for button in dialog.buttons() if button.text() == "Borrar de todos modos")
        with patch.object(ui.QMessageBox, "exec", return_value=0), patch.object(ui.QMessageBox, "clickedButton", clicked), \
                patch.object(self.window, "begin_local_deletion") as delete, patch.object(ui.engine, "YouTubeClient") as api:
            self.window.delete_selected_local_video(self.item)
        delete.assert_called_once_with([self.item])
        api.assert_not_called()

    def test_uploaded_file_keeps_verified_option_and_can_choose_override(self):
        item = dict(self.item, status="Subido", youtube_id="remote-id")
        dialogs = []
        def show(dialog):
            dialogs.append(dialog)
            return 0
        def clicked(dialog):
            return next(button for button in dialog.buttons() if button.text() == "Comprobar y borrar")
        with patch.object(ui.QMessageBox, "exec", show), patch.object(ui.QMessageBox, "clickedButton", clicked), \
                patch.object(ui.threading, "Thread") as thread:
            self.window.delete_selected_local_video(item)
        self.assertIn("Borrar de todos modos", [button.text() for button in dialogs[0].buttons()])
        self.assertEqual(thread.call_args.kwargs["target"], self.window._delete_local_verified_thread)
        self.assertEqual(thread.call_args.kwargs["args"], ([item],))

    def test_stale_selection_never_offers_deletion_of_changed_file(self):
        self.path.write_bytes(b"changed-content")
        with patch.object(ui.QMessageBox, "warning") as warning, patch.object(ui.QMessageBox, "exec") as confirm, \
                patch.object(self.window, "refresh_folder"), patch.object(self.window, "begin_local_deletion") as delete:
            self.window.delete_selected_local_video(self.item)
        warning.assert_called_once()
        confirm.assert_not_called()
        delete.assert_not_called()
        self.assertTrue(self.path.exists())

    def test_deletion_pauses_automatic_uploads_and_prevents_duplicate_operations(self):
        worker = Mock()
        self.window.worker = worker
        with patch.object(ui.threading, "Thread") as thread:
            self.window.begin_local_deletion([self.item])
            self.window.begin_local_deletion([self.item])
        self.assertFalse(self.window.auto_enabled)
        worker.pause_after_current.assert_called_once()
        self.assertEqual(thread.call_count, 1)
        self.assertFalse(self.window.auto_btn.isEnabled())
        self.assertEqual(thread.call_args.kwargs["args"], ([self.item], False))

    def test_worker_deletes_pending_file_and_updates_registry_without_api(self):
        with patch.object(ui.engine, "YouTubeClient") as api:
            self.window._delete_local_files_thread([self.item])
        self.assertFalse(self.path.exists())
        self.window.store.mark_local_deleted.assert_called_once_with(self.item["signature"])
        api.assert_not_called()
        results = []
        while not self.window.events.empty():
            results.append(self.window.events.get())
        self.assertIn(("manual_local_delete_result", {"deleted": 1, "errors": []}), results)

    def test_unknown_duration_review_can_offer_local_deletion(self):
        self.window.store.pending_upload_reviews.return_value = {self.item["signature"]: {"seconds": None}}
        def clicked(dialog):
            return next(button for button in dialog.buttons() if button.text() == "Borrar local")
        with patch.object(ui.QMessageBox, "exec", return_value=0), patch.object(ui.QMessageBox, "clickedButton", clicked), \
                patch.object(self.window, "delete_selected_local_video") as delete:
            self.window.review_selected_video(self.item)
        delete.assert_called_once_with(self.item)

    def test_completion_reenables_controls(self):
        self.window.local_delete_running = True
        self.window.auto_btn.setEnabled(False)
        self.window.upload_btn.setEnabled(False)
        self.window.events.put(("manual_local_delete_result", {"deleted": 1, "errors": []}))
        with patch.object(self.window, "refresh_folder"), patch.object(ui.QMessageBox, "information"):
            self.window.process_events()
        self.assertFalse(self.window.local_delete_running)
        self.assertTrue(self.window.auto_btn.isEnabled())
        self.assertTrue(self.window.upload_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
