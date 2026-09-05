"""
dashboard/screen_streamer.py — High-Performance Screen Streaming & Remote Input Controller

Provides low-latency MJPEG streaming and real-time mouse/keyboard/system control
from remote devices (phones/tablets/browsers).
"""

import asyncio
import io
import os
import platform
import subprocess
import sys
import time
from typing import AsyncGenerator, Optional, Tuple

try:
    import mss
    _MSS_OK = True
except ImportError:
    _MSS_OK = False

try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Avoid exceptions when moving to corners via remote
    pyautogui.PAUSE = 0.001     # Ultra-fast remote input response
    _PUI_OK = True
except ImportError:
    _PUI_OK = False

_IS_WIN = platform.system() == "Windows"
_IS_MAC = platform.system() == "Darwin"
_IS_LINUX = platform.system() == "Linux"


class ScreenStreamer:
    """Manages live screen frame capture, compression, and remote input handling."""

    def __init__(self):
        self._last_frame_bytes: Optional[bytes] = None
        self._last_capture_time: float = 0.0
        self._mss_instance = None

    def get_screen_size(self) -> Tuple[int, int]:
        if _PUI_OK:
            try:
                w, h = pyautogui.size()
                return int(w), int(h)
            except Exception:
                pass
        return 1920, 1080

    def capture_frame_jpeg(self, quality: int = 55, scale: float = 0.65) -> bytes:
        """Captures the primary monitor and returns JPEG bytes."""
        screen_img = None

        if _MSS_OK:
            try:
                if self._mss_instance is None:
                    _mss_cls = getattr(mss, "MSS", None) or mss.mss
                    self._mss_instance = _mss_cls()
                monitor = self._mss_instance.monitors[1] if len(self._mss_instance.monitors) > 1 else self._mss_instance.monitors[0]
                sct_img = self._mss_instance.grab(monitor)
                if _PIL_OK:
                    # Convert BGRA to RGB
                    screen_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                self._mss_instance = None  # Reset in case of display reconfiguration

        if screen_img is None and _PUI_OK:
            try:
                screen_img = pyautogui.screenshot()
            except Exception:
                pass

        if screen_img is None:
            # Fallback black dummy frame
            if _PIL_OK:
                screen_img = Image.new("RGB", (640, 360), color=(15, 18, 28))
            else:
                return b""

        # Scale down for network efficiency
        if scale < 0.99:
            w = max(320, int(screen_img.width * scale))
            h = max(180, int(screen_img.height * scale))
            screen_img = screen_img.resize((w, h), Image.Resampling.BILINEAR)

        buf = io.BytesIO()
        screen_img.save(buf, format="JPEG", quality=quality, optimize=False)
        self._last_frame_bytes = buf.getvalue()
        self._last_capture_time = time.time()
        return self._last_frame_bytes

    async def generate_mjpeg_stream(
        self,
        fps: int = 15,
        quality: int = 50,
        scale: float = 0.60
    ) -> AsyncGenerator[bytes, None]:
        """Yields multipart MJPEG stream frames."""
        frame_interval = 1.0 / max(1, min(fps, 30))
        while True:
            t0 = time.time()
            try:
                # Capture frame in executor so event loop isn't blocked
                loop = asyncio.get_running_loop()
                frame = await loop.run_in_executor(None, self.capture_frame_jpeg, quality, scale)
                
                header = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame)).encode("ascii") + b"\r\n\r\n"
                )
                yield header + frame + b"\r\n"
            except Exception:
                await asyncio.sleep(0.1)
                continue

            elapsed = time.time() - t0
            sleep_time = max(0.01, frame_interval - elapsed)
            await asyncio.sleep(sleep_time)

    # ── Remote Mouse Handlers ─────────────────────────────────────────────────

    def handle_mouse(self, action: str, data: dict) -> dict:
        if not _PUI_OK:
            return {"ok": False, "error": "pyautogui is not installed"}

        sw, sh = self.get_screen_size()
        try:
            if action == "move_abs":
                # Absolute percentage coordinates (0.0 to 1.0)
                x_pct = float(data.get("x_pct", 0.5))
                y_pct = float(data.get("y_pct", 0.5))
                target_x = max(0, min(sw - 1, int(x_pct * sw)))
                target_y = max(0, min(sh - 1, int(y_pct * sh)))
                pyautogui.moveTo(target_x, target_y)
                return {"ok": True, "x": target_x, "y": target_y}

            elif action == "move_rel":
                # Relative delta (e.g. from trackpad swipe)
                dx = float(data.get("dx", 0))
                dy = float(data.get("dy", 0))
                speed = float(data.get("speed", 1.0))
                pyautogui.moveRel(int(dx * speed), int(dy * speed))
                return {"ok": True}

            elif action == "click":
                btn = str(data.get("button", "left")).lower()
                if "x_pct" in data and "y_pct" in data:
                    x_pct = float(data.get("x_pct", 0.5))
                    y_pct = float(data.get("y_pct", 0.5))
                    target_x = max(0, min(sw - 1, int(x_pct * sw)))
                    target_y = max(0, min(sh - 1, int(y_pct * sh)))
                    pyautogui.click(target_x, target_y, button=btn)
                else:
                    pyautogui.click(button=btn)
                return {"ok": True}

            elif action == "double_click":
                if "x_pct" in data and "y_pct" in data:
                    x_pct = float(data.get("x_pct", 0.5))
                    y_pct = float(data.get("y_pct", 0.5))
                    target_x = max(0, min(sw - 1, int(x_pct * sw)))
                    target_y = max(0, min(sh - 1, int(y_pct * sh)))
                    pyautogui.doubleClick(target_x, target_y)
                else:
                    pyautogui.doubleClick()
                return {"ok": True}

            elif action == "right_click":
                if "x_pct" in data and "y_pct" in data:
                    x_pct = float(data.get("x_pct", 0.5))
                    y_pct = float(data.get("y_pct", 0.5))
                    target_x = max(0, min(sw - 1, int(x_pct * sw)))
                    target_y = max(0, min(sh - 1, int(y_pct * sh)))
                    pyautogui.rightClick(target_x, target_y)
                else:
                    pyautogui.rightClick()
                return {"ok": True}

            elif action == "mouse_down":
                btn = str(data.get("button", "left")).lower()
                pyautogui.mouseDown(button=btn)
                return {"ok": True}

            elif action == "mouse_up":
                btn = str(data.get("button", "left")).lower()
                pyautogui.mouseUp(button=btn)
                return {"ok": True}

            elif action == "scroll":
                dy = int(data.get("dy", 0))
                # dy positive = scroll down in touch, negative = scroll up
                scroll_amount = -int(dy)
                pyautogui.scroll(scroll_amount)
                return {"ok": True}

            return {"ok": False, "error": f"Unknown mouse action '{action}'"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Remote Keyboard Handlers ──────────────────────────────────────────────

    def handle_keyboard(self, action: str, data: dict) -> dict:
        if not _PUI_OK:
            return {"ok": False, "error": "pyautogui is not installed"}

        try:
            if action == "type":
                text = str(data.get("text", ""))
                if text:
                    # Write with small delay
                    pyautogui.write(text, interval=0.01)
                return {"ok": True}

            elif action == "press":
                key = str(data.get("key", "")).lower()
                key_map = {
                    "enter": "enter",
                    "return": "enter",
                    "backspace": "backspace",
                    "delete": "delete",
                    "del": "delete",
                    "escape": "esc",
                    "esc": "esc",
                    "tab": "tab",
                    "space": "space",
                    "up": "up",
                    "down": "down",
                    "left": "left",
                    "right": "right",
                    "win": "win" if _IS_WIN else "command",
                    "cmd": "command" if _IS_MAC else "win",
                    "super": "win" if _IS_WIN else "command",
                    "home": "home",
                    "end": "end",
                    "pageup": "pageup",
                    "pagedown": "pagedown",
                    "f5": "f5",
                    "f11": "f11",
                }
                actual_key = key_map.get(key, key)
                pyautogui.press(actual_key)
                return {"ok": True, "pressed": actual_key}

            elif action == "hotkey":
                keys = data.get("keys", [])
                if isinstance(keys, str):
                    keys = [k.strip() for k in keys.split("+")]
                if keys:
                    pyautogui.hotkey(*keys)
                return {"ok": True, "hotkey": keys}

            return {"ok": False, "error": f"Unknown keyboard action '{action}'"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── System Power & Quick Actions ──────────────────────────────────────────

    def handle_system_action(self, action: str, value: Optional[str] = None) -> dict:
        try:
            if action == "volume_up":
                if _IS_WIN:
                    subprocess.run(["powershell", "-c", "$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys([char]175)"], check=False)
                elif _IS_MAC:
                    subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 10)"], check=False)
                elif _IS_LINUX:
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"], check=False)
                return {"ok": True, "action": "volume_up"}

            elif action == "volume_down":
                if _IS_WIN:
                    subprocess.run(["powershell", "-c", "$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys([char]174)"], check=False)
                elif _IS_MAC:
                    subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 10)"], check=False)
                elif _IS_LINUX:
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"], check=False)
                return {"ok": True, "action": "volume_down"}

            elif action == "volume_mute":
                if _IS_WIN:
                    subprocess.run(["powershell", "-c", "$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys([char]173)"], check=False)
                elif _IS_MAC:
                    subprocess.run(["osascript", "-e", "set volume output muted (not (output muted of (get volume settings)))"], check=False)
                elif _IS_LINUX:
                    subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"], check=False)
                return {"ok": True, "action": "volume_mute"}

            elif action == "media_play_pause":
                if _PUI_OK:
                    pyautogui.press("playpause")
                return {"ok": True}

            elif action == "media_next":
                if _PUI_OK:
                    pyautogui.press("nexttrack")
                return {"ok": True}

            elif action == "media_prev":
                if _PUI_OK:
                    pyautogui.press("prevtrack")
                return {"ok": True}

            elif action == "lock":
                if _IS_WIN:
                    import ctypes
                    ctypes.windll.user32.LockWorkStation()
                elif _IS_MAC:
                    subprocess.run(["pmset", "displaysleepnow"], check=False)
                elif _IS_LINUX:
                    subprocess.run(["xdg-screensaver", "lock"], check=False)
                return {"ok": True, "action": "lock"}

            elif action == "sleep":
                if _IS_WIN:
                    subprocess.run(["rundll32.exe", "powrfprof.dll,SetSuspendState", "0,1,0"], check=False)
                elif _IS_MAC:
                    subprocess.run(["pmset", "sleepnow"], check=False)
                elif _IS_LINUX:
                    subprocess.run(["systemctl", "suspend"], check=False)
                return {"ok": True, "action": "sleep"}

            elif action == "shutdown":
                if _IS_WIN:
                    subprocess.run(["shutdown", "/s", "/t", "10"], check=False)
                elif _IS_MAC or _IS_LINUX:
                    subprocess.run(["shutdown", "-h", "+1"], check=False)
                return {"ok": True, "action": "shutdown_scheduled"}

            elif action == "restart":
                if _IS_WIN:
                    subprocess.run(["shutdown", "/r", "/t", "10"], check=False)
                elif _IS_MAC or _IS_LINUX:
                    subprocess.run(["shutdown", "-r", "+1"], check=False)
                return {"ok": True, "action": "restart_scheduled"}

            return {"ok": False, "error": f"Unknown system action '{action}'"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# Singleton instance
streamer = ScreenStreamer()
