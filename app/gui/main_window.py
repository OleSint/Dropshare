from __future__ import annotations
import uuid
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..discovery import LanDiscovery
from ..models import SharedFile
from ..server import FileServer
from ..tunnel import CloudflareTunnel
from ..upnp import setup_upnp_async
from .file_list import FileListWidget
from .network_panel import NetworkPanel
from .share_dialog import ShareDialog


class _Signals(QObject):
    """Thread-safe bridge: server/UPnP/discovery threads → Qt main thread."""
    share_changed   = pyqtSignal(str)                  # token
    upnp_done       = pyqtSignal(bool, str, int)       # success, ip, port
    peer_shares     = pyqtSignal(str, str, int, list)  # name, ip, port, files
    peer_lost       = pyqtSignal(str)                  # name
    download_done   = pyqtSignal(bool, str)            # success, filename
    tunnel_status   = pyqtSignal(str)                  # status text
    tunnel_ready    = pyqtSignal(str)                  # base URL
    tunnel_error    = pyqtSignal(str)                  # error text


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._node_id = uuid.uuid4().hex[:8]
        self._files: dict[str, SharedFile] = {}
        self._public_ip: Optional[str] = None
        self._upnp_ok = False

        self._signals = _Signals()
        self._signals.share_changed.connect(self._on_share_changed)
        self._signals.upnp_done.connect(self._on_upnp_done)
        self._signals.peer_shares.connect(self._on_peer_shares)
        self._signals.peer_lost.connect(self._on_peer_lost)
        self._signals.download_done.connect(self._on_download_done)
        self._signals.tunnel_status.connect(self._on_tunnel_status)
        self._signals.tunnel_ready.connect(self._on_tunnel_ready)
        self._signals.tunnel_error.connect(self._on_tunnel_error)

        self._server = FileServer()
        self._server.on_share_changed = (
            lambda token: self._signals.share_changed.emit(token)
        )
        self._server.start()

        self._tunnel: Optional[CloudflareTunnel] = None
        self._tunnel_url: Optional[str] = None
        self._discovery: Optional[LanDiscovery] = None
        self._start_tunnel()
        self._start_discovery()
        self._start_upnp()
        self._build_ui()

        # Periodisch Peer-Listen aktualisieren (alle 30 s)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_peers)
        self._refresh_timer.start(30_000)

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle("DropShare")
        self.setMinimumSize(640, 460)
        self.resize(740, 560)
        self.setStyleSheet("QMainWindow { background: #F8F9FA; }")

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 16, 16, 8)
        outer.setSpacing(10)

        # Header row
        hdr_row = QHBoxLayout()
        title = QLabel("DropShare")
        f = title.font()
        f.setPointSize(15)
        f.setBold(True)
        title.setFont(f)
        hdr_row.addWidget(title)
        hdr_row.addStretch()

        self._dl_btn = QPushButton("↓  Link herunterladen")
        self._dl_btn.setToolTip("Einen DropShare- oder HTTP-Link in die App einfügen und herunterladen")
        self._dl_btn.setStyleSheet(
            "QPushButton { border: 1px solid #BDC3C7; border-radius: 4px;"
            " padding: 4px 12px; font-size: 9pt; color: #2C3E50; }"
            "QPushButton:hover { background: #EBF5FB; }"
        )
        self._dl_btn.clicked.connect(self._on_paste_link)
        hdr_row.addWidget(self._dl_btn)
        outer.addLayout(hdr_row)

        sub = QLabel("Dateien per Drag & Drop hinzufügen, dann per Rechtsklick freigeben.")
        sub.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        outer.addWidget(sub)

        # Main file list
        self._file_list = FileListWidget()
        self._file_list.files_dropped.connect(self._on_files_dropped)
        self._file_list.share_requested.connect(self._on_share_requested)
        self._file_list.stop_sharing_requested.connect(self._on_stop_sharing)
        self._file_list.remove_requested.connect(self._on_remove_file)
        self._file_list.copy_link_requested.connect(self._on_copy_link)

        # Network panel (initially hidden)
        self._net_panel = NetworkPanel()
        self._net_panel.download_requested.connect(self._on_network_download)
        self._net_panel.copy_link_requested.connect(
            lambda url: QApplication.clipboard().setText(url)
        )
        self._net_panel.setVisible(False)

        outer.addWidget(self._file_list, stretch=3)
        outer.addWidget(self._net_panel, stretch=2)

        # Status bar
        sb = QStatusBar()
        sb.setStyleSheet("QStatusBar { font-size: 8pt; color: #7F8C8D; }")
        self.setStatusBar(sb)
        self._lbl_port = QLabel(f"Server: Port {self._server.port}")
        self._lbl_tunnel = QLabel("Tunnel: wird gestartet …")
        sb.addWidget(self._lbl_port)
        sb.addWidget(_sep())
        sb.addWidget(self._lbl_tunnel)

    # ── Networking ────────────────────────────────────────────────────────

    def _start_tunnel(self) -> None:
        if self._server.port is None:
            return
        self._tunnel = CloudflareTunnel(self._server.port)
        self._tunnel.on_status = lambda msg: self._signals.tunnel_status.emit(msg)
        self._tunnel.on_ready  = lambda url: self._signals.tunnel_ready.emit(url)
        self._tunnel.on_error  = lambda err: self._signals.tunnel_error.emit(err)
        self._tunnel.start()

    def _start_upnp(self) -> None:
        if self._server.port is None:
            return
        setup_upnp_async(
            self._server.port,
            lambda ok, ip, port: self._signals.upnp_done.emit(ok, ip or "", port or 0),
        )

    def _start_discovery(self) -> None:
        if self._server.port is None:
            return
        self._discovery = LanDiscovery(
            port=self._server.port,
            node_id=self._node_id,
            on_peer_added=self._on_peer_found,
            on_peer_removed=lambda name: self._signals.peer_lost.emit(name),
        )
        if self._discovery.available:
            self._discovery.start()

    def _on_peer_found(self, name: str, ip: str, port: int) -> None:
        self._server.fetch_peer_shares(
            ip, port,
            lambda files: self._signals.peer_shares.emit(name, ip, port, files),
        )

    def _refresh_peers(self) -> None:
        if not self._discovery:
            return
        for name, (ip, port) in list(self._discovery._peers.items()):
            self._on_peer_found(name, ip, port)

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
            sf, self._server.port, self._public_ip, self._upnp_ok,
            tunnel_url=self._tunnel_url, parent=self,
        )
        if dlg.exec() and dlg.was_started():
            max_dl, share_type = dlg.result_settings()
            sf.max_downloads = max_dl
            sf.download_count = 0
            sf.share_type = share_type
            sf.active = True
            sf.link = dlg.result_link()
            self._server.add_share(sf)
            self._file_list.refresh_item(path_str)

    def _on_stop_sharing(self, path_str: str) -> None:
        sf = self._files.get(path_str)
        if sf:
            sf.active = False
            sf.share_type = ""
            sf.link = ""
            self._server.remove_share(sf.token)
            self._file_list.refresh_item(path_str)

    def _on_remove_file(self, path_str: str) -> None:
        sf = self._files.pop(path_str, None)
        if sf and sf.active:
            self._server.remove_share(sf.token)
        self._file_list.remove_file(path_str)

    def _on_copy_link(self, path_str: str) -> None:
        sf = self._files.get(path_str)
        if sf and sf.link:
            QApplication.clipboard().setText(sf.link)

    def _on_share_changed(self, token: str) -> None:
        for path_str, sf in self._files.items():
            if sf.token == token:
                self._file_list.refresh_item(path_str)
                break

    def _on_upnp_done(self, success: bool, ip: str, port: int) -> None:
        self._upnp_ok = success
        self._public_ip = ip or None

    def _on_tunnel_status(self, msg: str) -> None:
        self._lbl_tunnel.setText(f"Tunnel: {msg}")

    def _on_tunnel_ready(self, url: str) -> None:
        self._tunnel_url = url
        self._lbl_tunnel.setText(f"Tunnel: ✓  bereit")
        self._lbl_tunnel.setStyleSheet("color: #27AE60;")

    def _on_tunnel_error(self, err: str) -> None:
        self._lbl_tunnel.setText(f"Tunnel: ✗  {err}")
        self._lbl_tunnel.setStyleSheet("color: #E74C3C;")

    def _on_peer_shares(self, name: str, ip: str, port: int, files: list) -> None:
        self._net_panel.update_peer(name, ip, port, files)
        self._net_panel.setVisible(self._net_panel.has_peers)

    def _on_peer_lost(self, name: str) -> None:
        self._net_panel.remove_peer(name)
        self._net_panel.setVisible(self._net_panel.has_peers)

    def _on_network_download(self, url: str, filename: str) -> None:
        dest = Path.home() / "Downloads" / filename
        # Eindeutigen Dateinamen sicherstellen
        stem, suffix = dest.stem, dest.suffix
        counter = 1
        while dest.exists():
            dest = dest.parent / f"{stem} ({counter}){suffix}"
            counter += 1
        self.statusBar().showMessage(f"Lade herunter: {filename} …")
        self._server.download_url(
            url, dest,
            lambda ok: self._signals.download_done.emit(ok, filename),
        )

    def _on_download_done(self, success: bool, filename: str) -> None:
        if success:
            self.statusBar().showMessage(f"✓  {filename} in Downloads gespeichert", 5000)
        else:
            self.statusBar().showMessage(f"✗  Download fehlgeschlagen: {filename}", 5000)

    def _on_paste_link(self) -> None:
        url, ok = QInputDialog.getText(
            self, "Link herunterladen",
            "DropShare- oder HTTP-Link einfügen:",
            text=QApplication.clipboard().text(),
        )
        if not ok or not url.strip():
            return
        url = url.strip()
        # dropshare:// → http://
        if url.startswith("dropshare://"):
            url = "http://" + url[len("dropshare://"):]
        if not url.startswith("http"):
            QMessageBox.warning(self, "Ungültiger Link", "Bitte einen gültigen http(s)- oder dropshare://-Link eingeben.")
            return
        filename = url.rstrip("/").split("/")[-1] or "download"
        self._on_network_download(url, filename)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._tunnel:
            self._tunnel.stop()
        if self._discovery:
            self._discovery.stop()
        super().closeEvent(event)


def _sep() -> QLabel:
    lbl = QLabel("|")
    lbl.setStyleSheet("color: #D5D8DC;")
    return lbl
