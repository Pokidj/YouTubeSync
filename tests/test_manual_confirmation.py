import json
import queue
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from youtube_sync_manual import youtube_video_id, quota_console_url
from youtube_sync_manual_ui import ManualConfirmationDialog
from fake_youtube_player import FakeYouTubePlayer

ui, ROOT = fixture.ui, fixture.ROOT
engine = ui.engine
VIDEO_ID = "aB3_dE6-fG9"


class LinkTests(unittest.TestCase):
    def test_valid_links_are_reduced_to_one_video_id(self):
        for value in (VIDEO_ID, f"https://youtu.be/{VIDEO_ID}?t=42", f"https://www.youtube.com/watch?v={VIDEO_ID}&list=abc",
                      f"https://m.youtube.com/shorts/{VIDEO_ID}", f"https://youtube.com/live/{VIDEO_ID}", f"https://www.youtube.com/embed/{VIDEO_ID}"):
            self.assertEqual(youtube_video_id(value), VIDEO_ID)

    def test_invalid_links_cannot_redirect_or_assign_an_unrelated_site(self):
        for value in ("", "bad-id", "javascript:alert(1)", f"https://youtube.com.evil.test/watch?v={VIDEO_ID}",
                      f"https://user:secret@youtube.com/watch?v={VIDEO_ID}", "https://youtube.com/playlist?list=abcdef"):
            with self.assertRaises(ValueError):
                youtube_video_id(value)

    def test_quota_link_uses_only_project_id_and_never_credentials(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "oauth.json"
            path.write_text(json.dumps({"installed": {"project_id": "my-project", "client_secret": "TOP_SECRET", "client_id": "private-client"}}))
            url = quota_console_url(str(path))
        self.assertTrue(url.endswith("?project=my-project"))
        self.assertNotIn("TOP_SECRET", url)
        self.assertNotIn("private-client", url)
        self.assertEqual(quota_console_url("missing-file"), "https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas")


class ManualMatchSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.path = self.base / "clip.mp4"
        self.path.write_bytes(b"full-original-content")
        self.signature = engine.file_signature(self.path)
        self.config = engine.Config(watch_folder=str(self.base))
        with patch.object(engine, "app_dir", return_value=self.base):
            self.store = engine.Store()

    def confirm(self, **kwargs):
        self.store.confirm_manual_match(self.path, self.signature, VIDEO_ID, acknowledged=True, **kwargs)

    def test_manual_confirmation_is_persistent_but_not_an_automatic_upload_receipt(self):
        with patch.object(engine, "YouTubeClient") as api:
            self.confirm()
        api.assert_not_called()
        self.assertTrue(self.store.has_success(self.signature))
        self.assertEqual(self.store.upload_status(self.signature), "manual_confirmed")
        self.assertIsNone(self.store.receipt(VIDEO_ID))
        self.assertEqual(self.store.uploaded_before(datetime.now() + timedelta(days=1)), [])
        with patch.object(engine, "app_dir", return_value=self.base):
            reopened = engine.Store()
        self.assertTrue(reopened.has_success(self.signature))
        self.assertEqual(reopened.daily_upload_attempt_count(), 0)

    def test_manual_mark_cannot_be_used_as_cryptographic_evidence_for_cleanup(self):
        self.confirm()
        client = engine.YouTubeClient(self.store, self.config, Mock())
        client._known_video_states = {VIDEO_ID: "processed"}
        client._known_title_candidates = {"Video": [VIDEO_ID]}
        client._known_video_metadata = {VIDEO_ID: {"filename": self.path.name, "size": self.path.stat().st_size}}
        confirmed, video_id, reason, state = client.verify_local_file(self.path, "Video", VIDEO_ID)
        self.assertFalse(confirmed)
        self.assertEqual(state, "unverified")

    def test_no_acknowledgement_no_confirmation(self):
        with self.assertRaises(ValueError):
            self.store.confirm_manual_match(self.path, self.signature, VIDEO_ID)
        self.assertFalse(self.store.has_success(self.signature))

    def test_changed_file_cannot_reuse_confirmation_or_stale_selection(self):
        self.path.write_bytes(b"changed")
        with self.assertRaises(OSError):
            self.confirm()
        self.assertFalse(self.store.has_success(engine.file_signature(self.path)))

    def test_change_during_hash_is_rejected_before_saving(self):
        def changed(path, **kwargs):
            path.write_bytes(b"changed-content")
            return "sha256:fake"
        with patch.object(engine, "full_content_fingerprint", side_effect=changed), self.assertRaises(OSError):
            self.confirm()
        self.assertFalse(self.store.has_success(self.signature))

    def test_cancelled_hash_cannot_save(self):
        with self.assertRaises(OSError):
            self.confirm(cancelled=lambda: True)
        self.assertFalse(self.store.has_success(self.signature))

    def test_same_id_cannot_be_manually_assigned_to_two_different_local_contents(self):
        self.confirm()
        other = self.base / "different.mp4"
        other.write_bytes(b"different-content")
        with self.assertRaises(ValueError):
            self.store.confirm_manual_match(other, engine.file_signature(other), VIDEO_ID, acknowledged=True)

    def test_actual_receipt_for_another_content_cannot_be_overridden(self):
        self.store.remember_receipt(self.signature, self.path, VIDEO_ID, engine.full_content_fingerprint(self.path))
        other = self.base / "different.mp4"
        other.write_bytes(b"different-content")
        with self.assertRaises(ValueError):
            self.store.confirm_manual_match(other, engine.file_signature(other), VIDEO_ID, acknowledged=True)

    def test_identical_copies_can_share_the_same_video(self):
        self.confirm()
        other = self.base / "copy.mp4"
        other.write_bytes(self.path.read_bytes())
        signature = engine.file_signature(other)
        self.store.confirm_manual_match(other, signature, VIDEO_ID, acknowledged=True)
        self.assertTrue(self.store.has_success(signature))

    def test_manual_confirmation_prevents_reupload_and_routine_reconciliation_requests(self):
        self.confirm()
        client = Mock()
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        worker.handle_file(self.path, client)
        client.verify_local_file.assert_not_called()
        client.upload.assert_not_called()
        with patch.object(worker, "is_stable", return_value=True):
            self.assertEqual(list(worker.iter_videos(self.base, self.config)), [])
        engine.reconcile_local_uploads(self.store, self.config, client, full=True)
        client.uploaded_video_index.assert_not_called()
        self.assertEqual(self.store.upload_status(self.signature), "manual_confirmed")

    def test_automatic_confirmation_is_not_downgraded_to_manual(self):
        self.store.remember_upload(self.signature, self.path, "Video", VIDEO_ID)
        with self.assertRaises(ValueError):
            self.confirm()
        self.assertEqual(self.store.registry_index()[0][self.signature][4], "uploaded")

    def test_rejected_match_survives_restart_and_clears_only_the_association(self):
        self.confirm()
        self.store.reject_manual_match(self.path, self.signature, VIDEO_ID)
        with patch.object(engine, "app_dir", return_value=self.base):
            reopened = engine.Store()
        self.assertEqual(reopened.rejected_video_ids(self.signature), {VIDEO_ID})
        self.assertFalse(reopened.has_success(self.signature))
        self.assertEqual(reopened.upload_status(self.signature), "pending")
        self.assertEqual(reopened.upload_identity(self.signature)[1], "")
        self.assertFalse(reopened.fresh_upload_authorized(self.signature))
        self.assertTrue(self.path.exists())
        self.assertEqual(reopened.daily_upload_attempt_count(), 0)

    def test_rejected_candidate_is_not_reassociated_even_with_matching_metadata(self):
        self.store.reject_manual_match(self.path, self.signature, VIDEO_ID)
        client = engine.YouTubeClient(self.store, self.config, Mock())
        client._known_video_states = {VIDEO_ID: "processed"}
        client._known_title_candidates = {"Video": [VIDEO_ID]}
        client._known_video_metadata = {VIDEO_ID: {"fingerprint": engine.full_content_fingerprint(self.path)}}
        self.assertEqual(client.verify_local_file(self.path, "Video", VIDEO_ID)[3], "missing")

    def test_rejection_cannot_modify_an_automatic_confirmation_or_changed_file(self):
        self.store.remember_upload(self.signature, self.path, "Video", VIDEO_ID)
        with self.assertRaises(ValueError):
            self.store.reject_manual_match(self.path, self.signature, VIDEO_ID)
        self.assertTrue(self.store.has_success(self.signature))
        self.path.write_bytes(b"changed")
        with self.assertRaises(OSError):
            self.store.reject_manual_match(self.path, self.signature, VIDEO_ID)

    def test_explicit_new_upload_is_authorized_once_and_keeps_attempt_history(self):
        self.store.reject_manual_match(self.path, self.signature, VIDEO_ID, upload_requested=True)
        self.assertTrue(self.store.fresh_upload_authorized(self.signature))
        self.assertIsNotNone(self.store.record_upload_attempt(self.signature, self.path, "Video"))
        self.assertFalse(self.store.fresh_upload_authorized(self.signature))
        self.assertIsNone(self.store.record_upload_attempt(self.signature, self.path, "Video"))
        self.assertEqual(self.store.daily_upload_attempt_count(), 1)

    def test_a_later_yes_replaces_only_this_rejection(self):
        self.store.reject_manual_match(self.path, self.signature, VIDEO_ID, upload_requested=True)
        self.confirm()
        self.assertEqual(self.store.rejected_video_ids(self.signature), set())
        self.assertFalse(self.store.fresh_upload_authorized(self.signature))
        self.assertTrue(self.store.has_success(self.signature))

    def test_rejection_does_not_erase_a_receipt_or_previous_attempts(self):
        fingerprint = engine.full_content_fingerprint(self.path)
        self.store.remember_receipt(self.signature, self.path, VIDEO_ID, fingerprint)
        first = self.store.record_upload_attempt(self.signature, self.path, "Video")
        self.store.finish_upload_attempt(first, "error", "Interrupted")
        self.store.reject_manual_match(self.path, self.signature, VIDEO_ID, upload_requested=True)
        self.assertIsNotNone(self.store.receipt(VIDEO_ID))
        self.assertEqual(self.store.daily_upload_attempt_count(), 1)
        self.store.clear_upload_incident(self.signature)  # Same path as explicit UI queueing.
        self.assertIsNotNone(self.store.record_upload_attempt(self.signature, self.path, "Video"))
        self.assertIsNone(self.store.record_upload_attempt(self.signature, self.path, "Video"))
        self.assertFalse(self.store.fresh_upload_authorized(self.signature))

    def test_stale_rejection_does_not_clear_a_changed_association(self):
        self.store.remember_upload(self.signature, self.path, "Video", "zY8_xW5-vU2", "needs_verification")
        with self.assertRaises(ValueError):
            self.store.reject_manual_match(self.path, self.signature, VIDEO_ID)
        self.assertEqual(self.store.upload_identity(self.signature)[1], "zY8_xW5-vU2")

    def test_new_upload_consent_overrides_ambiguity_not_confirmed_processing(self):
        self.store.reject_manual_match(self.path, self.signature, VIDEO_ID, upload_requested=True)
        self.store.approve_upload_review(self.path, self.signature)
        client = Mock()
        client.verify_local_file.return_value = (False, "zY8_xW5-vU2", "sin pruebas", "unverified")
        client.upload.side_effect = TimeoutError("Interrupted")
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        with patch.object(engine, "local_video_duration", return_value=60.0):
            worker.handle_file(self.path, client)
            worker.handle_file(self.path, client)
        client.upload.assert_called_once()
        client.delete_video.assert_not_called()
        self.assertEqual(self.store.daily_upload_attempt_count(), 1)


class ManualDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)
        embedded = patch("youtube_sync_manual_ui.EmbeddedYouTubePlayer", FakeYouTubePlayer)
        embedded.start()
        self.addCleanup(embedded.stop)
        browser = patch.object(ui.webbrowser, "open")
        browser.start()
        self.addCleanup(browser.stop)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.base = Path(self.temporary.name)
        self.path = self.base / "video.mp4"
        self.path.write_bytes(b"video")
        self.signature = engine.file_signature(self.path)
        self.item = {"path": str(self.path), "signature": self.signature, "youtube_id": VIDEO_ID, "title": "Video", "status": "Por verificar", "error": ""}
        self.window.config.watch_folder = str(self.base)
        self.window.store.registry_index.return_value = ({self.signature: (self.signature, "Video", str(self.path), VIDEO_ID, "needs_verification", "today")}, {})
        self.window.store.upload_status_index.return_value = ({self.signature: (self.signature, "Video", str(self.path), "verification_pending", "faltan pruebas", "today")}, {})

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)
        self.temporary.cleanup()

    def select(self):
        self.window.refresh_folder()
        self.window.video_table.selectRow(0)

    def test_guided_steps_and_editing_link_require_another_remote_review(self):
        dialog = ManualConfirmationDialog(self.item, self.window, autoplay=False)
        try:
            self.assertEqual(dialog.pages.currentIndex(), 0)
            dialog.accept()
            self.assertFalse(dialog._closed)
            with patch.object(dialog.preview, "pause") as pause:
                dialog.advance()
            pause.assert_called()
            self.assertEqual(dialog.pages.currentIndex(), 1)
            self.assertEqual(dialog.opened_id, VIDEO_ID)
            dialog.advance()
            self.assertEqual(dialog.pages.currentIndex(), 2)
            self.assertTrue(dialog.yes.isEnabled())
            dialog.link.setText("https://youtube.com/watch?v=zY8_xW5-vU2")
            self.assertFalse(dialog.yes.isEnabled())
            self.assertEqual(dialog.opened_id, "")
            dialog.link.setText("bad-link")
            self.assertFalse(dialog.open_youtube.isEnabled())
        finally:
            dialog.close()

    def test_preview_links_open_the_bound_local_file_and_canonical_youtube_url(self):
        dialog = ManualConfirmationDialog(self.item, self.window, autoplay=False)
        try:
            with patch("youtube_sync_local_player.os.startfile") as local, patch("youtube_sync_manual_ui.webbrowser.open", return_value=True) as remote:
                dialog.preview.open_external()
                dialog.open_remote()
            local.assert_called_once_with(str(self.path))
            remote.assert_called_once_with(f"https://www.youtube.com/watch?v={VIDEO_ID}")
        finally:
            dialog.close()

    def test_no_requires_a_separate_new_upload_choice(self):
        for upload in (False, True):
            dialog = ManualConfirmationDialog(self.item, self.window, autoplay=False)
            try:
                dialog.advance()
                dialog.advance()
                dialog.no.click()
                self.assertEqual(dialog.pages.currentIndex(), 3)
                self.assertEqual(dialog.decision, "")
                with patch.object(dialog.preview, "release") as release:
                    (dialog.upload_new if upload else dialog.keep_pending).click()
                release.assert_called_once()
                self.assertEqual(dialog.result(), ui.QDialog.Accepted)
                self.assertEqual(dialog.decision, "different")
                self.assertEqual(dialog.upload_requested, upload)
            finally:
                dialog.close()

    def test_yes_confirms_and_closing_always_releases_the_player(self):
        dialog = ManualConfirmationDialog(self.item, self.window, autoplay=False)
        dialog.advance()
        dialog.advance()
        dialog.yes.click()
        self.assertEqual(dialog.result(), ui.QDialog.Accepted)
        self.assertEqual(dialog.decision, "match")
        self.assertTrue(dialog.preview.player.source().isEmpty())
        other = ManualConfirmationDialog(self.item, self.window)
        with patch.object(other.preview, "release") as release, patch.object(other.preview, "play_file") as play:
            other.reject()
            other.start_preview()
        release.assert_called_once()
        play.assert_not_called()

    def test_failed_browser_cannot_unlock_the_decision(self):
        dialog = ManualConfirmationDialog(self.item, self.window, autoplay=False)
        try:
            dialog.remote_preview.auto_review = False
            with patch("youtube_sync_manual_ui.webbrowser.open", return_value=False):
                dialog.advance()
                dialog.open_remote()
            self.assertEqual(dialog.pages.currentIndex(), 1)
            self.assertFalse(dialog.next.isEnabled())
            self.assertFalse(dialog.yes.isEnabled())
            dialog.finish("match")
            self.assertEqual(dialog.decision, "")
        finally:
            dialog.close()

    def test_mismatch_only_queues_when_new_upload_is_explicit(self):
        for upload in (False, True):
            self.window.events.put(("manual_confirmation_result", {"item": self.item, "video_id": VIDEO_ID,
                                    "decision": "different", "upload_requested": upload}))
            with patch.object(self.window, "queue_video") as queue_video, patch.object(self.window, "refresh_folder"):
                self.window.process_events()
            self.assertEqual(queue_video.call_count, int(upload))
            if upload:
                self.assertEqual(queue_video.call_args.args[0]["status"], "Pendiente")
                self.assertEqual(queue_video.call_args.args[0]["youtube_id"], "")

    def test_unverified_notice_has_both_previews_manual_confirmation_and_targeted_check(self):
        self.select()
        actions = [action for label, action in self.window.active_guidance.actions]
        self.assertEqual(actions, ["open_video", "open_local", "manual_verify", "check_video", "console"])
        self.assertFalse(hasattr(self.window, "guidance_buttons"))
        self.assertFalse(self.window.local_preview.verify.isHidden())
        self.assertFalse(self.window.local_preview.buttons["check_video"].isHidden())

    def test_video_actions_are_outside_notice_card_and_visible_in_sidebar(self):
        self.select()
        self.window.set_guidance("other", ui.Guidance("Otro aviso", "Detalle"))
        self.window.resize(940, 620)
        for _ in range(4):
            self.app.processEvents()
            self.window.adjust_channel_layout()
        self.assertEqual(self.window.width(), 940)
        self.assertTrue(self.window.local_preview_host.isAncestorOf(self.window.local_preview.actions_widget))
        for button in self.window.local_preview.buttons.values():
            if button.isVisible():
                self.assertFalse(self.window.guidance_card.isAncestorOf(button))
                self.assertTrue(self.window.local_preview.actions_widget.rect().contains(
                    button.mapTo(self.window.local_preview.actions_widget, button.rect().bottomRight())))

    def test_navigation_buttons_move_both_directions_and_do_not_stick_on_false_click_argument(self):
        self.window.set_guidance("one", ui.Guidance("Uno", "Detalle"))
        self.window.set_guidance("two", ui.Guidance("Dos", "Detalle"))
        first = self.window.guidance_selected
        self.window.guidance_next.click()
        self.assertNotEqual(self.window.guidance_selected, first)
        self.window.guidance_previous.click()
        self.assertEqual(self.window.guidance_selected, first)

    def test_manual_status_is_visibly_distinct_and_cannot_be_queued(self):
        self.window.store.registry_index.return_value = ({self.signature: (self.signature, "Video", str(self.path), VIDEO_ID, "manual_confirmed", "today")}, {})
        self.select()
        self.assertEqual(self.window.video_table.item(0, 4).text(), "Subido (manual)")
        self.assertIn("1 manual", self.window.video_summary.text())
        with patch.object(self.window, "start_worker") as worker, patch.object(ui.QMessageBox, "information"):
            self.window.queue_video(self.window.selected_video_row())
        worker.assert_not_called()

    def test_manual_saving_thread_does_not_call_api(self):
        with patch.object(engine, "YouTubeClient") as api:
            self.window._confirm_manual_thread(self.item, VIDEO_ID)
        self.window.store.confirm_manual_match.assert_called_once()
        api.assert_not_called()

    def test_cancelling_comparison_does_not_save_or_leave_controls_blocked(self):
        self.select()
        with patch.object(ui, "ManualConfirmationDialog") as dialog, patch.object(ui.threading, "Thread") as thread:
            dialog.return_value.exec.return_value = ui.QDialog.Rejected
            self.window.confirm_video_manually()
        self.assertFalse(self.window.manual_confirmation_running)
        self.assertTrue(self.window.auto_btn.isEnabled())
        self.window.store.confirm_manual_match.assert_not_called()
        thread.assert_not_called()

    def test_manual_action_is_bound_to_notice_file_not_a_later_selection(self):
        self.select()
        other = self.base / "other.mp4"
        other.write_bytes(b"other")
        table = self.window.video_table
        table.blockSignals(True)
        table.setSortingEnabled(False)
        table.insertRow(1)
        for column, text in ((1, "Other"), (4, "Por verificar"), (5, str(other))):
            table.setItem(1, column, ui.table_item(text))
        self.window.video_rows[1] = dict(self.item, path=str(other), signature=engine.file_signature(other))
        table.selectRow(1)
        table.blockSignals(False)
        self.window.set_guidance("verification", ui.Guidance("Revisar", "Detalle", "warning", (("Confirmar", "manual_verify"),), str(self.path)))
        self.window.guidance_selected = "verification"
        self.window.guidance_browsing = True
        self.window.render_guidance()
        with patch.object(self.window, "confirm_video_manually") as confirm:
            self.window.run_guidance_action(0)
        confirm.assert_called_once()
        self.assertEqual(self.window.selected_video_row()["path"], str(self.path))

    def test_targeted_check_requests_only_this_id_and_preserves_state_if_no_proof(self):
        client = Mock()
        client.verify_local_file.return_value = (False, VIDEO_ID, "no hay huella", "unverified")
        with patch.object(engine, "YouTubeClient", return_value=client):
            self.window._check_single_video_thread(self.item)
        client.uploaded_video_index.assert_called_once_with(force=True, video_ids=[VIDEO_ID])
        self.window.store.apply_reconciliation.assert_not_called()
        client.upload.assert_not_called()

    def test_only_a_real_technical_match_can_promote_manual_to_automatic(self):
        with patch.object(engine, "app_dir", return_value=self.base):
            store = engine.Store()
        store.confirm_manual_match(self.path, self.signature, VIDEO_ID, acknowledged=True)
        self.window.store = store
        client = Mock()
        client.verify_local_file.return_value = (True, VIDEO_ID, "huella confirmada", "processed")
        with patch.object(engine, "YouTubeClient", return_value=client):
            self.window._check_single_video_thread(self.item)
        self.assertEqual(store.upload_status(self.signature), "uploaded")
        self.assertEqual(store.registry_index()[0][self.signature][4], "uploaded")
        self.assertIsNone(store.receipt(VIDEO_ID))

    def test_quota_error_during_targeted_check_keeps_manual_mark(self):
        with patch.object(engine, "app_dir", return_value=self.base):
            store = engine.Store()
        store.confirm_manual_match(self.path, self.signature, VIDEO_ID, acknowledged=True)
        self.window.store = store
        client = Mock()
        client.uploaded_video_index.side_effect = RuntimeError("quotaExceeded")
        with patch.object(engine, "YouTubeClient", return_value=client):
            self.window._check_single_video_thread(self.item)
        self.assertEqual(store.upload_status(self.signature), "manual_confirmed")
        self.assertTrue(store.has_success(self.signature))

    def test_failed_check_clears_progress_notice_and_running_flag(self):
        self.select()
        self.window.single_verifications.add(self.signature)
        self.window.set_guidance("verification", ui.Guidance("Comprobando", "En curso", target=str(self.path)))
        self.window.events.put(("single_verification_result", {"item": self.item, "confirmed": False, "error": "quotaExceeded"}))
        with patch.object(self.window, "refresh_folder"), patch.object(self.window, "report_problem"):
            self.window.process_events()
        self.assertNotIn(self.signature, self.window.single_verifications)
        self.assertNotIn("verification", self.window.guidance_notices)

    def test_stale_cancel_button_cannot_cancel_a_different_active_file(self):
        self.window.worker = Mock(active_path=self.base / "another.mp4")
        self.window.set_guidance("upload", ui.Guidance("Transferencia", "En curso", actions=(("Cancelar", "cancel_upload"),), target=str(self.path)))
        with patch.object(self.window, "refresh_folder") as refresh, patch.object(self.window, "cancel_upload") as cancel:
            self.window.run_guidance_action(0)
        cancel.assert_not_called()
        refresh.assert_called_once()

    def test_saved_upload_id_is_available_even_if_registry_has_no_row(self):
        self.window.store.registry_index.return_value = ({}, {})
        self.window.store.upload_identity.return_value = ("Video", VIDEO_ID)
        self.select()
        self.assertEqual(self.window.selected_video_row()["youtube_id"], VIDEO_ID)
        self.assertEqual(self.window.active_guidance.actions[0][1], "open_video")

    def test_channel_limit_and_project_quota_have_separate_actions_without_api(self):
        self.window.channel_limit_state = {"retry_at": (datetime.now().astimezone() + timedelta(hours=1)).isoformat(), "message": "uploadLimitExceeded"}
        self.window.show_channel_limit()
        notice = self.window.guidance_notices["channel_limit"]
        self.assertIn("estimación", notice.detail)
        self.assertEqual([action for label, action in notice.actions], ["studio", "channel_limits", "quota", "console"])
        self.window.guidance_selected = "channel_limit"
        self.window.guidance_browsing = True
        self.window.render_guidance()
        with patch.object(ui.webbrowser, "open") as browser, patch.object(engine, "YouTubeClient") as api:
            self.window.run_guidance_action(0)
            self.window.run_guidance_action(2)
        self.assertEqual(browser.call_count, 2)
        api.assert_not_called()

    def test_copy_detail_redacts_credentials(self):
        self.window.set_guidance("error", ui.Guidance("Error", "Detalle", "error", (("Copiar", "copy_detail"),), diagnostic="access_token=TOP_SECRET"))
        self.window.run_guidance_action(0)
        self.assertNotIn("TOP_SECRET", self.app.clipboard().text())


if __name__ == "__main__":
    unittest.main()
