"""
Inspector panel: detailed inspection of the currently selected tree node,
presented as a rounded card with a donut breakdown of its largest children.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from disklens.ui.tree_model import format_bytes
from disklens.ui.widgets import ElidedLabel, DonutWidget, PALETTE
from disklens.heuristics.engine import get_engine
from disklens.macos import reveal_in_finder
from disklens.encoding import safe_decode


class InspectorView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.heuristics = get_engine()
        self.current_node_id = 0

        self.setMinimumWidth(260)
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title = QLabel("INSPECTOR")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        self.name_lbl = ElidedLabel("No item selected")
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(name_font.pointSize() + 3)
        self.name_lbl.setFont(name_font)
        layout.addWidget(self.name_lbl)

        self.path_lbl = ElidedLabel("")
        self.path_lbl.setObjectName("muted")
        layout.addWidget(self.path_lbl)

        self.donut = DonutWidget()
        layout.addWidget(self.donut)

        self.legend_lbl = QLabel("")
        self.legend_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.legend_lbl.setWordWrap(True)
        layout.addWidget(self.legend_lbl)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(128,128,128,70);")
        layout.addWidget(line)

        self.size_lbl = QLabel("Size: -")
        self.size_lbl.setWordWrap(True)
        layout.addWidget(self.size_lbl)

        self.items_lbl = QLabel("Items: -")
        self.items_lbl.setWordWrap(True)
        layout.addWidget(self.items_lbl)

        self.cat_lbl = QLabel("Category: Normal")
        self.cat_lbl.setWordWrap(True)
        layout.addWidget(self.cat_lbl)

        self.desc_lbl = QLabel("")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setObjectName("muted")
        layout.addWidget(self.desc_lbl)

        self.action_lbl = QLabel("")
        self.action_lbl.setWordWrap(True)
        self.action_lbl.setObjectName("tip")
        layout.addWidget(self.action_lbl)

        layout.addStretch()

        self.reveal_btn = QPushButton("Reveal in Finder")
        self.reveal_btn.setObjectName("secondary")
        self.reveal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reveal_btn.clicked.connect(self._on_reveal)
        layout.addWidget(self.reveal_btn)

    def _clear(self):
        self.name_lbl.setText("No item selected")
        self.path_lbl.setText("")
        self.size_lbl.setText("Size: -")
        self.items_lbl.setText("Items: -")
        self.cat_lbl.setText("Category: Normal")
        self.desc_lbl.setText("")
        self.action_lbl.setText("")
        self.donut.set_segments([])
        self.legend_lbl.setText("")

    def _update_breakdown(self, node_id: int, total: int):
        session = self.controller.session
        use_alloc = self.controller.size_metric == "alloc"
        children = session.get_sorted_children(node_id, "alloc" if use_alloc else "logical", True)
        segments = []
        used = 0
        for cid in children[:5]:
            ci = session.get_node_info(cid)
            sz = ci.total_alloc if use_alloc else ci.total_logical
            if sz > 0:
                segments.append((safe_decode(ci.name), sz))
                used += sz
        if total > used > 0 and len(children) > 5:
            segments.append(("Other", total - used))

        self.donut.set_segments(segments, format_bytes(total))
        rows = []
        for i, (name, sz) in enumerate(segments):
            short = name if len(name) <= 24 else name[:23] + "…"
            short = short.replace("&", "&amp;").replace("<", "&lt;")
            color = PALETTE[i % len(PALETTE)][1]
            rows.append(f'<span style="color:{color}">●</span> {short} '
                        f'<span style="color:gray">— {format_bytes(sz)}</span>')
        self.legend_lbl.setText("<br>".join(rows))

    def set_node(self, node_id: int):
        self.current_node_id = node_id
        if node_id == 0:
            self._clear()
            return

        info = self.controller.session.get_node_info(node_id)
        self.name_lbl.setText(safe_decode(info.name))
        self.path_lbl.setText(safe_decode(self.controller.session.get_full_path(node_id)))

        self.size_lbl.setText(
            f"<b>{format_bytes(info.total_alloc)}</b> on disk "
            f"<span style='color:gray'>({format_bytes(info.total_logical)} logical)</span>")
        self.items_lbl.setText(f"{info.file_count:,} files · {info.dir_count:,} subfolders")

        total = info.total_alloc if self.controller.size_metric == "alloc" else info.total_logical
        self._update_breakdown(node_id, total)

        if info.rule_id != 0:
            rule = self.heuristics.get_rule(info.rule_id)
            if rule:
                self.cat_lbl.setText(f"<b>{rule['category']}</b> · {rule['safety'].upper()}")
                self.desc_lbl.setText(rule["description"])
                self.action_lbl.setText(f"Tip: {rule['action']}")
        else:
            self.cat_lbl.setText("Category: Normal")
            self.desc_lbl.setText("")
            self.action_lbl.setText("")

    def _on_reveal(self):
        if self.current_node_id != 0:
            path = self.controller.session.get_full_path(self.current_node_id)
            reveal_in_finder(path)
