"""Render the canonical SVG and package native, multi-resolution Windows icons."""

import os
from pathlib import Path
import struct

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_logo(source, size):
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise ValueError("Invalid logo SVG")
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def build(root):
    source = root / "assets/youtube-sync-logo.svg"
    image = render_logo(source, 1024)
    if not image.save(str(root / "assets/youtube-sync-logo.png"), "PNG"):
        raise OSError("Could not export logo PNG")
    frames = []
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not render_logo(source, size).save(buffer, "PNG"):
            raise OSError("Could not render icon frame")
        frames.append((size, bytes(buffer.data())))
    directory = bytearray(struct.pack("<HHH", 0, 1, len(frames)))
    offset = 6 + 16 * len(frames)
    for size, data in frames:
        dimension = 0 if size == 256 else size
        directory.extend(struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (root / "assets/youtube-sync.ico").write_bytes(bytes(directory) + b"".join(data for _, data in frames))
    print("Logo SVG exported to PNG and 8 native Windows icon sizes")


if __name__ == "__main__":
    app = QGuiApplication.instance() or QGuiApplication([])
    build(Path(__file__).resolve().parents[1])
