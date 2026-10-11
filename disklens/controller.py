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
DiskLens Application Controller: coordinates scan operations, UI polling, and model updates.
"""

from PySide6.QtCore import QObject, QTimer, Signal
from disklens import diskcore


class AppController(QObject):
    progress_updated = Signal(object)
    scan_finished = Signal()
    errors_updated = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = diskcore.Session()
        self.root_path = "/"
        self.size_metric = "alloc"  # "alloc" or "logical"

        # Poll timer (10 Hz)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(100)
        self.poll_timer.timeout.connect(self._on_poll)

    def start_scan(self, root_path: str = "/", file_threshold_mb: int = 1):
        self.root_path = root_path
        threshold_bytes = file_threshold_mb * 1024 * 1024
        self.session.start_scan(root_path, threshold_bytes)
        self.poll_timer.start()

    def rescan_subtree(self, node_id: int):
        self.session.rescan_subtree(node_id)
        if not self.poll_timer.isActive():
            self.poll_timer.start()

    def stop_scan(self):
        self.session.stop_scan()
        self.poll_timer.stop()

    def set_size_metric(self, metric: str):
        if metric in ("alloc", "logical"):
            self.size_metric = metric

    def _on_poll(self):
        prog = self.session.get_progress()
        self.progress_updated.emit(prog)

        errors = self.session.drain_errors(100)
        if errors:
            self.errors_updated.emit(errors)

        if prog.is_complete:
            self.poll_timer.stop()
            self.scan_finished.emit()
