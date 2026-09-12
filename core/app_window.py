"""
core/app_window.py — Dedicated Desktop App-Mode Window Launcher for ANSH Dashboard

Opens the ANSH Dashboard in an isolated, native desktop application window
(without URL bar, tabs, or bookmarks) using Chromium/Edge app-mode.
Falls back to system browser if no Chromium-based runtime is found.
"""
from __future__ import annotations

import os
import sys
import platform
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, List

_SYSTEM = platform.system()


def _get_candidate_executables() -> List[Path]:
    """Returns candidate browser executables ordered by preference."""
    candidates = []

    if _SYSTEM == "Windows":
        # Check standard installation locations on Windows
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        local_appdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))

        paths = [
            # Edge (Default on Windows 10/11)
            Path(program_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(program_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            # Chrome
            Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(local_appdata) / "Google" / "Chrome" / "Application" / "chrome.exe",
            # Brave
            Path(program_files) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
            Path(local_appdata) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
        ]
        candidates.extend(paths)

    elif _SYSTEM == "Darwin":
        paths = [
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
        ]
        candidates.extend(paths)

    else:
        # Linux binaries in PATH
        import shutil
        for name in ("microsoft-edge", "google-chrome", "chromium-browser", "chromium", "brave-browser"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))

    return candidates


def find_app_browser() -> Optional[str]:
    """Finds first available Chromium-based browser supporting --app mode."""
    for p in _get_candidate_executables():
        if p.exists() and os.access(p, os.X_OK if _SYSTEM != "Windows" else os.R_OK):
            return str(p)
    return None


def open_dashboard_window(
    url: str = "http://localhost:8000",
    width: int = 1280,
    height: int = 820
) -> bool:
    """
    Launches url in a dedicated application window (without address bar/tabs).
    If app-mode is unavailable, falls back to standard system browser.
    """
    browser_exe = find_app_browser()

    if browser_exe:
        cmd = [
            browser_exe,
            f"--app={url}",
            f"--window-size={width},{height}",
            "--window-position=center",
            "--disable-extensions",
            "--app-launch-url-for-shortcuts-menu-item",
        ]
        try:
            # Launch detached so it doesn't block the caller
            if _SYSTEM == "Windows":
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                subprocess.Popen(cmd, creationflags=flags, close_fds=True)
            else:
                subprocess.Popen(cmd, start_new_session=True)

            print(f"[AppWindow] Launched dashboard in dedicated window: {url}")
            return True
        except Exception as e:
            print(f"[AppWindow] Failed to launch window via {browser_exe}: {e}")

    # Fallback to standard web browser
    try:
        print(f"[AppWindow] Falling back to default browser for {url}")
        webbrowser.open(url)
        return True
    except Exception as e:
        print(f"[AppWindow] Fallback browser launch failed: {e}")
        return False
