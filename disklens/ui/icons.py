"""
Monochrome vector pictograms for DiskLens UI.
Renders resolution-independent crisp QIcons from SVGs.
Supports Normal (slate/charcoal) and Selected (pure white) states.
"""

from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import QByteArray, QRectF, Qt

ICONS_SVG = {
    "tree": """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="6" height="5" rx="1.5"/>
  <rect x="15" y="7" width="6" height="5" rx="1.5"/>
  <rect x="15" y="16" width="6" height="5" rx="1.5"/>
  <path d="M6 8v10h9"/>
  <path d="M6 9.5h9"/>
</svg>
""",
    "treemap": """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="18" height="18" rx="2.5"/>
  <line x1="12" y1="3" x2="12" y2="21"/>
  <line x1="12" y1="12" x2="21" y2="12"/>
</svg>
""",
    "suggestions": """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>
  <path d="M19 3v4"/>
  <path d="M21 5h-4"/>
</svg>
""",
    "summary": """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21.2 15.8A10 10 0 1 1 8.2 2.8"/>
  <path d="M22 12A10 10 0 0 0 12 2v10z"/>
</svg>
""",
    "errors": """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
  <line x1="12" y1="9" x2="12" y2="13"/>
  <circle cx="12" cy="17" r="0.8" fill="{color}"/>
</svg>
"""
}


def get_monochrome_icon(name: str, size: int = 18) -> QIcon:
    """Generate a crisp high-DPI QIcon from monochrome vector SVG."""
    svg_template = ICONS_SVG.get(name)
    if not svg_template:
        return QIcon()

    icon = QIcon()
    px_size = size * 2
    for mode, color in [(QIcon.Mode.Normal, "#475569"), (QIcon.Mode.Selected, "#ffffff")]:
        svg_bytes = svg_template.format(color=color).strip().encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg_bytes))
        pixmap = QPixmap(px_size, px_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap.setDevicePixelRatio(2.0)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        icon.addPixmap(pixmap, mode)

    return icon
