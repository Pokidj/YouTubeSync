"""The same column/order/color editor for both video tables."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QListWidget, QVBoxLayout

from youtube_sync_channel_columns import SELECTION_COLORS, selection_color
from youtube_sync_i18n_widgets import QComboBox, QLabel, QListWidgetItem, QPushButton, QWidget
from youtube_sync_icons import app_icon
import unicodedata


def settings_search_key(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(char))


class TableSettingsEditor(QWidget):
    def __init__(self, definitions, visible, defaults, color="green", tooltips=None, parent=None):
        super().__init__(parent)
        self.definitions = definitions
        self.defaults = list(defaults)
        self.tooltips = tooltips or {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        row = QHBoxLayout()
        self.columns = QListWidget()
        self.columns.setIconSize(QSize(20, 20))
        self.columns.setMinimumHeight(252)
        self.columns.setSelectionMode(QAbstractItemView.SingleSelection)
        self.columns.setDragDropMode(QAbstractItemView.InternalMove)
        self.columns.setDefaultDropAction(Qt.MoveAction)
        row.addWidget(self.columns, 1)
        tools = QVBoxLayout()
        for delta, icon, label in ((-1, "chevron-up", "Mover columna arriba"), (1, "chevron-down", "Mover columna abajo")):
            button = QPushButton(app_icon(icon), "")
            button.setMinimumWidth(92)
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.clicked.connect(lambda _checked=False, delta=delta: self.move_column(delta))
            tools.addWidget(button)
        tools.addStretch(1)
        self.reset = QPushButton(app_icon("rotate-ccw"), "Predeterminadas")
        self.reset.setToolTip("Restaurar columnas de esta tabla")
        self.reset.clicked.connect(lambda: self.fill(self.defaults))
        tools.addWidget(self.reset)
        row.addLayout(tools)
        layout.addLayout(row, 1)
        footer = QHBoxLayout()
        footer.addWidget(QLabel("Color de selección"))
        self.color = QComboBox()
        for key, (label, value) in SELECTION_COLORS.items():
            self.color.addItem(app_icon("circle-check", value), label, key)
        self.color.setCurrentIndex(max(0, self.color.findData(selection_color(color))))
        footer.addWidget(self.color, 1)
        layout.addLayout(footer)
        self.fill(visible)

    def fill(self, visible):
        self.columns.clear()
        definitions = {key: (label, icon) for key, label, icon in self.definitions}
        ordered = []
        for key in visible:
            if isinstance(key, str) and key in definitions and key not in ordered:
                ordered.append(key)
        for key in ordered + [key for key in definitions if key not in ordered]:
            label, icon = definitions[key]
            item = QListWidgetItem(app_icon(icon), label)
            item.setData(Qt.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            item.setCheckState(Qt.Checked if key in ordered else Qt.Unchecked)
            item.setSizeHint(QSize(0, 28))
            if key in self.tooltips:
                item.setToolTip(self.tooltips[key])
            self.columns.addItem(item)
        self.columns.setCurrentRow(0)

    def move_column(self, delta):
        row = self.columns.currentRow()
        target = row + delta
        if row >= 0 and 0 <= target < self.columns.count():
            self.columns.insertItem(target, self.columns.takeItem(row))
            self.columns.setCurrentRow(target)

    def selected_columns(self):
        return [self.columns.item(row).data(Qt.UserRole) for row in range(self.columns.count())
                if self.columns.item(row).checkState() == Qt.Checked]


def table_selection_style(color):
    value = SELECTION_COLORS[selection_color(color)][1]
    return (f"QTableWidget {{ selection-background-color: {value}; selection-color: white; }} "
            f"QTableWidget::item:selected {{ background: {value}; color: white; }}")
