"""
Volume summary view: calculates APFS total, used, free, scanned, and unattributed space.
"""

import shutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QProgressBar
from PySide6.QtGui import QFont
from disklens.ui.tree_model import format_bytes


class SummaryView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Storage & Volume Summary")
        font = QFont()
        font.setBold(True)
        font.setPointSize(16)
        title.setFont(font)
        layout.addWidget(title)

        self.disk_info_lbl = QLabel("Volume: Macintosh HD")
        layout.addWidget(self.disk_info_lbl)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        layout.addWidget(self.bar)

        self.breakdown_lbl = QLabel("Loading storage metrics...")
        self.breakdown_lbl.setWordWrap(True)
        layout.addWidget(self.breakdown_lbl)

        layout.addStretch()

    def refresh_summary(self):
        try:
            total, used, free = shutil.disk_usage("/")
            prog = self.controller.session.get_progress()
            scanned = prog.bytes_scanned

            used_pct = int((used / total) * 100)
            self.bar.setValue(used_pct)

            unattributed = max(0, used - scanned)

            text = (
                f"• Total Capacity: {format_bytes(total)}\n"
                f"• Space Used: {format_bytes(used)} ({used_pct}%)\n"
                f"• Free Available: {format_bytes(free)}\n\n"
                f"• Scanned by DiskLens: {format_bytes(scanned)}\n"
                f"• Unattributed (Snapshots / System / APFS metadata): {format_bytes(unattributed)}"
            )
            self.breakdown_lbl.setText(text)
        except Exception as e:
            self.breakdown_lbl.setText(f"Error querying disk metrics: {e}")
