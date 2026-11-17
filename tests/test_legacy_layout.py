import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from test_layout import ui

legacy = ui.legacy


class LegacyWindowLayoutTests(unittest.TestCase):
    def setUp(self):
        self.patches = ExitStack()
        store = Mock()
        store.load_config.return_value = legacy.Config()
        store.get_upload_limit.return_value = None
        self.patches.enter_context(patch.object(legacy, "Store", return_value=store))
        for name in ("start_worker", "ensure_tray", "process_events", "check_youtube_connection",
                     "update_upload_limit_countdown", "refresh_folder_contents", "on_main_tab_changed"):
            self.patches.enter_context(patch.object(legacy.App, name))
        self.window = legacy.App()
        self.window.title("YouTubeSync - prueba de interfaz")
        self.window.status_var.set("Subiendo un video de ejemplo: 35%")
        self.window.set_card(self.window.youtube_card, "Conectado", "Mi canal / Mi lista", "#22c55e", "\u2713")
        self.window.set_card(self.window.progress_card, "35%", "Un video de ejemplo.mp4", "#3ea6ff", "\u2191")
        self.window.progress_var.set(35)
        for i in range(20):
            self.window.pending_table.insert("", "end", values=(
                f"Video {i}.mp4", "100 MB", "2026-11-17", "Pendiente", "Listo para subir", "C:/Videos"))
        self.window.update()

    def tearDown(self):
        self.window.destroy()
        self.patches.close()

    def settle(self):
        for _ in range(4):
            self.window.update_idletasks()
            self.window.update()

    def test_tables_visible_in_window_mode(self):
        for width, height in ((1120, 740), (900, 650), (1440, 900)):
            self.window.geometry(f"{width}x{height}")
            for tab, table in ((self.window.videos_tab, self.window.pending_table),
                               (self.window.gallery_tab, self.window.gallery_table),
                               (self.window.console_tab, self.window.log_box)):
                with self.subTest(size=(width, height), tab=str(tab)):
                    self.window.notebook.select(tab)
                    self.settle()
                    self.assertGreaterEqual(table.winfo_height(), 100)
                    bottom = table.winfo_rooty() + table.winfo_height()
                    self.assertLessEqual(bottom, self.window.winfo_rooty() + self.window.winfo_height())

    def test_small_window_can_scroll_and_resize_back(self):
        self.window.geometry("760x520")
        self.settle()
        self.assertGreater(self.window.main_root.winfo_height(), self.window.main_canvas.winfo_height())
        self.window.main_canvas.yview_moveto(1)
        self.window.geometry("1120x740")
        self.settle()
        self.assertEqual(self.window.main_root.winfo_height(), self.window.main_canvas.winfo_height())

    def test_summary_counts_do_not_count_active_videos_twice(self):
        payload = {"total": 49, "pending": 12, "active": 29, "uploaded": 8,
                   "other": 0, "error": "", "pending_rows": [], "other_rows": [], "uploaded_rows": []}
        self.window.apply_folder_rows(payload)
        values = (self.window.pending_count_var, self.window.active_count_var,
                  self.window.uploaded_count_var, self.window.issue_count_var)
        self.assertEqual(sum(int(value.get()) for value in values), 49)
        self.assertTrue(self.window.pending_summary_var.get().startswith("41 por resolver"))


if __name__ == "__main__":
    unittest.main()
