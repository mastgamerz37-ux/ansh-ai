"""
core/autostart.py — Cross-Platform Auto-Start on System Boot for ANSH

Registers ANSH to launch automatically when the computer boots up.
Supports Windows (HKCU Run Registry), macOS (LaunchAgent), and Linux (xdg autostart).
"""
from __future__ import annotations

import os
import sys
import platform
from pathlib import Path

APP_NAME = "ANSH_AI"
_SYSTEM = platform.system()


def _get_launch_command() -> str:
    """
    Returns the exact command to launch ANSH in the background.
    Prefers pythonw.exe on Windows to prevent an intrusive console window.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    base_dir = Path(__file__).resolve().parent.parent
    main_script = base_dir / "main.py"

    if _SYSTEM == "Windows":
        # Check for pythonw.exe in python directory
        py_dir = Path(sys.executable).parent
        pythonw = py_dir / "pythonw.exe"
        exe = str(pythonw if pythonw.exists() else sys.executable)
        return f'"{exe}" "{main_script}"'

    return f'"{sys.executable}" "{main_script}"'


def is_autostart_enabled() -> bool:
    """Returns True if ANSH is currently registered to start on boot."""
    try:
        if _SYSTEM == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            )
            try:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(val)
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)

        elif _SYSTEM == "Darwin":
            plist = Path.home() / "Library" / "LaunchAgents" / "com.ansh.assistant.plist"
            return plist.exists()

        else:
            desktop_file = Path.home() / ".config" / "autostart" / "ansh.desktop"
            return desktop_file.exists()
    except Exception as e:
        print(f"[Autostart] Error checking autostart status: {e}")
        return False


def enable_autostart() -> bool:
    """Registers ANSH to launch automatically on system boot."""
    cmd = _get_launch_command()
    try:
        if _SYSTEM == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_ALL_ACCESS,
            )
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            print(f"[Autostart] Enabled Windows boot startup: {cmd}")
            return True

        elif _SYSTEM == "Darwin":
            plist_dir = Path.home() / "Library" / "LaunchAgents"
            plist_dir.mkdir(parents=True, exist_ok=True)
            plist = plist_dir / "com.ansh.assistant.plist"
            base_dir = Path(__file__).resolve().parent.parent
            content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ansh.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{base_dir / "main.py"}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""
            plist.write_text(content, encoding="utf-8")
            print(f"[Autostart] Enabled macOS LaunchAgent: {plist}")
            return True

        else:
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_file = autostart_dir / "ansh.desktop"
            content = f"""[Desktop Entry]
Type=Application
Exec={cmd}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=ANSH AI
Comment=Your Own AI Friend
"""
            desktop_file.write_text(content, encoding="utf-8")
            print(f"[Autostart] Enabled Linux autostart: {desktop_file}")
            return True

    except Exception as e:
        print(f"[Autostart] Error enabling autostart: {e}")
        return False


def disable_autostart() -> bool:
    """Removes ANSH from system boot startup."""
    try:
        if _SYSTEM == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_ALL_ACCESS,
            )
            try:
                winreg.DeleteValue(key, APP_NAME)
                print("[Autostart] Disabled Windows boot startup.")
                return True
            except FileNotFoundError:
                return True
            finally:
                winreg.CloseKey(key)

        elif _SYSTEM == "Darwin":
            plist = Path.home() / "Library" / "LaunchAgents" / "com.ansh.assistant.plist"
            plist.unlink(missing_ok=True)
            print("[Autostart] Disabled macOS LaunchAgent.")
            return True

        else:
            desktop_file = Path.home() / ".config" / "autostart" / "ansh.desktop"
            desktop_file.unlink(missing_ok=True)
            print("[Autostart] Disabled Linux autostart.")
            return True
    except Exception as e:
        print(f"[Autostart] Error disabling autostart: {e}")
        return False


def toggle_autostart() -> bool:
    """Toggles autostart on or off and returns the new enabled state."""
    if is_autostart_enabled():
        disable_autostart()
        return False
    else:
        enable_autostart()
        return True


def ensure_autostart() -> bool:
    """Ensures autostart is registered on system startup."""
    if not is_autostart_enabled():
        return enable_autostart()
    return True
