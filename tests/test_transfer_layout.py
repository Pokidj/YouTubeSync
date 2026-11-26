import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from test_layout import ROOT, ui


class TransferLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    setUp = fixture.ResponsiveLayoutTests.setUp
    tearDown = fixture.ResponsiveLayoutTests.tearDown
    settle = fixture.ResponsiveLayoutTests.settle

    def pause(self, bucket="upload"):
        return {"kind": "proyecto", "bucket": bucket,
                "retry_at": (datetime.now().astimezone() + timedelta(hours=1)).isoformat()}

    def test_manual_notice_survives_activity_churn_and_new_notices(self):
        self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning"))
        self.window.set_guidance("library", ui.Guidance("Revisar videos", "Dos casos", "warning"))
        self.window.next_guidance()
        self.assertEqual(self.window.guidance_selected, "library")
        for index in range(8):
            self.window.set_guidance("activity", ui.Guidance("Comprobando", str(index)))
            self.window.set_guidance("activity", None)
            self.window.set_guidance("quota", ui.Guidance("Cuota", f"Cuenta atras {index}", "warning"))
            self.window.set_guidance("connection", ui.Guidance("Revisa OAuth", str(index), "error"))
            self.assertEqual(self.window.guidance_selected, "library")
        self.assertEqual(self.window.active_guidance.title, "Revisar videos")
        self.assertEqual(self.window.status.text(), "Requiere atencion")

    def test_routine_activity_is_not_an_extra_notice_to_cycle(self):
        self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning"))
        self.window.set_guidance("activity", ui.Guidance("Trabajando", "Leyendo"))
        self.assertEqual(self.window.guidance_order, ["quota"])
        self.assertTrue(self.window.guidance_next.isHidden())

    def test_resolved_selected_notice_advances_to_a_remaining_notice(self):
        self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning"))
        self.window.set_guidance("library", ui.Guidance("Revisar", "Un caso", "warning"))
        self.window.next_guidance()
        self.window.set_guidance("library", None)
        self.assertEqual(self.window.guidance_selected, "quota")
        self.assertFalse(self.window.guidance_browsing)

    def test_folder_refresh_does_not_restart_manual_notice_navigation(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "clip.mp4"
            path.write_bytes(b"clip")
            signature = ui.engine.file_signature(path)
            self.window.config = ui.engine.Config(watch_folder=temporary, client_secret_path=str(ROOT / "README.md"))
            self.window.store.registry_index.return_value = ({}, {})
            self.window.store.upload_status_index.return_value = ({signature: (signature, "Clip", str(path), "error", "Error", "2026-11-21")}, {})
            self.window.refresh_folder()
            self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning"))
            self.window.next_guidance()
            self.assertEqual(self.window.guidance_selected, "library")
            for _ in range(3):
                self.window.refresh_folder()
                self.window.events.put(("busy", True))
                self.window.events.put(("busy", False))
                self.window.process_events()
                self.assertEqual(self.window.guidance_selected, "library")

    def test_profile_has_no_redundant_visible_field_captions(self):
        texts = [label.text() for label in self.window.state_card.findChildren(ui.QLabel)]
        for caption in ("Canal", "Carpeta", "Lista", "Categoria", "Privacidad"):
            self.assertNotIn(caption, texts)
        self.assertEqual({field.accessibleName() for field in self.window.profile_fields},
                         {"Canal", "Carpeta", "Lista", "Categoria", "Privacidad"})

    def test_profile_uses_three_balanced_rows_with_a_stronger_first_row(self):
        grid = self.window.profile_grid
        for row, fields in enumerate(((self.window.state_card.value, self.window.profile_channel),
                                      (self.window.profile_folder, self.window.profile_privacy),
                                      (self.window.profile_category, self.window.profile_playlist))):
            for column, field in enumerate(fields):
                container = grid.itemAtPosition(row, column).widget()
                self.assertTrue(container.isAncestorOf(field))
        self.assertEqual(grid.columnStretch(0), grid.columnStretch(1))
        self.assertEqual(self.window.profile_channel.objectName(), "ProfileLeadValue")
        self.assertEqual(self.window.state_card.value.objectName(), "ProfileLeadValue")
        self.assertEqual(self.window.profile_folder.objectName(), "ProfileValue")

    def test_header_only_contains_auto_and_settings_and_tools_belong_to_local_page(self):
        from PySide6.QtWidgets import QAbstractButton
        self.assertEqual(set(self.window.header_actions.findChildren(QAbstractButton)),
                         {self.window.auto_btn, self.window.general_options_button, self.window.settings_btn})
        self.assertIs(self.window.header_actions.layout().itemAt(1).widget(), self.window.general_options_button)
        self.assertFalse(hasattr(self.window, "channel_general_options_button"))
        self.assertFalse(self.window.tabs.widget(0).isAncestorOf(self.window.general_options_button))
        for button in (self.window.upload_btn, self.window.cancel_btn, self.window.refresh_btn):
            self.assertTrue(self.window.tabs.widget(0).isAncestorOf(button))
            self.assertFalse(self.window.header_actions.isAncestorOf(button))
        self.assertIsNone(self.window.upload_btn.menu())
        self.assertEqual(self.window.upload_btn.text(), "Subir pendientes")
        self.assertEqual(len(self.window.refresh_btn.menu().actions()), 1)
        self.assertEqual(self.window.refresh_btn.menu().actions()[0].text(), "Comprobar con YouTube")
        self.assertTrue(self.window.local_preview_host.isAncestorOf(self.window.reveal_file_button))

    def test_consolidated_buttons_keep_selected_and_bulk_uploads_and_refreshes_separate(self):
        with patch.object(ui.engine, "Store", return_value=self.window.store), \
                patch.object(ui.MainWindow, "build_tray"), patch.object(ui.MainWindow, "refresh_all"), \
                patch.object(ui.MainWindow, "upload_selected_video") as selected, \
                patch.object(ui.MainWindow, "upload_pending") as pending, \
                patch.object(ui.MainWindow, "refresh_folder") as local, \
                patch.object(ui.MainWindow, "request_remote_refresh") as remote:
            window = ui.MainWindow()
            try:
                window.upload_btn.click()
                selected.assert_not_called()
                pending.assert_called_once()
                window.refresh_btn.click()
                local.assert_called_once()
                remote.assert_not_called()
                window.remote_refresh_action.trigger()
                remote.assert_called_once()
            finally:
                window._allow_exit = True
                window.close()
                window.deleteLater()

    def test_stop_is_available_for_a_queue_or_transfer_but_not_remote_processing(self):
        self.window.worker = None
        for phase in ("idle", "processing", "canceling", "queued", "uploading", "paused"):
            with self.subTest(phase=phase):
                self.window.set_transfer_state(phase, "clip.mp4", 15)
                self.assertEqual(self.window.cancel_btn.isEnabled(), phase in {"queued", "uploading", "paused"})

    def test_notice_heading_uses_avisos_and_keeps_its_position(self):
        self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning"))
        self.assertEqual(self.window.guidance_card.title.text(), "AVISOS")
        self.window.set_guidance("library", ui.Guidance("Revisar", "Un caso", "warning"))
        self.window.next_guidance()
        self.assertEqual(self.window.guidance_card.title.text(), "AVISOS / 2 DE 2")

    def test_notices_remain_information_only_even_with_multiple_actions(self):
        self.window.tabs.setCurrentIndex(0)
        actions = (("Confirmar coincidencia", "manual_verify"), ("Ver YouTube", "open_video"),
                   ("Ver local", "open_local"), ("Reintentar", "retry_video"), ("Consola", "console"))
        self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning"))
        self.window.set_guidance("selection", ui.Guidance("Revisar", "Comprueba el candidato", "warning", actions))
        self.window.next_guidance()
        for width, height in ((940, 620), (1920, 1080), (940, 620)):
            self.window.resize(width, height)
            self.settle()
            self.assertEqual(self.window.width(), width)
            from PySide6.QtWidgets import QAbstractButton
            self.assertEqual(set(self.window.guidance_card.findChildren(QAbstractButton)),
                             {self.window.guidance_previous, self.window.guidance_next})
            self.assertTrue(self.window.guidance_next.isVisible())

    def test_user_selection_opens_that_file_notice_without_later_refresh_jumps(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "clip.mp4"
            path.write_bytes(b"clip")
            signature = ui.engine.file_signature(path)
            self.window.config = ui.engine.Config(watch_folder=temporary, client_secret_path=str(ROOT / "README.md"))
            self.window.store.registry_index.return_value = ({}, {})
            self.window.store.upload_status_index.return_value = ({signature: (signature, "Clip", str(path), "error", "timeout", "2026-11-21")}, {})
            self.window.refresh_folder()
            self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning"))
            self.window.video_table.selectRow(0)
            self.assertEqual(self.window.guidance_selected, "selection")
            self.window.refresh_folder()
            self.assertEqual(self.window.guidance_selected, "selection")
            self.assertEqual(self.window.active_guidance.target, str(path))

    def test_strip_is_initially_hidden_and_is_below_both_top_cards(self):
        self.window.tabs.setCurrentIndex(0)
        self.assertTrue(self.window.transfer_strip.isHidden())
        self.window.set_transfer_state("uploading", "clip.mp4", 35)
        self.settle()
        self.assertGreaterEqual(self.window.transfer_strip.mapTo(self.window.centralWidget(), self.window.transfer_strip.rect().topLeft()).y(),
                                self.window.state_card.mapTo(self.window.centralWidget(), self.window.state_card.rect().bottomLeft()).y())
        self.assertEqual(self.window.transfer_strip.height(), 44)
        self.assertFalse(hasattr(self.window, "upload_card"))

    def test_upload_progress_displays_file_and_percentage(self):
        self.window.events.put(("progress", {"percent": 37, "filename": "clip.mp4"}))
        self.window.process_events()
        strip = self.window.transfer_strip
        self.assertFalse(strip.isHidden())
        self.assertEqual(strip.phase, "uploading")
        self.assertEqual(strip.filename.full_text, "clip.mp4")
        self.assertEqual(strip.progress.value(), 37)
        self.assertEqual(strip.percent_label.text(), "37%")

    def test_quota_only_shows_a_paused_strip_when_there_is_pending_work(self):
        self.window.auto_enabled = True
        self.window.transfer_candidates = 2
        self.window.events.put(("api_quota", self.pause()))
        self.window.events.put(("busy", False))
        self.window.process_events()
        self.assertEqual(self.window.transfer_strip.phase, "paused")
        self.assertFalse(self.window.transfer_strip.isHidden())
        self.assertIn("2", self.window.transfer_strip.filename.full_text)

    def test_read_only_quota_with_no_uploads_keeps_the_strip_hidden(self):
        self.window.events.put(("api_quota", self.pause("general")))
        self.window.process_events()
        self.assertTrue(self.window.transfer_strip.isHidden())
        self.assertIn("quota", self.window.guidance_notices)

    def test_stopping_a_paused_queue_hides_the_strip(self):
        self.window.auto_enabled = True
        self.window.transfer_candidates = 1
        self.window.api_pause_state = self.pause()
        self.window.refresh_transfer_state()
        self.assertEqual(self.window.transfer_strip.phase, "paused")
        self.window.auto_enabled = False
        self.window.refresh_transfer_state(cycle_finished=True)
        self.assertTrue(self.window.transfer_strip.isHidden())

    def test_cancel_acknowledgement_hides_the_transfer(self):
        self.window.set_transfer_state("uploading", "clip.mp4", 15)
        self.window.events.put(("problem", {"message": "Subida cancelada por el usuario", "source": "upload", "path": "C:/clip.mp4"}))
        self.window.events.put(("busy", False))
        self.window.process_events()
        self.assertTrue(self.window.transfer_strip.isHidden())

    def test_processing_is_indeterminate_and_not_hidden_by_connection_checks(self):
        self.window.events.put(("upload_completed", {"path": "C:/clip.mp4"}))
        with patch.object(self.window, "check_youtube"):
            self.window.process_events()
        self.window.processing_files = ["clip.mp4"]
        self.window.events.put(("youtube", {"title": "Canal"}))
        self.window.process_events()
        self.assertEqual(self.window.transfer_strip.phase, "processing")
        self.assertEqual(self.window.progress.maximum(), 0)
        self.assertTrue(self.window.transfer_strip.percent_label.isHidden())

    def test_confirmed_local_rows_hide_processing_strip(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "clip.mp4"
            path.write_bytes(b"clip")
            signature = ui.engine.file_signature(path)
            self.window.config = ui.engine.Config(watch_folder=temporary, client_secret_path=str(ROOT / "README.md"))
            self.window.store.registry_index.return_value = ({signature: (signature, "Clip", str(path), "id", "uploaded", "2026-11-21")}, {})
            self.window.store.upload_status_index.return_value = ({signature: (signature, "Clip", str(path), "uploaded", "", "2026-11-21")}, {})
            self.window.set_transfer_state("processing", str(path), 100)
            self.window.refresh_folder()
            self.assertTrue(self.window.transfer_strip.isHidden())

    def test_receipt_being_processed_is_still_visible_with_auto_off(self):
        self.window.auto_enabled = False
        self.window.processing_files = ["clip.mp4"]
        self.window.refresh_transfer_state()
        self.assertEqual(self.window.transfer_strip.phase, "processing")
        self.assertFalse(self.window.transfer_strip.isHidden())

    def test_paused_strip_disappears_when_no_eligible_files_remain(self):
        self.window.auto_enabled = True
        self.window.transfer_candidates = 1
        self.window.api_pause_state = self.pause()
        self.window.refresh_transfer_state()
        self.window.transfer_candidates = 0
        self.window.refresh_transfer_state()
        self.assertTrue(self.window.transfer_strip.isHidden())

    def test_pause_waits_for_folder_snapshot_before_clearing_a_running_queue(self):
        self.window.auto_enabled = True
        self.window.api_pause_state = self.pause()
        self.window.set_transfer_state("paused", "clip.mp4", 0)
        self.window.refresh_transfer_state(cycle_finished=True)
        self.assertEqual(self.window.transfer_strip.phase, "paused")
        self.window.refresh_transfer_state()
        self.assertTrue(self.window.transfer_strip.isHidden())

    def test_profile_and_strip_fit_small_and_wide_windows(self):
        self.window.config = ui.engine.Config(watch_folder=str(ROOT / "work"), client_secret_path=str(ROOT / "README.md"),
                                             connected_channel_name="Canal largo " * 30, playlist_id="list", playlist_name="Lista larga " * 30)
        self.window.refresh_connection_card()
        self.window.set_transfer_state("uploading", "clip_largo_" * 30 + ".mp4", 55)
        for width, height in ((940, 620), (1280, 780), (1920, 1080)):
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                self.settle()
                self.assertEqual(self.window.width(), width)
                self.assertEqual(self.window.state_card.height(), self.window.guidance_card.height())
                self.assertGreaterEqual(self.window.video_table.height(), 100)
                for button in (self.window.upload_btn, self.window.cancel_btn, self.window.refresh_btn):
                    corner = button.mapTo(self.window.tabs.widget(0), button.rect().bottomRight())
                    self.assertTrue(self.window.tabs.widget(0).rect().contains(corner))
                self.assertGreaterEqual(self.window.channel_table.height(), 100)
                self.assertLessEqual(self.window.transfer_strip.x() + self.window.transfer_strip.width(), self.window.width())
                for field in self.window.profile_fields:
                    corner = field.mapTo(self.window.state_card, field.rect().bottomRight())
                    self.assertTrue(self.window.state_card.rect().contains(corner))


if __name__ == "__main__":
    unittest.main()
