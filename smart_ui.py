"""
smart_ui.py — Futuristic Dynamic Island UI with Glowing Neon Outlines,
Always-Visible Quick Buttons, Interactive Phone Pairing, and Smooth Animations.
"""
from __future__ import annotations

import io
import json
import math
import os
import platform
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Any

from PyQt6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QIcon,
    QImage,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import keyboard


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"


def _read_full_config() -> dict:
    try:
        return json.loads(API_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── Phone Pairing Dialog ──────────────────────────────────────────────────────

class PhonePairingDialog(QDialog):
    """Modern dark modal popup showing QR code, PIN, and LAN link for mobile connection."""

    def __init__(self, parent: QWidget, url: str, key: str, auto_login_url: str, manual_url: str):
        super().__init__(parent)
        self.setWindowTitle("ANSH — Connect Smartphone")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(400, 510)
        self.setStyleSheet("""
            QDialog {
                background-color: #0c0e17;
                color: #ffffff;
                border-radius: 20px;
                border: 2px solid #00d4ff;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            QPushButton {
                background-color: #171b2b;
                color: #00d4ff;
                border: 1.5px solid rgba(0, 212, 255, 0.5);
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
                cursor: pointer;
            }
            QPushButton:hover {
                background-color: rgba(0, 212, 255, 0.3);
                border-color: #00d4ff;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Title
        title_lbl = QLabel("📱 Connect Smartphone")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #00d4ff;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel("Scan QR with Phone or open LAN link in Mobile Browser")
        sub_lbl.setStyleSheet("font-size: 12px; color: #8e95ad;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_lbl)

        # QR Code Display
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(186, 186)
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet("""
            background-color: #ffffff;
            border-radius: 14px;
            padding: 8px;
        """)
        self._generate_qr(auto_login_url)

        qr_container = QHBoxLayout()
        qr_container.addStretch()
        qr_container.addWidget(self.qr_label)
        qr_container.addStretch()
        layout.addLayout(qr_container)

        # PIN & URL Info Box
        info_box = QWidget()
        info_box.setStyleSheet("""
            QWidget {
                background-color: #141724;
                border-radius: 12px;
                border: 1px solid rgba(0, 212, 255, 0.25);
            }
        """)
        info_lay = QVBoxLayout(info_box)
        info_lay.setContentsMargins(16, 12, 16, 12)
        info_lay.setSpacing(6)

        url_lbl = QLabel(f"🌐 Link: <b style='color:#00d4ff;'>{url}</b>")
        url_lbl.setStyleSheet("font-size: 13px;")
        url_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_lay.addWidget(url_lbl)

        pin_lbl = QLabel(f"🔑 Security PIN: <b style='color:#00ff88; font-size:17px; letter-spacing:3px;'>{key}</b>")
        pin_lbl.setStyleSheet("font-size: 13px;")
        pin_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_lay.addWidget(pin_lbl)

        layout.addWidget(info_box)

        # Action Buttons
        btn_row = QHBoxLayout()
        copy_btn = QPushButton("📋 Copy Link")
        copy_btn.clicked.connect(lambda: self._copy_link(url))
        btn_row.addWidget(copy_btn)

        close_btn = QPushButton("Done")
        close_btn.setStyleSheet("""
            background-color: #00d4ff;
            color: #07090f;
            border: none;
            font-weight: bold;
        """)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _generate_qr(self, data: str):
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=1,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qimg = QImage.fromData(buf.getvalue())
            pix = QPixmap.fromImage(qimg).scaled(170, 170, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.qr_label.setPixmap(pix)
        except Exception:
            self.qr_label.setText(f"Link:\n{data}")
            self.qr_label.setStyleSheet("color: black; font-size: 10px;")

    def _copy_link(self, url: str):
        QApplication.clipboard().setText(url)
        QMessageBox.information(self, "Copied", f"Link copied to clipboard:\n{url}")


# ── Custom Painted Container with Glowing Outline ─────────────────────────────

class GlowingIslandContainer(QWidget):
    """
    Renders custom high-contrast glowing neon outline and translucent background.
    """

    def __init__(self, parent: SmartIslandWindow):
        super().__init__(parent)
        self.parent_window = parent
        self.pulse_phase = 0.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(1.5, 1.5, w - 3.0, h - 3.0)
        radius = min(22.0, h / 2.0)

        # 1. Dark Obsidian Glass Background
        bg_brush = QBrush(QColor(11, 13, 20, 245))
        painter.setBrush(bg_brush)

        # 2. Glowing Dynamic Outline Border
        state = getattr(self.parent_window, "_current_state", "IDLE")
        muted = getattr(self.parent_window, "_muted", False)

        # Pulse animation factor
        pulse = 0.8 + 0.2 * math.sin(self.pulse_phase)

        if muted:
            # Crimson Red
            c1 = QColor(255, 50, 75, int(255 * pulse))
            border_pen = QPen(c1, 2.2)
        elif state == "LISTENING":
            # Vibrant Electric Cyan
            c1 = QColor(0, 240, 255, int(255 * pulse))
            border_pen = QPen(c1, 2.2)
        elif state == "THINKING":
            # Royal Violet
            c1 = QColor(176, 38, 255, int(255 * pulse))
            border_pen = QPen(c1, 2.2)
        elif state == "SPEAKING":
            # Emerald Wave
            c1 = QColor(0, 255, 136, int(255 * pulse))
            border_pen = QPen(c1, 2.2)
        else:
            # IDLE: Radiant Cyan/Violet Gradient Outline
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor(0, 212, 255, int(230 * pulse)))
            grad.setColorAt(0.5, QColor(138, 43, 226, int(210 * pulse)))
            grad.setColorAt(1.0, QColor(0, 212, 255, int(230 * pulse)))
            border_pen = QPen(QBrush(grad), 2.2)

        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, radius, radius)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_window.handle_left_click(event)
        elif event.button() == Qt.MouseButton.RightButton:
            self.parent_window.show_context_menu(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.parent_window.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.parent_window.handle_mouse_release(event)
        super().mouseReleaseEvent(event)


# ── Main Smart Island Window ──────────────────────────────────────────────────

class SmartIslandWindow(QWidget):
    subtitle_signal = pyqtSignal(str)
    state_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._muted = False
        self._ready = True
        self._assistant_name = _read_full_config().get("assistant_name", "ANSH") or "ANSH"

        self.on_text_command: Optional[Callable[[str], None]] = None
        self.on_remote_clicked: Optional[Callable[[], Any]] = None
        self.on_interrupt: Optional[Callable[[], None]] = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.base_width = 330
        self.base_height = 54
        self.expanded_width = 500
        self.expanded_height = 165
        self.is_expanded = False

        self._drag_start_pos: Optional[QPoint] = None
        self._drag_win_pos: Optional[QPoint] = None
        self._dragged = False

        self.init_ui()
        self.setup_hotkey()

        self.subtitle_signal.connect(self.show_subtitle)
        self.state_signal.connect(self.update_state)

        # Auto-hide / idle timer
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._on_idle_timeout)
        self.idle_timer.start(60000)

        # Smooth pulse & outline glow timer (30 fps)
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._on_pulse_tick)
        self.pulse_timer.start(33)

        self._current_state = "IDLE"
        self.update_state("IDLE")
        self.enforce_autostart()

    def enforce_autostart(self):
        try:
            if platform.system() == "Windows":
                import winreg
                reg = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_ALL_ACCESS,
                )
                pythonw = Path(sys.executable).parent / "pythonw.exe"
                exe = str(pythonw if pythonw.exists() else sys.executable)
                script = str(Path(__file__).resolve().parent / "main.py")
                winreg.SetValueEx(reg, "ANSH_AI", 0, winreg.REG_SZ, f'"{exe}" "{script}"')
                winreg.CloseKey(reg)
            print("[SYS] Auto-start enforced.")
        except Exception as e:
            print(f"[ERR] Auto-start failed: {e}")

    def init_ui(self):
        self.setFixedSize(self.base_width, self.base_height)
        screen = QApplication.primaryScreen().geometry()
        self.x_pos = (screen.width() - self.base_width) // 2
        self.y_pos = 12
        self.move(self.x_pos, self.y_pos)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetNoConstraint)

        self.container = GlowingIslandContainer(self)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(14, 8, 14, 8)
        self.container_layout.setSpacing(6)
        self.container_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetNoConstraint)

        # ── Header Row (Always Visible) ───────────────────────────────────────
        self.header_row = QHBoxLayout()
        self.header_row.setContentsMargins(0, 0, 0, 0)
        self.header_row.setSpacing(8)

        # Status Dot
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #00d4ff; font-size: 14px; background: transparent; border: none;")
        self.status_dot.setFixedWidth(16)
        self.header_row.addWidget(self.status_dot)

        # Assistant Name / Subtitle Label
        self.subtitle_label = QLabel(self._assistant_name)
        self.subtitle_label.setStyleSheet("""
            color: #ffffff;
            font-weight: 700;
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 14px;
            border: none;
            background: transparent;
        """)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.subtitle_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.header_row.addWidget(self.subtitle_label)

        # Quick Phone Pairing Button (Always Visible in Header)
        self.quick_phone_btn = QPushButton("📱 Phone")
        self.quick_phone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_phone_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 212, 255, 0.15);
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.45);
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d4ff;
                color: #080a12;
            }
        """)
        self.quick_phone_btn.clicked.connect(self.open_phone_pairing)
        self.header_row.addWidget(self.quick_phone_btn)

        # Quick Mic Toggle Button (Always Visible in Header)
        self.quick_mic_btn = QPushButton("🎙")
        self.quick_mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_mic_btn.setFixedSize(30, 30)
        self.quick_mic_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: #00ff88;
                border: 1px solid rgba(0, 255, 136, 0.3);
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 136, 0.3);
            }
        """)
        self.quick_mic_btn.clicked.connect(self._toggle_mute)
        self.header_row.addWidget(self.quick_mic_btn)

        # Expand / Collapse Arrow Button
        self.expand_btn = QPushButton("⌄")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setFixedSize(28, 28)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #cccccc;
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                color: #ffffff;
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        self.header_row.addWidget(self.expand_btn)

        self.container_layout.addLayout(self.header_row)

        # ── Expanded Controls Box ─────────────────────────────────────────────
        self.expanded_box = QWidget()
        self.expanded_box.setStyleSheet("background: transparent; border: none;")
        self.expanded_box_layout = QVBoxLayout(self.expanded_box)
        self.expanded_box_layout.setContentsMargins(0, 6, 0, 0)
        self.expanded_box_layout.setSpacing(10)

        # Command Text Input
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(20, 23, 34, 0.95);
                color: #ffffff;
                border: 1.5px solid rgba(0, 212, 255, 0.4);
                border-radius: 10px;
                padding: 7px 14px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #00d4ff;
                background-color: rgba(28, 32, 48, 1.0);
            }
        """)
        self.input_field.setPlaceholderText("Type a command or question for ANSH...")
        self.input_field.returnPressed.connect(self.on_submit)
        self.expanded_box_layout.addWidget(self.input_field)

        # Action Buttons Row
        self.btn_row = QHBoxLayout()
        self.btn_row.setContentsMargins(0, 0, 0, 0)
        self.btn_row.setSpacing(10)

        # Full Connect Phone Button
        self.phone_btn = QPushButton("📱 Connect Phone")
        self.phone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.phone_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e2238;
                color: #00d4ff;
                border: 1.5px solid #00d4ff;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d4ff;
                color: #080a12;
            }
        """)
        self.phone_btn.clicked.connect(self.open_phone_pairing)
        self.btn_row.addWidget(self.phone_btn)

        # Full Mic Toggle Button
        self.mute_btn = QPushButton("🎙 Mic Active")
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e291e;
                color: #00ff88;
                border: 1.5px solid #00ff88;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00ff88;
                color: #080a12;
            }
        """)
        self.mute_btn.clicked.connect(self._toggle_mute)
        self.btn_row.addWidget(self.mute_btn)

        self.btn_row.addStretch()

        # Send Button
        self.send_btn = QPushButton("Send ↵")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
            }
        """)
        self.send_btn.clicked.connect(self.on_submit)
        self.btn_row.addWidget(self.send_btn)

        # Collapse Button
        self.collapse_btn = QPushButton("✕")
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: #aaaaaa;
                border: none;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 60, 60, 0.7);
                color: #ffffff;
            }
        """)
        self.collapse_btn.clicked.connect(self.collapse)
        self.btn_row.addWidget(self.collapse_btn)

        self.expanded_box_layout.addLayout(self.btn_row)
        self.expanded_box.hide()
        self.container_layout.addWidget(self.expanded_box)

        self.layout.addWidget(self.container)

    def _on_pulse_tick(self):
        self.container.pulse_phase += 0.1
        if self.container.pulse_phase > 2 * math.pi:
            self.container.pulse_phase -= 2 * math.pi
        self.container.update()

    def setup_hotkey(self):
        try:
            keyboard.add_hotkey("ctrl+shift+a", self.toggle_expand_safe)
        except Exception as e:
            print(f"Failed to bind hotkey: {e}")

    def reset_idle_timer(self):
        self.show()
        self.idle_timer.start(60000)

    def _on_idle_timeout(self):
        if self.is_expanded:
            self.collapse()

    # ── Mouse Drag Handlers ───────────────────────────────────────────────────

    def handle_left_click(self, event: QMouseEvent):
        self._drag_start_pos = event.globalPosition().toPoint()
        self._drag_win_pos = self.pos()
        self._dragged = False

    def handle_mouse_move(self, event: QMouseEvent):
        if self._drag_start_pos and self._drag_win_pos:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            if delta.manhattanLength() > 5:
                self._dragged = True
                self.move(self._drag_win_pos + delta)
                self.x_pos = self.x()
                self.y_pos = self.y()

    def handle_mouse_release(self, event: QMouseEvent):
        if not self._dragged:
            self.reset_idle_timer()
            # If clicked on empty space of collapsed pill, expand it
            if not self.is_expanded:
                self.expand()
        self._drag_start_pos = None
        self._drag_win_pos = None
        self._dragged = False

    def show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #12141f;
                color: #ffffff;
                border: 1.5px solid #00d4ff;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #00d4ff;
                color: #000000;
                font-weight: 600;
            }
        """)

        phone_act = menu.addAction("📱 Connect Phone (QR Code & PIN)")
        phone_act.triggered.connect(self.open_phone_pairing)

        mute_txt = "🎙 Unmute Microphone" if self._muted else "🔇 Mute Microphone"
        mute_act = menu.addAction(mute_txt)
        mute_act.triggered.connect(self._toggle_mute)

        toggle_act = menu.addAction("💬 Command Bar" if not self.is_expanded else "✕ Collapse")
        toggle_act.triggered.connect(self.toggle_expand)

        menu.addSeparator()

        exit_act = menu.addAction("❌ Exit ANSH")
        exit_act.triggered.connect(lambda: sys.exit(0))

        menu.exec(global_pos)

    def open_phone_pairing(self):
        """Pops up the Phone Pairing Dialog with real QR Code and 6-digit key."""
        self.reset_idle_timer()
        if self.on_remote_clicked:
            info = self.on_remote_clicked()
            if info:
                url, key, auto_login_url, manual = info
                dialog = PhonePairingDialog(self, url, key, auto_login_url, manual)
                dialog.exec()
                return
        QMessageBox.information(
            self,
            "Phone Connection",
            "Dashboard is starting up...\nPlease ensure main.py is running and retry.",
        )

    def toggle_expand_safe(self):
        QTimer.singleShot(0, self.reset_idle_timer)
        QTimer.singleShot(0, self.toggle_expand)

    def toggle_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def animate_size(self, width: int, height: int):
        safe_w = max(330, width)
        safe_h = max(54, height)
        screen = QApplication.primaryScreen().geometry()
        new_x = (screen.width() - safe_w) // 2

        self.size_anim = QPropertyAnimation(self, b"geometry")
        self.size_anim.setDuration(200)
        self.size_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.size_anim.setEndValue(QRect(new_x, self.y_pos, safe_w, safe_h))
        self.size_anim.start()

    def expand(self):
        self.is_expanded = True
        self.expanded_box.show()
        self.expand_btn.setText("⌃")
        self.input_field.setFocus()
        self.animate_size(self.expanded_width, self.expanded_height)

    def collapse(self):
        self.is_expanded = False
        self.expanded_box.hide()
        self.expand_btn.setText("⌄")
        self.input_field.clear()

        if getattr(self, "_current_state", "IDLE") != "SPEAKING":
            self.subtitle_label.setText(self._assistant_name)
            self.animate_size(self.base_width, self.base_height)
        else:
            self.show_subtitle(self.subtitle_label.text())

    def show_subtitle(self, text: str):
        self.reset_idle_timer()
        self.subtitle_label.setText(text)
        if not self.subtitle_label.isVisible() and text.strip():
            self.subtitle_label.show()

        if getattr(self, "_current_state", "IDLE") == "SPEAKING" and not self.is_expanded:
            if text == self._assistant_name:
                self.animate_size(self.base_width, self.base_height)
            else:
                chars = len(text)
                target_w = min(560, max(330, chars * 10 + 60))
                lines = chars // 45 + 1
                target_h = max(70, 48 + lines * 24)
                self.animate_size(target_w, target_h)

    def update_state(self, state: str):
        self.reset_idle_timer()
        self._current_state = state

        if state == "SPEAKING":
            self.status_dot.setStyleSheet("color: #00ff88; font-size: 14px; background: transparent; border: none;")
            self.show_subtitle(self.subtitle_label.text())
        elif state == "LISTENING":
            self.status_dot.setStyleSheet("color: #00f0ff; font-size: 14px; background: transparent; border: none;")
        elif state == "THINKING":
            self.status_dot.setStyleSheet("color: #b026ff; font-size: 14px; background: transparent; border: none;")
        else:
            self.status_dot.setStyleSheet("color: #00d4ff; font-size: 14px; background: transparent; border: none;")
            if not self.is_expanded:
                self.subtitle_label.setText(self._assistant_name)
                self.animate_size(self.base_width, self.base_height)

        self.container.update()

    def on_submit(self):
        self.reset_idle_timer()
        text = self.input_field.text().strip()
        if text:
            if self.on_text_command:
                threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()
            self.collapse()

    def _toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self.quick_mic_btn.setText("🔇")
            self.quick_mic_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 50, 75, 0.25);
                    color: #ff4d6d;
                    border: 1px solid rgba(255, 50, 75, 0.8);
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)
            self.mute_btn.setText("🔇 Mic Muted")
            self.mute_btn.setStyleSheet("""
                QPushButton {
                    background-color: #380e14;
                    color: #ff4d6d;
                    border: 1.5px solid #ff4d6d;
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff4d6d;
                    color: #ffffff;
                }
            """)
            self.status_dot.setStyleSheet("color: #ff3b5c; font-size: 14px; background: transparent; border: none;")
            self.subtitle_signal.emit("MUTED")
        else:
            self.quick_mic_btn.setText("🎙")
            self.quick_mic_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.1);
                    color: #00ff88;
                    border: 1px solid rgba(0, 255, 136, 0.3);
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(0, 255, 136, 0.3);
                }
            """)
            self.mute_btn.setText("🎙 Mic Active")
            self.mute_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0e291e;
                    color: #00ff88;
                    border: 1.5px solid #00ff88;
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00ff88;
                    color: #080a12;
                }
            """)
            self.status_dot.setStyleSheet("color: #00f0ff; font-size: 14px; background: transparent; border: none;")
            self.subtitle_signal.emit("LISTENING")

        self.container.update()
        self.reset_idle_timer()

    def notify_phone_connected(self):
        self.subtitle_signal.emit("📱 Phone Connected!")
        QTimer.singleShot(4000, lambda: self.subtitle_signal.emit(self._assistant_name))

    def start_camera_stream(self): pass
    def stop_camera_stream(self): pass


class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app

    def mainloop(self):
        self._app.exec()

    def protocol(self, *_):
        pass


class AnshUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = SmartIslandWindow()
        self._win.show()
        self.root = _RootShim(self._app)

        self._log_sig = pyqtSignal(str)
        self._content_sig = pyqtSignal(str, str)
        self._reconfig_sig = pyqtSignal()
        self._camera_sig = pyqtSignal(bytes)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return None

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    @property
    def on_remote_clicked(self):
        return self._win.on_remote_clicked

    @on_remote_clicked.setter
    def on_remote_clicked(self, cb):
        self._win.on_remote_clicked = cb

    @property
    def on_interrupt(self):
        return self._win.on_interrupt

    @on_interrupt.setter
    def on_interrupt(self, cb):
        self._win.on_interrupt = cb

    def notify_phone_connected(self) -> None:
        self._win.notify_phone_connected()

    def set_state(self, state: str):
        self._win.state_signal.emit(state)

    def write_log(self, text: str):
        if text.startswith("ANSH:") or text.startswith("Ansh:"):
            msg = text.split(":", 1)[1].strip()
            self._win.subtitle_signal.emit(msg)

    def wait_for_api_key(self):
        config = _read_full_config()
        changed = False

        if not config.get("api_key") and not config.get("gemini_api_key"):
            text, ok = QInputDialog.getText(
                None,
                "Welcome to ANSH",
                "First time setup: Enter your Gemini API Key:",
                QLineEdit.EchoMode.Password,
            )
            if ok and text:
                config["api_key"] = text.strip()
                config["gemini_api_key"] = text.strip()
                changed = True
            else:
                QMessageBox.critical(None, "Error", "API Key is required to run ANSH.")
                sys.exit(0)

        if not config.get("user_name"):
            text, ok = QInputDialog.getText(
                None,
                "Welcome to ANSH",
                "First time setup: What is your name?",
                QLineEdit.EchoMode.Normal,
            )
            if ok and text:
                config["user_name"] = text.strip()
                changed = True

        if changed:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            API_FILE.write_text(json.dumps(config, indent=4), encoding="utf-8")

    def show_content(self, title: str, text: str): pass
    def prompt_reconfig(self): pass
    def show_camera_frame(self, img_bytes: bytes): pass
    def start_camera_stream(self) -> None: pass
    def stop_camera_stream(self) -> None: pass

    @property
    def assistant_name(self) -> str:
        return self._win._assistant_name

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")
