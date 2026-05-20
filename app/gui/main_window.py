from __future__ import annotations
import uuid
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..discovery import LanDiscovery
from ..models import SharedFile
from ..server import FileServer
from ..upnp import setup_upnp_async
from .file_list import FileListWidget
from .share_dialog import ShareDialog


class _Signals(QObject):
    """Thread-safe bridge: server/UPnP threads → Qt main thread."""
    share_changed = pyqtSignal(str)                     # token (empty = UPnP update)
    upnp_done = pyqtSignal(bool, str, int)              # success, ip, port


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._node_id = uuid.uuid4().hex[:8]
        self._files: dict[str, SharedFile] = {}        # path str → SharedFile
        self._public_ip: Optional[str] = None
        self._upnp_ok = False

        self._signals = _Signals()
        self._signals.share_changed.connect(self._on_share_changed)
        self._signals.upnp_done.connect(self._on_upnp_done)

        self._server = FileServer()
        self._server.on_share_changed = (
            lambda token: self._signals.share_changed.emit(token)
        )
        self._server.start()

        self._discovery: Optional[LanDiscovery] = None
        self._start_discovery()
        self._start_upnp()
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle("DropShare")
        self.setMinimumSize(620, 420)
        self.resize(720, 520)
        self.setStyleSheet("QMainWindow { background: #F8F9FA; }")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(10)

        header = QLabel("DropShare")
        font = header.font()
        font.setPointSize(15)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)

        sub = QLabel("Dateien per Rechtsklick freigeben — Empfänger brauchen nur den Link.")
        sub.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        layout.addWidget(sub)

        self._file_list = FileListWidget()
        self._file_list.files_dropped.connect(self._on_files_dropped)
        self._file_list.share_requested.connect(self._on_share_requested)
        self._file_list.stop_sharing_requested.connect(self._on_stop_sharing)
        self._file_list.remove_requested.connect(self._on_remove_file)
        layout.addWidget(self._file_list)

        sb = QStatusBar()
        sb.setStyleSheet("QStatusBar { font-size: 8pt; color: #7F8C8D; }")
        self.setStatusBar(sb)

        self._lbl_port = QLabel(f"Server: Port {self._server.port}")
        self._lbl_upnp = QLabel("UPnP: wird geprüft …")
        sb.addWidget(self._lbl_port)
        sb.addWidget(_sep())
        sb.addWidget(self._lbl_upnp)

    # ── Networking ────────────────────────────────────────────────────────

    def _start_upnp(self) -> None:
        if self._server.port is None:
            return
        setup_upnp_async(
            self._server.port,
            lambda ok, ip, port: self._signals.upnp_done.emit(
                ok, ip or "", port or 0
            ),
        )

    def _start_discovery(self) -> None:
        if self._server.port is None:
            return
        self._discovery = LanDiscovery(
            port=self._server.port,
            node_id=self._node_id,
        )
        if self._discovery.available:
            self._discovery.start()

    # ── Slot handlers ─────────────────────────────────────────────────────

    def _on_files_dropped(self, paths: list[Path]) -> None:
        for path in paths:
            key = str(path)
            if key not in self._files:
                sf = SharedFile(path=path)
                self._files[key] = sf
                self._file_list.add_file(sf)

    def _on_share_requested(self, path_str: str) -> None:
        sf = self._files.get(path_str)
        if not sf:
            return
        dlg = ShareDialog(
            sf, self._server.port, self._public_ip, self._upnp_ok, self
        )
        if dlg.exec() and dlg.was_started():
            max_dl, share_type = dlg.result_settings()
            sf.max_downloads = max_dl
            sf.download_count = 0
            sf.share_type = share_type
            sf.active = True
            self._server.add_share(sf)
            self._file_list.refresh_item(path_str)

    def _on_stop_sharing(self, path_str: str) -> None:
        sf = self._files.get(path_str)
        if sf:
            sf.active = False
            sf.share_type = ""
            self._server.remove_share(sf.token)
            self._file_list.refresh_item(path_str)

    def _on_remove_file(self, path_str: str) -> None:
        sf = self._files.pop(path_str, None)
        if sf and sf.active:
            self._server.remove_share(sf.token)
        self._file_list.remove_file(path_str)

    def _on_share_changed(self, token: str) -> None:
        for path_str, sf in self._files.items():
            if sf.token == token:
                self._file_list.refresh_item(path_str)
                break

    def _on_upnp_done(self, success: bool, ip: str, port: int) -> None:
        self._upnp_ok = success
        self._public_ip = ip or None
        if success:
            self._lbl_upnp.setText(f"UPnP: ✓  {ip}")
        elif ip:
            self._lbl_upnp.setText(f"UPnP: fehlgeschlagen  (öffentl. IP: {ip})")
        else:
            self._lbl_upnp.setText("UPnP: nicht verfügbar — manuelle Weiterleitung nötig")

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._discovery:
            self._discovery.stop()
        super().closeEvent(event)


def _sep() -> QLabel:
    lbl = QLabel("|")
    lbl.setStyleSheet("color: #D5D8DC;")
    return lbl
