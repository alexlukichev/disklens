"""
Cleanup Suggestions tab: lists all detected trash, cache, build artifacts, etc.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal
from disklens.ui.tree_model import format_bytes
from disklens.heuristics.engine import get_engine
from disklens.macos import reveal_in_finder
from disklens.encoding import safe_decode


class SuggestionsView(QWidget):
    node_selected = Signal(int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.heuristics = get_engine()
        self.suggestions = []  # list of (node_id, rule_id, size)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Category", "Safety", "Size", "Suggested Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Suggestions")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh_suggestions)
        btn_layout.addWidget(refresh_btn)

        reveal_btn = QPushButton("Reveal in Finder")
        reveal_btn.setObjectName("secondary")
        reveal_btn.clicked.connect(self._on_reveal_selected)
        btn_layout.addWidget(reveal_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def refresh_suggestions(self):
        self.table.setRowCount(0)
        self.suggestions.clear()

        # Gather root children and subtrees with rule_id != 0
        def collect(node_id: int, depth: int = 0):
            if depth > 8:
                return
            info = self.controller.session.get_node_info(node_id)
            if info.rule_id != 0:
                sz = info.total_alloc if self.controller.size_metric == "alloc" else info.total_logical
                self.suggestions.append((node_id, info.rule_id, sz))
                return  # Prune: do not dive into subfolders of matched caches/artifacts

            # inspect top 25 largest children
            children = self.controller.session.get_sorted_children(node_id, "alloc", True)
            for c in children[:25]:
                c_info = self.controller.session.get_node_info(c)
                # Only dive if directory and size > 25 MB
                if c_info.kind == 1 and c_info.total_alloc > 25 * 1024 * 1024:
                    collect(c, depth + 1)

        collect(1, 0)  # start from root

        # Sort descending by size and keep top 200 largest reclaimable targets
        self.suggestions.sort(key=lambda x: x[2], reverse=True)
        self.suggestions = self.suggestions[:200]

        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(self.suggestions))
            for row, (nid, rid, sz) in enumerate(self.suggestions):
                info = self.controller.session.get_node_info(nid)
                rule = self.heuristics.get_rule(rid) or {}

                name_item = QTableWidgetItem(safe_decode(info.name))
                cat_item = QTableWidgetItem(rule.get("category", "Unknown"))
                safe_item = QTableWidgetItem(rule.get("safety", "normal").upper())
                size_item = QTableWidgetItem(format_bytes(sz))
                action_item = QTableWidgetItem(rule.get("action", ""))

                name_item.setData(Qt.ItemDataRole.UserRole, nid)

                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, cat_item)
                self.table.setItem(row, 2, safe_item)
                self.table.setItem(row, 3, size_item)
                self.table.setItem(row, 4, action_item)
        finally:
            self.table.setUpdatesEnabled(True)

    def _on_row_double_clicked(self, item):
        row = item.row()
        nid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.node_selected.emit(nid)

    def _on_reveal_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            nid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            path = self.controller.session.get_full_path(nid)
            reveal_in_finder(path)
