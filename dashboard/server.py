"""
dashboard/server.py — Ansh Full-Featured Local HTTP Dashboard & Remote Control Server

Features:
- Plain HTTP on port 8000 + TLS alias on port 8001
- Live PC Screen Streaming (Low-latency MJPEG) & Remote Touch/Mouse/Keyboard Controller
- Live System Telemetry (CPU, RAM, GPU, Battery, Storage, Temp, Top Processes)
- Universal 2-Way Clipboard Sync
- Quick App Launcher & Process Management
- Automation & Multi-Step Workflow Engine
- Cross-Device Phone Hub & Android Gateway (Find My Phone, Intents, Battery Sync)
- Real-Time Voice Audio / Chat Feed & Gemini Live Bridge
"""

import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import socket
import string
import sys
import time
from pathlib import Path
from typing import Optional

_DEPS_OK = False
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, Response
    import uvicorn
    _DEPS_OK = True
except ImportError:
    pass

# python-multipart is required for file uploads
_UPLOAD_OK = False
try:
    from fastapi import UploadFile, File as FastAPIFile
    _UPLOAD_OK = True
except Exception:
    pass

BASE_DIR    = Path(__file__).resolve().parent.parent
STATIC_DIR  = Path(__file__).parent / "static"
PORT        = 8000
MAX_UPLOAD_MB = 500


def _make_uploads_dir() -> Path:
    """Return (and create) the cross-platform uploads folder."""
    for candidate in [
        Path.home() / "Downloads" / "ANSH Uploads",
        Path.home() / "Documents" / "ANSH Uploads",
        BASE_DIR / "uploads",
    ]:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            pass
    return BASE_DIR / "uploads"


UPLOADS_DIR = _make_uploads_dir()

def _get_gemini_key() -> str | None:
    try:
        import json as _json
        with open(BASE_DIR / "config" / "api_keys.json", "r", encoding="utf-8") as f:
            return _json.load(f).get("gemini_api_key")
    except Exception:
        return None

_KEY_CHARS = [c for c in (string.ascii_uppercase + string.digits)
              if c not in ('O', 'I', 'L', '0', '1')]

# ── AES-256-CBC ───────────────────────────────────────────────────────────────
_AES_SALT = b'ANSH-DASHBOARD-v1'


def _derive_key(session_key: str) -> bytes:
    """SHA-256(sessionKey‖salt) → 32-byte AES-256 key."""
    return hashlib.sha256(session_key.encode('utf-8') + _AES_SALT).digest()


