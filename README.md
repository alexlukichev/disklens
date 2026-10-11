# DiskLens

Fast, native, and read-only disk usage analyzer and cleanup advisor for macOS.

DiskLens combines a high-performance **C++20 multi-threaded scanning core** (using Darwin's native `getattrlistbulk(2)` system call) with a modern **PySide6 / Qt 6 desktop interface** to analyze millions of files in seconds without high memory usage.

---

## Key Features

- **Blazing Fast Scanning**: Traverses millions of filesystem nodes in seconds using Darwin `getattrlistbulk(2)` with adaptive worker thread pooling.
- **Strictly Read-Only & Safe**: Zero destructive filesystem operations. DiskLens cannot delete, truncate, unlink, or modify any files on disk. Verified by automated AST guardrail checks.
- **Hierarchical Tree View**: Deep subtree navigation with proportional gradient size bars, item counts, safety ratings, and right-click context menus.
- **Interactive Treemap**: Squarified, zoomable visualization of storage usage with responsive hover highlighting and parent navigation.
- **Smart Cleanup Advisor**: Identifies reclaimable storage across common macOS locations (caches, Xcode DerivedData, `node_modules`, package manager caches, logs, and build artifacts).
- **Storage & Volume Summary**: Inspects APFS volume capacity, allocated space, free space, and unattributed system snapshot space.
- **Detailed Inspector Panel**: Live donut chart showing subfolder weight distribution, path breadcrumbs, file counts, and one-click *Reveal in Finder*.
- **Switchable Size Metrics**: Toggle instantly between physical disk allocation (APFS blocks on disk) and logical file size.
- **APFS & Firmlink Aware**: Respects filesystem mount boundaries and avoids duplicating macOS read-only / Data firmlinks.
- **Full Disk Access (FDA) Detection**: Alerts when macOS TCC permissions restrict access to protected folders (`~/Library/Mail`, `~/Library/Containers`, etc.) with quick-access setup links.

---

## Prerequisites

- **Operating System**: macOS 13.0 (Ventura) or newer
- **Python**: Python 3.10 or higher
- **C++ Compiler**: Apple Clang supporting C++20 (install via `xcode-select --install`)
- **CMake**: Version 3.20 or newer

---

## Build & Installation

### 1. Clone & Set Up Virtual Environment

From the project root directory:

```bash
# Create a dedicated Python virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Upgrade pip and install build dependencies
pip install --upgrade pip
pip install scikit-build-core nanobind ninja pytest
```

### 2. Build the Native C++ Extension & Install DiskLens

Build the native `diskcore` extension and install DiskLens in editable mode:

```bash
pip install --no-build-isolation -e .
```

---

## Running DiskLens

Make sure your virtual environment is active, then launch DiskLens:

```bash
# Launch via module
python3 -m disklens

# Or via the installed console entrypoint
disklens
```

---

## Full Disk Access (FDA)

macOS restricts terminal applications from reading certain sensitive user directories (such as `~/Library/Mail`, `~/Library/Safari`, and certain application sandboxes in `~/Library/Containers`).

To allow DiskLens to scan your entire drive without `Operation not permitted` errors:

1. Open **System Settings** → **Privacy & Security** → **Full Disk Access**.
2. Click the **+** button.
3. Add your terminal application (e.g., **Terminal**, **iTerm2**, or **Ghostty**) and ensure the toggle is enabled.
4. If running from an IDE (VS Code, Cursor, etc.), grant Full Disk Access to the IDE.

*DiskLens will display a dismissible warning banner if Full Disk Access is not detected, along with a direct button to open the settings panel.*

---

## Testing & Safety Verification

### Running the Test Suite

```bash
pytest
```

### Verifying the Read-Only Safety Guardrail

DiskLens includes a static AST guardrail script that scans the entire codebase (both Python and C++) to guarantee that no destructive file system APIs (`unlink`, `rmdir`, `remove`, `truncate`, `rmtree`, etc.) exist:

```bash
python3 scripts/check_no_delete.py
```

Expected output:
```
✅ Guardrail Check Passed: Zero destructive filesystem APIs found.
```

---

## Project Structure

```
mac_cleaner/
├── CMakeLists.txt              # CMake build definition for native diskcore module
├── pyproject.toml              # Project packaging configuration & dependencies
├── cpp/                        # Native C++20 scanning core
│   ├── bindings.cpp            # nanobind Python bindings
│   ├── include/diskcore/       # C++ header files
│   └── src/                    # Scanner, node store, mount policy, and rules engine
├── disklens/                   # Python application package
│   ├── __main__.py             # Application launcher
│   ├── app.py                  # MainWindow and central UI layout
│   ├── controller.py           # Controller bridging Qt and C++ diskcore engine
│   ├── encoding.py             # Resilient UTF-8 / surrogate-escape path decoder
│   ├── macos.py                # macOS platform utilities (FDA, Finder reveal)
│   ├── heuristics/             # Storage cleanup rules and safety classification
│   └── ui/                     # PySide6 UI views and custom widgets
│       ├── icons.py            # Resolution-independent monochrome vector pictograms
│       ├── inspector.py        # Card inspector with donut chart breakdown
│       ├── suggestions.py      # Cleanup advisor table view
│       ├── summary_view.py     # Volume & APFS storage summary view
│       ├── theme.py            # Palette-driven stylesheet
│       ├── tree_model.py       # QAbstractItemModel wrapping C++ node store
│       ├── tree_view.py        # Tree view with size bar delegates
│       ├── treemap_view.py     # Interactive squarified treemap
│       └── widgets.py          # Segmented controls, elided labels, size delegates
├── scripts/
│   └── check_no_delete.py      # Static safety check ensuring zero delete calls
└── tests/
    └── test_scanner.py         # Scanner engine test cases
```
