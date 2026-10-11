"""
DiskLens Main Window (PySide6 / Qt 6 Widgets).
Modern, slick macOS design with a clean sidebar, unified controls, and elided status.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QStackedWidget,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QProgressBar, QFrame,
    QToolButton
)
from PySide6.QtCore import Qt, QSize
from disklens.controller import AppController
from disklens.ui.tree_model import TreeModel, format_bytes
from disklens.ui.tree_view import TreeView
from disklens.ui.inspector import InspectorView
from disklens.ui.suggestions import SuggestionsView
from disklens.ui.errors_view import ErrorsView
from disklens.ui.treemap_view import TreemapView
from disklens.ui.summary_view import SummaryView
from disklens.ui.widgets import SegmentedControl, ElidedLabel
from disklens.ui.icons import get_monochrome_icon
from disklens.ui.theme import STYLESHEET
from disklens.macos import check_full_disk_access, open_fda_settings
from disklens.encoding import safe_decode


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("DiskLens — macOS Disk Usage Analyzer")
        self.resize(1180, 760)
        self.setMinimumSize(880, 540)
        self.setStyleSheet(STYLESHEET)

        self.tree_model = TreeModel(self.controller.session, self.controller)

        self._init_ui()
        self._check_fda()

        # Connect controller signals
        self.controller.progress_updated.connect(self._on_progress)
        self.controller.scan_finished.connect(self._on_scan_finished)
        self.controller.errors_updated.connect(self._on_errors_updated)

    def _init_ui(self):
        root_widget = QWidget(self)
        self.setCentralWidget(root_widget)
        root_layout = QHBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -------------------------------------------------------------
        # Left Sidebar
        # -------------------------------------------------------------
        sidebar_frame = QWidget()
        sidebar_frame.setFixedWidth(185)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(0, 0, 0, 10)
        sidebar_layout.setSpacing(6)

        brand_lbl = QLabel("DiskLens")
        brand_lbl.setObjectName("brand")
        sidebar_layout.addWidget(brand_lbl)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setIconSize(QSize(18, 18))

        self.nav_items = [
            ("tree", "Hierarchical Tree"),
            ("treemap", "Treemap"),
            ("suggestions", "Suggestions"),
            ("summary", "Volume Summary"),
            ("errors", "Scan Errors"),
        ]
        for icon_key, name in self.nav_items:
            item = QListWidgetItem(get_monochrome_icon(icon_key), name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item.setSizeHint(QSize(160, 36))
            self.sidebar.addItem(item)

        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._on_tab_changed)
        sidebar_layout.addWidget(self.sidebar)

        root_layout.addWidget(sidebar_frame)

        # -------------------------------------------------------------
        # Right Main Content Area
        # -------------------------------------------------------------
        content_widget = QWidget()
        content_widget.setObjectName("content")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(14, 12, 14, 10)
        content_layout.setSpacing(8)

        # 1. Unified Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)

        scope_lbl = QLabel("Scope:")
        scope_lbl.setObjectName("muted")
        toolbar_layout.addWidget(scope_lbl)

        self.scope_ctrl = SegmentedControl(["Macintosh HD", "Home"])
        toolbar_layout.addWidget(self.scope_ctrl)

        toolbar_layout.addSpacing(6)

        metric_lbl = QLabel("Metric:")
        metric_lbl.setObjectName("muted")
        toolbar_layout.addWidget(metric_lbl)

        self.metric_ctrl = SegmentedControl(["On Disk", "Logical"])
        self.metric_ctrl.currentIndexChanged.connect(self._on_metric_changed)
        toolbar_layout.addWidget(self.metric_ctrl)

        toolbar_layout.addStretch()

        self.rescan_btn = QPushButton("Rescan Subtree")
        self.rescan_btn.setObjectName("secondary")
        self.rescan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rescan_btn.clicked.connect(self._rescan_selection)
        toolbar_layout.addWidget(self.rescan_btn)

        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setObjectName("primary")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self._toggle_scan)
        toolbar_layout.addWidget(self.scan_btn)

        content_layout.addLayout(toolbar_layout)

        # 2. Thin Progress Line (3px)
        self.progress_line = QProgressBar()
        self.progress_line.setObjectName("scanProgress")
        self.progress_line.setRange(0, 0)
        self.progress_line.setTextVisible(False)
        self.progress_line.setFixedHeight(3)
        self.progress_line.setVisible(False)
        content_layout.addWidget(self.progress_line)

        # 3. Dismissible Full Disk Access Banner
        self.fda_banner = QFrame()
        self.fda_banner.setObjectName("banner")
        fda_layout = QHBoxLayout(self.fda_banner)
        fda_layout.setContentsMargins(12, 6, 10, 6)
        fda_layout.setSpacing(10)

        fda_msg = QLabel("⚠ Full Disk Access recommended to analyze app caches, mail, and system data without permission errors.")
        fda_msg.setStyleSheet("color: #854d0e; font-size: 12px; font-weight: 500;")
        fda_layout.addWidget(fda_msg, 1)

        fda_btn = QPushButton("Grant Access…")
        fda_btn.setObjectName("flat")
        fda_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fda_btn.clicked.connect(open_fda_settings)
        fda_layout.addWidget(fda_btn)

        close_btn = QToolButton()
        close_btn.setObjectName("bannerClose")
        close_btn.setText("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(lambda: self.fda_banner.setVisible(False))
        fda_layout.addWidget(close_btn)

        self.fda_banner.setVisible(False)
        content_layout.addWidget(self.fda_banner)

        # 4. Main Splitter: Stacked Views on Left, Inspector on Right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.stack = QStackedWidget()

        # View 0: Tree View
        self.tree_view = TreeView(self.controller)
        self.tree_view.setModel(self.tree_model)
        self.tree_view.node_selected.connect(self._on_node_selected)
        self.tree_view.rescan_requested.connect(self.controller.rescan_subtree)
        self.stack.addWidget(self.tree_view)

        # View 1: Treemap
        self.treemap_view = TreemapView(self.controller)
        self.treemap_view.node_selected.connect(self._on_node_selected)
        self.stack.addWidget(self.treemap_view)

        # View 2: Cleanup Suggestions
        self.suggestions_view = SuggestionsView(self.controller)
        self.suggestions_view.node_selected.connect(self._on_node_selected)
        self.stack.addWidget(self.suggestions_view)

        # View 3: Volume Summary
        self.summary_view = SummaryView(self.controller)
        self.stack.addWidget(self.summary_view)

        # View 4: Scan Errors
        self.errors_view = ErrorsView(self.controller)
        self.stack.addWidget(self.errors_view)

        splitter.addWidget(self.stack)

        # Right-side Inspector
        self.inspector_view = InspectorView(self.controller)
        splitter.addWidget(self.inspector_view)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        content_layout.addWidget(splitter, 1)

        # 5. Bottom Status Strip (Single Row with Elided Label)
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(2, 2, 2, 0)
        status_bar.setSpacing(8)

        self.status_lbl = ElidedLabel("Ready to scan")
        self.status_lbl.setObjectName("status")
        status_bar.addWidget(self.status_lbl, 1)

        self.stats_lbl = QLabel("")
        self.stats_lbl.setObjectName("status")
        status_bar.addWidget(self.stats_lbl)

        content_layout.addLayout(status_bar)

        root_layout.addWidget(content_widget, 1)

    def _check_fda(self):
        has_fda = check_full_disk_access()
        self.fda_banner.setVisible(not has_fda)

    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)
        if idx == 1:
            self.treemap_view.refresh_map()
        elif idx == 2:
            self.suggestions_view.refresh_suggestions()
        elif idx == 3:
            self.summary_view.refresh_summary()

    def _toggle_scan(self):
        if self.controller.session.is_running():
            self.controller.stop_scan()
            self.scan_btn.setText("Start Scan")
            self.progress_line.setVisible(False)
            self.status_lbl.setText("Scan cancelled.")
            self.stats_lbl.setText("")
        else:
            scope = "/" if self.scope_ctrl.currentIndex() == 0 else str(Path.home())
            self.controller.start_scan(scope)
            self.scan_btn.setText("■ Stop Scan")
            self.progress_line.setVisible(True)
            self.status_lbl.setText(f"Scanning {scope}…")
            self.stats_lbl.setText("Starting…")

    def _rescan_selection(self):
        curr_id = self.inspector_view.current_node_id
        if curr_id > 0:
            self.controller.rescan_subtree(curr_id)

    def _on_metric_changed(self, idx: int):
        metric = "alloc" if idx == 0 else "logical"
        self.controller.set_size_metric(metric)
        self.tree_model.refresh_visible()
        self.inspector_view.set_node(self.inspector_view.current_node_id)
        self.treemap_view.refresh_map()

    def _on_node_selected(self, node_id: int):
        self.inspector_view.set_node(node_id)

    def _on_errors_updated(self, records):
        self.errors_view.add_errors(records)
        err_count = self.controller.session.total_errors()
        err_item = self.sidebar.item(4)
        if err_item:
            err_item.setText(f"Scan Errors ({err_count})" if err_count > 0 else "Scan Errors")

    def _on_progress(self, prog):
        curr_path = safe_decode(prog.current_path)
        self.status_lbl.setText(curr_path if curr_path else "Scanning…")
        self.stats_lbl.setText(
            f"{prog.items_scanned:,} items  ·  "
            f"{format_bytes(prog.bytes_scanned)}  ·  "
            f"{prog.active_workers} workers  ·  "
            f"{prog.errors_count} errors"
        )

    def _on_scan_finished(self):
        self.scan_btn.setText("Start Scan")
        self.progress_line.setVisible(False)
        prog = self.controller.session.get_progress()
        self.status_lbl.setText("Scan Complete")
        self.stats_lbl.setText(
            f"Finished: {prog.items_scanned:,} items  ·  {format_bytes(prog.bytes_scanned)}  ·  {prog.errors_count} errors"
        )
        self.tree_model.refresh_visible()
        self.suggestions_view.refresh_suggestions()
        self.summary_view.refresh_summary()
        self.treemap_view.refresh_map()
