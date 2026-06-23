from __future__ import annotations
import socket
from typing import Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

from ..models import SharedFile


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class ShareDialog(QDialog):
    def __init__(
        self,
        sf: SharedFile,
        port: Optional[int],
        public_ip: Optional[str],
        upnp_ok: bool,
        tunnel_url: Optional[str] = None,
        tailscale_ip: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._sf = sf
        self._port = port
        self._public_ip = public_ip
        self._upnp_ok = upnp_ok
        self._tunnel_url = tunnel_url
        self._tailscale_ip = tailscale_ip
        self._started = False
        self._max_dl_result = 0
        self._share_type_result = "lan"
        self._link = ""
        self._build()

    def _build(self) -> None:
        self.setWindowTitle(f"Freigeben: {self._sf.path.name}")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        name_lbl = QLabel(f"<b>{self._sf.path.name}</b>")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("color: #2C3E50;")
        layout.addWidget(name_lbl)

        type_group = QGroupBox("Freigabe-Art")
        type_group.setStyleSheet("QGroupBox { color: #2C3E50; }")
        type_layout = QVBoxLayout(type_group)
        self._rb_lan = QRadioButton("Für andere Nutzer derselben Software  (LAN + App-Link)")
        self._rb_lan.setStyleSheet("color: #2C3E50;")
        self._rb_http = QRadioButton("Per Download-Link für alle  (HTTP, für jeden Browser)")
        self._rb_http.setStyleSheet("color: #2C3E50;")
        self._rb_lan.setChecked(True)
        type_layout.addWidget(self._rb_lan)
        type_layout.addWidget(self._rb_http)

        if self._tailscale_ip:
            self._rb_tailscale = QRadioButton(
                "Über Tailscale  (privat & verschlüsselt, nur eigene Geräte)"
            )
            self._rb_tailscale.setStyleSheet("color: #2C3E50;")
            type_layout.addWidget(self._rb_tailscale)
        else:
            self._rb_tailscale = QRadioButton(
                "Über Tailscale  (nicht verbunden — siehe tailscale.com/download)"
            )
            self._rb_tailscale.setStyleSheet("color: #95A5A6;")
            self._rb_tailscale.setEnabled(False)
            type_layout.addWidget(self._rb_tailscale)

        layout.addWidget(type_group)

        # Status-Zeile für Internet-Freigabe (nur wenn HTTP gewählt)
        internet_ok = bool(self._tunnel_url) or self._upnp_ok
        if self._tunnel_url:
            status_text = "✓  Cloudflare-Tunnel aktiv — Link funktioniert sofort weltweit."
            status_style = "color: #27AE60; font-size: 9pt; padding: 4px;"
        elif self._upnp_ok:
            status_text = "✓  UPnP aktiv — Port wurde automatisch freigegeben."
            status_style = "color: #27AE60; font-size: 9pt; padding: 4px;"
        else:
            status_text = (
                "⚠  Tunnel noch nicht bereit. Bitte einige Sekunden warten "
                "und den Dialog erneut öffnen."
            )
            status_style = "color: #E67E22; font-size: 9pt; padding: 4px;"

        self._warn = QLabel(status_text)
        self._warn.setWordWrap(True)
        self._warn.setStyleSheet(status_style)
        self._warn.setVisible(False)
        layout.addWidget(self._warn)

        self._rb_http.toggled.connect(lambda checked: self._warn.setVisible(checked))
        if not internet_ok:
            self._rb_http.toggled.connect(
                lambda checked: self._start_btn.setEnabled(not checked or internet_ok)
            )

        # Status-Zeile für Tailscale-Freigabe
        self._ts_info = QLabel(
            f"✓  Verbunden als {self._tailscale_ip} — Link erreichbar für alle "
            "Geräte in deinem Tailnet." if self._tailscale_ip else ""
        )
        self._ts_info.setWordWrap(True)
        self._ts_info.setStyleSheet("color: #27AE60; font-size: 9pt; padding: 4px;")
        self._ts_info.setVisible(False)
        layout.addWidget(self._ts_info)
        if self._tailscale_ip:
            self._rb_tailscale.toggled.connect(self._ts_info.setVisible)

        form = QFormLayout()
        self._spin = QSpinBox()
        self._spin.setMinimum(0)
        self._spin.setMaximum(9999)
        self._spin.setValue(0)
        self._spin.setSpecialValueText("Unbegrenzt (∞)")
        self._spin.setFixedWidth(150)
        form.addRow("Max. Downloads:", self._spin)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._cancel_btn = QPushButton("Abbrechen")
        self._cancel_btn.clicked.connect(self.reject)
        self._start_btn = QPushButton("Freigabe starten")
        self._start_btn.setDefault(True)
        self._start_btn.clicked.connect(self._on_start)
        self._start_btn.setStyleSheet(
            "QPushButton { background: #27AE60; color: white; border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background: #2ECC71; }"
            "QPushButton:pressed { background: #219A52; }"
        )
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._start_btn)
        layout.addLayout(btn_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setVisible(False)
        self._sep = sep
        layout.addWidget(sep)

        self._link_frame = QFrame()
        link_layout = QHBoxLayout(self._link_frame)
        link_layout.setContentsMargins(0, 0, 0, 0)
        self._link_edit = QLineEdit()
        self._link_edit.setReadOnly(True)
        self._link_edit.setStyleSheet("font-family: monospace; font-size: 9pt;")
        self._copy_btn = QPushButton("Kopieren")
        self._copy_btn.setFixedWidth(80)
        self._copy_btn.clicked.connect(self._copy_link)
        link_layout.addWidget(self._link_edit)
        link_layout.addWidget(self._copy_btn)
        self._link_frame.setVisible(False)
        layout.addWidget(self._link_frame)

    def _on_start(self) -> None:
        self._started = True
        self._max_dl_result = self._spin.value()
        if self._tailscale_ip and self._rb_tailscale.isChecked():
            self._share_type_result = "tailscale"
        elif self._rb_lan.isChecked():
            self._share_type_result = "lan"
        else:
            self._share_type_result = "http"

        local_ip = _local_ip()

        if self._share_type_result == "lan":
            self._link = (
                f"http://{local_ip}:{self._port}"
                f"/{self._sf.token}/{self._sf.path.name}"
            )
        elif self._share_type_result == "tailscale":
            self._link = (
                f"http://{self._tailscale_ip}:{self._port}"
                f"/{self._sf.token}/{self._sf.path.name}"
            )
        else:
            if self._tunnel_url:
                base = self._tunnel_url.rstrip("/")
                self._link = f"{base}/{self._sf.token}/{self._sf.path.name}"
            elif self._public_ip:
                self._link = (
                    f"http://{self._public_ip}:{self._port}"
                    f"/{self._sf.token}/{self._sf.path.name}"
                )
            else:
                self._link = (
                    f"http://<Öffentliche-IP>:{self._port}"
                    f"/{self._sf.token}/{self._sf.path.name}"
                    f"  —  Portweiterleitung: {self._port} → {local_ip}"
                )

        self._link_edit.setText(self._link)
        self._sep.setVisible(True)
        self._link_frame.setVisible(True)
        self._rb_lan.setEnabled(False)
        self._rb_http.setEnabled(False)
        self._rb_tailscale.setEnabled(False)
        self._spin.setEnabled(False)
        self._cancel_btn.setVisible(False)
        self._start_btn.setText("Schließen")
        self._start_btn.setStyleSheet(
            "QPushButton { background: #3498DB; color: white; border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background: #5DADE2; }"
        )
        self._start_btn.clicked.disconnect(self._on_start)
        self._start_btn.clicked.connect(self.accept)
        self.adjustSize()

    def _copy_link(self) -> None:
        QApplication.clipboard().setText(self._link_edit.text())
        self._copy_btn.setText("✓")
        self._copy_btn.setEnabled(False)

    def result_settings(self) -> Tuple[int, str]:
        return self._max_dl_result, self._share_type_result

    def result_link(self) -> str:
        return self._link

    def was_started(self) -> bool:
        return self._started
