"""Loaded only after the isolated WebEngine startup check succeeds."""

import json
from urllib.parse import urlsplit

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView

from youtube_sync_manual import youtube_video_id
from youtube_sync_youtube_player import EVENT_PREFIX, PLAYER_ORIGIN
from youtube_sync_player_controls import telemetry


class PlayerIdentity(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        url = info.requestUrl()
        if (url.host() in {"www.youtube.com", "www.youtube-nocookie.com"}
                and (url.path().startswith("/embed/") or url.path() == "/iframe_api")):
            info.setHttpHeader(b"Referer", (PLAYER_ORIGIN + "/").encode("ascii"))


class PlayerPage(QWebEnginePage):
    event = Signal(str, str, object)

    def javaScriptConsoleMessage(self, level, message, line, source):
        if not message.startswith(EVENT_PREFIX):
            return
        try:
            data = json.loads(message[len(EVENT_PREFIX):])
            if data.get("type") == "progress":
                self.event.emit(youtube_video_id(data["id"]), "progress", telemetry(data["value"]))
            elif (data.get("type") in {"ready", "state", "error", "autoplay"}
                    and type(data.get("value")) is int):
                self.event.emit(youtube_video_id(data["id"]), data["type"], data["value"])
        except (ValueError, KeyError, TypeError):
            pass

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if is_main_frame:
            return url.scheme() in {"about", "data"} or url.host() == urlsplit(PLAYER_ORIGIN).hostname
        return url.scheme() == "https"


def create_webview(parent, event, terminated, muted):
    view = QWebEngineView(parent)
    profile = QWebEngineProfile(view)  # Memory-only; no OAuth or browser cookies.
    profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
    identity = PlayerIdentity(profile)
    profile.setUrlRequestInterceptor(identity)
    profile._identity = identity
    page = PlayerPage(profile, view)
    page.setAudioMuted(muted)
    page.setBackgroundColor(QColor("#09090b"))
    page.settings().setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
    page.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)
    page.event.connect(event)
    page.renderProcessTerminated.connect(lambda *_: terminated(view))
    view.setPage(page)
    view.setContextMenuPolicy(Qt.NoContextMenu)
    return view, profile
