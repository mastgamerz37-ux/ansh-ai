"""
ANSH AI — Dynamic Compact Desktop Smart Island (Enhanced SVG & Modernized Edition)
Implements Apple-level morphing Desktop Smart Island:
  - Embedded near top camera notch
  - Magnetic snapping to top-center
  - Ultra-compact dimensions (180x36 Standby)
  - SVG vector icons for crisp scaling (no emojis!)
  - Clean Standby mode (Synthesizing text view removed per user preference)
  - Dynamic State-Aware Audio Wave Visualizer (Standby ambient, Speaking, Listening, Music)
  - Real-Time Windows System Media Sync (Spotify, YouTube/Chrome, Edge, VLC) with Live Cover Art & Metadata
"""

from __future__ import annotations

import math
import os
import sys
import asyncio
import threading
import webbrowser
from typing import Callable, Optional, Dict, Any

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, QRect, QRectF, QSize, Qt,
    QTimer, pyqtSignal, QBuffer, QIODevice, QByteArray
)
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient, QImage, QIcon
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

# Optional WinRT System Media Transport Control Integration
_WINRT_MEDIA_AVAILABLE = False
try:
    if sys.platform == "win32":
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
        from winrt.windows.storage.streams import DataReader
        _WINRT_MEDIA_AVAILABLE = True
except Exception:
    _WINRT_MEDIA_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# Crisp Modern SVG Icons Dictionary
