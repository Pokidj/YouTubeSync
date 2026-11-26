"""Qt presentation adapters; editable user content and enum models are not translated."""

from PySide6 import QtWidgets as W
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction as NativeAction
from youtube_sync_i18n import t


class Presentation:
    def setWindowTitle(self, text):
        super().setWindowTitle(t(text))

    def setToolTip(self, text):
        self.setProperty("sourceToolTip", text)
        super().setToolTip(t(text))

    def setAccessibleName(self, text):
        self.setProperty("sourceAccessibleName", text)
        super().setAccessibleName(t(text))


class TextPresentation(Presentation):
    def __init__(self, *args, **kwargs):
        raw = next((arg for arg in args if isinstance(arg, str)), kwargs.get("text", ""))
        args = tuple(t(arg) if isinstance(arg, str) else arg for arg in args)
        if "text" in kwargs:
            kwargs["text"] = t(kwargs["text"])
        super().__init__(*args, **kwargs)
        self.setProperty("sourceText", raw)

    def setText(self, text):
        self.setProperty("sourceText", text)
        super().setText(t(text))


class QLabel(TextPresentation, W.QLabel):
    def setRawText(self, text):
        W.QLabel.setText(self, text)


class RawLabel(Presentation, W.QLabel):
    """Names, paths, URLs and other user-authored content are never translated."""


class QPushButton(TextPresentation, W.QPushButton):
    pass


class QCheckBox(TextPresentation, W.QCheckBox):
    pass


class QToolButton(TextPresentation, W.QToolButton):
    pass


class QAction(TextPresentation, NativeAction):
    pass


class QWidget(Presentation, W.QWidget):
    pass


class QDialog(Presentation, W.QDialog):
    pass


class QMainWindow(Presentation, W.QMainWindow):
    pass


class QLineEdit(Presentation, W.QLineEdit):
    def setPlaceholderText(self, text):
        super().setPlaceholderText(t(text))


class QStyledItemDelegate(W.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        view = self.parent()
        columns = view.property("translatedColumns") if view is not None else None
        if columns and index.column() in columns:
            option.text = t(option.text)


class ComboDelegate(W.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if self.parent().translate_item(index.row()):
            option.text = t(option.text)


class QComboBox(Presentation, W.QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setItemDelegate(ComboDelegate(self))

    def translate_item(self, index):
        # Playlist names and account names are user content, even if named "Todas".
        if self.itemData(index, Qt.UserRole + 57) is False:
            return False
        limit = self.property("translatedItemCount")
        return limit is None or index < limit

    def paintEvent(self, event):
        painter = W.QStylePainter(self)
        option = W.QStyleOptionComboBox()
        self.initStyleOption(option)
        if self.translate_item(self.currentIndex()):
            option.currentText = t(option.currentText)
        painter.drawComplexControl(W.QStyle.CC_ComboBox, option)
        painter.drawControl(W.QStyle.CE_ComboBoxLabel, option)


class HeaderView(W.QHeaderView):
    def paintSection(self, painter, rect, index):
        if not rect.isValid():
            return
        option = W.QStyleOptionHeader()
        self.initStyleOption(option)
        self.initStyleOptionForIndex(option, index)
        option.rect = rect
        option.text = t(option.text)
        self.style().drawControl(W.QStyle.CE_Header, option, painter, self)


class QTableWidget(Presentation, W.QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setHorizontalHeader(HeaderView(Qt.Horizontal, self))
        self.setItemDelegate(QStyledItemDelegate(self))


class QTableWidgetItem(W.QTableWidgetItem):
    def setToolTip(self, text):
        super().setToolTip(t(text))


class QTabWidget(Presentation, W.QTabWidget):
    def addTab(self, *args):
        return super().addTab(*tuple(t(arg) if isinstance(arg, str) else arg for arg in args))


class QListWidgetItem(W.QListWidgetItem):
    def __init__(self, *args):
        super().__init__(*tuple(t(arg) if isinstance(arg, str) else arg for arg in args))


class QMessageBox(TextPresentation, W.QMessageBox):
    def setInformativeText(self, text):
        super().setInformativeText(t(text))

    def setDetailedText(self, text):
        super().setDetailedText(t(text))

    @staticmethod
    def information(parent, title, text, *args, **kwargs):
        return W.QMessageBox.information(parent, t(title), t(text), *args, **kwargs)

    @staticmethod
    def warning(parent, title, text, *args, **kwargs):
        return W.QMessageBox.warning(parent, t(title), t(text), *args, **kwargs)

    @staticmethod
    def critical(parent, title, text, *args, **kwargs):
        return W.QMessageBox.critical(parent, t(title), t(text), *args, **kwargs)

    @staticmethod
    def question(parent, title, text, *args, **kwargs):
        return W.QMessageBox.question(parent, t(title), t(text), *args, **kwargs)

    def addButton(self, *args):
        return super().addButton(*tuple(t(arg) if isinstance(arg, str) else arg for arg in args))


class QFileDialog:
    @staticmethod
    def getExistingDirectory(parent, caption, directory="", *args, **kwargs):
        return W.QFileDialog.getExistingDirectory(parent, t(caption), directory, *args, **kwargs)

    @staticmethod
    def getOpenFileName(parent, caption, directory="", filter="", *args, **kwargs):
        return W.QFileDialog.getOpenFileName(parent, t(caption), directory, t(filter), *args, **kwargs)

    @staticmethod
    def getSaveFileName(parent, caption, directory="", filter="", *args, **kwargs):
        return W.QFileDialog.getSaveFileName(parent, t(caption), directory, t(filter), *args, **kwargs)


class QInputDialog:
    @staticmethod
    def getText(parent, title, label, *args, **kwargs):
        return W.QInputDialog.getText(parent, t(title), t(label), *args, **kwargs)

    @staticmethod
    def getItem(parent, title, label, items, *args, translate_items=True, **kwargs):
        translated = [t(item) for item in items] if translate_items else list(items)
        value, ok = W.QInputDialog.getItem(parent, t(title), t(label), translated, *args, **kwargs)
        return (items[translated.index(value)] if ok and value in translated else value), ok


class QMenu(Presentation, W.QMenu):
    def addAction(self, *args):
        action = super().addAction(*tuple(t(arg) if isinstance(arg, str) else arg for arg in args))
        for arg in args:
            if isinstance(arg, str):
                action.setProperty("sourceText", arg)
                break
        return action
