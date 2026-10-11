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
Custom QTreeView with context menus and column sorting for DiskLens.
"""

from PySide6.QtWidgets import QTreeView, QMenu, QHeaderView
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from disklens.macos import reveal_in_finder, open_in_terminal
from disklens.encoding import safe_decode
from disklens.ui.widgets import SizeBarDelegate


class TreeView(QTreeView):
    node_selected = Signal(int)
    rescan_requested = Signal(int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setIndentation(18)
        self.setItemDelegateForColumn(1, SizeBarDelegate(self))
        self.header().setSectionsClickable(True)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, width in ((1, 260), (2, 90), (3, 110), (4, 100)):
            self.header().setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self.header().resizeSection(col, width)
        self.header().sectionClicked.connect(self._on_header_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.clicked.connect(self._on_item_clicked)

    def setModel(self, model):
        super().setModel(model)
        if model:
            self.header().setStretchLastSection(False)
            self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for col, width in ((1, 240), (2, 90), (3, 110), (4, 100)):
                self.header().setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
                self.header().resizeSection(col, width)

    def _on_header_clicked(self, logical_index: int):
        model = self.model()
        if not model:
            return

        key = "alloc" if self.controller.size_metric == "alloc" else "logical"
        if logical_index == 0:
            key = "name"
        elif logical_index == 1:
            key = "alloc" if self.controller.size_metric == "alloc" else "logical"
        elif logical_index == 2:
            key = "items"
        elif logical_index == 4:
            key = "modified"

        # Toggle or default descending
        desc = True if key in ("alloc", "logical", "items") else False
        model.set_sort(key, desc)

    def _on_item_clicked(self, index):
        if index.isValid():
            node_id = index.internalId()
            self.node_selected.emit(node_id)

    def _show_context_menu(self, pos):
        index = self.indexAt(pos)
        if not index.isValid():
            return

        node_id = index.internalId()
        path = safe_decode(self.controller.session.get_full_path(node_id))

        menu = QMenu(self)

        rescan_act = QAction("⟳ Rescan This Subtree", self)
        rescan_act.triggered.connect(lambda: self.rescan_requested.emit(node_id))
        menu.addAction(rescan_act)

        menu.addSeparator()

        reveal_act = QAction("Reveal in Finder", self)
        reveal_act.triggered.connect(lambda: reveal_in_finder(path))
        menu.addAction(reveal_act)

        terminal_act = QAction("Open in Terminal", self)
        terminal_act.triggered.connect(lambda: open_in_terminal(path))
        menu.addAction(terminal_act)

        copy_act = QAction("Copy Path", self)
        from PySide6.QtGui import QGuiApplication
        copy_act.triggered.connect(lambda: QGuiApplication.clipboard().setText(path))
        menu.addAction(copy_act)

        menu.exec(self.viewport().mapToGlobal(pos))
