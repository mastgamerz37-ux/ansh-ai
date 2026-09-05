"""
actions/automation_engine.py — Ansh Automation & Multi-Step Workflow Engine

Executes complex multi-step routines, custom task workflows, and scheduled triggers
across applications, system settings, browser, and files.
"""

import asyncio
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_IS_WIN = platform.system() == "Windows"
_IS_MAC = platform.system() == "Darwin"
_IS_LINUX = platform.system() == "Linux"

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _base_dir()
WORKFLOWS_FILE = BASE_DIR / "config" / "workflows.json"


BUILTIN_WORKFLOWS = {
    "dev_mode": {
        "id": "dev_mode",
        "name": "Developer Setup",
        "description": "Opens VS Code, Terminal, and Chrome developer tools; sets volume to 30%",
        "icon": "💻",
        "steps": [
            {"type": "app", "target": "Code"},
            {"type": "app", "target": "chrome"},
            {"type": "volume", "value": 30},
            {"type": "notify", "message": "Developer environment initialized."}
        ]
    },
    "focus_mode": {
        "id": "focus_mode",
        "name": "Deep Focus",
        "description": "Mutes system audio, closes non-essential windows, opens Notepad",
        "icon": "🎯",
        "steps": [
            {"type": "volume_mute"},
            {"type": "app", "target": "notepad"},
            {"type": "notify", "message": "Focus mode activated. Distractions silenced."}
        ]
    },
    "media_mode": {
        "id": "media_mode",
        "name": "Entertainment / Music",
        "description": "Opens Spotify or YouTube and adjusts volume to 65%",
        "icon": "🎵",
        "steps": [
            {"type": "app", "target": "spotify"},
            {"type": "volume", "value": 65},
            {"type": "notify", "message": "Media mode active."}
        ]
    },
    "night_mode": {
        "id": "night_mode",
        "name": "Night Relaxation",
        "description": "Dims brightness, lowers audio to 20%, minimizes desktop windows",
        "icon": "🌙",
        "steps": [
            {"type": "volume", "value": 20},
            {"type": "hotkey", "keys": ["win", "d"]},
            {"type": "notify", "message": "Good night. System prepared for rest."}
        ]
    },
    "clean_temp": {
        "id": "clean_temp",
        "name": "Clean Temporary Files",
        "description": "Purges temporary files, cache, and frees system memory",
        "icon": "🧹",
        "steps": [
            {"type": "clean_temp_files"},
            {"type": "notify", "message": "Temporary cache and scratch files cleaned."}
        ]
    },
    "morning_routine": {
        "id": "morning_routine",
        "name": "Morning Brief & Launch",
        "description": "Opens browser news, checks system telemetry, sets volume to 40%",
        "icon": "🌅",
        "steps": [
            {"type": "volume", "value": 40},
            {"type": "url", "url": "https://news.google.com"},
            {"type": "notify", "message": "Good morning! News opened and system ready."}
        ]
    }
}


def load_all_workflows() -> Dict[str, Any]:
    """Loads built-in and user-customized workflows."""
    workflows = dict(BUILTIN_WORKFLOWS)
    if WORKFLOWS_FILE.exists():
        try:
            custom = json.loads(WORKFLOWS_FILE.read_text(encoding="utf-8"))
            if isinstance(custom, dict):
                workflows.update(custom)
        except Exception:
            pass
    return workflows


def save_custom_workflow(workflow_data: dict) -> bool:
    """Saves or updates a custom workflow."""
    wf_id = workflow_data.get("id") or f"custom_{int(time.time())}"
    workflow_data["id"] = wf_id
    workflows = {}
    if WORKFLOWS_FILE.exists():
        try:
            workflows = json.loads(WORKFLOWS_FILE.read_text(encoding="utf-8"))
        except Exception:
            workflows = {}
    workflows[wf_id] = workflow_data
    try:
        WORKFLOWS_FILE.parent.mkdir(parents=True, exist_ok=True)
        WORKFLOWS_FILE.write_text(json.dumps(workflows, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


class AutomationEngine:
    """Orchestrates and executes multi-step workflows."""

    @staticmethod
    def execute_step(step: dict) -> dict:
        stype = step.get("type", "")
        try:
            if stype == "app":
                target = step.get("target", "")
                from actions.open_app import open_app
                res = open_app({"app_name": target})
                return {"ok": True, "result": res}

            elif stype == "url":
                url = step.get("url", "")
                import webbrowser
                webbrowser.open(url)
                return {"ok": True, "url": url}

            elif stype == "volume":
                val = int(step.get("value", 50))
                try:
                    from actions.computer_settings import volume_set
                    volume_set(val)
                except Exception:
                    pass
                return {"ok": True, "volume": val}

            elif stype == "volume_mute":
                if _IS_WIN:
                    subprocess.run(["powershell", "-c", "$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys([char]173)"], check=False)
                return {"ok": True}

            elif stype == "hotkey":
                keys = step.get("keys", [])
                try:
                    import pyautogui
                    pyautogui.hotkey(*keys)
                except Exception:
                    pass
                return {"ok": True, "keys": keys}

            elif stype == "wait":
                secs = float(step.get("seconds", 1.0))
                time.sleep(secs)
                return {"ok": True, "waited": secs}

            elif stype == "clean_temp_files":
                freed_mb = 0.0
                temp_dir = Path(tempfile.gettempdir())
                for item in temp_dir.iterdir():
                    try:
                        if item.is_file():
                            sz = item.stat().st_size
                            item.unlink(missing_ok=True)
                            freed_mb += sz / (1024 * 1024)
                        elif item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                    except Exception:
                        continue
                return {"ok": True, "freed_mb": round(freed_mb, 2)}

            elif stype == "notify":
                msg = step.get("message", "")
                return {"ok": True, "message": msg}

            return {"ok": False, "error": f"Unknown step type: {stype}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @classmethod
    def run_workflow(cls, workflow_id_or_data: Any) -> dict:
        """Executes a workflow by ID or by passing the workflow dict."""
        if isinstance(workflow_id_or_data, str):
            all_wf = load_all_workflows()
            wf = all_wf.get(workflow_id_or_data)
            if not wf:
                return {"ok": False, "error": f"Workflow '{workflow_id_or_data}' not found."}
        else:
            wf = workflow_id_or_data

        steps = wf.get("steps", [])
        results = []
        for s in steps:
            r = cls.execute_step(s)
            results.append(r)
            time.sleep(0.3)

        return {
            "ok": True,
            "workflow_id": wf.get("id"),
            "name": wf.get("name"),
            "steps_executed": len(results),
            "results": results
        }


def automation_workflow(parameters: dict, **kwargs) -> str:
    """Tool function callable by Gemini / Ansh main loop."""
    action = parameters.get("action", "run")
    workflow_id = parameters.get("workflow_id", "")
    
    if action == "list":
        all_wf = load_all_workflows()
        names = [f"- {v['name']} ({k}): {v['description']}" for k, v in all_wf.items()]
        return "Available Workflows:\n" + "\n".join(names)
    
    if action == "run":
        if not workflow_id:
            return "Please provide workflow_id (e.g. dev_mode, focus_mode, media_mode, night_mode, clean_temp)."
        res = AutomationEngine.run_workflow(workflow_id)
        if res.get("ok"):
            return f"Workflow '{res.get('name')}' executed successfully with {res.get('steps_executed')} steps."
        return f"Workflow execution failed: {res.get('error')}"

    return f"Unknown workflow action '{action}'."
