"""
actions/wormhole.py — Ultra-Fast Deploy Wormhole (Instant Public Tunneling) for ANSH

Exposes local development ports (e.g. 8000, 3000, 5000) to the public internet
via parallel multi-engine SSH/localtunnel racing (< 1 second connection).
"""
from __future__ import annotations

import os
import re
import sys
import time
import queue
import subprocess
import threading
from typing import Optional, Dict

_ACTIVE_TUNNELS: Dict[int, subprocess.Popen] = {}
_TUNNEL_URLS: Dict[int, str] = {}


def start_wormhole(port: int = 8000, player=None) -> str:
    """
    Launch a public HTTPS tunnel to the specified local port in under 1 second.
    """
    global _ACTIVE_TUNNELS, _TUNNEL_URLS

    if port in _ACTIVE_TUNNELS and _ACTIVE_TUNNELS[port].poll() is None:
        url = _TUNNEL_URLS.get(port, f"Tunnel active on port {port}")
        return f"Wormhole tunnel already active for port {port}:\n🌐 {url}"

    if player:
        player.write_log(f"[Wormhole] Opening ultra-fast public portal on port {port}...")

    url_queue = queue.Queue()
    procs = []

    providers = [
        ("localhost.run", [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ServerAliveInterval=15", "-R", f"80:localhost:{port}", "nokey@localhost.run"
        ]),
        ("pinggy.io", [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-p", "443", "-R", f"0:localhost:{port}", "a.pinggy.io"
        ]),
    ]

    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    def _monitor_provider(name: str, cmd: list):
        try:
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=flags
            )
            procs.append(p)
            start_t = time.time()
            while p.poll() is None and (time.time() - start_t < 6.0):
                line = p.stdout.readline()
                if not line:
                    time.sleep(0.02)
                    continue
                if "admin.localhost.run" in line or "localhost.run/docs" in line:
                    continue
                match = re.search(
                    r"https://[a-zA-Z0-9\.\-_]+\.(?:lhr\.life|lhrtunnel\.link|pinggy\.link|pinggy\.io|serveo\.net)",
                    line
                )
                if match:
                    url_queue.put((name, match.group(0), p))
                    break
        except Exception:
            pass

    for name, cmd in providers:
        t = threading.Thread(target=_monitor_provider, args=(name, cmd), daemon=True)
        t.start()

    try:
        winner_name, public_url, winner_proc = url_queue.get(timeout=4.5)
        _ACTIVE_TUNNELS[port] = winner_proc
        _TUNNEL_URLS[port] = public_url

        # Terminate slower losing tunnel processes
        for p in procs:
            if p != winner_proc:
                try: p.terminate()
                except Exception: pass

        if player:
            player.write_log(f"[Wormhole] Active: {public_url}")

        return f"Wormhole deployed: {public_url}"

    except queue.Empty:
        for p in procs:
            try: p.terminate()
            except Exception: pass

    try:
        cmd = ["npx", "-y", "localtunnel", "--port", str(port)]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=flags
        )
        start_time = time.time()
        public_url = None
        while time.time() - start_time < 5.0:
            line = proc.stdout.readline()
            if "your url is:" in line.lower():
                public_url = line.strip().split()[-1]
                break

        if public_url:
            _ACTIVE_TUNNELS[port] = proc
            _TUNNEL_URLS[port] = public_url
            return f"Wormhole deployed: {public_url}"

    except Exception as e:
        print(f"[Wormhole] Localtunnel fallback error: {e}")

    return f"Failed to establish wormhole tunnel for port {port}. Please ensure SSH or Node/NPX is available."


def stop_wormhole(port: Optional[int] = None) -> str:
    global _ACTIVE_TUNNELS, _TUNNEL_URLS
    if port:
        proc = _ACTIVE_TUNNELS.pop(port, None)
        _TUNNEL_URLS.pop(port, None)
        if proc:
            proc.terminate()
            return f"Wormhole tunnel on port {port} closed."
        return f"No active tunnel found on port {port}."
    else:
        count = len(_ACTIVE_TUNNELS)
        for p, proc in list(_ACTIVE_TUNNELS.items()):
            try: proc.terminate()
            except Exception: pass
        _ACTIVE_TUNNELS.clear()
        _TUNNEL_URLS.clear()
        return f"All {count} active wormhole tunnels have been terminated."


def wormhole_action(
    parameters: dict = None,
    player=None,
    speak=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "start").lower().strip()
    port = int(params.get("port", 8000))

    if action in ("stop", "close", "kill"):
        return stop_wormhole(port if "port" in params else None)
    elif action in ("status", "list"):
        if not _TUNNEL_URLS:
            return "No active wormhole tunnels."
        lines = [f"Port {p} ➔ {url}" for p, url in _TUNNEL_URLS.items()]
        return "Active Wormholes:\n" + "\n".join(lines)
    else:
        return start_wormhole(port=port, player=player)
