from __future__ import annotations
from typing import Callable

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

_ROLE_DATA = Qt.ItemDataRole.UserRole
_ROLE_TYPE = Qt.ItemDataRole.UserRole + 1   # "header" | "file"

_HEADER_BG = QColor("#EBF5FB")
_HEADER_FG = QColor("#2980B9")
_FILE_FG   = QColor("#2C3E50")
_SUB_FG    = QColor("#95A5A6")
_SEP       = QColor("#EEEEEE")


def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class _Delegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        item_type = index.data(_ROLE_TYPE)
        r = option.rect

        if item_type == "header":
            painter.fillRect(r, _HEADER_BG)
            f = QFont()
            f.setPointSize(9)
            f.setBold(True)
            painter.setFont(f)
            painter.setPen(_HEADER_FG)
            painter.drawText(r.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter, index.data())
        else:
            is_sel = bool(option.state & QStyle.StateFlag.State_Selected)
            painter.fillRect(r, QColor("#EBF5FB") if is_sel else QColor("white"))
            data = index.data(_ROLE_DATA) or {}
            name = data.get("name", "")
            size = data.get("size", 0)
            remaining = data.get("remaining", -1)

            pad = 12
            f_name = QFont()
            f_name.setPointSize(9)
            painter.setFont(f_name)
            painter.setPen(_FILE_FG)
            painter.drawText(r.adjusted(pad + 20, 4, -pad, 0),
                             Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, name)

            f_sub = QFont()
            f_sub.setPointSize(8)
            painter.setFont(f_sub)
            painter.setPen(_SUB_FG)
            sub = _fmt_size(size)
            if remaining >= 0:
                sub += f"  ·  noch {remaining}× verfügbar"
            painter.drawText(r.adjusted(pad + 20, r.height() // 2 + 2, -pad, 0),
                             Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, sub)

            # small download arrow hint
            painter.setPen(QColor("#2980B9"))
            painter.drawText(r.adjusted(pad, 0, -pad, 0),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "↓")

        painter.setPen(_SEP)
        painter.drawLine(r.left(), r.bottom(), r.right(), r.bottom())
        painter.restore()

    def sizeHint(self, option, index) -> "QSize":
        from PyQt6.QtCore import QSize
        t = index.data(_ROLE_TYPE)
        return QSize(0, 26 if t == "header" else 46)


class NetworkPanel(QWidget):
    """Shows files shared by other DropShare instances on the LAN."""

    download_requested = pyqtSignal(str, str)   # url, filename
    copy_link_requested = pyqtSignal(str)        # url

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._peers: dict[str, dict] = {}   # name -> {ip, port, files}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(4)

        hdr = QLabel("Im Netzwerk")
        f = hdr.font()
        f.setPointSize(11)
        f.setBold(True)
        hdr.setFont(f)
        layout.addWidget(hdr)

        sub = QLabel("Freigegebene Dateien anderer DropShare-Nutzer im selben WLAN")
        sub.setStyleSheet("color: #7F8C8D; font-size: 8pt;")
        layout.addWidget(sub)

        self._list = QListWidget()
        self._list.setItemDelegate(_Delegate())
        self._list.setStyleSheet(
            "QListWidget { border: 1px solid #D5D8DC; border-radius: 8px; background: white; outline: none; }"
            "QListWidget::item { border: none; padding: 0; }"
            "QListWidget::item:selected { background: transparent; }"
        )
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._context_menu)
        self._list.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    def update_peer(self, name: str, ip: str, port: int, files: list) -> None:
        self._peers[name] = {"ip": ip, "port": port, "files": files}
        self._refresh()

    def remove_peer(self, name: str) -> None:
        self._peers.pop(name, None)
        self._refresh()

    @property
    def has_peers(self) -> bool:
        return bool(self._peers)

    def _refresh(self) -> None:
        self._list.clear()
        for name, peer in self._peers.items():
            # Peer header row
            hdr_item = QListWidgetItem(f"📡  {peer['ip']}:{peer['port']}")
            hdr_item.setData(_ROLE_TYPE, "header")
            hdr_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(hdr_item)

            if not peer["files"]:
                empty = QListWidgetItem("    (keine aktiven Freigaben)")
                empty.setData(_ROLE_TYPE, "file")
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                self._list.addItem(empty)
                continue

            for f in peer["files"]:
                url = f"http://{peer['ip']}:{peer['port']}/{f['token']}/{f['name']}"
                item = QListWidgetItem(f["name"])
                item.setData(_ROLE_TYPE, "file")
                item.setData(_ROLE_DATA, {**f, "url": url})
                self._list.addItem(item)

    def _file_data(self, item: QListWidgetItem) -> dict | None:
        if item and item.data(_ROLE_TYPE) == "file":
            return item.data(_ROLE_DATA)
        return None

    def _on_double_click(self, index) -> None:
        item = self._list.item(index.row())
        data = self._file_data(item)
        if data and data.get("url"):
            self.download_requested.emit(data["url"], data["name"])

    def _context_menu(self, pos: QPoint) -> None:
        item = self._list.itemAt(pos)
        data = self._file_data(item)
        if not data or not data.get("url"):
            return
        menu = QMenu(self)
        act_dl = menu.addAction("Herunterladen")
        act_dl.triggered.connect(
            lambda: self.download_requested.emit(data["url"], data["name"])
        )
        act_copy = menu.addAction("Link kopieren")
        act_copy.triggered.connect(
            lambda: self.copy_link_requested.emit(data["url"])
        )
        menu.exec(self._list.viewport().mapToGlobal(pos))
