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
Unit and integration tests for DiskLens core scanner and safety rules.
"""

import os
import time
from pathlib import Path
import pytest
from disklens import diskcore
from disklens.heuristics.engine import get_engine
from disklens.controller import AppController


def test_session_instantiation():
    session = diskcore.Session()
    assert session is not None
    assert session.node_count() == 0
    assert not session.is_running()


def test_scan_local_workspace():
    session = diskcore.Session()
    workspace_dir = str(Path(__file__).resolve().parent.parent)

    # Start scan on local workspace directory
    started = session.start_scan(workspace_dir, file_threshold_bytes=1024)
    assert started

    # Wait for scan to complete
    for _ in range(50):
        prog = session.get_progress()
        if prog.is_complete:
            break
        time.sleep(0.05)

    prog = session.get_progress()
    assert prog.is_complete
    assert prog.items_scanned > 0
    assert prog.bytes_scanned > 0
    assert session.node_count() > 0

    # Validate root node
    root_info = session.get_node_info(1)
    assert root_info.id == 1
    assert root_info.total_alloc > 0
    assert root_info.total_logical > 0

    # Verify children retrieval & sorting
    children = session.get_sorted_children(1, "alloc", True)
    assert len(children) > 0

    # Ensure descending order
    first_info = session.get_node_info(children[0])
    if len(children) > 1:
        second_info = session.get_node_info(children[1])
        assert first_info.total_alloc >= second_info.total_alloc


def test_heuristics_classification():
    engine = get_engine()
    # Rule 1 is node_modules
    rule1 = engine.get_rule(1)
    assert rule1 is not None
    assert rule1["category"] == "Build Artifact"
    assert rule1["safety"] == "safe"

    # Rule 5 is Caches
    rule5 = engine.get_rule(5)
    assert rule5 is not None
    assert rule5["category"] == "App Cache"


def test_subtree_rescan():
    session = diskcore.Session()
    workspace_dir = str(Path(__file__).resolve().parent.parent)

    session.start_scan(workspace_dir, file_threshold_bytes=1024)
    for _ in range(50):
        if session.get_progress().is_complete:
            break
        time.sleep(0.05)

    initial_bytes = session.get_node_info(1).total_alloc
    assert initial_bytes > 0

    # Rescan root
    ok = session.rescan_subtree(1)
    assert ok

    for _ in range(50):
        if session.get_progress().is_complete:
            break
        time.sleep(0.05)

    rescanned_bytes = session.get_node_info(1).total_alloc
    # Totals should be consistent after rescan
    assert rescanned_bytes > 0