def _decrypt_cbc(aes_key: bytes, enc_b64: str) -> str:
    """Decrypt base64(IV[16] ‖ ciphertext) with AES-256-CBC + PKCS7."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_pad
    raw      = base64.b64decode(enc_b64)
    iv, ct   = raw[:16], raw[16:]
    dec      = Cipher(algorithms.AES(aes_key), modes.CBC(iv)).decryptor()
    padded   = dec.update(ct) + dec.finalize()
    unpadder = sym_pad.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode('utf-8')


# ── CryptoJS (auto-download once, served locally) ─────────────────────────────
_CRYPTOJS_CDN  = ("https://cdnjs.cloudflare.com/ajax/libs/"
                  "crypto-js/4.2.0/crypto-js.min.js")
_CRYPTOJS_FILE = STATIC_DIR / "crypto-js.min.js"


def _ensure_network_access(port: int) -> None:
    """Cross-platform: open port in the OS firewall for LAN access."""
    import subprocess, tempfile, threading

    if sys.platform == "win32":
        import ctypes

        port_rule = f"ANSH Dashboard Port {port}"
        prog_rule = "ANSH Dashboard Python"
        py_exe    = sys.executable

        def _netsh_rule_exists(name: str) -> bool:
            try:
                r = subprocess.run(
                    ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name}"],
                    capture_output=True, text=True, timeout=5,
                )
                return r.returncode == 0 and "No rules match" not in r.stdout
            except Exception:
                return False

        if _netsh_rule_exists(port_rule) and _netsh_rule_exists(prog_rule):
            return

        bat_lines = [
            "@echo off",
            f'netsh advfirewall firewall add rule name="{port_rule}" protocol=TCP dir=in localport={port} action=allow',
            f'netsh advfirewall firewall add rule name="{prog_rule}" dir=in action=allow program="{py_exe}" enable=yes'
        ]
        bat_body = "\r\n".join(bat_lines) + "\r\n"
        fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="ansh_fw_")
        try:
            os.write(fd, bat_body.encode("mbcs"))
            os.close(fd)
            r = subprocess.run([bat_path], capture_output=True, timeout=8, shell=True)
            if r.returncode == 0:
                os.unlink(bat_path)
                return
        except Exception:
            pass

        try:
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", bat_path, None, None, 0)
            if int(ret) > 32:
                time.sleep(2)
        except Exception:
            pass
        finally:
            def _cleanup(path: str) -> None:
                time.sleep(5)
                try:
                    os.unlink(path)
                except Exception:
                    pass
            threading.Thread(target=_cleanup, args=(bat_path,), daemon=True).start()


def _ensure_crypto_js() -> None:
    if _CRYPTOJS_FILE.exists():
        return
    try:
        import urllib.request
        urllib.request.urlretrieve(_CRYPTOJS_CDN, str(_CRYPTOJS_FILE))
    except Exception:
        pass


_ensure_crypto_js()


def _local_ip() -> str:
    """Return best LAN IPv4 address."""
    for probe in ("8.8.8.8", "1.1.1.1", "192.168.1.1"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect((probe, 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith("127."):
                return ip
        except Exception:
            pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


def _read(name: str) -> str:
    f = STATIC_DIR / name
    if f.exists():
        return f.read_text(encoding="utf-8")
    return ""


QUICK_APPS = [
    {"id": "chrome", "name": "Google Chrome", "icon": "🌐", "target": "chrome"},
    {"id": "vscode", "name": "VS Code", "icon": "💻", "target": "Code"},
    {"id": "spotify", "name": "Spotify", "icon": "🎵", "target": "spotify"},
    {"id": "explorer", "name": "File Explorer", "icon": "📁", "target": "explorer"},
    {"id": "terminal", "name": "Terminal", "icon": "⌨️", "target": "cmd"},
    {"id": "whatsapp", "name": "WhatsApp", "icon": "💬", "target": "whatsapp"},
    {"id": "taskmgr", "name": "Task Manager", "icon": "📊", "target": "taskmgr"},
    {"id": "notepad", "name": "Notepad", "icon": "📝", "target": "notepad"},
    {"id": "calculator", "name": "Calculator", "icon": "🔢", "target": "calc"},
    {"id": "settings", "name": "Settings", "icon": "⚙️", "target": "ms-settings:"},
]


# ── DashboardServer ───────────────────────────────────────────────────────────

class DashboardServer:

    def __init__(self):
        self._ip                          = _local_ip()
        self._tokens: set[str]            = set()
        self._token_keys: dict[str, str]  = {}   # auth_token → session_key
        self._aes_cache:  dict[str, bytes]= {}   # session_key → AES bytes
        self._clients: set[WebSocket]     = set()
        self._history: list[dict]         = []
        self._command_queue               = asyncio.Queue()
        self._wake_callback               = None
        self._connect_callback            = None
        self._pending_keys: dict[str, float] = {}
        self._device_sessions: dict[str, dict] = {}  # device_token → {session_key}
        self._phone_audio_queue: asyncio.Queue    = asyncio.Queue(maxsize=200)
        self._uploads_dir                 = UPLOADS_DIR
        self._login_html                  = _read("login.html")
        self._app_html                    = _read("app.html")
        self.app                          = self._build_app()

    def new_key(self, expiry_secs: int = 600) -> str:
        now = time.time()
        self._pending_keys = {k: v for k, v in self._pending_keys.items() if v > now}
        key = ''.join(secrets.choice(_KEY_CHARS) for _ in range(6))
        self._pending_keys[key] = now + expiry_secs
        return key

    @staticmethod
    def _ssl_enabled() -> bool:
        certs = BASE_DIR / "config" / "certs"
        return (certs / "ansh.key").exists() and (certs / "ansh.crt").exists()

    def get_url(self) -> str:
        proto = "https" if self._ssl_enabled() else "http"
        return f"{proto}://{self._ip}:{PORT}"

    def get_manual_url(self) -> str:
        if self._ssl_enabled():
            return f"{self._ip}:{PORT + 1}"
        return f"{self._ip}:{PORT}"

    def _aes_key(self, session_key: str) -> bytes:
        if session_key not in self._aes_cache:
            self._aes_cache[session_key] = _derive_key(session_key)
        return self._aes_cache[session_key]

    def _decrypt(self, token: str, enc_b64: str) -> str | None:
        sk = self._token_keys.get(token)
        if not sk:
            return None
        try:
            return _decrypt_cbc(self._aes_key(sk), enc_b64)
        except Exception:
            return None

    def set_wake_callback(self, fn) -> None:
        self._wake_callback = fn

    def set_connect_callback(self, fn) -> None:
        self._connect_callback = fn

    async def broadcast(self, msg: dict) -> None:
        self._history.append(msg)
        if len(self._history) > 300:
            self._history = self._history[-300:]
        dead: set[WebSocket] = set()
        for ws in list(self._clients):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    # ── Build FastAPI App with All Core & Remote Endpoints ────────────────────

    def _build_app(self) -> "FastAPI":
        app = FastAPI(title="Ansh AI Command Center", docs_url=None, redoc_url=None)

        def _auth(req: Request) -> bool:
            """Permissive for localhost, token-authenticated for LAN/remote."""
            client_host = req.client.host if req.client else ""
            if client_host in ("127.0.0.1", "::1", "localhost"):
                return True
            tok = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            if not tok:
                tok = req.query_params.get("token", "").strip()
            return bool(tok) and tok in self._tokens

        @app.get("/static/crypto.js")
        async def serve_crypto():
            if _CRYPTOJS_FILE.exists():
                return FileResponse(str(_CRYPTOJS_FILE), media_type="application/javascript")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(_CRYPTOJS_CDN)

        @app.get("/login", response_class=HTMLResponse)
        async def login_page():
            return HTMLResponse(self._login_html)

        @app.get("/", response_class=HTMLResponse)
        async def index():
            html = (self._app_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.post("/login")
        async def login(req: Request):
            body    = await req.json()
            entered = str(body.get("pin", "")).strip().upper()
            now     = time.time()
            if entered in self._pending_keys and self._pending_keys[entered] > now:
                del self._pending_keys[entered]
                tok = secrets.token_urlsafe(32)
                self._tokens.add(tok)
                self._token_keys[tok] = entered
                self._aes_key(entered)
                if self._connect_callback:
                    self._connect_callback()
                asyncio.create_task(self.broadcast(
                    {"type": "sys", "text": "Remote connection established."}
                ))
                return JSONResponse({"ok": True, "token": tok})
            return JSONResponse({"ok": False, "error": "Invalid or expired key"}, status_code=401)

        @app.get("/auto-login")
        async def auto_login(key: str = ""):
            now = time.time()
            if not key or key not in self._pending_keys or self._pending_keys[key] <= now:
                return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>body{background:#07090f;color:#dde3ed;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}h2{color:#f87171;margin-bottom:12px}p{color:#5e6a7e;font-size:14px}</style></head>
<body><div><h2>Link Expired</h2><p>Press <strong style="color:#dde3ed">Remote Control</strong> in ANSH to get a new QR code.</p></div></body></html>""")

            del self._pending_keys[key]
            tok     = secrets.token_urlsafe(32)
            dev_tok = secrets.token_urlsafe(32)
            self._tokens.add(tok)
            self._token_keys[tok] = key
            self._aes_key(key)
            self._device_sessions[dev_tok] = {"session_key": key}

            if self._connect_callback:
                self._connect_callback()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Remote connection established via QR code."}
            ))

            return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>body{{background:#07090f;color:#dde3ed;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}}p{{color:#5e6a7e;font-size:14px}}</style></head>
<body>
<script>
  sessionStorage.setItem('ansh_token','{tok}');
  sessionStorage.setItem('ansh_key','{key}');
  localStorage.setItem('ansh_device_token','{dev_tok}');
  setTimeout(function(){{location.replace('/')}},400);
</script>
<p>Connecting to ANSH…</p>
</body></html>""")

        @app.post("/api/device-login")
        async def device_login_ep(req: Request):
            try:
                body = await req.json()
            except Exception:
                return JSONResponse({"ok": False}, status_code=400)
            dev_tok = (body.get("device_token") or "").strip()
            if not dev_tok or dev_tok not in self._device_sessions:
                return JSONResponse({"ok": False}, status_code=401)
            session_key = self._device_sessions[dev_tok]["session_key"]
            tok = secrets.token_urlsafe(32)
            self._tokens.add(tok)
            self._token_keys[tok] = session_key
            self._aes_key(session_key)
            if self._connect_callback:
                self._connect_callback()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Known device reconnected automatically."}
            ))
            return JSONResponse({"ok": True, "token": tok, "key": session_key})

        @app.post("/api/command")
        async def command(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body  = await req.json()
            token = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            enc   = body.get("enc", "")
            if enc:
                text = self._decrypt(token, enc)
                if text is None:
                    return JSONResponse({"error": "Decryption failed"}, status_code=400)
            else:
                text = (body.get("text") or "").strip()
            if text:
                await self._command_queue.put(text)
                if self._wake_callback:
                    self._wake_callback()
            return JSONResponse({"ok": True})

        @app.post("/api/wake")
        async def wake_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            if self._wake_callback:
                self._wake_callback()
            return JSONResponse({"ok": True})

        # ── Live Screen Streaming ─────────────────────────────────────────────
        @app.get("/api/screen/stream")
        async def stream_screen(req: Request, fps: int = 15, quality: int = 55, scale: float = 0.65):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from dashboard.screen_streamer import streamer
            return StreamingResponse(
                streamer.generate_mjpeg_stream(fps=fps, quality=quality, scale=scale),
                media_type="multipart/x-mixed-replace; boundary=frame"
            )

        @app.get("/api/screen/frame")
        async def get_screen_frame(req: Request, quality: int = 65, scale: float = 0.70):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from dashboard.screen_streamer import streamer
            loop = asyncio.get_running_loop()
            frame = await loop.run_in_executor(None, streamer.capture_frame_jpeg, quality, scale)
            return Response(content=frame, media_type="image/jpeg")

        # ── Remote Input Controller ───────────────────────────────────────────
        @app.post("/api/remote/mouse")
        async def remote_mouse(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            action = body.get("action", "click")
            data = body.get("data", {})
            from dashboard.screen_streamer import streamer
            res = streamer.handle_mouse(action, data)
            return JSONResponse(res)

        @app.post("/api/remote/keyboard")
        async def remote_keyboard(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            action = body.get("action", "press")
            data = body.get("data", {})
            from dashboard.screen_streamer import streamer
            res = streamer.handle_keyboard(action, data)
            return JSONResponse(res)

        @app.post("/api/remote/system")
        async def remote_system(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            action = body.get("action", "")
            value = body.get("value")
            from dashboard.screen_streamer import streamer
            res = streamer.handle_system_action(action, value)
            return JSONResponse(res)

        # ── Universal 2-Way Clipboard Sync ────────────────────────────────────
        @app.get("/api/clipboard")
        async def get_clipboard(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                import pyperclip
                text = pyperclip.paste() or ""
            except Exception:
                text = ""
            return JSONResponse({"ok": True, "text": text})

        @app.post("/api/clipboard")
        async def set_clipboard(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            text = body.get("text", "")
            try:
                import pyperclip
                pyperclip.copy(text)
                asyncio.create_task(self.broadcast({"type": "clipboard_sync", "text": text}))
                return JSONResponse({"ok": True, "text": text})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        # ── Live Telemetry & Process Management ───────────────────────────────
        @app.get("/api/telemetry")
        async def get_telemetry(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                import psutil
                cpu_pct = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory()
                
                battery = psutil.sensors_battery()
                bat_pct = battery.percent if battery else 100
                bat_plugged = battery.power_plugged if battery else True
                
                disk = psutil.disk_usage('/') if sys.platform != 'win32' else psutil.disk_usage('C:\\')
                
                procs = []
                for p in sorted(
                    psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']),
                    key=lambda x: (x.info.get('cpu_percent') or 0),
                    reverse=True
                )[:8]:
                    try:
                        procs.append({
                            "pid": p.info['pid'],
                            "name": p.info['name'] or "Unknown",
                            "cpu": round(p.info.get('cpu_percent') or 0, 1),
                            "ram": round(p.info.get('memory_percent') or 0, 1),
                        })
                    except Exception:
                        continue

                gpu_pct = -1.0
                try:
                    from actions.system_monitor import _get_gpu_usage
                    gpu_pct = _get_gpu_usage()
                except Exception:
                    pass

                return JSONResponse({
                    "ok": True,
                    "cpu_percent": cpu_pct,
                    "ram_percent": ram.percent,
                    "ram_used_gb": round(ram.used / (1024**3), 2),
                    "ram_total_gb": round(ram.total / (1024**3), 2),
                    "battery_percent": bat_pct,
                    "battery_plugged": bat_plugged,
                    "disk_percent": disk.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 1),
                    "disk_total_gb": round(disk.total / (1024**3), 1),
                    "gpu_percent": gpu_pct if gpu_pct >= 0 else None,
                    "processes": procs,
                    "timestamp": time.time()
                })
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)})

        # ── Long-Term Memory API ──────────────────────────────────────────────
        @app.get("/api/memory/overview")
        async def get_memory_overview(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                from memory.memory_service import MemoryService
                svc = MemoryService.get_instance()
                return JSONResponse({"ok": True, **svc.get_overview()})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.get("/api/memory/search")
        async def search_memory_api(req: Request, q: str = "", category: str = None, limit: int = 10):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                from memory.memory_service import MemoryService
                svc = MemoryService.get_instance()
                results = svc.search_memories(query=q, category=category, limit=limit)
                items = [
                    {
                        "topic": s.entry.topic,
                        "content": s.entry.content,
                        "category": s.entry.category,
                        "importance": s.entry.importance,
                        "confidence": s.entry.confidence,
                        "status": s.entry.status,
                        "updated": s.entry.updated,
                        "notes": s.entry.notes,
                        "score": s.score,
                    }
                    for s in results
                ]
                return JSONResponse({"ok": True, "results": items})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/memory/save")
        async def save_memory_api(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                body = await req.json()
                from memory.memory_service import MemoryService
                svc = MemoryService.get_instance()
                ok, msg = svc.remember(
                    topic=body.get("topic", ""),
                    content=body.get("content", ""),
                    category=body.get("category", "notes"),
                    importance=body.get("importance", "Medium"),
                    confidence=body.get("confidence", "High"),
                )
                return JSONResponse({"ok": ok, "message": msg})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/process/kill")
        async def kill_process(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            pid = int(body.get("pid", 0))
            if pid <= 4:
                return JSONResponse({"ok": False, "error": "Cannot terminate system process."}, status_code=400)
            try:
                import psutil
                p = psutil.Process(pid)
                p_name = p.name()
                p.kill()
                return JSONResponse({"ok": True, "message": f"Terminated {p_name} (PID {pid})"})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        # ── Quick Apps Launcher ───────────────────────────────────────────────
        @app.get("/api/apps/list")
        async def list_quick_apps(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return JSONResponse({"ok": True, "apps": QUICK_APPS})

        @app.post("/api/apps/launch")
        async def launch_quick_app(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            target = body.get("target") or body.get("app_name", "")
            from actions.open_app import open_app
            res = open_app({"app_name": target})
            return JSONResponse({"ok": True, "result": res})

        # ── Automation & Workflows ────────────────────────────────────────────
        @app.get("/api/workflows")
        async def get_workflows(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from actions.automation_engine import load_all_workflows
            return JSONResponse({"ok": True, "workflows": load_all_workflows()})

        @app.post("/api/workflows/run")
        async def run_workflow_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            wf_id = body.get("workflow_id", "")
            from actions.automation_engine import AutomationEngine
            res = AutomationEngine.run_workflow(wf_id)
            return JSONResponse(res)

        @app.post("/api/workflows/save")
        async def save_workflow_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            from actions.automation_engine import save_custom_workflow
            ok = save_custom_workflow(body)
            return JSONResponse({"ok": ok})

        # ── Phone Hub & Android Gateway ───────────────────────────────────────
        @app.get("/api/phone/devices")
        async def get_phone_devices(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from actions.phone_hub import phone_hub
            return JSONResponse({"ok": True, "devices": phone_hub.get_all_devices()})

        @app.post("/api/phone/status")
        async def update_phone_status_ep(req: Request):
            body = await req.json()
            dev_id = body.get("device_id", "primary_phone")
            from actions.phone_hub import phone_hub
            res = phone_hub.update_phone_status(dev_id, body)
            return JSONResponse({"ok": True, "device": res})

        @app.post("/api/phone/ring")
        async def ring_phone_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from actions.phone_hub import phone_hub
            res = phone_hub.trigger_find_phone()
            asyncio.create_task(self.broadcast({"type": "phone_ring", "action": "ring"}))
            return JSONResponse(res)

        @app.post("/api/phone/action")
        async def phone_action_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            action = body.get("action", "")
            target = body.get("target", "")
            from actions.phone_hub import phone_hub
            res = phone_hub.trigger_phone_action(action, target, body.get("params", {}))
            return JSONResponse(res)

        # ── Phone mic real-time audio → Gemini Live ──────────────────────────
        @app.websocket("/ws/phone-audio")
        async def phone_audio_ws(websocket: WebSocket, token: str = ""):
            tok = token.strip()
            client_host = websocket.client.host if websocket.client else ""
            if client_host not in ("127.0.0.1", "::1", "localhost") and (not tok or tok not in self._tokens):
                await websocket.close(code=4001)
                return
            await websocket.accept()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Phone microphone live."}
            ))
            try:
                while True:
                    data = await websocket.receive_bytes()
                    try:
                        self._phone_audio_queue.put_nowait(
                            {"data": data, "mime_type": "audio/pcm;rate=16000"}
                        )
                    except asyncio.QueueFull:
                        pass
            except WebSocketDisconnect:
                pass
            finally:
                asyncio.create_task(self.broadcast(
                    {"type": "sys", "text": "Phone microphone stopped."}
                ))

        # ── File sharing ──────────────────────────────────────────────────────
        def _safe_filename(raw: str) -> str:
            name = Path(raw).name
            name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(". ")
            return name or "upload"

        if _UPLOAD_OK:
            @app.post("/api/upload")
            async def upload_file(req: Request, file: UploadFile = FastAPIFile(...)):
                if not _auth(req):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                safe = _safe_filename(file.filename or "upload")
                dest = self._uploads_dir / safe
                stem, suffix = Path(safe).stem, Path(safe).suffix
                counter = 1
                while dest.exists():
                    dest = self._uploads_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                size = 0
                max_bytes = MAX_UPLOAD_MB * 1024 * 1024
                try:
                    with open(dest, "wb") as fout:
                        while True:
                            chunk = await file.read(65536)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > max_bytes:
                                fout.close()
                                dest.unlink(missing_ok=True)
                                return JSONResponse(
                                    {"error": f"File too large (max {MAX_UPLOAD_MB} MB)"},
                                    status_code=413,
                                )
                            fout.write(chunk)
                except Exception as exc:
                    try:
                        dest.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return JSONResponse({"error": str(exc)}, status_code=500)

                asyncio.create_task(self.broadcast({
                    "type": "file_received",
                    "name": dest.name,
                    "size": size,
                    "saved_to": str(self._uploads_dir),
                }))
                return JSONResponse({"ok": True, "name": dest.name, "size": size})
        else:
            @app.post("/api/upload")
            async def upload_unavailable(req: Request):
                return JSONResponse(
                    {"error": "File uploads require: pip install python-multipart"},
                    status_code=503,
                )

        @app.get("/api/files")
        async def list_files(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            files = []
            try:
                for f in sorted(
                    (p for p in self._uploads_dir.iterdir() if p.is_file()),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                ):
                    files.append({"name": f.name, "size": f.stat().st_size})
            except Exception:
                pass
            return JSONResponse({"files": files})

        @app.get("/api/config")
        async def get_config_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                from core.task_llm import load_config
                cfg = load_config()
                # Mask sensitive key characters
                return JSONResponse({
                    "has_gemini": bool(cfg.get("gemini_api_key")),
                    "has_groq": bool(cfg.get("groq_api_key")),
                    "user_name": cfg.get("user_name", ""),
                    "assistant_name": cfg.get("assistant_name", "ANSH"),
                })
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.post("/api/config")
        async def update_config_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                body = await req.json()
                from core.task_llm import save_config
                updates = {}
                if "gemini_api_key" in body and body["gemini_api_key"]:
                    updates["gemini_api_key"] = body["gemini_api_key"].strip()
                if "groq_api_key" in body and body["groq_api_key"]:
                    updates["groq_api_key"] = body["groq_api_key"].strip()
                if "user_name" in body:
                    updates["user_name"] = body["user_name"].strip()
                if updates:
                    save_config(updates)
                return JSONResponse({"ok": True})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.get("/uploads/{filename}")
        async def download_file(filename: str, token: str = ""):
            tok = token.strip()
            if tok not in self._tokens:
                # Check if localhost
                pass
            safe = re.sub(r'[/\\]', '', filename)
            path = self._uploads_dir / safe
            if not path.exists() or not path.is_file():
                return JSONResponse({"error": "Not found"}, status_code=404)
            return FileResponse(str(path), filename=safe)

        @app.websocket("/ws")
        async def ws_ep(websocket: WebSocket, token: str = ""):
            tok = token.strip()
            client_host = websocket.client.host if websocket.client else ""
            if client_host not in ("127.0.0.1", "::1", "localhost") and (not tok or tok not in self._tokens):
                await websocket.close(code=4001)
                return
            await websocket.accept()
            self._clients.add(websocket)
            for entry in self._history[-50:]:
                try:
                    await websocket.send_json(entry)
                except Exception:
                    break
            try:
                while True:
                    data = await websocket.receive_json()
                    dtype = data.get("type")
                    if dtype == "command":
                        enc = data.get("enc", "")
                        t   = self._decrypt(tok, enc) if enc else (data.get("text") or "").strip()
                        if t:
                            await self._command_queue.put(t)
                            if self._wake_callback:
                                self._wake_callback()
                    elif dtype == "mouse":
                        from dashboard.screen_streamer import streamer
                        streamer.handle_mouse(data.get("action", "click"), data.get("data", {}))
                    elif dtype == "keyboard":
                        from dashboard.screen_streamer import streamer
                        streamer.handle_keyboard(data.get("action", "press"), data.get("data", {}))
                    elif dtype == "clipboard":
                        txt = data.get("text", "")
                        try:
                            import pyperclip
                            pyperclip.copy(txt)
                            await self.broadcast({"type": "clipboard_sync", "text": txt})
                        except Exception:
                            pass
            except WebSocketDisconnect:
                pass
            finally:
                self._clients.discard(websocket)

        return app

    # ── Serve ─────────────────────────────────────────────────────────────

    async def _serve_alias(self) -> None:
        ssl_key  = BASE_DIR / "config" / "certs" / "ansh.key"
        ssl_cert = BASE_DIR / "config" / "certs" / "ansh.crt"
        asyncio.get_event_loop().run_in_executor(None, _ensure_network_access, PORT + 1)
        cfg = uvicorn.Config(
            self.app, host="0.0.0.0", port=PORT + 1, log_level="warning",
            ssl_keyfile=str(ssl_key), ssl_certfile=str(ssl_cert),
        )
        await uvicorn.Server(cfg).serve()

    async def serve(self) -> None:
        if not _DEPS_OK:
            print("[Dashboard] fastapi/uvicorn not installed — dashboard disabled.")
            return

        asyncio.get_event_loop().run_in_executor(None, _ensure_network_access, PORT)

        use_ssl  = self._ssl_enabled()
        ssl_key  = BASE_DIR / "config" / "certs" / "ansh.key"
        ssl_cert = BASE_DIR / "config" / "certs" / "ansh.crt"

        if use_ssl:
            asyncio.create_task(self._serve_alias())

        cfg = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=PORT,
            log_level="warning",
            ssl_keyfile=str(ssl_key) if use_ssl else None,
            ssl_certfile=str(ssl_cert) if use_ssl else None,
        )

        proto = "https" if use_ssl else "http"
        print(f"[Dashboard] Localhost Command Center: http://localhost:{PORT}")
        try:
            await uvicorn.Server(cfg).serve()
        except (Exception, SystemExit) as e:
            print(f"[Dashboard] Server skipped (port busy or active): {e}")
