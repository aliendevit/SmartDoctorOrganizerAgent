# UI/icons.py
from __future__ import annotations
from PyQt5 import QtCore, QtGui, QtSvg

_ICONS = {
    "extraction": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="3.5" width="17" height="17" rx="3"/>
  <path d="M7 8h10M7 12h10M7 16h6"/>
</svg>
""",
    "appointments": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="4.5" width="17" height="16" rx="3"/>
  <path d="M8 3v4M16 3v4M3.5 9.5h17"/>
  <circle cx="12" cy="14" r="3.2"/>
  <path d="M12 12.2V14l1.2 1.2"/>
</svg>
""",
    "dashboard": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 13a8 8 0 1 1 16 0"/>
  <path d="M12 13l4-4"/>
  <circle cx="12" cy="13" r="1.2" fill="currentColor"/>
  <path d="M3 21h18"/>
</svg>
""",
    "accounts": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="5" width="17" height="14" rx="2.5"/>
  <path d="M3.5 9h17M8 13h4M8 16h8"/>
</svg>
""",
    "stats": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 20V6M10 20V10M16 20V4M22 20H2"/>
</svg>
""",
    "calc": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
  <rect x="4" y="3.5" width="16" height="17" rx="2.5"/>
  <path d="M8 7h8M8 12h4M14 12h2M9 16h2M13 16h2"/>
</svg>
""",
    "time": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="8.5"/>
  <path d="M12 7.5v5l3 2"/>
</svg>
""",
    "report": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
  <path d="M6 4h9l3 3v13H6z"/>
  <path d="M15 4v3h3M8 12h8M8 15.5h8M8 9h5"/>
</svg>
""",
    "payment": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="6.5" width="17" height="11" rx="2.5"/>
  <path d="M3.5 10.5h17M8 14h4"/>
</svg>
""",
    "chat": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
  <path d="M5 18l-2 3V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6z"/>
  <path d="M8 9h8M8 12h5"/>
</svg>
""",
    "settings": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3.2"/>
  <path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.02.02a2 2 0 1 1-2.83 2.83l-.02-.02A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .18 1.8 1.8 0 0 1-2 0A1.8 1.8 0 0 0 11 19.4a1.8 1.8 0 0 0-1 .18 1.8 1.8 0 0 1-2 0A1.8 1.8 0 0 0 7 19.4a1.8 1.8 0 0 0-1.98-.36l-.02.02a2 2 0 1 1-2.83-2.83l.02-.02A1.8 1.8 0 0 0 4.6 15c0-.33-.06-.66-.18-.98a1.8 1.8 0 0 0 0-1.99c.12-.32.18-.65.18-.98a1.8 1.8 0 0 0-.36-1.98l-.02-.02a2 2 0 1 1 2.83-2.83l.02.02C6.34 5.24 6.67 5.12 7 5.12c.33 0 .66-.06.98-.18a1.8 1.8 0 0 0 1.99 0c.32-.12.65-.18 1.02-.18s.66.06.98.18a1.8 1.8 0 0 0 1.99 0c.32-.12.65-.18 1.02-.18.33 0 .66.06.98.18l.02-.02a2 2 0 1 1 2.83 2.83l-.02.02c.24.3.36.63.36.98 0 .33.06.66.18.98a1.8 1.8 0 0 0 0 1.99c-.12.32-.18.65-.18.98Z"/>
</svg>
""",
}

def icon(name: str, *, size: int = 18, color: str = "#0f172a") -> QtGui.QIcon:
    svg = _ICONS.get(name)
    if not svg:
        svg = _ICONS["dashboard"]
    svg = svg.replace("currentColor", color)
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
    img = QtGui.QImage(size, size, QtGui.QImage.Format_ARGB32)
    img.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(img)
    p.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
    renderer.render(p)
    p.end()
    return QtGui.QIcon(QtGui.QPixmap.fromImage(img))
