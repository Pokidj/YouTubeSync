from functools import lru_cache
from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton, QStyle
from youtube_sync_i18n import source_text


BUTTON_TONES = {
    "success": ("#203c30", "#3d7557", "#c6efda", "#294d3c", "#182e24"),
    "info": ("#22354a", "#42658a", "#d1e5fa", "#2c4561", "#192a3c"),
    "warning": ("#403522", "#806943", "#f1dfb9", "#51432c", "#30281c"),
    "danger": ("#49272d", "#8c4854", "#ffd5db", "#60343c", "#371e24"),
}


def button_tone(button, tone="", *, icon=""):
    if not tone:
        tone = {"arrow-up": "success", "play": "success", "circle-check": "success",
                "trash": "danger", "square": "danger", "x": "danger",
                "search": "info", "refresh-cw": "info", "external-link": "info",
                "folder-open": "info", "list-video": "info", "share-2": "info",
                "layers": "info", "download": "success", "key-round": "info",
                "brush": "warning", "lock": "warning", "rotate-ccw": "warning",
                "circle-question-mark": "warning"}.get(icon, "")
    button.setProperty("actionTone", tone)
    button.style().unpolish(button)
    button.style().polish(button)


def button_tone_styles():
    rules = []
    for tone, (background, border, foreground, hover, pressed) in BUTTON_TONES.items():
        selectors = [f'{kind}[actionTone="{tone}"]' for kind in ("QPushButton", "QToolButton")]
        selectors.append(f'#PrimaryButton[actionTone="{tone}"]')
        for state, colors in (("", (background, border, foreground)),
                              (":hover", (hover, border, foreground)),
                              (":pressed", (pressed, foreground, foreground)),
                              (":disabled", ("#1c1d21", "#282a30", "#757b87"))):
            rules.append(", ".join(selector + state for selector in selectors)
                         + " { background: %s; border-color: %s; color: %s; }" % colors)
    return "\n".join(rules)


@lru_cache(maxsize=128)
def app_icon(name: str, color: str = "#e5e7eb") -> QIcon:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    renderer = QSvgRenderer(QByteArray((root / "assets" / "icons" / f"{name}.svg").read_bytes()))
    if not renderer.isValid():
        raise ValueError(f"Icono no valido: {name}")
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def standard_icon(value: QStyle.StandardPixmap | QIcon) -> QIcon:
    if isinstance(value, QIcon):
        return value
    names = {
        QStyle.SP_ArrowRight: "arrow-right", QStyle.SP_BrowserReload: "refresh-cw",
        QStyle.SP_ComputerIcon: "external-link", QStyle.SP_DialogApplyButton: "key-round",
        QStyle.SP_DialogOpenButton: "external-link", QStyle.SP_DialogYesButton: "lock",
        QStyle.SP_DirOpenIcon: "folder-open", QStyle.SP_FileDialogContentsView: "terminal",
        QStyle.SP_FileDialogDetailedView: "settings", QStyle.SP_FileDialogListView: "layers",
        QStyle.SP_FileLinkIcon: "share-2", QStyle.SP_MediaPlay: "play", QStyle.SP_TrashIcon: "trash",
    }
    return app_icon(names.get(value, "circle-question-mark"))


def decorate_buttons(root) -> None:
    names = {"Elegir": "folder-open", "Guardar": "circle-check", "Cancelar": "x",
             "Conectar mi canal": "key-round", "Cargar listas": "refresh-cw", "Crear lista": "list-video",
             "Buscar actualizaciones": "refresh-cw", "Descargar": "download", "Abrir carpeta": "folder-open",
             "Consola": "terminal", "GitHub": "external-link", "Notas": "file-text", "Cerrar": "x"}
    for button in root.findChildren(QPushButton):
        name = names.get(source_text(button))
        if name:
            button.setIcon(app_icon(name))
            button_tone(button, icon=name)
