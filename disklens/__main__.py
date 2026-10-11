"""
DiskLens entry point.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from disklens.controller import AppController
from disklens.app import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DiskLens")
    app.setOrganizationName("DiskLens")

    controller = AppController()
    window = MainWindow(controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
