"""
core/skills_manager.py — Dynamic Modular Skills & Extensible Tool Registry for Ansh

Discovers, loads, and manages executable skills from the `skills/` directory.
Allows Ansh to dynamically expand its toolset with custom community & system skills.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

def _base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _base_dir()
SKILLS_DIR = BASE_DIR / "skills"


DEFAULT_SKILLS = {
    "screen_remote": {
        "id": "screen_remote",
        "name": "Live Screen Streaming & Remote Input",
        "description": "Streams real-time display frames and processes remote mouse, touch gestures, and keyboard input.",
        "category": "system",
        "author": "Ansh Core"
    },
    "automation_workflows": {
        "id": "automation_workflows",
        "name": "Automation & Workflow Engine",
        "description": "Executes complex multi-step routine sequences across applications, browser, and settings.",
        "category": "automation",
        "author": "Ansh Core"
    },
    "phone_gateway": {
        "id": "phone_gateway",
        "name": "Cross-Device Android Gateway",
        "description": "Connects smartphone telemetry, WhatsApp intents, dialer intents, and find-my-phone ring triggers.",
        "category": "cross-device",
        "author": "Ansh Core"
    },
    "universal_clipboard": {
        "id": "universal_clipboard",
        "name": "Universal 2-Way Clipboard Sync",
        "description": "Synchronizes text and clipboard history across PC and connected mobile devices in real time.",
        "category": "productivity",
        "author": "Ansh Core"
    },
    "hardware_telemetry": {
        "id": "hardware_telemetry",
        "name": "Hardware Telemetry & Process Monitor",
        "description": "Monitors CPU, RAM, GPU, Battery, Storage metrics, and allows process termination.",
        "category": "hardware",
        "author": "Ansh Core"
    },
    "coding_agent": {
        "id": "coding_agent",
        "name": "Developer & Coding Agent",
        "description": "Inspects code, reviews architectures, fixes errors, and generates full-stack code projects.",
        "category": "developer",
        "author": "Ansh Core"
    }
}


class SkillsManager:
    """Manages skill discovery, loading, and registration."""

    def __init__(self):
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        self._skills: Dict[str, dict] = self._load_all_skills()

    def _load_all_skills(self) -> Dict[str, dict]:
        skills = dict(DEFAULT_SKILLS)
        if SKILLS_DIR.exists():
            for f in SKILLS_DIR.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    sid = data.get("id") or f.stem
                    skills[sid] = data
                except Exception:
                    continue
        return skills

    def get_skills(self) -> List[dict]:
        return list(self._skills.values())

    def get_skill(self, skill_id: str) -> Optional[dict]:
        return self._skills.get(skill_id)

    def register_custom_skill(self, skill_data: dict) -> bool:
        sid = skill_data.get("id")
        if not sid:
            return False
        self._skills[sid] = skill_data
        try:
            file_path = SKILLS_DIR / f"{sid}.json"
            file_path.write_text(json.dumps(skill_data, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False


skills_manager = SkillsManager()


def skills_tool(parameters: dict, **kwargs) -> str:
    """Tool callable by Ansh LLM."""
    action = parameters.get("action", "list")
    if action == "list":
        sk_list = skills_manager.get_skills()
        res = ["🧩 Active Ansh Skills:"]
        for s in sk_list:
            res.append(f"- **{s.get('name')}** (`{s.get('id')}`): {s.get('description')}")
        return "\n".join(res)
    return f"Unknown skills action '{action}'."
