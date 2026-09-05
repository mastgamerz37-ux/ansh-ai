"""
d:\\ansh\\location.py — Display & Camera Notch Location Locator Utility
"""

import sys
from PyQt6.QtCore import QPoint, QRectF, QTimer, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QWidget


def get_screen_telemetry():
    """Detect and return screen resolution and camera notch target coordinates."""
    app = QApplication.instance() or QApplication(sys.argv)
    screen = app.primaryScreen()
    geom = screen.geometry()
    avail = screen.availableGeometry()

    width = geom.width()
    height = geom.height()
    left = geom.left()
    top = geom.top()

    top_center_x = left + (width // 2)
    top_center_y = top + 4

    screen_center_x = left + (width // 2)
    screen_center_y = top + (height // 2)

    return {
        "width": width,
        "height": height,
        "left": left,
        "top": top,
        "top_center_x": top_center_x,
        "top_center_y": top_center_y,
        "screen_center_x": screen_center_x,
        "screen_center_y": screen_center_y,
        "avail_width": avail.width(),
        "avail_height": avail.height(),
        "device_pixel_ratio": screen.devicePixelRatio()
    }


class LocationTargetWidget(QWidget):
    """Visual target marker window overlay."""

    def __init__(self, telemetry: dict):
        super().__init__()
        self.telemetry = telemetry

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1, 1)

        w, h = 320, 75
        x = telemetry["top_center_x"] - (w // 2)
        y = telemetry["top"] + 2

        self.setGeometry(x, y, w, h)
        QTimer.singleShot(6000, self.close)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        painter.fillPath(path, QBrush(QColor(15, 23, 42, 245)))
        painter.strokePath(path, QPen(QColor(56, 189, 248, 220), 1.5))

        cx = rect.center().x()
        cy = rect.top() + 10

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(239, 68, 68, 240)))
        painter.drawEllipse(QPoint(int(cx), int(cy)), 5, 5)

        painter.setPen(QPen(QColor(241, 245, 249)))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text = f"🎯 CAMERA NOTCH: X={self.telemetry['top_center_x']}, Y={self.telemetry['top_center_y']}"
        painter.drawText(self.rect().adjusted(0, 18, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, text)

        painter.setPen(QPen(QColor(148, 163, 184)))
        painter.setFont(QFont("Segoe UI", 8))
        subtext = f"Screen: {self.telemetry['width']}x{self.telemetry['height']} | DPI Ratio: {self.telemetry['device_pixel_ratio']:.1f}\n(Auto-closing in 6s...)"
        painter.drawText(self.rect().adjusted(0, 36, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, subtext)


def main():
    app = QApplication(sys.argv)
    t = get_screen_telemetry()

    print("\n" + "=" * 60)
    print(" 🖥️  ANSH DISPLAY & CAMERA NOTCH LOCATION TELEMETRY")
    print("=" * 60)
    print(f" • Screen Resolution       : {t['width']} x {t['height']} px")
    print(f" • Screen Bounds (L, T)     : Left={t['left']}, Top={t['top']}")
    print(f" • Device Pixel Ratio (DPI) : {t['device_pixel_ratio']}")
    print("-" * 60)p
    print(f" 🎯 TOP CAMERA CENTER TARGET : X = {t['top_center_x']} px, Y = {t['top_center_y']} px")
    print(f" 🎯 SCREEN DEAD CENTER TARGET: X = {t['screen_center_x']} px, Y = {t['screen_center_y']} px")
    print("=" * 60 + "\n")

    target = LocationTargetWidget(t)
    target.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
