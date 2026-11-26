import queue
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as layout_fixture
from test_layout import ROOT, ui


class GuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layout_fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = layout_fixture.ResponsiveLayoutTests.app

    setUp = layout_fixture.ResponsiveLayoutTests.setUp
    tearDown = layout_fixture.ResponsiveLayoutTests.tearDown
    settle = layout_fixture.ResponsiveLayoutTests.settle

    def quota(self):
        return {"kind": "proyecto", "bucket": "upload",
                "retry_at": (datetime.now().astimezone() + timedelta(hours=2)).isoformat()}

    def test_state_and_configuration_are_one_card(self):
        self.assertFalse(hasattr(self.window, "config_card"))
        self.assertTrue(self.window.state_card.title.isHidden())
        self.assertEqual(self.window.state_card.title.text(), "")
        self.assertIs(self.window.progress.parentWidget(), self.window.transfer_strip)

    def test_folder_refresh_does_not_replace_connected_channel(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            self.window.config = ui.engine.Config(watch_folder=temporary, client_secret_path=str(ROOT / "README.md"),
                                                 connected_channel_name="Canal correcto", playlist_id="playlist", playlist_name="Mis clips")
            self.window.connection_value = "Conectado"
            self.window.connection_channel = "Canal correcto"
            self.window.refresh_connection_card()
            self.window.store.registry_index.return_value = ({}, {})
            self.window.store.upload_status_index.return_value = ({}, {})
            self.window.refresh_folder()
            self.assertEqual(self.window.state_card.value.text(), "Conectado")
            self.assertEqual(self.window.profile_channel.full_text, "Canal correcto")
            self.assertIn("Mis clips", self.window.profile_playlist.toolTip())
            self.assertEqual(self.window.profile_folder.toolTip(), temporary)

    def test_missing_folder_has_an_actionable_configuration_notice(self):
        self.window.refresh_connection_card()
        self.assertEqual(self.window.active_guidance.actions[0][1], "folder_settings")

    def test_oauth_network_permissions_and_disabled_api_offer_specific_actions(self):
        for message, action in (("OAuth invalid_grant", "connect"), ("Connection timed out", "refresh"),
                                ("403 insufficientPermissions", "settings"), ("accessNotConfigured API has not been used", "enable_api"),
                                ("La carpeta no existe", "folder_settings")):
            with self.subTest(message=message):
                notice = ui.problem_guidance(message)
                self.assertEqual(notice.actions[0][1], action)
                self.assertTrue(notice.detail)

    def test_busy_and_progress_cannot_hide_a_quota_pause(self):
        self.window.api_pause_state = self.quota()
        self.window.update_quota_status()
        self.window.events.put(("progress", {"percent": 10, "filename": "video.mp4"}))
        self.window.events.put(("busy", False))
        self.window.process_events()
        self.assertEqual(self.window.guidance_selected, "quota")
        self.assertIn("subidas", self.window.active_guidance.title)

    def test_countdown_updates_do_not_interrupt_browsing_other_notices(self):
        self.window.set_guidance("library", ui.Guidance("Revisar videos", "No hay pruebas suficientes", "warning"))
        self.window.api_pause_state = self.quota()
        self.window.update_quota_status()
        self.window.next_guidance()
        self.assertEqual(self.window.guidance_selected, "library")
        self.window.update_quota_status()
        self.assertEqual(self.window.guidance_selected, "library")

    def test_connect_action_opens_setup_not_an_upload(self):
        self.window.set_guidance("connection", ui.problem_guidance("invalid_grant OAuth"))
        with patch.object(self.window, "open_setup") as setup, patch.object(self.window, "start_worker") as worker:
            self.window.run_guidance_action(0)
        setup.assert_called_once()
        worker.assert_not_called()

    def test_quota_action_does_not_reset_local_pause_or_call_youtube(self):
        self.window.api_pause_state = self.quota()
        self.window.update_quota_status()
        with patch.object(ui.webbrowser, "open") as browser, patch.object(ui.engine, "YouTubeClient") as client:
            self.window.run_guidance_action(0)
        browser.assert_called_once()
        client.assert_not_called()
        self.window.store.clear_api_pause.assert_not_called()

    def test_refresh_removes_a_quota_notice_when_no_pause_remains(self):
        self.window.api_pause_state = self.quota()
        self.window.update_quota_status()
        with patch.object(self.window, "refresh_folder"):
            ui.MainWindow.refresh_all(self.window, light=True)
        self.assertNotIn("quota", self.window.guidance_notices)

    def test_retry_action_uses_the_notice_file_not_an_unrelated_selection(self):
        self.window.video_table.blockSignals(True)
        self.window.video_table.setRowCount(2)
        for row, path in enumerate(("C:/first.mp4", "C:/second.mp4")):
            self.window.video_table.setItem(row, 4, ui.table_item("Incidencia"))
            self.window.video_table.setItem(row, 5, ui.table_item(path))
            self.window.video_rows[row] = {"path": path, "signature": str(row), "youtube_id": "", "error": "timeout"}
        self.window.video_table.selectRow(1)
        self.window.video_table.blockSignals(False)
        self.window.set_guidance("upload", ui.problem_guidance("timeout", "Subida", "C:/first.mp4"))
        with patch.object(self.window, "retry_selected_video") as retry:
            self.window.run_guidance_action(0)
        retry.assert_called_once()
        self.assertEqual(self.window.selected_video_row()["path"], "C:/first.mp4")

    def test_async_upload_problem_survives_idle_events_and_tab_changes(self):
        self.window.events.put(("problem", {"source": "upload", "message": "Connection aborted", "path": "C:/clip.mp4"}))
        self.window.events.put(("busy", False))
        self.window.process_events()
        self.window.tabs.setCurrentIndex(0)
        self.assertEqual(self.window.active_guidance.target, "C:/clip.mp4")
        self.assertEqual(self.window.active_guidance.actions[0][1], "retry_video")
        self.assertIn("Connection aborted", self.window.guidance_card.toolTip())
        self.assertNotEqual(self.window.status.text(), "Preparado")

    def test_manual_cancellation_is_not_reported_as_an_api_failure(self):
        notice = ui.problem_guidance("Subida cancelada por el usuario", "Subida", "C:/clip.mp4")
        self.assertEqual(notice.level, "info")
        self.assertEqual(notice.actions[0][1], "retry_video")

    def test_cleanup_warning_is_visible_without_reading_console(self):
        self.window.events.put(("cleanup_warning", "No se confirmo el archivo"))
        self.window.process_events()
        self.assertEqual(self.window.guidance_selected, "cleanup")
        self.assertEqual(self.window.active_guidance.actions[0][1], "videos")

    def test_channel_failure_has_a_reload_action_without_background_modal(self):
        with patch.object(ui.QMessageBox, "warning") as modal:
            self.window.channel_failed("Connection timed out")
        modal.assert_not_called()
        self.assertEqual(self.window.active_guidance.actions[0][1], "channel_reload")

    def test_profile_and_notices_fit_small_and_large_windows(self):
        self.window.config = ui.engine.Config(watch_folder=str(ROOT), client_secret_path=str(ROOT / "README.md"),
                                             playlist_name="Lista larga " * 30, playlist_id="playlist")
        self.window.refresh_connection_card()
        self.window.set_guidance("upload", ui.problem_guidance("Connection timed out", "Subida", "C:/" + "clip_" * 30 + ".mp4"))
        self.window.set_guidance("library", ui.Guidance("Otro aviso", "Sin confirmar", "warning"))
        for width, height in ((940, 620), (1280, 780), (1920, 1080)):
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                self.settle()
                self.assertEqual(self.window.width(), width)
                self.assertGreaterEqual(self.window.channel_table.height(), 100)
                heights = {card.height() for card in (self.window.state_card, self.window.guidance_card)}
                self.assertEqual(len(heights), 1)
                from PySide6.QtWidgets import QAbstractButton
                self.assertEqual(set(self.window.guidance_card.findChildren(QAbstractButton)),
                                 {self.window.guidance_previous, self.window.guidance_next})

    def test_backend_emits_structured_problem_for_missing_configuration(self):
        events = queue.Queue()
        worker = ui.engine.SyncWorker(Mock(), lambda: ui.engine.Config(watch_folder=""), events)
        worker.set_enabled(True)
        worker.scan_once()
        problems = [value for kind, value in list(events.queue) if kind == "problem"]
        self.assertEqual(problems[0]["source"], "configuration")

    def test_failed_settings_save_does_not_change_the_running_configuration(self):
        original = self.window.config.watch_folder
        self.window.open_settings()
        dialog = self.window.settings_dialog
        dialog.folder.setText("C:/unsaved-folder")
        self.window.store.save_config.side_effect = OSError("Read-only file system")
        with patch.object(ui.QMessageBox, "warning"):
            dialog.save()
        self.assertEqual(self.window.config.watch_folder, original)
        self.assertIn("settings", self.window.guidance_notices)
        dialog.close()


if __name__ == "__main__":
    unittest.main()
