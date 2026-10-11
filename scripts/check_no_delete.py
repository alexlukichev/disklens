#!/usr/bin/env python3
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
Static guardrail verification script.
Ensures that NO deletion, removal, or destructive file system APIs exist in the codebase.
"""

import ast
import os
import sys
from pathlib import Path

FORBIDDEN_CALLS = {
    "unlink", "unlinkat", "rmdir", "remove", "removedirs", "rename", "truncate",
    "rmtree", "move", "send2trash", "removeRecursively", "moveToTrash"
}

ALLOWED_FILES = {
    "appfiles.py",  # Only file allowed to create application logs / snapshots
    "check_no_delete.py"
}


def check_python_file(path: Path) -> list:
    errors = []
    if path.name in ALLOWED_FILES:
        return errors

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as e:
        return [f"Failed to parse {path}: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check function name or attribute name
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in FORBIDDEN_CALLS:
                errors.append(f"{path}:{node.lineno} - Destructive API call detected: '{func_name}'")

    return errors


def check_cpp_file(path: Path) -> list:
    errors = []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for forbidden in ["unlink(", "unlinkat(", "rmdir(", "remove(", "truncate(", "ftruncate(", "std::filesystem::remove"]:
            if forbidden in line:
                errors.append(f"{path}:{lineno} - Destructive C++ call detected: '{forbidden}'")
    return errors


def main():
    root = Path(__file__).resolve().parent.parent
    all_errors = []

    for p in root.rglob("*"):
        if ".venv" in p.parts or "build" in p.parts or ".git" in p.parts:
            continue
        if p.suffix == ".py":
            all_errors.extend(check_python_file(p))
        elif p.suffix in (".cpp", ".hpp", ".h"):
            all_errors.extend(check_cpp_file(p))

    if all_errors:
        print("❌ READ-ONLY SAFETY VIOLATION DETECTED:")
        for err in all_errors:
            print("  ", err)
        sys.exit(1)
    else:
        print("✅ Guardrail Check Passed: Zero destructive filesystem APIs found.")


if __name__ == "__main__":
    main()
