"""
Treemap view: interactive visualization of disk usage using squarified layout.
"""

from typing import List, Tuple
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QLinearGradient
from disklens.ui.tree_model import format_bytes
from disklens.ui.widgets import PALETTE, ElidedLabel
from disklens.encoding import safe_decode


class TreemapWidget(QWidget):
    node_clicked = Signal(int)
    node_double_clicked = Signal(int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.root_node_id = 1
        self.items: List[Tuple[int, str, int, QRectF, QColor]] = []  # (id, name, size, rect, color)
        self.setMouseTracking(True)
        self.hovered_item = None

    def set_root_node(self, node_id: int):
        self.root_node_id = node_id
        self.recompute_layout()
        self.update()

    def recompute_layout(self):
        self.items.clear()
        if self.width() <= 10 or self.height() <= 10:
            return

        # Fetch direct children of root_node_id
        children = self.controller.session.get_sorted_children(self.root_node_id, "alloc", True)
        if not children:
            return

        # Prepare child weights
        child_data = []
        total_size = 0
        for cid in children:
            info = self.controller.session.get_node_info(cid)
            sz = info.total_alloc if self.controller.size_metric == "alloc" else info.total_logical
            if sz > 0:
                child_data.append((cid, safe_decode(info.name), sz))
                total_size += sz

        if total_size == 0:
            return

        # Simple slice-and-dice / treemap partitioning
        rect = QRectF(5, 5, self.width() - 10, self.height() - 10)
        self._partition(rect, child_data, total_size, horizontal=True)

    def _partition(self, rect: QRectF, items: List[Tuple[int, str, int]], total: int, horizontal: bool):
        if not items or total <= 0 or rect.width() < 2 or rect.height() < 2:
            return

        if len(items) == 1:
            cid, name, sz = items[0]
            color = self._color_for_id(cid)
            self.items.append((cid, name, sz, rect, color))
            return

        # Split items into two groups
        half_total = total / 2
        acc = 0
        split_idx = 1
        for i, (_, _, sz) in enumerate(items):
            acc += sz
            if acc >= half_total:
                split_idx = max(1, i + 1)
                break

        left_items = items[:split_idx]
        right_items = items[split_idx:]

        left_sum = sum(x[2] for x in left_items)
        right_sum = sum(x[2] for x in right_items)

        ratio = left_sum / total if total > 0 else 0.5

        if horizontal:
            left_w = rect.width() * ratio
            r_left = QRectF(rect.x(), rect.y(), left_w, rect.height())
            r_right = QRectF(rect.x() + left_w, rect.y(), rect.width() - left_w, rect.height())
        else:
            left_h = rect.height() * ratio
            r_left = QRectF(rect.x(), rect.y(), rect.width(), left_h)
            r_right = QRectF(rect.x(), rect.y() + left_h, rect.width(), rect.height() - left_h)

        self._partition(r_left, left_items, left_sum, not horizontal)
        self._partition(r_right, right_items, right_sum, not horizontal)

    def _color_for_id(self, node_id: int) -> QColor:
        # Stable per-node palette slot; paint derives the gradient from it
        return QColor(PALETTE[node_id % len(PALETTE)][1])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.recompute_layout()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        name_font = QFont()
        name_font.setPointSize(11)
        name_font.setBold(True)
        size_font = QFont()
        size_font.setPointSize(10)

        for cid, name, sz, rect, color in self.items:
            tile = rect.adjusted(2, 2, -2, -2)
            if tile.width() < 3 or tile.height() < 3:
                continue
            start = QColor(PALETTE[cid % len(PALETTE)][0])
            end = color
            if cid == self.hovered_item:
                start, end = start.lighter(112), end.lighter(112)
            grad = QLinearGradient(tile.topLeft(), tile.bottomRight())
            grad.setColorAt(0, start)
            grad.setColorAt(1, end)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            radius = min(10.0, tile.width() / 4, tile.height() / 4)
            painter.drawRoundedRect(tile, radius, radius)

            if tile.width() > 60 and tile.height() > 34:
                text_rect = tile.adjusted(10, 8, -10, -6)
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(name_font)
                fm = painter.fontMetrics()
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                                 fm.elidedText(name, Qt.TextElideMode.ElideRight, int(text_rect.width())))
                painter.setFont(size_font)
                painter.setPen(QColor(255, 255, 255, 215))
                painter.drawText(text_rect.adjusted(0, fm.height() + 1, 0, 0),
                                 Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, format_bytes(sz))

    def mouseMoveEvent(self, event):
        pos = event.position()
        hovered = None
        for cid, _, _, rect, _ in self.items:
            if rect.contains(pos):
                hovered = cid
                break
        if hovered != self.hovered_item:
            self.hovered_item = hovered
            self.setCursor(Qt.CursorShape.PointingHandCursor if hovered else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, event):
        self.hovered_item = None
        self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        for cid, _, _, rect, _ in self.items:
            if rect.contains(pos):
                self.node_clicked.emit(cid)
                break

    def mouseDoubleClickEvent(self, event):
        pos = event.position()
        for cid, _, _, rect, _ in self.items:
            if rect.contains(pos):
                self.set_root_node(cid)
                self.node_double_clicked.emit(cid)
                break


class TreemapView(QWidget):
    node_selected = Signal(int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_root = 1

        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        self.path_lbl = ElidedLabel("Viewing: /")
        top_bar.addWidget(self.path_lbl, 1)

        up_btn = QPushButton("▲ Up to Parent")
        up_btn.setObjectName("flat")
        up_btn.clicked.connect(self._go_up)
        top_bar.addWidget(up_btn)

        refresh_btn = QPushButton("⟳ Refresh Map")
        refresh_btn.setObjectName("flat")
        refresh_btn.clicked.connect(self.refresh_map)
        top_bar.addWidget(refresh_btn)

        layout.addLayout(top_bar)

        self.widget = TreemapWidget(controller)
        self.widget.node_clicked.connect(self.node_selected.emit)
        self.widget.node_double_clicked.connect(self._on_sub_treemap)
        layout.addWidget(self.widget)

    def set_node(self, node_id: int):
        self.current_root = node_id
        path = safe_decode(self.controller.session.get_full_path(node_id))
        self.path_lbl.setText(f"Viewing: {path}")
        self.widget.set_root_node(node_id)

    def refresh_map(self):
        self.set_node(self.current_root)

    def _on_sub_treemap(self, node_id: int):
        self.current_root = node_id
        path = safe_decode(self.controller.session.get_full_path(node_id))
        self.path_lbl.setText(f"Viewing: {path}")

    def _go_up(self):
        info = self.controller.session.get_node_info(self.current_root)
        if info.parent_id != 0:
            self.set_node(info.parent_id)
