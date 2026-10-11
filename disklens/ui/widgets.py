# Copyright 2026 Alexander Lukichev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Reusable custom widgets for the DiskLens UI: segmented control, elided label,
donut chart and a size-bar item delegate.
"""

from typing import List, Tuple
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QButtonGroup, QLabel, QSizePolicy,
    QWidget, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QPalette

# Curated palette (start, end) gradient pairs shared by treemap and donut.
PALETTE: List[Tuple[str, str]] = [
    ("#38bdf8", "#3b82f6"),  # blue
    ("#2dd4bf", "#0d9488"),  # teal
    ("#fbbf24", "#f97316"),  # orange
    ("#c084fc", "#9333ea"),  # purple
    ("#fb7185", "#e11d48"),  # rose
    ("#a3e635", "#65a30d"),  # lime
    ("#818cf8", "#4f46e5"),  # indigo
    ("#f472b6", "#db2777"),  # pink
]


class SegmentedControl(QFrame):
    """Compact exclusive button group with a QComboBox-like API."""
    currentIndexChanged = Signal(int)

    def __init__(self, labels: List[str], parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: List[QPushButton] = []
        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("segButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._group.addButton(btn, i)
            layout.addWidget(btn)
            self._buttons.append(btn)

        self._index = 0
        self._buttons[0].setChecked(True)
        self._group.idClicked.connect(self._on_clicked)

    def _on_clicked(self, idx: int):
        if idx != self._index:
            self._index = idx
            self.currentIndexChanged.emit(idx)

    def currentIndex(self) -> int:
        return self._index

    def setCurrentIndex(self, idx: int):
        if 0 <= idx < len(self._buttons):
            self._buttons[idx].setChecked(True)
            self._on_clicked(idx)


class ElidedLabel(QLabel):
    """Single-line label that elides in the middle and never widens its parent."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self.setText(text)

    def setText(self, text: str):
        if text == self._full:
            return
        self._full = text
        self.setToolTip(text)
        self.update()

    def text(self) -> str:
        return self._full

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def sizeHint(self) -> QSize:
        return QSize(0, super().sizeHint().height())

    def paintEvent(self, event):
        painter = QPainter(self)
        color = self.palette().color(QPalette.ColorRole.WindowText)
        painter.setPen(color)
        elided = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle, self.width())
        painter.drawText(self.rect(), int(self.alignment()) | int(Qt.AlignmentFlag.AlignVCenter), elided)


class DonutWidget(QWidget):
    """Donut chart of (label, value) segments with a centre caption."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments: List[Tuple[str, int]] = []
        self._center_text = ""
        self.setMinimumSize(140, 140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(150)

    def set_segments(self, segments: List[Tuple[str, int]], center_text: str = ""):
        self._segments = [s for s in segments if s[1] > 0]
        self._center_text = center_text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 16
        thickness = 16
        rect = QRectF((self.width() - side) / 2 + thickness / 2, 8 + thickness / 2,
                      side - thickness, side - thickness)

        track = QColor(128, 128, 128, 40)
        painter.setPen(QPen(track, thickness))
        painter.drawEllipse(rect)

        total = sum(v for _, v in self._segments)
        if total > 0:
            start = 90 * 16
            for i, (_, value) in enumerate(self._segments):
                span = -int(round(360 * 16 * value / total))
                color = QColor(PALETTE[i % len(PALETTE)][1])
                painter.setPen(QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                painter.drawArc(rect, start, span)
                start += span

        painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._center_text)


class SizeBarDelegate(QStyledItemDelegate):
    """Draws a proportional bar behind right-aligned size text."""
    TEXT_WIDTH = 80

    def paint(self, painter: QPainter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ""
        widget = opt.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)

        model = index.model()
        frac = model.fraction(index) if hasattr(model, "fraction") else 0.0
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)

        area = opt.rect.adjusted(8, 0, -8, 0)
        bar_max = max(0, area.width() - self.TEXT_WIDTH - 8)
        if bar_max > 0 and frac > 0:
            base = model.bar_color(index) if hasattr(model, "bar_color") else None
            if base is None:
                base = QColor("#3b82f6")
            width = max(6.0, bar_max * frac)
            bar = QRectF(area.left(), area.center().y() - 4, width, 8)
            grad = QLinearGradient(bar.left(), 0, bar.right(), 0)
            if selected:
                grad.setColorAt(0, QColor(255, 255, 255, 230))
                grad.setColorAt(1, QColor(255, 255, 255, 160))
            else:
                grad.setColorAt(0, base.lighter(125))
                grad.setColorAt(1, base)
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(bar, 4.0, 4.0)
            painter.restore()

        painter.save()
        role = QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text
        painter.setPen(opt.palette.color(role))
        painter.drawText(area, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), text)
        painter.restore()
