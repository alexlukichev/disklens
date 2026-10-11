"""
Application stylesheet. Uses palette() roles and translucent greys so it follows
the system light/dark appearance automatically.
"""

STYLESHEET = """
QMainWindow, QWidget#content { background: palette(window); }

/* Sidebar */
QListWidget#sidebar {
    background: rgba(128, 128, 128, 22);
    border: none;
    border-right: 1px solid rgba(128, 128, 128, 55);
    padding: 10px 8px;
    outline: 0;
    font-size: 13px;
}
QListWidget#sidebar::item {
    padding: 8px 10px;
    border-radius: 8px;
    margin-bottom: 2px;
}
QListWidget#sidebar::item:hover:!selected { background: rgba(128, 128, 128, 40); }
QListWidget#sidebar::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
}
QLabel#brand { font-size: 17px; font-weight: 700; padding: 14px 18px 4px 18px; }

/* Segmented control */
QFrame#segmented {
    background: rgba(128, 128, 128, 40);
    border-radius: 8px;
}
QPushButton#segButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 14px;
}
QPushButton#segButton:checked {
    background: palette(base);
    border: 1px solid rgba(128, 128, 128, 70);
    font-weight: 600;
}

/* Buttons */
QPushButton#primary {
    background: palette(highlight);
    color: palette(highlighted-text);
    border: none;
    border-radius: 8px;
    padding: 6px 22px;
    font-weight: 600;
}
QPushButton#primary:hover { background: palette(highlight); }
QPushButton#primary:pressed { padding-top: 7px; }
QPushButton#secondary, QPushButton#flat {
    background: rgba(128, 128, 128, 40);
    border: none;
    border-radius: 7px;
    padding: 5px 12px;
}
QPushButton#secondary:hover, QPushButton#flat:hover { background: rgba(128, 128, 128, 70); }
QToolButton#bannerClose { border: none; background: transparent; font-size: 14px; padding: 2px 6px; }

/* Progress line + status */
QProgressBar#scanProgress {
    border: none;
    background: rgba(128, 128, 128, 35);
    min-height: 3px;
    max-height: 3px;
    border-radius: 1px;
}
QProgressBar#scanProgress::chunk { background: palette(highlight); border-radius: 1px; }
QLabel#status { color: rgba(128, 128, 128, 255); font-size: 12px; }

/* Banner and cards */
QFrame#banner {
    background: rgba(255, 196, 0, 40);
    border: 1px solid rgba(255, 180, 0, 130);
    border-radius: 8px;
}
QFrame#card {
    background: palette(base);
    border: 1px solid rgba(128, 128, 128, 55);
    border-radius: 12px;
}
QLabel#cardTitle { font-size: 11px; font-weight: 700; color: rgba(128, 128, 128, 255); }
QLabel#muted { color: rgba(128, 128, 128, 255); font-size: 11px; }
QLabel#tip { color: #16a34a; font-weight: 600; font-size: 11px; }

/* Views */
QTreeView, QTableWidget {
    background: palette(base);
    alternate-background-color: rgba(128, 128, 128, 16);
    border: 1px solid rgba(128, 128, 128, 55);
    border-radius: 10px;
    outline: 0;
}
QTreeView::item { padding: 3px 0; }
QTableWidget { gridline-color: transparent; }
QHeaderView::section {
    background: transparent;
    border: none;
    border-bottom: 1px solid rgba(128, 128, 128, 70);
    padding: 6px 8px;
    font-weight: 600;
}
QSplitter::handle { background: transparent; }
"""
