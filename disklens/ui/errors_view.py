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
Errors view tab: lists background I/O errors and permission restrictions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QHBoxLayout, QLabel
)
from PySide6.QtCore import Qt
from disklens.macos import open_fda_settings
from disklens.encoding import safe_decode


class ErrorsView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        self.summary_lbl = QLabel("Errors: 0 recorded during scan.")
        header_layout.addWidget(self.summary_lbl)

        fda_btn = QPushButton("Grant Full Disk Access...")
        fda_btn.setObjectName("secondary")
        fda_btn.clicked.connect(open_fda_settings)
        header_layout.addWidget(fda_btn)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        self.table = QTableWidget(0, 3)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalHeaderLabels(["Path", "Errno", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

    def add_errors(self, error_records):
        self.table.setUpdatesEnabled(False)
        max_display_rows = 500
        try:
            for rec in error_records:
                if self.table.rowCount() >= max_display_rows:
                    break
                row = self.table.rowCount()
                self.table.insertRow(row)

                path_str = safe_decode(rec.path)
                msg_str = safe_decode(rec.message)

                path_item = QTableWidgetItem(path_str)
                errno_item = QTableWidgetItem(str(rec.error_number))
                msg_item = QTableWidgetItem(msg_str)

                self.table.setItem(row, 0, path_item)
                self.table.setItem(row, 1, errno_item)
                self.table.setItem(row, 2, msg_item)
        finally:
            self.table.setUpdatesEnabled(True)

        total = self.controller.session.total_errors()
        display_note = f" (showing first {max_display_rows})" if total > max_display_rows else ""
        self.summary_lbl.setText(f"Errors: {total:,} recorded during scan{display_note}.")
