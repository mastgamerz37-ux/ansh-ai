"""
core/telegram_bot.py — Telegram Remote Control Gateway for ANSH.

Allows the user to fully control their laptop from their smartphone via Telegram:
- Real-time screenshot & webcam capture
- System status & hardware telemetry (CPU, RAM, Battery, Disk)
- Media & volume control
- Windows lock, sleep, shutdown, restart
- Application launcher & process manager
- PowerShell / Command execution with live output
- Bidirectional file transfer & clipboard sync
- Desktop TTS speech & popup notifications
- Natural language AI assistant commands
"""
from __future__ import annotations

import io
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import requests

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "api_keys.json"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Config Helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[TelegramBot] ⚠️ Config load error: {e}")
    return {}


def save_config_value(key: str, value: Any) -> None:
    try:
        data = load_config()
        data[key] = value
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(data, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[TelegramBot] ⚠️ Config save error: {e}")


# ── Telegram Bot Core Client ──────────────────────────────────────────────────

class TelegramRemoteBot:
    """Lightweight, resilient Telegram Bot client using HTTP long-polling."""

    def __init__(self, token: Optional[str] = None, allowed_chat_id: Optional[str | int] = None):
        self.token = (token or "").strip()
        self.allowed_chat_id = str(allowed_chat_id).strip() if allowed_chat_id else ""
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_update_id = 0
        self._pairing_pin = ""
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def update_credentials(self, token: str, allowed_chat_id: Optional[str | int] = None) -> None:
        self.token = token.strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        if allowed_chat_id:
            self.allowed_chat_id = str(allowed_chat_id).strip()

    # ── Telegram HTTP API Methods ─────────────────────────────────────────────

    def _api_call(self, endpoint: str, data: Optional[dict] = None, files: Optional[dict] = None, timeout: int = 35) -> dict:
        if not self.token:
            return {"ok": False, "description": "No bot token configured"}
        url = f"{self.base_url}/{endpoint}"
        try:
            if files:
                r = requests.post(url, data=data, files=files, timeout=timeout)
            else:
                r = requests.post(url, json=data, timeout=timeout)
            return r.json()
        except Exception as e:
            return {"ok": False, "description": str(e)}

    def send_message(self, chat_id: str | int, text: str, reply_markup: Optional[dict] = None, parse_mode: str = "HTML") -> dict:
        # Sanitize HTML tags or chunk if message exceeds 4000 chars
        if len(text) > 4000:
            text = text[:3980] + "\n… [truncated]"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        res = self._api_call("sendMessage", data=payload)
        # Fallback to plain text if HTML parsing failed
        if not res.get("ok") and "can't parse" in res.get("description", "").lower():
            payload.pop("parse_mode", None)
            res = self._api_call("sendMessage", data=payload)
        return res

    def send_photo(self, chat_id: str | int, photo_bytes: bytes, caption: str = "", filename: str = "screen.png") -> dict:
        files = {"photo": (filename, photo_bytes, "image/png")}
        data: dict[str, Any] = {"chat_id": chat_id, "caption": caption[:1024]}
        return self._api_call("sendPhoto", data=data, files=files)

    def send_document(self, chat_id: str | int, file_bytes: bytes, filename: str, caption: str = "") -> dict:
        files = {"document": (filename, file_bytes, "application/octet-stream")}
        data: dict[str, Any] = {"chat_id": chat_id, "caption": caption[:1024]}
        return self._api_call("sendDocument", data=data, files=files)

    # ── Keyboards & Menus ─────────────────────────────────────────────────────

    def _main_keyboard(self) -> dict:
        return {
            "keyboard": [
                [{"text": "📸 Screenshot"}, {"text": "📊 Status"}, {"text": "🔒 Lock PC"}],
                [{"text": "🔊 Vol Up"}, {"text": "🔉 Vol Down"}, {"text": "🔇 Mute"}],
                [{"text": "⏯ Play/Pause"}, {"text": "📋 Clipboard"}, {"text": "❓ Help"}],
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False,
        }

    # ── Action Dispatchers ────────────────────────────────────────────────────

    def _handle_screenshot(self, chat_id: str | int) -> None:
        self.send_message(chat_id, "📸 <i>Capturing laptop screen…</i>")
        try:
            import mss
            from PIL import Image

            with mss.mss() as sct:
                # Capture primary monitor
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                shot = sct.grab(mon)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                buf.seek(0)
                now_str = datetime.now().strftime("%I:%M:%S %p")
                self.send_photo(chat_id, buf.getvalue(), caption=f"🖥️ <b>Laptop Screen</b> ({now_str})")
        except Exception as e:
            self.send_message(chat_id, f"❌ Screenshot failed: {e}")

    def _handle_webcam(self, chat_id: str | int) -> None:
        self.send_message(chat_id, "📷 <i>Capturing webcam photo…</i>")
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.send_message(chat_id, "❌ Webcam is unavailable or in use by another app.")
                return
            # Let sensor auto-expose
            for _ in range(5):
                cap.read()
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                self.send_message(chat_id, "❌ Failed to read frame from webcam.")
                return

            ret, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
            now_str = datetime.now().strftime("%I:%M:%S %p")
            self.send_photo(chat_id, buf.tobytes(), caption=f"📷 <b>Laptop Webcam</b> ({now_str})", filename="webcam.jpg")
        except Exception as e:
            self.send_message(chat_id, f"❌ Webcam error: {e}")

    def _handle_status(self, chat_id: str | int) -> None:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            bat = psutil.sensors_battery()
            uptime_secs = int(time.time() - psutil.boot_time())
            uptime_str = f"{uptime_secs // 3600}h {(uptime_secs % 3600) // 60}m"

            bat_str = "🔌 Plugged In (No battery)"
            if bat:
                plugged = "⚡ Charging" if bat.power_plugged else "🔋 On Battery"
                bat_str = f"{bat.percent}% ({plugged})"

            # Top 3 processes
            procs = []
            for p in sorted(psutil.process_iter(['name', 'cpu_percent', 'memory_percent']),
                            key=lambda x: x.info.get('cpu_percent') or 0, reverse=True)[:4]:
                pname = p.info.get('name') or 'unknown'
                pcpu = p.info.get('cpu_percent') or 0.0
                procs.append(f"• <code>{pname}</code>: {pcpu:.1f}% CPU")

            procs_str = "\n".join(procs) if procs else "• None"

            msg = (
                f"📊 <b>ANSH Laptop Telemetry</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚙️ <b>CPU Load:</b> {cpu}%\n"
                f"🧠 <b>RAM Usage:</b> {mem.percent}% ({mem.used // (1024**2)} MB / {mem.total // (1024**2)} MB)\n"
                f"💽 <b>Disk Space:</b> {disk.percent}% ({disk.free // (1024**3)} GB free)\n"
                f"🔋 <b>Power:</b> {bat_str}\n"
                f"⏱️ <b>Uptime:</b> {uptime_str}\n\n"
                f"🔥 <b>Top Processes:</b>\n{procs_str}"
            )
            self.send_message(chat_id, msg)
        except Exception as e:
            self.send_message(chat_id, f"❌ Failed to fetch telemetry: {e}")

    def _handle_lock(self, chat_id: str | int) -> None:
        try:
            if platform.system() == "Windows":
                subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
                self.send_message(chat_id, "🔒 <b>Laptop screen locked successfully!</b>")
            else:
                self.send_message(chat_id, "⚠️ Lock command is currently configured for Windows.")
        except Exception as e:
            self.send_message(chat_id, f"❌ Failed to lock: {e}")

    def _handle_sleep(self, chat_id: str | int) -> None:
        try:
            self.send_message(chat_id, "🌙 <i>Putting laptop to sleep…</i>")
            if platform.system() == "Windows":
                subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        except Exception as e:
            self.send_message(chat_id, f"❌ Sleep command failed: {e}")

    def _handle_volume(self, chat_id: str | int, action: str, level: Optional[int] = None) -> None:
        try:
            import pyautogui
            if action == "up":
                for _ in range(5):
                    pyautogui.press("volumeup")
                self.send_message(chat_id, "🔊 Volume increased (+10%)")
            elif action == "down":
                for _ in range(5):
                    pyautogui.press("volumedown")
                self.send_message(chat_id, "🔉 Volume decreased (-10%)")
            elif action == "mute":
                pyautogui.press("volumemute")
                self.send_message(chat_id, "🔇 Master volume muted/unmuted")
            elif action == "set" and level is not None:
                # Try pycaw on Windows
                try:
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, level / 100.0)), None)
                    self.send_message(chat_id, f"🔊 Master volume set to <b>{level}%</b>")
                except Exception:
                    self.send_message(chat_id, f"🔊 Volume adjustment sent.")
        except Exception as e:
            self.send_message(chat_id, f"❌ Volume control error: {e}")

    def _handle_media(self, chat_id: str | int, command: str) -> None:
        try:
            import pyautogui
            key_map = {
                "play": "playpause",
                "pause": "playpause",
                "next": "nexttrack",
                "prev": "prevtrack",
                "stop": "stop",
            }
            key = key_map.get(command, "playpause")
            pyautogui.press(key)
            self.send_message(chat_id, f"🎵 Media command <code>{command}</code> executed.")
        except Exception as e:
            self.send_message(chat_id, f"❌ Media control error: {e}")

    def _handle_open_app(self, chat_id: str | int, app_name: str) -> None:
        if not app_name:
            self.send_message(chat_id, "⚠️ Usage: <code>/open &lt;app_name&gt;</code> (e.g. <code>/open chrome</code>)")
            return
        try:
            from actions.open_app import open_app
            res = open_app(app_name)
            self.send_message(chat_id, f"🚀 <b>{res}</b>")
        except Exception as e:
            self.send_message(chat_id, f"❌ Failed to open app: {e}")

    def _handle_cmd(self, chat_id: str | int, command_text: str) -> None:
        if not command_text:
            self.send_message(chat_id, "⚠️ Usage: <code>/cmd &lt;powershell or cmd command&gt;</code>")
            return
        self.send_message(chat_id, f"⚡ <i>Running:</i> <code>{command_text}</code>")
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command_text],
                capture_output=True,
                text=True,
                timeout=25,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            res_text = out if out else (f"❌ Error:\n{err}" if err else "✅ Command executed with no output.")
            if len(res_text) > 3500:
                res_text = res_text[:3500] + "\n… [output truncated]"
            self.send_message(chat_id, f"💻 <b>Output:</b>\n<pre>{res_text}</pre>")
        except subprocess.TimeoutExpired:
            self.send_message(chat_id, "⏱️ Command timed out (exceeded 25s).")
        except Exception as e:
            self.send_message(chat_id, f"❌ Execution failed: {e}")

    def _handle_clipboard(self, chat_id: str | int, set_text: Optional[str] = None) -> None:
        try:
            import pyperclip
            if set_text is not None:
                pyperclip.copy(set_text)
                self.send_message(chat_id, "📋 <b>Text copied to laptop clipboard!</b>")
            else:
                clip = pyperclip.paste()
                if clip:
                    if len(clip) > 3000:
                        clip = clip[:3000] + "… [truncated]"
                    self.send_message(chat_id, f"📋 <b>Laptop Clipboard:</b>\n<code>{clip}</code>")
                else:
                    self.send_message(chat_id, "📋 Laptop clipboard is empty.")
        except Exception as e:
            self.send_message(chat_id, f"❌ Clipboard error: {e}")

    def _handle_say_tts(self, chat_id: str | int, text_to_say: str) -> None:
        if not text_to_say:
            self.send_message(chat_id, "⚠️ Usage: <code>/say &lt;text to speak out loud&gt;</code>")
            return
        try:
            from core.tts import play_tts_async
            play_tts_async(text_to_say)
            self.send_message(chat_id, f"🗣️ Speaking on laptop speakers: <i>\"{text_to_say}\"</i>")
        except Exception as e:
            # Fallback to pyttsx3 or SAPI
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text_to_say)
                engine.runAndWait()
                self.send_message(chat_id, f"🗣️ Spoke: <i>\"{text_to_say}\"</i>")
            except Exception as e2:
                self.send_message(chat_id, f"❌ TTS failed: {e2}")

    def _handle_notify(self, chat_id: str | int, msg_text: str) -> None:
        if not msg_text:
            self.send_message(chat_id, "⚠️ Usage: <code>/notify &lt;toast alert message&gt;</code>")
            return
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast("ANSH Remote Alert", msg_text, duration=5, threaded=True)
            self.send_message(chat_id, f"🔔 Notification shown on laptop screen: <b>{msg_text}</b>")
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, msg_text, "ANSH Notification", 0x40 | 0x1000)
                self.send_message(chat_id, "🔔 Alert box displayed.")
            except Exception as e:
                self.send_message(chat_id, f"❌ Toast failed: {e}")

    def _handle_getfile(self, chat_id: str | int, file_path_str: str) -> None:
        if not file_path_str:
            self.send_message(chat_id, "⚠️ Usage: <code>/getfile &lt;full_file_path&gt;</code>")
            return
        p = Path(file_path_str.strip('"').strip("'"))
        if not p.exists() or not p.is_file():
            self.send_message(chat_id, f"❌ File not found: <code>{p}</code>")
            return
        if p.stat().st_size > 48 * 1024 * 1024:
            self.send_message(chat_id, "❌ File is larger than 48MB (Telegram Bot API limit).")
            return
        self.send_message(chat_id, f"📤 <i>Sending {p.name}…</i>")
        try:
            data = p.read_bytes()
            self.send_document(chat_id, data, filename=p.name, caption=f"📁 File: {p.name}")
        except Exception as e:
            self.send_message(chat_id, f"❌ Failed to send file: {e}")

    def _handle_natural_ai_command(self, chat_id: str | int, prompt: str) -> None:
        """Processes plain text user command via ANSH's dual AI engine."""
        self.send_message(chat_id, "🤖 <i>Processing with ANSH AI…</i>")
        try:
            from core.task_llm import ask_task_llm
            system_prompt = (
                "You are ANSH, an advanced AI controlling the user's laptop remotely via Telegram.\n"
                "The user is messaging you from their phone.\n"
                "Respond concisely, clearly, and directly.\n"
                "If the user is asking you to perform a task, explain what was done or provide the direct answer."
            )
            response = ask_task_llm(prompt=prompt, system=system_prompt, temperature=0.5)
            self.send_message(chat_id, f"🤖 <b>ANSH:</b>\n\n{response}")
        except Exception as e:
            self.send_message(chat_id, f"❌ AI processing error: {e}")

    # ── Incoming Message Router ───────────────────────────────────────────────

    def process_message(self, message: dict) -> None:
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        user_name = message.get("from", {}).get("first_name", "User")
        text = (message.get("text") or "").strip()

        # Handle File / Document Download
        if "document" in message or "photo" in message:
            if self.allowed_chat_id and str(self.allowed_chat_id) != chat_id:
                return
            self._handle_incoming_file(chat_id, message)
            return

        if not text:
            return

        # ── Pairing Security Check ──
        if not self.allowed_chat_id:
            # First time setup / Pairing mode
            if text.startswith("/start") or text.startswith("/pair"):
                self.allowed_chat_id = chat_id
                save_config_value("telegram_chat_id", chat_id)
                self.send_message(
                    chat_id,
                    f"🎉 <b>Pairing Successful, {user_name}!</b>\n\n"
                    f"Your phone is now securely paired with ANSH Laptop Remote Control.\n"
                    f"Chat ID: <code>{chat_id}</code> saved.\n\n"
                    f"Type /help to see all available remote commands.",
                    reply_markup=self._main_keyboard()
                )
                return
            else:
                self.send_message(
                    chat_id,
                    "🔒 <b>ANSH Security Gate</b>\n\n"
                    "This bot is waiting to pair with its owner.\n"
                    "Send <code>/start</code> or <code>/pair</code> to link your Telegram account."
                )
                return

        # Verify chat_id against configured allowed owner
        if str(self.allowed_chat_id) != chat_id:
            print(f"[TelegramBot] ⚠️ Blocked unauthorized access attempt from chat_id={chat_id}")
            self.send_message(chat_id, "⛔ <b>Access Denied</b>: You are not authorized to control this laptop.")
            return

        # ── Commands Routing ──
        cmd = text.split()[0].lower()
        args = text[len(cmd):].strip()

        if cmd in ("/start", "/help", "❓ help"):
            help_msg = (
                f"👋 <b>Welcome to ANSH Remote Control</b>\n\n"
                f"<b>📸 Vision & Screen:</b>\n"
                f"• <code>/screen</code> or <code>/screenshot</code> — Live laptop screen photo\n"
                f"• <code>/cam</code> or <code>/webcam</code> — Live webcam snapshot\n\n"
                f"<b>⚡ System & Power:</b>\n"
                f"• <code>/status</code> — CPU, RAM, Battery, Top procs\n"
                f"• <code>/lock</code> — Lock laptop screen\n"
                f"• <code>/sleep</code> — Put laptop to sleep\n\n"
                f"<b>🔊 Audio & Media:</b>\n"
                f"• <code>/vol &lt;0-100&gt;</code>, <code>/vol up</code>, <code>/vol down</code>, <code>/mute</code>\n"
                f"• <code>/play</code>, <code>/next</code>, <code>/prev</code> — Media controls\n\n"
                f"<b>🚀 Apps & Commands:</b>\n"
                f"• <code>/open &lt;app&gt;</code> — E.g. <code>/open chrome</code>, <code>/open spotify</code>\n"
                f"• <code>/cmd &lt;command&gt;</code> — Run PowerShell commands\n\n"
                f"<b>📁 File & Clipboard:</b>\n"
                f"• <code>/clip</code> or <code>/setclip &lt;text&gt;</code> — Clipboard sync\n"
                f"• <code>/getfile &lt;path&gt;</code> — Download file from PC\n"
                f"• Send any document/photo to save it directly to laptop!\n\n"
                f"<b>🗣️ Voice & Alerts:</b>\n"
                f"• <code>/say &lt;text&gt;</code> — Speak aloud on laptop\n"
                f"• <code>/notify &lt;text&gt;</code> — Desktop toast alert\n\n"
                f"💡 <i>Or just type any question/command in plain English or Hindi!</i>"
            )
            self.send_message(chat_id, help_msg, reply_markup=self._main_keyboard())

        elif cmd in ("/screen", "/screenshot", "📸 screenshot"):
            self._handle_screenshot(chat_id)

        elif cmd in ("/cam", "/webcam", "📷 webcam"):
            self._handle_webcam(chat_id)

        elif cmd in ("/status", "/stats", "📊 status"):
            self._handle_status(chat_id)

        elif cmd in ("/lock", "🔒 lock pc"):
            self._handle_lock(chat_id)

        elif cmd in ("/sleep", "🌙 sleep"):
            self._handle_sleep(chat_id)

        elif cmd in ("/vol", "🔊 vol up", "🔉 vol down", "🔇 mute"):
            if "up" in text.lower():
                self._handle_volume(chat_id, "up")
            elif "down" in text.lower():
                self._handle_volume(chat_id, "down")
            elif "mute" in text.lower():
                self._handle_volume(chat_id, "mute")
            elif args.isdigit():
                self._handle_volume(chat_id, "set", level=int(args))
            else:
                self.send_message(chat_id, "⚠️ Usage: <code>/vol up</code>, <code>/vol down</code>, <code>/vol 50</code>, <code>/mute</code>")

        elif cmd in ("/play", "/pause", "/playpause", "⏯ play/pause"):
            self._handle_media(chat_id, "play")
        elif cmd == "/next":
            self._handle_media(chat_id, "next")
        elif cmd == "/prev":
            self._handle_media(chat_id, "prev")

        elif cmd == "/open":
            self._handle_open_app(chat_id, args)

        elif cmd in ("/cmd", "/ps", "/exec"):
            self._handle_cmd(chat_id, args)

        elif cmd in ("/clip", "/clipboard", "📋 clipboard"):
            self._handle_clipboard(chat_id)

        elif cmd == "/setclip":
            self._handle_clipboard(chat_id, set_text=args)

        elif cmd in ("/say", "/tts", "/speak"):
            self._handle_say_tts(chat_id, args)

        elif cmd in ("/notify", "/toast", "/alert"):
            self._handle_notify(chat_id, args)

        elif cmd in ("/getfile", "/download"):
            self._handle_getfile(chat_id, args)

        else:
            # Plain text -> AI Assistant Command
            self._handle_natural_ai_command(chat_id, text)

    def _handle_incoming_file(self, chat_id: str | int, message: dict) -> None:
        try:
            file_id = ""
            orig_name = "received_file"
            if "document" in message:
                file_id = message["document"]["file_id"]
                orig_name = message["document"].get("file_name", "received_file")
            elif "photo" in message:
                file_id = message["photo"][-1]["file_id"]
                orig_name = f"photo_{int(time.time())}.jpg"

            if not file_id:
                return

            self.send_message(chat_id, f"📥 <i>Saving {orig_name} to laptop…</i>")
            # Get file path from Telegram
            file_info = self._api_call("getFile", data={"file_id": file_id})
            if not file_info.get("ok"):
                self.send_message(chat_id, "❌ Failed to retrieve file info from Telegram.")
                return

            telegram_file_path = file_info["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{self.token}/{telegram_file_path}"

            r = requests.get(download_url, timeout=45)
            save_dest = UPLOAD_DIR / orig_name
            save_dest.write_bytes(r.content)

            self.send_message(
                chat_id,
                f"✅ <b>File saved on laptop:</b>\n<code>{save_dest}</code>\n"
                f"Size: {len(r.content) // 1024} KB"
            )
        except Exception as e:
            self.send_message(chat_id, f"❌ Failed to save incoming file: {e}")

    # ── Long-Polling Loop ─────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        print("[TelegramBot] 🚀 Telegram Remote Control polling started.")
        while self._running:
            try:
                if not self.token:
                    time.sleep(3)
                    continue

                updates = self._api_call("getUpdates", data={
                    "offset": self._last_update_id + 1,
                    "timeout": 20,
                    "allowed_updates": ["message", "callback_query"]
                }, timeout=25)

                if updates.get("ok") and updates.get("result"):
                    for item in updates["result"]:
                        self._last_update_id = item["update_id"]
                        if "message" in item:
                            threading.Thread(target=self.process_message, args=(item["message"],), daemon=True).start()
            except Exception as e:
                # Sleep briefly on network glitches
                time.sleep(2.5)

    def start(self) -> bool:
        if self._running:
            return True
        if not self.token:
            print("[TelegramBot] ⚠️ No Telegram bot token configured.")
            return False
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False


# ── Global Singleton Instance ─────────────────────────────────────────────────

_global_bot: Optional[TelegramRemoteBot] = None


def get_telegram_bot() -> TelegramRemoteBot:
    global _global_bot
    if _global_bot is None:
        cfg = load_config()
        token = cfg.get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN") or ""
        chat_id = cfg.get("telegram_chat_id") or os.environ.get("TELEGRAM_CHAT_ID") or ""
        _global_bot = TelegramRemoteBot(token=token, allowed_chat_id=chat_id)
    return _global_bot


def start_telegram_bot_service() -> bool:
    bot = get_telegram_bot()
    cfg = load_config()
    token = cfg.get("telegram_bot_token") or ""
    chat_id = cfg.get("telegram_chat_id") or ""
    if token:
        bot.update_credentials(token, chat_id)
        return bot.start()
    return False
