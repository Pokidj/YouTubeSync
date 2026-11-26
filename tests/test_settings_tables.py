import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_layout as fixture
from youtube_sync_table_settings import TableSettingsEditor, settings_search_key
from youtube_sync_i18n import set_language

ui = fixture.ui


class SettingsTablesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)
        self.dialog = ui.SettingsDialog(self.window.store, self.window.config)

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        fixture.ResponsiveLayoutTests.tearDown(self)
        set_language("es")

    def test_both_tables_share_editor_controls_and_independent_colors(self):
        dialog = self.dialog
        self.assertEqual(dialog.settings_tabs.tabText(5), "En mi equipo")
        self.assertEqual(dialog.settings_tabs.tabText(6), "En YouTube")
        self.assertEqual(dialog.settings_tabs.tabText(1), "Conexión")
        for editor in (dialog.library_editor, dialog.channel_editor):
            self.assertIsInstance(editor, TableSettingsEditor)
            self.assertEqual(editor.columns.iconSize(), dialog.library_editor.columns.iconSize())
            self.assertEqual(editor.columns.minimumHeight(), dialog.library_editor.columns.minimumHeight())
            self.assertEqual(editor.columns.selectionMode(), dialog.library_editor.columns.selectionMode())
            self.assertEqual(editor.color.count(), 4)
        dialog.library_color.setCurrentIndex(dialog.library_color.findData("blue"))
        dialog.channel_color.setCurrentIndex(dialog.channel_color.findData("red"))
        with patch.object(ui.engine, "set_run_at_startup"):
            dialog.save()
        saved = self.window.store.save_config.call_args.args[0]
        self.assertEqual(saved.library_selection_color, "blue")
        self.assertEqual(saved.channel_selection_color, "red")
        self.assertEqual(self.window.config.library_selection_color, "green")

    def test_reset_restores_columns_without_touching_color_or_the_other_table(self):
        editor = self.dialog.library_editor
        self.dialog.fill_library_columns(["status"])
        editor.color.setCurrentIndex(editor.color.findData("blue"))
        self.dialog.fill_channel_columns(["id", "title"])
        editor.reset.click()
        self.assertEqual(self.dialog.selected_library_columns(), list(ui.DEFAULT_LIBRARY_COLUMNS))
        self.assertEqual(editor.color.currentData(), "blue")
        self.assertEqual(self.dialog.selected_channel_columns(), ["id", "title"])

    def test_search_preserves_matching_tab_accepts_accents_and_recovers_from_empty(self):
        dialog = self.dialog
        dialog.show()
        dialog.settings_tabs.setCurrentIndex(6)
        dialog.settings_search.setText("resolucion")
        self.assertEqual(dialog.settings_tabs.currentIndex(), 6)
        self.assertEqual(settings_search_key("RESOLUCIÓN"), "resolucion")
        dialog.settings_search.setText("no-existe-987")
        self.assertFalse(dialog.settings_empty.isHidden())
        dialog.settings_search.clear()
        self.assertTrue(dialog.settings_empty.isHidden())
        self.assertTrue(all(dialog.settings_tabs.isTabEnabled(index) for index in range(dialog.settings_tabs.count())))

    def test_advanced_intervals_are_not_silently_clamped_and_cleanup_controls_follow_toggle(self):
        self.dialog.close()
        self.dialog = ui.SettingsDialog(self.window.store, ui.engine.Config(scan_interval_seconds=7000, stable_wait_seconds=1))
        self.assertEqual(self.dialog.scan_interval.value(), 7000)
        self.assertEqual(self.dialog.stable_wait.value(), 1)
        self.assertFalse(self.dialog.cleanup_delay.isEnabled())
        self.assertFalse(self.dialog.cleanup_unit.isEnabled())
        self.dialog.auto_delete.setChecked(True)
        self.assertTrue(self.dialog.cleanup_delay.isEnabled())
        self.assertTrue(self.dialog.cleanup_unit.isEnabled())

    def test_color_preferences_survive_store_reopening_and_style_is_applied_to_both_tables(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(ui.engine, "app_dir", return_value=Path(folder)):
            store = ui.engine.Store()
            store.save_config(ui.engine.Config(library_selection_color="blue", channel_selection_color="red"))
            config = ui.engine.Store().load_config()
        self.window.config = config
        self.window.configure_library_columns()
        self.window.configure_channel_table_columns()
        self.assertIn("#1765b3", self.window.video_table.styleSheet())
        self.assertIn("#b91c39", self.window.channel_table.styleSheet())

    def test_english_search_empty_message_is_translated(self):
        set_language("en")
        dialog = ui.SettingsDialog(self.window.store, self.window.config)
        try:
            self.assertEqual(dialog.settings_empty.text(), "No settings match your search.")
        finally:
            dialog.close()
