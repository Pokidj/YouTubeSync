import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from youtube_sync_icons import app_icon
from youtube_sync_local_player import LocalVideoPlayer
from youtube_sync_manual import youtube_video_id
from youtube_sync_youtube_player import EmbeddedYouTubePlayer
from youtube_sync_i18n_widgets import QDialog, QLabel, QLineEdit, QPushButton, QWidget, RawLabel


class ManualConfirmationDialog(QDialog):
    """Compare local and embedded YouTube playback, then decide explicitly."""

    def __init__(self, item: dict, parent=None, autoplay: bool = True):
        super().__init__(parent)
        self.item = dict(item)
        self.decision = ""
        self.upload_requested = False
        self.opened_id = ""
        self._closed = False
        self.autoplay = autoplay
        self.setWindowTitle("Comparar vídeo / YouTubeSync")
        self.setMinimumSize(640, 510)
        self.resize(760, 580)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        heading = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("PageTitle")
        heading.addWidget(self.title, 1)
        self.step_label = QLabel()
        self.step_label.setObjectName("Muted")
        heading.addWidget(self.step_label)
        layout.addLayout(heading)
        filename = RawLabel(Path(item["path"]).name)
        filename.setTextFormat(Qt.PlainText)
        filename.setWordWrap(True)
        filename.setToolTip(item["path"])
        layout.addWidget(filename)
        self.pages = QStackedWidget()
        layout.addWidget(self.pages, 1)

        local_page = QWidget()
        local_layout = QVBoxLayout(local_page)
        local_layout.setContentsMargins(0, 0, 0, 0)
        self.preview = LocalVideoPlayer(item["path"], self)
        local_layout.addWidget(self.preview)
        self.pages.addWidget(local_page)

        remote_page, remote = self.page()
        remote.setSpacing(8)
        remote_tools = QHBoxLayout()
        self.link = QLineEdit()
        self.link.setPlaceholderText("Enlace o ID del vídeo de YouTube")
        self.link.returnPressed.connect(self.open_embedded)
        remote_tools.addWidget(self.link, 1)
        self.reload_youtube = self.button("", "refresh-cw", self.open_embedded)
        self.reload_youtube.setAccessibleName("Reproducir YouTube aquí")
        self.reload_youtube.setToolTip("Reproducir YouTube aquí")
        remote_tools.addWidget(self.reload_youtube)
        self.open_youtube = self.button("", "external-link", self.open_remote)
        self.open_youtube.setAccessibleName("Abrir YouTube en navegador")
        self.open_youtube.setToolTip("Abrir YouTube en navegador")
        remote_tools.addWidget(self.open_youtube)
        remote.addLayout(remote_tools)
        self.remote_preview = EmbeddedYouTubePlayer(self)
        self.remote_preview.status.connect(self.remote_status_changed)
        self.remote_preview.reviewed.connect(self.remote_reviewed)
        self.remote_preview.failed.connect(self.remote_failed)
        remote.addWidget(self.remote_preview, 1)
        self.remote_status = self.label("Candidato de YouTube", remote)
        self.remote_status.setObjectName("Muted")

        decision_page, decision_layout = self.page()
        decision_layout.addStretch(1)
        self.label("¿Es el mismo vídeo completo y de tu canal?", decision_layout).setObjectName("CardValue")
        self.comparison_link = self.label("", decision_layout)
        self.comparison_link.setTextInteractionFlags(Qt.TextSelectableByMouse)
        choices = QHBoxLayout()
        self.yes = self.button("Sí, corresponde", "circle-check", lambda: self.finish("match"))
        self.yes.setObjectName("PrimaryButton")
        self.no = self.button("No, es otro vídeo", "x", lambda: self.set_step(3))
        for button in (self.yes, self.no):
            button.setMinimumHeight(40)
            choices.addWidget(button)
        decision_layout.addLayout(choices)
        self.label("«Sí» guardará «Subido (manual)», sin gastar API ni autorizar limpieza automática. Con «No» podrás descartar la asociación o solicitar una subida nueva.", decision_layout)
        decision_layout.addStretch(1)

        mismatch_page, mismatch = self.page()
        mismatch.addStretch(1)
        self.label("El candidato no corresponde", mismatch).setObjectName("CardValue")
        self.label("Se guardará la discrepancia para no volver a vincular este candidato al archivo. No se eliminará ningún vídeo de YouTube.", mismatch)
        self.upload_new = self.button("Subir como vídeo nuevo", "arrow-up", lambda: self.finish("different", True))
        self.upload_new.setObjectName("PrimaryButton")
        mismatch.addWidget(self.upload_new)
        self.keep_pending = self.button("Guardar sin subir", "clock", lambda: self.finish("different", False))
        mismatch.addWidget(self.keep_pending)
        self.label("Subir como nuevo solicita una transferencia adicional y puede consumir cuota. Guardar sin subir deja el archivo pendiente, con Auto OFF.", mismatch)
        mismatch.addStretch(1)

        nav = QHBoxLayout()
        self.cancel = self.button("Cancelar", "x", self.reject)
        self.cancel.setDefault(False)
        nav.addWidget(self.cancel)
        nav.addStretch(1)
        self.back = self.button("Anterior", "arrow-left", self.go_back)
        nav.addWidget(self.back)
        self.next = self.button("Siguiente: YouTube", "arrow-right", self.advance)
        self.next.setObjectName("PrimaryButton")
        nav.addWidget(self.next)
        layout.addLayout(nav)
        self.link.textChanged.connect(self.link_changed)
        self.link.setText(f"https://www.youtube.com/watch?v={item['youtube_id']}" if item.get("youtube_id") else "")
        self.set_step(0)

    def page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(16)
        self.pages.addWidget(page)
        return page, layout

    def label(self, text, layout):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.PlainText)
        layout.addWidget(label)
        return label

    def button(self, label, icon, callback):
        button = QPushButton(app_icon(icon), label)
        button.setToolTip(label)
        button.setAccessibleName(label)
        button.setAutoDefault(False)
        button.clicked.connect(callback)
        return button

    def video_id(self):
        return youtube_video_id(self.link.text())

    def link_changed(self):
        self.remote_preview.release()
        self.opened_id = ""
        self.decision = ""
        self.remote_status.setText("Candidato de YouTube")
        self.update_state()

    def update_state(self):
        try:
            video_id = self.video_id()
        except ValueError:
            video_id = ""
        self.open_youtube.setEnabled(bool(video_id))
        self.reload_youtube.setEnabled(bool(video_id))
        index = self.pages.currentIndex()
        self.next.setVisible(index < 2)
        self.next.setEnabled(Path(self.item["path"]).is_file() if index == 0 else bool(video_id and self.opened_id == video_id))
        self.next.setText("Siguiente: YouTube" if index == 0 else "Ya lo he revisado")
        self.next.setAccessibleName(self.next.text())
        self.next.setToolTip(self.next.text())
        self.back.setVisible(index > 0)
        ready = bool(video_id and self.opened_id == video_id)
        self.yes.setEnabled(ready)
        self.no.setEnabled(ready)
        self.upload_new.setEnabled(ready)
        self.keep_pending.setEnabled(ready)

    def set_step(self, index):
        if self._closed:
            return
        if index > 0:
            self.preview.pause()
        if index != 1:
            self.remote_preview.release()
        self.pages.setCurrentIndex(index)
        self.title.setText(("Revisa el archivo local", "Compara con YouTube", "Confirma la correspondencia", "Elige qué hacer")[index])
        self.step_label.setText(f"{min(index + 1, 3)} de 3")
        if index == 2:
            self.comparison_link.setText(f"YouTube: https://www.youtube.com/watch?v={self.video_id()}")
        self.update_state()
        if index == 0 and self.autoplay and self.isVisible():
            self.preview.play_file()

    def advance(self):
        if not self.next.isEnabled():
            return
        if self.pages.currentIndex() == 0:
            self.set_step(1)
            if self.open_youtube.isEnabled():
                self.open_embedded()
        elif self.pages.currentIndex() == 1 and self.opened_id:
            self.set_step(2)

    def go_back(self):
        self.set_step(max(0, self.pages.currentIndex() - 1))

    def open_remote(self):
        try:
            video_id = self.video_id()
            self.preview.pause()
            self.remote_preview.release()
            if not webbrowser.open(f"https://www.youtube.com/watch?v={video_id}"):
                self.remote_status.setText("No se ha podido abrir el navegador. Vuelve a intentarlo.")
                return
            self.opened_id = video_id
            self.remote_status.setText("Candidato abierto en el navegador")
        except (ValueError, OSError) as exc:
            self.remote_status.setText(str(exc))
        self.update_state()

    def open_embedded(self):
        if self._closed or self.pages.currentIndex() != 1:
            return
        try:
            video_id = self.video_id()
            self.preview.pause()
            self.opened_id = ""
            self.update_state()
            self.remote_preview.load_video(video_id)
        except (ValueError, OSError, RuntimeError) as exc:
            self.remote_failed(str(exc))

    def remote_status_changed(self, message):
        if not self._closed:
            self.remote_status.setText(message)

    def remote_reviewed(self, video_id):
        if not self._closed and self.pages.currentIndex() == 1:
            try:
                if video_id == self.video_id():
                    self.opened_id = video_id
                    self.update_state()
            except ValueError:
                pass

    def remote_failed(self, message):
        if not self._closed and self.pages.currentIndex() == 1:
            self.opened_id = ""
            self.remote_status.setText(message)
            self.update_state()

    def finish(self, decision, upload_requested=False):
        valid_step = (decision == "match" and self.pages.currentIndex() == 2) or (decision == "different" and self.pages.currentIndex() == 3)
        if not valid_step or not self.opened_id:
            return
        if self.video_id() != self.opened_id:
            return
        self.decision, self.upload_requested = decision, upload_requested
        self.accept()

    def accept(self):
        if (self.decision == "match" and self.pages.currentIndex() == 2) or (self.decision == "different" and self.pages.currentIndex() == 3):
            super().accept()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.start_preview)

    def start_preview(self):
        if not self._closed and self.autoplay and self.isVisible() and self.pages.currentIndex() == 0:
            self.preview.play_file()

    def done(self, result):
        self._closed = True
        self.preview.release()
        self.remote_preview.release()
        super().done(result)

    def reject(self):
        self.done(QDialog.Rejected)
