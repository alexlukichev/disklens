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
QAbstractItemModel implementation wrapping C++ NodeStore.
Performs lazy-loading on expansion and zero per-node Python object allocations.
"""

from typing import List, Dict, Any
from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from disklens.heuristics.engine import get_engine
from disklens.encoding import safe_decode


def format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    elif b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    else:
        return f"{b / (1024 * 1024 * 1024):.2f} GB"


class TreeModel(QAbstractItemModel):
    COL_NAME = 0
    COL_SIZE = 1
    COL_ITEMS = 2
    COL_CATEGORY = 3
    COL_MODIFIED = 4
    COL_COUNT = 5

    def __init__(self, session, controller, parent=None):
        super().__init__(parent)
        self.session = session
        self.controller = controller
        self.heuristics = get_engine()
        self.sort_key = "alloc"
        self.sort_desc = True

        # Cache of expanded children: node_id -> list of child node_ids
        self._children_cache: Dict[int, List[int]] = {}
        # Parent mapping: child_node_id -> (parent_node_id, row)
        self._parent_map: Dict[int, int] = {}

    def set_sort(self, key: str, desc: bool):
        self.sort_key = key
        self.sort_desc = desc
        self.beginResetModel()
        self._children_cache.clear()
        self._parent_map.clear()
        self.endResetModel()

    def reset_model(self):
        self.beginResetModel()
        self._children_cache.clear()
        self._parent_map.clear()
        self.endResetModel()

    def refresh_visible(self):
        self.reset_model()

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_id = parent.internalId() if parent.isValid() else 1  # 1 is root
        children = self._get_children(parent_id)

        if 0 <= row < len(children):
            child_id = children[row]
            return self.createIndex(row, column, child_id)
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        node_id = index.internalId()
        if node_id == 1:  # Root has no parent
            return QModelIndex()

        info = self.session.get_node_info(node_id)
        parent_id = info.parent_id
        if parent_id == 0:
            return QModelIndex()

        # Find row of parent_id in grandparent's children
        grandparent_info = self.session.get_node_info(parent_id)
        gp_id = grandparent_info.parent_id if grandparent_info.parent_id != 0 else 1
        gp_children = self._get_children(gp_id)

        try:
            row = gp_children.index(parent_id)
        except ValueError:
            row = 0

        return self.createIndex(row, 0, parent_id)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        parent_id = parent.internalId() if parent.isValid() else 1
        return len(self._get_children(parent_id))

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return self.COL_COUNT

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            headers = ["Name", "Size", "Items", "Category", "Modified"]
            if 0 <= section < len(headers):
                return headers[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        node_id = index.internalId()
        info = self.session.get_node_info(node_id)

        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == self.COL_NAME:
                return safe_decode(info.name)
            elif col == self.COL_SIZE:
                sz = info.total_alloc if self.controller.size_metric == "alloc" else info.total_logical
                return format_bytes(sz)
            elif col == self.COL_ITEMS:
                total_items = info.file_count + info.dir_count
                return f"{total_items:,}" if total_items > 0 else "-"
            elif col == self.COL_CATEGORY:
                if info.rule_id != 0:
                    return self.heuristics.category_name(info.rule_id)
                return "Normal"
            elif col == self.COL_MODIFIED:
                return ""

        elif role == Qt.ItemDataRole.ForegroundRole:
            if info.rule_id != 0:
                safety = self.heuristics.safety_level(info.rule_id)
                if safety == "safe":
                    return QColor(46, 160, 67)  # Green
                elif safety == "review":
                    return QColor(210, 153, 34)  # Orange
            if (info.flags & 2) != 0:  # Partial/error
                return QColor(200, 50, 50)  # Red

        elif role == Qt.ItemDataRole.UserRole:
            # Raw size in bytes for delegates / sorting
            return info.total_alloc if self.controller.size_metric == "alloc" else info.total_logical

        return None

    def _metric(self, info) -> int:
        return info.total_alloc if self.controller.size_metric == "alloc" else info.total_logical

    def fraction(self, index: QModelIndex) -> float:
        """Share of this node's size relative to its parent (0..1)."""
        info = self.session.get_node_info(index.internalId())
        if info.parent_id == 0:
            return 1.0
        parent_total = self._metric(self.session.get_node_info(info.parent_id))
        if parent_total <= 0:
            return 0.0
        return min(1.0, self._metric(info) / parent_total)

    def bar_color(self, index: QModelIndex):
        """Bar color: green/orange for cleanup candidates, None for default accent."""
        info = self.session.get_node_info(index.internalId())
        if info.rule_id != 0:
            safety = self.heuristics.safety_level(info.rule_id)
            if safety == "safe":
                return QColor(46, 160, 67)
            if safety == "review":
                return QColor(230, 150, 30)
        return None

    def _get_children(self, parent_id: int) -> List[int]:
        if parent_id in self._children_cache:
            return self._children_cache[parent_id]

        children = self.session.get_sorted_children(parent_id, self.sort_key, self.sort_desc)
        self._children_cache[parent_id] = children
        return children
