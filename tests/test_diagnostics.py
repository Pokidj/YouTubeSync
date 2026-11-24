import queue
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from test_layout import ROOT, ui
from youtube_sync_diagnostics import DiagnosticBuffer, DiagnosticWindow, redact_secrets
from youtube_sync_icons import app_icon


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    def setUp(self):
        self.buffer = DiagnosticBuffer()
        self.window = DiagnosticWindow(self.buffer)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.render_timer.stop()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_entries_have_timestamp_source_and_level(self):
        self.buffer.append("[12:34:56] No se pudo subir clip.mp4", source="Subida")
        entry = self.buffer.entries[-1]
        self.assertEqual(entry.level, "ERROR")
        self.assertEqual(entry.source, "Subida")
        self.assertNotIn("12:34:56", entry.message)
        self.assertIsNotNone(datetime.fromisoformat(entry.timestamp).tzinfo)

    def test_unverified_files_are_warnings_but_processing_is_not_an_error(self):
        self.buffer.append("No se sube ni se borra clip.mp4: No hay datos suficientes")
        self.assertEqual(self.buffer.entries[-1].level, "WARNING")
        self.buffer.append("YouTube aun esta procesando el video")
        self.assertEqual(self.buffer.entries[-1].level, "INFO")

    def test_redacts_tokens_json_query_headers_and_passwords(self):
        for original, secret in (("Authorization: Bearer dangerous-token", "dangerous-token"),
                                 ('{"refresh_token": "refresh-secret"}', "refresh-secret"),
                                 ('{"client_secret":"oauth-secret"}', "oauth-secret"),
                                 ("https://example.invalid/?upload_id=private-session&part=snippet", "private-session"),
                                 ("Cookie: SID=private-cookie; HSID=secret", "private-cookie"),
                                 ("password=private-password", "private-password"),
                                 ("code_verifier=private-verifier", "private-verifier"),
                                 ("https://proxy-user:proxy-password@proxy.example.invalid/", "proxy-password")):
            with self.subTest(original=original):
                self.buffer.append(original)
                self.assertNotIn(secret, self.buffer.entries[-1].text())
                self.assertNotIn(secret, self.buffer.report())
                self.assertIn("[OCULTO]", redact_secrets(original))

    def test_plain_text_does_not_interpret_html_from_an_api_error(self):
        self.buffer.append('HttpError: <a href="quota">quotaExceeded</a>')
        self.window.render()
        self.assertIn('<a href="quota">', self.window.viewer.toPlainText())
        self.assertTrue(self.window.viewer.isReadOnly())

    def test_buffer_is_bounded(self):
        for index in range(2100):
            self.buffer.append(f"Message {index}", level="INFO")
        self.assertEqual(len(self.buffer.entries), 2000)
        self.assertEqual(self.buffer.entries[0].message, "Message 100")

    def test_filters_by_level_source_and_text(self):
        self.buffer.append("archivo_uno.mp4 / HTTP 403", "API", "ERROR")
        self.buffer.append("archivo_dos.mp4 / pausa", "Subida", "WARNING")
        self.buffer.append("Escaneo terminado", "Servicio", "INFO")
        self.window.render()
        self.window.level_filter.setCurrentIndex(1)
        self.assertEqual(len(self.window.filtered_entries()), 2)
        self.window.source_filter.setCurrentText("API")
        self.window.search.setText("403")
        self.assertEqual(len(self.window.filtered_entries()), 1)
        self.window.level_filter.setCurrentIndex(2)
        self.assertEqual(self.window.filtered_entries()[0].source, "API")

    def test_copy_errors_contains_incidents_not_routine_progress(self):
        self.buffer.append("Progreso ordinario", "Subida", "INFO")
        self.buffer.append("quotaExceeded", "API", "WARNING")
        self.buffer.append("Transferencia fallida", "Subida", "ERROR")
        self.window.copy_errors()
        report = self.app.clipboard().text()
        self.assertNotIn("Progreso ordinario", report)
        self.assertIn("quotaExceeded", report)
        self.assertIn("Transferencia fallida", report)

    def test_copy_full_report_has_version_and_context(self):
        self.buffer.append("Operacion: Transferir\nArchivo: clip.mp4\nHttpError 403: quotaExceeded", "Subida", "ERROR")
        self.window.copy_report()
        report = self.app.clipboard().text()
        self.assertIn("YouTubeSync 1.0", report)
        self.assertIn("Operacion: Transferir", report)
        self.assertIn("Archivo: clip.mp4", report)

    def test_export_is_utf8_and_redacted(self):
        self.buffer.append("Fallo de conexion / access_token=private-value", "API", "ERROR")
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "report.log"
            with patch("youtube_sync_diagnostics.QFileDialog.getSaveFileName", return_value=(str(path), "")):
                self.window.export_report()
            text = path.read_text(encoding="utf-8")
        self.assertNotIn("private-value", text)
        self.assertIn("Fallo de conexion", text)

    def test_cancel_export_does_not_write_anything(self):
        with patch("youtube_sync_diagnostics.QFileDialog.getSaveFileName", return_value=("", "")), \
                patch("youtube_sync_diagnostics.QSaveFile") as output:
            self.window.export_report()
        output.assert_not_called()

    def test_export_failure_is_recorded_with_its_source(self):
        failed = Mock()
        failed.open.return_value = False
        failed.errorString.return_value = "Acceso denegado"
        with patch("youtube_sync_diagnostics.QFileDialog.getSaveFileName", return_value=("report.log", "")), \
                patch("youtube_sync_diagnostics.QSaveFile", return_value=failed), \
                patch("youtube_sync_diagnostics.QMessageBox.warning"):
            self.window.export_report()
        self.assertEqual(self.buffer.entries[-1].source, "Consola")
        self.assertEqual(self.buffer.entries[-1].level, "ERROR")

    def test_selection_is_not_replaced_while_new_messages_arrive(self):
        self.buffer.append("Primer mensaje")
        self.window.render()
        self.window.viewer.selectAll()
        before = self.window.viewer.textCursor().selectedText()
        self.buffer.append("Segundo mensaje")
        self.window.render()
        self.assertEqual(self.window.viewer.textCursor().selectedText(), before)
        self.assertEqual(len(self.buffer.entries), 2)
        self.window.search.setText("Segundo")
        self.window.render()
        self.assertIn("Segundo", self.window.viewer.toPlainText())

    def test_clear_also_removes_selected_text(self):
        self.buffer.append("Mensaje seleccionado")
        self.window.render()
        self.window.viewer.selectAll()
        self.buffer.clear()
        self.window.render()
        self.assertEqual(self.window.viewer.toPlainText(), "")
        self.assertEqual(len(self.buffer.entries), 0)

    def test_close_and_reopen_preserves_background_messages(self):
        self.window.close()
        self.buffer.append("Capturado con la ventana cerrada")
        self.window.show()
        self.app.processEvents()
        self.assertIn("ventana cerrada", self.window.viewer.toPlainText())

    def test_all_bundled_icons_render_visible_pixels(self):
        for path in (ROOT / "outputs/youtube-sync-modern/assets/icons").glob("*.svg"):
            with self.subTest(icon=path.stem):
                image = app_icon(path.stem).pixmap(24, 24).toImage()
                self.assertFalse(image.isNull())
                self.assertTrue(any(image.pixelColor(x, y).alpha() for y in range(image.height()) for x in range(image.width())))


class DiagnosticIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    setUp = fixture.ResponsiveLayoutTests.setUp
    tearDown = fixture.ResponsiveLayoutTests.tearDown
    settle = fixture.ResponsiveLayoutTests.settle

    def test_main_tabs_only_contain_videos_and_channel(self):
        self.assertEqual([self.window.tabs.tabText(index) for index in range(self.window.tabs.count())], ["Videos", "Canal"])
        self.assertFalse(hasattr(self.window, "build_console_page"))

    def test_settings_console_button_opens_a_separate_reusable_window(self):
        self.window.open_settings()
        self.window.settings_dialog.settings_search.setText("consola")
        button = next(button for button in self.window.settings_dialog.findChildren(ui.QPushButton) if button.text() == "Consola")
        button.click()
        self.assertIsNotNone(self.window.diagnostic_window)
        first = self.window.diagnostic_window
        self.assertTrue(first.isWindow())
        self.window.open_console()
        self.assertIs(self.window.diagnostic_window, first)

    def test_settings_search_preserves_the_application_version_section(self):
        self.window.open_settings()
        dialog = self.window.settings_dialog
        dialog.settings_search.setText("version")
        sections = [frame for frame, _, terms in dialog.settings_sections if "updater" in terms]
        self.assertFalse(sections[0].isHidden())

    def test_guidance_console_action_does_not_change_the_active_tab(self):
        self.window.set_guidance("upload", ui.Guidance("Error", "Fallo", "warning", (("Consola", "console"),)))
        index = self.window.tabs.currentIndex()
        self.window.run_guidance_action(0)
        self.assertEqual(self.window.tabs.currentIndex(), index)
        self.assertTrue(self.window.diagnostic_window.isVisible())

    def test_quota_without_a_transfer_only_appears_in_guidance(self):
        state = {"kind": "proyecto", "bucket": "upload", "reason": "rateLimitExceeded",
                 "retry_at": (datetime.now().astimezone() + timedelta(hours=1)).isoformat()}
        self.window.events.put(("api_quota", state))
        self.window.process_events()
        self.assertTrue(self.window.transfer_strip.isHidden())
        self.window.update_quota_status()
        self.window.update_quota_status()
        entries = [entry for entry in self.window.diagnostic_buffer.entries if entry.source == "API"]
        self.assertEqual(len(entries), 1)
        self.assertIn("rateLimitExceeded", entries[0].message)

    def test_clearing_diagnostics_does_not_change_storage(self):
        before = list(self.window.store.method_calls)
        self.window.log("Error de prueba", level="ERROR")
        self.window.diagnostic_buffer.clear()
        self.assertEqual(self.window.store.method_calls, before)

    def test_exception_diagnostics_include_operation_path_and_trace(self):
        events = queue.Queue()
        worker = ui.engine.SyncWorker(Mock(), ui.engine.Config, events)
        try:
            raise TimeoutError("Respuesta interrumpida")
        except TimeoutError as error:
            worker.problem("No se pudo subir", Path("clip.mp4"), error=error, operation="Transferir video")
        kind, value = events.get_nowait()
        self.window.events.put((kind, value))
        self.window.process_events()
        text = self.window.diagnostic_buffer.entries[-1].message
        self.assertIn("Operacion: Transferir video", text)
        self.assertIn("Archivo: clip.mp4", text)
        self.assertIn("TimeoutError", text)


if __name__ == "__main__":
    unittest.main()
