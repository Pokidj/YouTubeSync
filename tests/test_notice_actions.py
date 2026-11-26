import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QAbstractButton
import test_layout as fixture
import test_local_preview as local_fixture
from test_layout import ui


class NoticeActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    setUp = fixture.ResponsiveLayoutTests.setUp
    tearDown = fixture.ResponsiveLayoutTests.tearDown
    settle = fixture.ResponsiveLayoutTests.settle
    select_file = local_fixture.LocalPreviewTests.select_fixture

    def state(self, status, error="", youtube_id=""):
        item = self.select_file()
        self.window.video_rows[0].update(status=status, error=error, youtube_id=youtube_id)
        self.window.video_table.item(0, 4).setText(status)
        self.window.video_selection_changed()
        return item

    def test_notices_only_have_navigation_even_for_errors_and_multiple_targets(self):
        self.state("Incidencia", "timeout")
        self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning", (("Cuota", "quota"),)))
        self.assertEqual(set(self.window.guidance_card.findChildren(QAbstractButton)),
                         {self.window.guidance_previous, self.window.guidance_next})
        self.assertFalse(hasattr(self.window, "guidance_buttons"))

    def test_selected_file_commands_are_docked_in_the_sidebar_not_toolbar(self):
        self.state("Pendiente")
        preview = self.window.local_preview
        self.assertTrue(self.window.local_preview_host.isAncestorOf(preview.actions_widget))
        self.assertFalse(preview.buttons["upload_file"].isHidden())
        self.assertFalse(preview.buttons["locate_file"].isHidden())
        self.assertFalse(preview.buttons["delete_local"].isHidden())
        self.assertEqual(self.window.upload_btn.text(), "Subir pendientes")
        self.assertIsNone(self.window.upload_btn.menu())

    def test_retry_and_individual_upload_are_available_for_incidents_and_quota_waits(self):
        for status, action in (("Incidencia", "retry_video"), ("En espera", "upload_file"), ("Revisar", "review_video")):
            self.state(status, "invalid_grant" if status == "Incidencia" else "")
            self.assertFalse(self.window.local_preview.buttons[action].isHidden())

    def test_verification_and_youtube_link_are_offered_for_the_selected_video(self):
        self.state("Por verificar", youtube_id="selected-video")
        for action in ("open_video", "manual_verify", "check_video"):
            self.assertFalse(self.window.local_preview.buttons[action].isHidden())
        with patch.object(ui.webbrowser, "open") as browser:
            self.window.local_preview.youtube.click()
        browser.assert_called_once_with("https://youtu.be/selected-video")

    def test_sidebar_action_does_not_use_an_unrelated_active_notice(self):
        item = self.state("Incidencia", "timeout")
        self.window.set_guidance("quota", ui.Guidance("Cuota", "En espera", "warning", (("Ver cuota", "quota"),)))
        self.window.select_guidance("quota")
        with patch.object(self.window, "retry_selected_video") as retry, patch.object(ui.webbrowser, "open") as browser:
            self.window.local_preview.buttons["retry_video"].click()
        retry.assert_called_once()
        browser.assert_not_called()
        self.assertEqual(self.window.selected_video_row()["path"], item["path"])

    def test_file_actions_fail_closed_when_target_is_missing_or_not_a_file_command(self):
        self.select_file()
        with patch.object(self.window, "upload_selected_video") as upload, patch.object(self.window, "open_setup") as setup:
            self.window.run_local_preview_action("upload_file", "C:/not-in-table.mp4")
            self.window.run_guidance_action(0, ui.Guidance("", "", actions=(("Subir", "upload_file"),)))
            self.window.run_local_preview_action("connect", self.window.selected_video_row()["path"])
        upload.assert_not_called()
        setup.assert_not_called()

    def test_menus_rebuild_without_losing_navigation_or_requesting_youtube(self):
        self.window.set_guidance("one", ui.Guidance("Uno", "Detalle"))
        self.window.set_guidance("two", ui.Guidance("Dos", "Detalle"))
        with patch.object(ui.engine, "YouTubeClient") as client:
            for menu in (self.window.general_options_menu,):
                self.window.build_general_menu(menu)
                self.window.build_general_menu(menu)
                navigation = menu.actions()[0].menu()
                radio = next(action for action in navigation.actions() if action.data() == "two")
                radio.trigger()
                self.assertEqual(self.window.guidance_selected, "two")
                self.assertIn("Consola", [action.text() for action in menu.actions()])
        client.assert_not_called()

    def test_docked_commands_fit_resized_windows_and_are_disabled_during_a_saving_operation(self):
        self.state("Por verificar", "timeout", "video-id")
        for size in ((940, 620), (1280, 780), (1920, 1080), (940, 620)):
            self.window.resize(*size)
            self.settle()
            host = self.window.local_preview_host
            actions = self.window.local_preview.actions_widget
            self.assertTrue(host.rect().contains(actions.geometry()))
            for button in self.window.local_preview.buttons.values():
                if not button.isHidden():
                    self.assertTrue(actions.rect().contains(button.geometry()))
                    self.assertEqual(button.text(), "")
                    self.assertEqual(button.width(), 42)
                    self.assertTrue(button.toolTip())
        self.window.manual_confirmation_running = True
        self.window.render_guidance()
        self.assertFalse(self.window.local_preview.actions_widget.isEnabled())

    def test_copy_detail_in_sidebar_redacts_credentials(self):
        self.state("Incidencia", "access_token=SECRET")
        self.window.local_preview.buttons["copy_detail"].click()
        self.assertNotIn("SECRET", self.app.clipboard().text())


if __name__ == "__main__":
    unittest.main()
