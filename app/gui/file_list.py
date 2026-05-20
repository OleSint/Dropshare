from __future__ import annotations
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QFont,
    QFontMetrics,
    QPainter,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from ..models import SharedFile

_ROLE_FILE = Qt.ItemDataRole.UserRole
_ROLE_PATH = Qt.ItemDataRole.UserRole + 1

_GREEN = QColor("#27AE60")
_DARK = QColor("#2C3E50")
_GREY = QColor("#95A5A6")
_ICON_BG = QColor("#ECF0F1")
_ICON_FG = QColor("#7F8C8D")
_BORDER = QColor("#EEEEEE")
_SEL_BG = QColor("#EBF5FB")
_WHITE = QColor("white")


def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class _FileDelegate(QStyledItemDelegate):
    _ITEM_H = 56
    _BADGE_W = 60
    _BADGE_H = 22

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(option.rect.width(), self._ITEM_H)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        r = option.rect
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)

        painter.fillRect(r, _SEL_BG if is_selected else _WHITE)

        sf: Optional[SharedFile] = index.data(_ROLE_FILE)
        if sf is None:
            painter.restore()
            return

        pad = 12
        icon_size = 36

        # File type icon box
        icon_x = r.left() + pad
        icon_y = r.top() + (r.height() - icon_size) // 2
        icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)
        painter.setBrush(_ICON_BG)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon_rect, 5, 5)

        ext = sf.path.suffix.upper().lstrip(".")[:4] or "FILE"
        f_ext = QFont()
        f_ext.setPointSize(7)
        f_ext.setBold(True)
        painter.setFont(f_ext)
        painter.setPen(_ICON_FG)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, ext)

        # Badge space reservation
        badge_text = sf.badge_text
        right_pad = (self._BADGE_W + pad) if badge_text else pad
        text_x = icon_rect.right() + pad
        text_w = r.right() - text_x - right_pad

        # Filename
        f_name = QFont()
        f_name.setPointSize(10)
        f_name.setBold(True)
        painter.setFont(f_name)
        painter.setPen(_DARK)
        fm = QFontMetrics(f_name)
        elided = fm.elidedText(sf.path.name, Qt.TextElideMode.ElideMiddle, text_w)
        name_rect = QRect(text_x, r.top() + 8, text_w, 20)
        painter.drawText(
            name_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            elided,
        )

        # Size + share type tag
        f_sub = QFont()
        f_sub.setPointSize(8)
        painter.setFont(f_sub)
        painter.setPen(_GREY)
        size_str = _fmt_size(sf.path.stat().st_size) if sf.path.exists() else "—"
        if sf.share_type == "lan":
            size_str += "  ·  LAN"
        elif sf.share_type == "http":
            size_str += "  ·  Internet"
        sub_rect = QRect(text_x, r.top() + r.height() // 2 + 4, text_w, 16)
        painter.drawText(
            sub_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            size_str,
        )

        # Green badge
        if badge_text:
            bx = r.right() - self._BADGE_W - pad
            by = r.top() + (r.height() - self._BADGE_H) // 2
            badge_rect = QRect(bx, by, self._BADGE_W, self._BADGE_H)
            painter.setBrush(_GREEN)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, self._BADGE_H // 2, self._BADGE_H // 2)
            f_badge = QFont()
            f_badge.setPointSize(8)
            f_badge.setBold(True)
            painter.setFont(f_badge)
            painter.setPen(_WHITE)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        # Bottom separator
        painter.setPen(_BORDER)
        painter.drawLine(r.left() + pad, r.bottom(), r.right() - pad, r.bottom())

        painter.restore()


class FileListWidget(QWidget):
    files_dropped = pyqtSignal(list)         # list[Path]
    share_requested = pyqtSignal(str)        # path_str
    stop_sharing_requested = pyqtSignal(str)
    remove_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: dict[str, QListWidgetItem] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._placeholder = QLabel("Dateien hier hineinziehen\num sie zu teilen")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #BDC3C7; font-size: 14px;"
            "border: 2px dashed #D5D8DC;"
            "border-radius: 8px; padding: 40px;"
        )

        self._list = QListWidget()
        self._list.setItemDelegate(_FileDelegate())
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setStyleSheet(
            "QListWidget { border: 1px solid #D5D8DC; border-radius: 8px; background: white; outline: none; }"
            "QListWidget::item { border: none; padding: 0; }"
            "QListWidget::item:selected { background: transparent; }"
        )
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.setAcceptDrops(False)

        layout.addWidget(self._placeholder)
        layout.addWidget(self._list)
        self._list.hide()

        self.setAcceptDrops(True)

    def _toggle_empty(self) -> None:
        empty = self._list.count() == 0
        self._placeholder.setVisible(empty)
        self._list.setVisible(not empty)

    def add_file(self, sf: SharedFile) -> None:
        key = str(sf.path)
        if key in self._items:
            return
        item = QListWidgetItem()
        item.setData(_ROLE_FILE, sf)
        item.setData(_ROLE_PATH, key)
        item.setSizeHint(QSize(0, 56))
        self._list.addItem(item)
        self._items[key] = item
        self._toggle_empty()

    def refresh_item(self, path_str: str) -> None:
        item = self._items.get(path_str)
        if item:
            self._list.update(self._list.indexFromItem(item))

    def remove_file(self, path_str: str) -> None:
        item = self._items.pop(path_str, None)
        if item:
            self._list.takeItem(self._list.row(item))
        self._toggle_empty()

    def _show_context_menu(self, pos: QPoint) -> None:
        item = self._list.itemAt(pos)
        if not item:
            return
        path_str: str = item.data(_ROLE_PATH)
        sf: SharedFile = item.data(_ROLE_FILE)

        menu = QMenu(self)
        if sf.is_shared:
            act_stop = menu.addAction("Freigabe beenden")
            act_stop.triggered.connect(lambda: self.stop_sharing_requested.emit(path_str))
        else:
            act_share = menu.addAction("Freigeben…")
            act_share.triggered.connect(lambda: self.share_requested.emit(path_str))
        menu.addSeparator()
        act_remove = menu.addAction("Aus Liste entfernen")
        act_remove.triggered.connect(lambda: self.remove_requested.emit(path_str))
        menu.exec(self._list.viewport().mapToGlobal(pos))

    # ── Drag & Drop ──────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            Path(u.toLocalFile())
            for u in event.mimeData().urls()
            if Path(u.toLocalFile()).is_file()
        ]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()
