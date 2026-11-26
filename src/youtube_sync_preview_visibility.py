"""Selection-aware sidebar visibility shared by the local and channel views."""

from PySide6.QtCore import QObject
from youtube_sync_icons import app_icon


class PreviewVisibility(QObject):
    def __init__(self, splitter, panel, button, stop, sizes):
        super().__init__(splitter)
        self.splitter = splitter
        self.panel = panel
        self.button = button
        self.stop = stop
        self.sizes = sizes
        self.has_selection = False
        self.user_hidden = False
        button.setCheckable(True)
        button.clicked.connect(self.toggle)
        panel.hide()
        self.apply()

    def selection_changed(self, selected):
        self.has_selection = bool(selected)
        self.apply()

    def toggle(self, checked):
        self.user_hidden = not checked
        self.apply()

    def apply(self):
        visible = self.has_selection and not self.user_hidden
        if visible and self.panel.isHidden():
            self.panel.show()
            self.splitter.setSizes(self.sizes)
        elif not visible and not self.panel.isHidden():
            sizes = self.splitter.sizes()
            if len(sizes) == 2 and all(size > 0 for size in sizes):
                self.sizes = sizes
            self.stop()
            self.panel.hide()
        self.button.setEnabled(self.has_selection)
        self.button.setChecked(visible)
        name = "Ocultar vista previa" if visible else "Mostrar vista previa"
        self.button.setAccessibleName(name)
        self.button.setToolTip(name)
        self.button.setText("")
        self.button.setIcon(app_icon("arrow-right" if visible else "arrow-left"))