# ──────────────────────────────────────────────────────────────────────────────
SVGS = {
    "search": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>''',
    "close": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>''',
    "dashboard": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1.5"/><rect width="7" height="5" x="14" y="3" rx="1.5"/><rect width="7" height="9" x="14" y="12" rx="1.5"/><rect width="7" height="5" x="3" y="16" rx="1.5"/></svg>''',
    "music": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>''',
    "briefing": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8z"/></svg>''',
    "shield": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/></svg>''',
    "prev": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="19 20 9 12 19 4 19 20"/><line x1="5" x2="5" y1="19" y2="5"/></svg>''',
    "play_pause": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>''',
    "next": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 4 15 12 5 20 5 4"/><line x1="19" x2="19" y1="5" y2="19"/></svg>''',
    "ai_spark": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"/></svg>''',
    "spotify": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm5.521 17.341c-.217.357-.679.467-1.036.25-2.834-1.732-6.402-2.124-10.605-1.164-.403.092-.806-.157-.899-.56-.092-.403.157-.806.56-.899 4.603-1.052 8.552-.603 11.73 1.336.357.217.467.679.25 1.037zm1.474-3.277c-.273.444-.856.586-1.3.313-3.243-1.993-8.188-2.569-12.025-1.404-.501.152-1.026-.134-1.178-.635-.152-.501.134-1.026.635-1.178 4.382-1.33 9.832-.693 13.555 1.597.444.273.586.856.313 1.3zm.127-3.415C15.228 8.49 8.8 8.277 5.12 9.394c-.604.183-1.242-.164-1.425-.768-.183-.604.164-1.242.768-1.425 4.228-1.283 11.31-1.036 15.932 1.706.544.323.722 1.028.399 1.572-.323.544-1.028.722-1.572.399z"/></svg>''',
    "youtube": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>'''
}


def create_svg_pixmap(key: str, size: int = 16, color: str = "#94a3b8") -> QPixmap:
    """Helper to render vector SVG directly to QPixmap with crisp anti-aliased scaling."""
    svg_xml = SVGS.get(key, SVGS["ai_spark"])
    colored_xml = svg_xml.replace('stroke="currentColor"', f'stroke="{color}"').replace('fill="currentColor"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(colored_xml.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, float(size), float(size)))
    painter.end()
    return pixmap


def create_svg_icon(key: str, size: int = 16, color: str = "#94a3b8") -> QIcon:
    """Helper to convert SVG pixmap into QIcon."""
    return QIcon(create_svg_pixmap(key, size, color))


class SvgLabel(QLabel):
    """Custom Label Widget that dynamically renders SVG graphics."""
    def __init__(self, key: str, size: int = 16, color: str = "#94a3b8", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.key = key
        self.color = color
        self._update_pixmap()

    def set_color(self, color: str):
        self.color = color
        self._update_pixmap()

    def _update_pixmap(self):
        self.setPixmap(create_svg_pixmap(self.key, self.width(), self.color))


class SmartIslandTheme:
    BG_DARK       = QColor(10, 10, 14, 252)
    BORDER        = QColor(255, 255, 255, 25)
    BORDER_GLOW   = QColor(125, 211, 252, 160)
    PRIMARY       = QColor(125, 211, 252)       # Soft Cyan #7dd3fc
    PRIMARY_RGB   = "#7dd3fc"
    SECONDARY     = QColor(192, 132, 252)      # Purple #c084fc
    SECONDARY_RGB = "#c084fc"
    SPOTIFY_GREEN = QColor(30, 215, 96)         # Spotify Green #1ed760
    YOUTUBE_RED   = QColor(255, 0, 0)           # YouTube Red #ff0000
    TEXT_MAIN     = "#f8fafc"
    TEXT_MUTED    = "#94a3b8"
    TEXT_DIM      = "#64748b"
    ALERT_RED     = QColor(239, 68, 68)         # #ef4444
    GREEN         = QColor(52, 211, 153)        # #34d399


class DynamicWaveVisualizer(QWidget):
    """
    Sleek, state-aware audio wave visualizer.
    Modes:
      - STANDBY: Smooth subtle ambient breathing wave
      - SPEAKING: High-energy dynamic multi-bar wave in cyan/violet gradient
      - LISTENING: Responsive glowing green/cyan wave
      - MUSIC: Rhythmic 5-bar equalizer in purple/magenta gradient
    """

    MODE_STANDBY   = "STANDBY"
    MODE_SPEAKING  = "SPEAKING"
    MODE_LISTENING = "LISTENING"
    MODE_MUSIC     = "MUSIC"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 16)
        self.mode = self.MODE_STANDBY
        self.phase = 0.0
        self.bar_heights = [3.0] * 5

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(33)  # ~30 fps

    def set_mode(self, mode: str):
        if self.mode != mode:
            self.mode = mode
            self.update()

    def _animate(self):
        self.phase += 0.18
        speed_mult = 1.0
        target_heights = []

        if self.mode == self.MODE_STANDBY:
            for i in range(5):
                target_heights.append(2.0)

        elif self.mode == self.MODE_SPEAKING:
            speed_mult = 1.4
            for i in range(5):
                val = math.sin(self.phase * speed_mult + i * 1.1) * 0.5 + 0.5
                target_heights.append(3.0 + val * 10.0)

        elif self.mode == self.MODE_LISTENING:
            speed_mult = 1.2
            for i in range(5):
                val = math.cos(self.phase * speed_mult + i * 0.9) * 0.5 + 0.5
                target_heights.append(3.5 + val * 9.0)

        elif self.mode == self.MODE_MUSIC:
            speed_mult = 1.5
            offsets = [0.0, 1.2, 2.4, 0.8, 1.9]
            for i in range(5):
                val = math.sin(self.phase * speed_mult + offsets[i]) * 0.5 + 0.5
                target_heights.append(4.0 + val * 10.5)

        for i in range(5):
            self.bar_heights[i] += (target_heights[i] - self.bar_heights[i]) * 0.35

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bars = 5
        bar_w = 2.5
        spacing = 2.5
        h = float(self.height())
        painter.setPen(Qt.PenStyle.NoPen)

        if self.mode == self.MODE_SPEAKING:
            color1, color2 = SmartIslandTheme.PRIMARY, SmartIslandTheme.SECONDARY
        elif self.mode == self.MODE_LISTENING:
            color1, color2 = SmartIslandTheme.GREEN, SmartIslandTheme.PRIMARY
        elif self.mode == self.MODE_MUSIC:
            color1, color2 = SmartIslandTheme.SECONDARY, QColor(244, 114, 182) # Magenta #f472b6
        else:
            color1, color2 = QColor(255, 255, 255, 180), SmartIslandTheme.PRIMARY

        total_w = bars * bar_w + (bars - 1) * spacing
        start_x = (float(self.width()) - total_w) / 2.0

        for i in range(bars):
            bar_h = min(h - 1, max(2.5, self.bar_heights[i]))
            x = start_x + i * (bar_w + spacing)
            y = (h - bar_h) / 2.0

            t = i / float(bars - 1)
            r = int(color1.red() * (1 - t) + color2.red() * t)
            g = int(color1.green() * (1 - t) + color2.green() * t)
            b = int(color1.blue() * (1 - t) + color2.blue() * t)
            alpha = 255 if self.mode != self.MODE_STANDBY else int(160 + 50 * math.sin(self.phase + i))

            painter.setBrush(QBrush(QColor(r, g, b, alpha)))
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 1.2, 1.2)


class IslandPillWidget(QWidget):
    """Custom painted compact pill container with glassmorphism glow & premium border."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state_glow = "NORMAL"
        self.glow_phase = 0.0

        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._tick_glow)
        self._glow_timer.start(35)

    def _tick_glow(self):
        self.glow_phase = (self.glow_phase + 0.06) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        radius = min(rect.height() / 2.0, 22.0)

        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        glow_alpha = int(40 + 25 * math.sin(self.glow_phase))

        if self.state_glow in ("ACTIVE", "SPEAKING", "YELLOW"):
            border_pen = QPen(QColor(250, 204, 21, glow_alpha + 140), 1.8)
        elif self.state_glow in ("GREEN", "LISTENING"):
            border_pen = QPen(QColor(52, 211, 153, glow_alpha + 140), 1.8)
        elif self.state_glow == "ALERT":
            border_pen = QPen(QColor(239, 68, 68, glow_alpha + 130), 1.8)
        elif self.state_glow == "MUSIC":
            border_pen = QPen(QColor(192, 132, 252, glow_alpha + 100), 1.5)
        else:
            border_pen = QPen(QColor(255, 255, 255, 32), 1.0)

        # Glassmorphic Fill
        painter.fillPath(path, QBrush(SmartIslandTheme.BG_DARK))

        # Top Highlight Reflection
        hl_path = QPainterPath()
        hl_path.addRoundedRect(rect.adjusted(1, 1, -1, -rect.height() * 0.45), radius, radius)
        hl_grad = QLinearGradient(rect.topLeft(), rect.center())
        hl_grad.setColorAt(0.0, QColor(255, 255, 255, 22))
        hl_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(hl_path, QBrush(hl_grad))

        # Border Stroke
        painter.strokePath(path, border_pen)


class GlowingOrbWidget(QWidget):
    """Pulsating radial SVG core orb."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.pulse_phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self):
        self.pulse_phase = (self.pulse_phase + 0.08) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QRectF(self.rect()).center()
        pulse = 0.8 + 0.2 * math.sin(self.pulse_phase)
        r_outer = 8.5 * pulse

        rad_grad = QRadialGradient(center, r_outer)
        rad_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        rad_grad.setColorAt(0.4, QColor(125, 211, 252, 220))
        rad_grad.setColorAt(1.0, QColor(56, 189, 248, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(rad_grad))
        painter.drawEllipse(center, r_outer, r_outer)


class SmartIslandWindow(QWidget):
    """
    Apple-level compact, frameless Desktop Smart Island with Real-Time Media Sync and SVG controls.
    Embedded right under top camera notch with magnetic snapping.
    """

    command_submitted = pyqtSignal(str)
    dashboard_requested = pyqtSignal()
    media_updated = pyqtSignal(dict)
    airtouch_alert = pyqtSignal(dict)

    STATE_STANDBY       = "STANDBY"
    STATE_SPOTLIGHT     = "SPOTLIGHT"
    STATE_MUSIC         = "MUSIC"
    STATE_BRIEFING      = "BRIEFING"
    STATE_ALERT         = "ALERT"

    def __init__(self, on_command: Optional[Callable[[str], None]] = None, on_open_dashboard: Optional[Callable[[], None]] = None):
        super().__init__()

        self.on_command = on_command
        self.on_open_dashboard = on_open_dashboard

        self.current_state = self.STATE_STANDBY
        self._drag_pos = QPoint()
        self._is_dragging = False
        self._current_media_info: Dict[str, Any] = {}

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1, 1)

        self._init_ui()
        self._position_top_center()

        if self.on_command:
            self.command_submitted.connect(self.on_command)
        if self.on_open_dashboard:
            self.dashboard_requested.connect(self.on_open_dashboard)

        self.media_updated.connect(self._apply_media_info)

        # Initialize AirTouch Vision Engine (runs silently in background, no intrusive UI alerts)
        try:
            from core.airtouch import AirTouchEngine
            self.airtouch = AirTouchEngine.get_instance()
            self.airtouch.start()
        except Exception as e:
            print(f"[SmartIsland] AirTouch init note: {e}")
            self.airtouch = None


        # Media Auto-Poll Timer
        self._media_timer = QTimer(self)
        self._media_timer.timeout.connect(self._poll_system_media)
        self._media_timer.start(1500)
        self._poll_system_media()


    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(2, 2, 2, 2)
        root_layout.setSpacing(0)

        self.pill = IslandPillWidget(self)
        pill_layout = QVBoxLayout(self.pill)
        pill_layout.setContentsMargins(8, 3, 8, 3)
        pill_layout.setSpacing(0)
        root_layout.addWidget(self.pill)

        self.stack = QStackedWidget(self.pill)
        pill_layout.addWidget(self.stack)

        self.view_standby = self._create_standby_view()
        self.stack.addWidget(self.view_standby)

        self.view_spotlight = self._create_spotlight_view()
        self.stack.addWidget(self.view_spotlight)

        self.view_music = self._create_music_view()
        self.stack.addWidget(self.view_music)

        self.view_briefing = self._create_briefing_view()
        self.stack.addWidget(self.view_briefing)

        self.view_alert = self._create_alert_view()
        self.stack.addWidget(self.view_alert)

        self.set_state(self.STATE_STANDBY)

    # ──────────────────────────────────────────────────────────────────────────
    # STANDBY MODE (180x36px) — Primary compact view with SVG sparkle
    # ──────────────────────────────────────────────────────────────────────────
    def _create_standby_view(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(6, 1, 6, 1)
        layout.setSpacing(6)

        spark_icon = SvgLabel("ai_spark", 13, SmartIslandTheme.PRIMARY_RGB)
        layout.addWidget(spark_icon)

        title_lbl = QLabel("Ansh")
        title_lbl.setStyleSheet(f"color: {SmartIslandTheme.TEXT_MAIN}; font-size: 12px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")
        layout.addWidget(title_lbl)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {SmartIslandTheme.GREEN.name()}; font-size: 7px;")
        layout.addWidget(dot)

        self.wave_vis = DynamicWaveVisualizer()
        layout.addWidget(self.wave_vis)

        w.setCursor(Qt.CursorShape.PointingHandCursor)
        w.mousePressEvent = lambda e: self.set_state(self.STATE_SPOTLIGHT)
        return w

    # ──────────────────────────────────────────────────────────────────────────
    # SPOTLIGHT / COMMAND INPUT ISLAND (330x64px) — SVG icons for Search/Close/Chips
    # ──────────────────────────────────────────────────────────────────────────
    def _create_spotlight_view(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        search_icon = SvgLabel("search", 14, "#64748b")
        input_row.addWidget(search_icon)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Ask Ansh or type a command...")
        self.cmd_input.setStyleSheet(f"QLineEdit {{ background: transparent; border: none; color: {SmartIslandTheme.TEXT_MAIN}; font-size: 12px; }}")
        self.cmd_input.returnPressed.connect(self._handle_command_enter)
        input_row.addWidget(self.cmd_input, stretch=1)

        shortcut_lbl = QLabel("Ctrl+K")
        shortcut_lbl.setStyleSheet("color: #64748b; font-size: 9px; font-family: 'Consolas'; background: rgba(255,255,255,0.06); padding: 1px 5px; border-radius: 3px;")
        input_row.addWidget(shortcut_lbl)

        close_btn = QPushButton()
        close_btn.setIcon(create_svg_icon("close", 12, "#64748b"))
        close_btn.setIconSize(QSize(12, 12))
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 9px; }")
        close_btn.clicked.connect(lambda: self.set_state(self.STATE_STANDBY))
        input_row.addWidget(close_btn)
        layout.addLayout(input_row)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)

        def make_svg_chip(label_text: str, svg_key: str, cmd: str):
            btn = QPushButton(f"  {label_text}")
            btn.setIcon(create_svg_icon(svg_key, 12, SmartIslandTheme.TEXT_MUTED))
            btn.setIconSize(QSize(12, 12))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 8px;
                    color: {SmartIslandTheme.TEXT_MUTED};
                    font-size: 10px;
                    padding: 2px 8px;
                }}
                QPushButton:hover {{
                    background: rgba(125,211,252,0.15);
                    border-color: {SmartIslandTheme.PRIMARY_RGB};
                    color: #fff;
                }}
            """)
            btn.clicked.connect(lambda: self._execute_chip(cmd))
            return btn

        chips_row.addWidget(make_svg_chip("Dashboard", "dashboard", "dashboard"))
        chips_row.addWidget(make_svg_chip("Media", "music", "mode_music"))
        chips_row.addWidget(make_svg_chip("Brief", "briefing", "mode_briefing"))
        chips_row.addStretch()
        layout.addLayout(chips_row)
        return w

    # ──────────────────────────────────────────────────────────────────────────
    # ENHANCED PREMIUM MEDIA PLAYER (295x155px) — SVG Controls
    # ──────────────────────────────────────────────────────────────────────────
    def _create_music_view(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        top_bar = QHBoxLayout()
        self.app_source_icon = SvgLabel("music", 12, SmartIslandTheme.PRIMARY_RGB)
        top_bar.addWidget(self.app_source_icon)

        self.app_source_lbl = QLabel("NOW PLAYING")
        self.app_source_lbl.setStyleSheet(f"color: {SmartIslandTheme.PRIMARY_RGB}; font-size: 9px; font-weight: 800; font-family: 'Consolas';")
        top_bar.addWidget(self.app_source_lbl)
        top_bar.addStretch()

        close_btn = QPushButton()
        close_btn.setIcon(create_svg_icon("close", 12, "#64748b"))
        close_btn.setIconSize(QSize(12, 12))
        close_btn.setFixedSize(16, 16)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 8px; }")
        close_btn.clicked.connect(lambda: self.set_state(self.STATE_STANDBY))
        top_bar.addWidget(close_btn)
        layout.addLayout(top_bar)

        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self.album_art_lbl = QLabel()
        self.album_art_lbl.setFixedSize(50, 50)
        self.album_art_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_art_lbl.setStyleSheet("background: #1e1b2e; border: 1px solid rgba(192,132,252,0.4); border-radius: 10px;")
        self.album_art_lbl.setPixmap(create_svg_pixmap("music", 24, SmartIslandTheme.SECONDARY_RGB))
        info_row.addWidget(self.album_art_lbl)

        track_col = QVBoxLayout()
        track_col.setSpacing(2)
        self.track_title = QLabel("Quantum Harmonics")
        self.track_title.setStyleSheet(f"color: {SmartIslandTheme.TEXT_MAIN}; font-size: 13px; font-weight: 700;")
        self.track_title.setWordWrap(True)

        self.track_artist = QLabel("Ansh Core")
        self.track_artist.setStyleSheet(f"color: {SmartIslandTheme.TEXT_MUTED}; font-size: 11px;")
        track_col.addWidget(self.track_title)
        track_col.addWidget(self.track_artist)
        info_row.addLayout(track_col, stretch=1)
        layout.addLayout(info_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_row.setSpacing(18)

        def _send_media_key(key_code: int):
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)
                except Exception:
                    pass

        btn_prev = QPushButton()
        btn_prev.setIcon(create_svg_icon("prev", 12, "#ffffff"))
        btn_prev.setIconSize(QSize(12, 12))
        btn_prev.setFixedSize(26, 26)
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.setStyleSheet("QPushButton { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 13px; } QPushButton:hover { background: rgba(255,255,255,0.15); }")
        btn_prev.clicked.connect(lambda: _send_media_key(0xB1))

        btn_play = QPushButton()
        btn_play.setIcon(create_svg_icon("play_pause", 14, "#0f172a"))
        btn_play.setIconSize(QSize(14, 14))
        btn_play.setFixedSize(32, 32)
        btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_play.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7dd3fc, stop:1 #c084fc); border: none; border-radius: 16px; } QPushButton:hover { background: #c084fc; }")
        btn_play.clicked.connect(lambda: _send_media_key(0xB3))

        btn_next = QPushButton()
        btn_next.setIcon(create_svg_icon("next", 12, "#ffffff"))
        btn_next.setIconSize(QSize(12, 12))
        btn_next.setFixedSize(26, 26)
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setStyleSheet("QPushButton { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 13px; } QPushButton:hover { background: rgba(255,255,255,0.15); }")
        btn_next.clicked.connect(lambda: _send_media_key(0xB0))

        ctrl_row.addWidget(btn_prev)
        ctrl_row.addWidget(btn_play)
        ctrl_row.addWidget(btn_next)
        layout.addLayout(ctrl_row)

        return w

    # ──────────────────────────────────────────────────────────────────────────
    # BRIEFING & ALERT VIEWS (SVG Icons)
    # ──────────────────────────────────────────────────────────────────────────
    def _create_briefing_view(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        tag_bar = QHBoxLayout()
        brief_icon = SvgLabel("briefing", 12, SmartIslandTheme.PRIMARY_RGB)
        tag_bar.addWidget(brief_icon)

        tag_badge = QLabel("INTELLIGENCE BRIEF")
        tag_badge.setStyleSheet(f"color: {SmartIslandTheme.PRIMARY_RGB}; font-size: 8px; font-weight: 800; font-family: 'Consolas';")
        tag_bar.addWidget(tag_badge)
        tag_bar.addStretch()

        close_btn = QPushButton()
        close_btn.setIcon(create_svg_icon("close", 12, "#64748b"))
        close_btn.setFixedSize(16, 16)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        close_btn.clicked.connect(lambda: self.set_state(self.STATE_STANDBY))
        tag_bar.addWidget(close_btn)
        layout.addLayout(tag_bar)

        self.headline = QLabel("Quantum Supremacy Claimed in Simulation Architecture")
        self.headline.setStyleSheet(f"color: {SmartIslandTheme.TEXT_MAIN}; font-size: 12px; font-weight: 700;")
        self.headline.setWordWrap(True)
        layout.addWidget(self.headline)

        return w

    def _create_alert_view(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        hdr = QHBoxLayout()
        hdr.setSpacing(4)
        shield_icon = SvgLabel("shield", 12, "#ef4444")
        hdr.addWidget(shield_icon)

        self.alert_t = QLabel("AirTouch: Unknown User")
        self.alert_t.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 700;")
        hdr.addWidget(self.alert_t, stretch=1)

        close_btn = QPushButton()
        close_btn.setIcon(create_svg_icon("close", 10, "#64748b"))
        close_btn.setFixedSize(14, 14)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        close_btn.clicked.connect(lambda: self.set_state(self.STATE_STANDBY))
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        self.alert_desc = QLabel("Camera detected an unknown face. Ye kon hain?")
        self.alert_desc.setStyleSheet("color: #f1f5f9; font-size: 9px;")
        self.alert_desc.setWordWrap(True)
        layout.addWidget(self.alert_desc)

        input_row = QHBoxLayout()
        input_row.setSpacing(4)

        self.alert_person_input = QLineEdit()
        self.alert_person_input.setPlaceholderText("Enter name (e.g., Rahul - Friend)...")
        self.alert_person_input.setStyleSheet(f"QLineEdit {{ background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); border-radius: 5px; color: {SmartIslandTheme.TEXT_MAIN}; font-size: 10px; padding: 1px 5px; }}")
        self.alert_person_input.returnPressed.connect(self._save_alert_person_identity)
        input_row.addWidget(self.alert_person_input, stretch=1)

        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"QPushButton {{ background: {SmartIslandTheme.PRIMARY_RGB}; border: none; border-radius: 5px; color: #0f172a; font-size: 10px; font-weight: 700; padding: 2px 6px; }} QPushButton:hover {{ background: #c084fc; }}")
        save_btn.clicked.connect(self._save_alert_person_identity)
        input_row.addWidget(save_btn)

        layout.addLayout(input_row)
        return w


    def _handle_unknown_person_detected(self, info: dict):
        """Triggered by AirTouch camera vision when an unknown face is detected."""
        self.alert_t.setText("AirTouch: Unknown User")
        self.alert_desc.setText("Camera detected an unknown face. Ye kon hain?")
        self.alert_person_input.clear()
        self.set_state(self.STATE_ALERT)
        self.alert_person_input.setFocus()

    def _save_alert_person_identity(self):
        text = self.alert_person_input.text().strip()
        if not text:
            self.set_state(self.STATE_STANDBY)
            return

        parts = text.split("-", 1)
        name = parts[0].strip()
        notes = parts[1].strip() if len(parts) > 1 else "Friend/Known person"

        if hasattr(self, "airtouch") and self.airtouch:
            msg = self.airtouch.register_identity(name, notes)
            print(f"[SmartIsland] AirTouch Identity Saved: {msg}")

        self.set_state(self.STATE_STANDBY)


    # ──────────────────────────────────────────────────────────────────────────
    # REAL-TIME SYSTEM MEDIA SYNC
    # ──────────────────────────────────────────────────────────────────────────
    def _poll_system_media(self):
        if not _WINRT_MEDIA_AVAILABLE:
            return

        def _worker():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                info = loop.run_until_complete(self._async_fetch_media_properties())
                loop.close()
                if info:
                    self.media_updated.emit(info)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    async def _async_fetch_media_properties(self) -> dict | None:
        try:
            mgr = await MediaManager.request_async()
            session = mgr.get_current_session()
            if not session:
                return None

            app_id = (session.source_app_user_model_id or "").lower()
            props = await session.try_get_media_properties_async()
            if not props:
                return None

            title = props.title or ""
            artist = props.artist or ""

            if not title and not artist:
                return None

            if "spotify" in app_id:
                source_name = "Spotify"
            elif "chrome" in app_id or "youtube" in app_id:
                source_name = "YouTube"
            elif "msedge" in app_id:
                source_name = "Edge Media"
            else:
                source_name = "System Media"

            pixmap = None
            if props.thumbnail:
                try:
                    stream = await props.thumbnail.open_read_async()
                    reader = DataReader(stream)
                    await reader.load_async(stream.size)
                    buf = bytearray(stream.size)
                    reader.read_bytes(buf)

                    img = QImage()
                    if img.loadFromData(buf):
                        pixmap = QPixmap.fromImage(img)
                except Exception:
                    pixmap = None

            return {
                "source": source_name,
                "title": title,
                "artist": artist,
                "pixmap": pixmap,
            }
        except Exception:
            return None

    def _apply_media_info(self, info: dict):
        if not info:
            return

        self._current_media_info = info
        src = info.get("source", "System Media")
        title = info.get("title", "Unknown Track")
        artist = info.get("artist", "")

        if src == "Spotify":
            badge_txt = "SPOTIFY"
            badge_clr = "#1ed760"
            svg_key = "spotify"
        elif src == "YouTube":
            badge_txt = "YOUTUBE"
            badge_clr = "#ff4444"
            svg_key = "youtube"
        else:
            badge_txt = src.upper()
            badge_clr = SmartIslandTheme.PRIMARY_RGB
            svg_key = "music"

        self.app_source_icon.key = svg_key
        self.app_source_icon.set_color(badge_clr)
        self.app_source_lbl.setText(badge_txt)
        self.app_source_lbl.setStyleSheet(f"color: {badge_clr}; font-size: 9px; font-weight: 800; font-family: 'Consolas';")

        self.track_title.setText(title)
        self.track_artist.setText(artist or "Active Stream")

        pixmap = info.get("pixmap")
        if pixmap and isinstance(pixmap, QPixmap) and not pixmap.isNull():
            scaled = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self.album_art_lbl.setPixmap(scaled)
        else:
            self.album_art_lbl.setPixmap(create_svg_pixmap(svg_key, 26, badge_clr))

        if self.current_state == self.STATE_STANDBY:
            self.wave_vis.set_mode(DynamicWaveVisualizer.MODE_MUSIC)
            self.pill.state_glow = "MUSIC"
            self.pill.update()

    # ──────────────────────────────────────────────────────────────────────────
    # STATE CONTROLLER & POSITIONING
    # ──────────────────────────────────────────────────────────────────────────
    def set_state(self, state: str, text: str = ""):
        if state == "SYNTHESIZING":
            state = self.STATE_STANDBY

        self.current_state = state

        if state == self.STATE_STANDBY:
            target_w, target_h = 180, 36
            self.pill.state_glow = "NORMAL"
            self.wave_vis.set_mode(DynamicWaveVisualizer.MODE_STANDBY)
            self.stack.setCurrentWidget(self.view_standby)

        elif state == self.STATE_SPOTLIGHT:
            target_w, target_h = 330, 64
            self.pill.state_glow = "ACTIVE"
            self.stack.setCurrentWidget(self.view_spotlight)
            self.cmd_input.setFocus()
            self.cmd_input.selectAll()

        elif state == self.STATE_MUSIC:
            target_w, target_h = 295, 155
            self.pill.state_glow = "MUSIC"
            self.wave_vis.set_mode(DynamicWaveVisualizer.MODE_MUSIC)
            self.stack.setCurrentWidget(self.view_music)

        elif state == self.STATE_BRIEFING:
            target_w, target_h = 340, 180
            self.pill.state_glow = "ACTIVE"
            self.stack.setCurrentWidget(self.view_briefing)

        elif state == self.STATE_ALERT:
            target_w, target_h = 280, 120
            self.pill.state_glow = "ALERT"
            self.stack.setCurrentWidget(self.view_alert)

        else:
            target_w, target_h = 180, 36
            self.pill.state_glow = "NORMAL"
            self.wave_vis.set_mode(DynamicWaveVisualizer.MODE_STANDBY)
            self.stack.setCurrentWidget(self.view_standby)

        for i in range(self.stack.count()):
            page = self.stack.widget(i)
            if page == self.stack.currentWidget():
                page.setMinimumSize(0, 0)
                page.setMaximumSize(16777215, 16777215)
                page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            else:
                page.setMinimumSize(0, 0)
                page.setMaximumSize(0, 0)
                page.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self._animate_resize(target_w, target_h)

    def _animate_resize(self, target_w: int, target_h: int):
        screen = QApplication.primaryScreen().geometry()
        center_x = screen.x() + (screen.width() // 2)
        new_x = int(center_x - target_w / 2)
        new_y = screen.y() + 4

        target_rect = QRect(new_x, new_y, target_w, target_h)
        self.setMinimumSize(1, 1)
        self.setMaximumSize(16777215, 16777215)

        if not self.isVisible():
            self.setGeometry(target_rect)
            return

        cur_geom = self.geometry()
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(220)
        self.anim.setStartValue(cur_geom)
        self.anim.setEndValue(target_rect)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def _position_top_center(self):
        screen = QApplication.primaryScreen().geometry()
        w, h = 180, 36
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + 4
        self.setGeometry(x, y, w, h)

    def _animate_snap_top_center(self):
        screen = QApplication.primaryScreen().geometry()
        target_x = screen.x() + (screen.width() - self.width()) // 2
        target_y = screen.y() + 4

        self.snap_anim = QPropertyAnimation(self, b"geometry")
        self.snap_anim.setDuration(280)
        self.snap_anim.setStartValue(self.geometry())
        self.snap_anim.setEndValue(QRect(target_x, target_y, self.width(), self.height()))
        self.snap_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.snap_anim.start()

    def _handle_command_enter(self):
        text = self.cmd_input.text().strip()
        if not text:
            self.set_state(self.STATE_STANDBY)
            return

        self.cmd_input.clear()
        cmd_lower = text.lower()

        if cmd_lower in ("dashboard", "open dashboard", "panel", "ui"):
            self.open_dashboard()
            self.set_state(self.STATE_STANDBY)
            return

        # Directly stay/return to compact Standby pill mode
        self.set_state(self.STATE_STANDBY)
        self.command_submitted.emit(text)

    def _execute_chip(self, action_cmd: str):
        if action_cmd == "dashboard":
            self.open_dashboard()
            self.set_state(self.STATE_STANDBY)
        elif action_cmd == "mode_briefing":
            self.set_state(self.STATE_BRIEFING)
        elif action_cmd == "mode_music":
            self.set_state(self.STATE_MUSIC)

    def open_dashboard(self):
        self.dashboard_requested.emit()
        try:
            webbrowser.open("http://localhost:8000")
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        screen = QApplication.primaryScreen().availableGeometry()
        if abs(self.geometry().center().x() - screen.width() // 2) < 200 and self.geometry().top() < screen.top() + 80:
            self._animate_snap_top_center()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.set_state(self.STATE_STANDBY)
        else:
            super().keyPressEvent(event)

    def set_speaking_state(self, is_speaking: bool):
        """Dynamic speaking wave state update."""
        if is_speaking:
            self.pill.state_glow = "SPEAKING"
            self.wave_vis.set_mode(DynamicWaveVisualizer.MODE_SPEAKING)
        else:
            self.pill.state_glow = "NORMAL"
            self.wave_vis.set_mode(DynamicWaveVisualizer.MODE_STANDBY)
        self.pill.update()
        self.wave_vis.update()

    def set_hearing_state(self, is_hearing: bool):
        """Dynamic listening wave state update."""
        if is_hearing:
            self.pill.state_glow = "GREEN"
            self.wave_vis.set_mode(DynamicWaveVisualizer.MODE_LISTENING)
        else:
            self.pill.state_glow = "NORMAL"
            if self.current_state == self.STATE_STANDBY:
                self.wave_vis.set_mode(DynamicWaveVisualizer.MODE_STANDBY)
        self.pill.update()
        self.wave_vis.update()

    def update_briefing(self, text: str):
        """Dynamically update spoken text in Intelligence Briefing view."""
        if hasattr(self, 'headline'):
            self.headline.setText(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    island = SmartIslandWindow(
        on_command=lambda cmd: print(f"[Test SmartIsland] Command: {cmd}"),
        on_open_dashboard=lambda: print("[Test SmartIsland] Dashboard requested")
    )
    island.show()
    print("ANSH Modernized SVG Smart Island running.")
    sys.exit(app.exec())
