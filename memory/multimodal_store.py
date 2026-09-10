"""
memory/multimodal_store.py — Multimodal Memory & Cross-Session Context Continuation
Stores and indexes visual snapshots, audio memos, and state checkpoints.
Enables seamless context continuation across long breaks and interaction mediums
(Desktop Smart Island, Telegram Bot, CLI).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DATA_DIR = BASE_DIR / "data" / "multimodal"
VISUAL_DIR = DATA_DIR / "visuals"
CHECKPOINT_FILE = DATA_DIR / "session_checkpoint.json"
CROSS_MEDIUM_FILE = DATA_DIR / "cross_medium_bus.json"


@dataclass
class VisualMemoryEntry:
    id: str
    timestamp: float
    app_name: str
    window_title: str
    summary_text: str
    tags: List[str]
    thumbnail_path: str = ""


@dataclass
class SessionCheckpoint:
    timestamp: float
    timestamp_human: str
    last_active_app: str
    open_window_titles: List[str]
    git_repo: Optional[str] = None
    git_branch: Optional[str] = None
    recent_files: List[str] = field(default_factory=list)
    pending_goals: List[str] = field(default_factory=list)
    last_emotional_state: str = "neutral"
    last_user_query: str = ""
    summary_briefing: str = ""


class MultimodalStore:
    """
    Multimodal Memory Engine.
    Coordinates persistent storage of visuals, screen context, and session checkpoints
    for seamless continuation across laptop wakeups, reboots, and Telegram remote switches.
    """

    _instance: Optional[MultimodalStore] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> MultimodalStore:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        VISUAL_DIR.mkdir(parents=True, exist_ok=True)
        self.visual_index: List[Dict[str, Any]] = []
        self._load_visual_index()

    def _index_path(self) -> Path:
        return DATA_DIR / "visual_index.json"

    def _load_visual_index(self) -> None:
        p = self._index_path()
        if p.exists():
            try:
                self.visual_index = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[MultimodalStore] ⚠️ Visual index load note: {e}")
                self.visual_index = []

    def _save_visual_index(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._index_path().write_text(json.dumps(self.visual_index[-300:], indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[MultimodalStore] ⚠️ Visual index save note: {e}")

    def save_visual_memory(
        self,
        summary_text: str,
        app_name: str = "",
        window_title: str = "",
        tags: Optional[List[str]] = None,
        image_bytes: Optional[bytes] = None,
    ) -> str:
        """
        Stores an indexed visual snapshot of the screen or camera image.
        """
        with self._lock:
            ts = time.time()
            entry_id = hashlib.sha256(f"{ts}_{window_title}_{summary_text}".encode()).hexdigest()[:12]
            thumb_filename = ""

            if image_bytes:
                try:
                    thumb_filename = f"{entry_id}.jpg"
                    thumb_path = VISUAL_DIR / thumb_filename
                    thumb_path.write_bytes(image_bytes)
                except Exception as e:
                    print(f"[MultimodalStore] Thumbnail write note: {e}")

            record = {
                "id": entry_id,
                "timestamp": ts,
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                "app_name": app_name,
                "window_title": window_title,
                "summary_text": summary_text,
                "tags": tags or [],
                "thumbnail_file": thumb_filename,
            }
            self.visual_index.append(record)
            self._save_visual_index()
            return entry_id

    def search_visual_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches past visual/screen memories by keyword query."""
        with self._lock:
            q_lower = query.lower()
            results = []
            for item in reversed(self.visual_index):
                match = (
                    q_lower in item.get("summary_text", "").lower()
                    or q_lower in item.get("window_title", "").lower()
                    or q_lower in item.get("app_name", "").lower()
                    or any(q_lower in tag.lower() for tag in item.get("tags", []))
                )
                if match:
                    results.append(item)
                    if len(results) >= limit:
                        break
            return results

    def capture_session_checkpoint(
        self,
        last_query: str = "",
        pending_goals: Optional[List[str]] = None,
        emotional_state: str = "neutral",
    ) -> SessionCheckpoint:
        """
        Captures the complete system and task context to allow instant continuation
        when returning to ANSH after a break or switching to Telegram.
        """
        with self._lock:
            now = time.time()
            now_human = time.strftime("%A, %B %d, %Y at %I:%M %p", time.localtime(now))

            # Detect Git status in current workspace if present
            git_repo: Optional[str] = None
            git_branch: Optional[str] = None
            try:
                out = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=str(BASE_DIR),
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                ).decode("utf-8").strip()
                git_branch = out
                git_repo = BASE_DIR.name
            except Exception:
                pass

            # Detect open windows and foreground app (Windows)
            open_windows: List[str] = []
            active_app = "Unknown"
            if sys.platform == "win32":
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    hwnd = user32.GetForegroundWindow()
                    length = user32.GetWindowTextLengthW(hwnd)
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if buff.value:
                        active_app = buff.value
                except Exception:
                    pass

            checkpoint = SessionCheckpoint(
                timestamp=now,
                timestamp_human=now_human,
                last_active_app=active_app,
                open_window_titles=open_windows[:5],
                git_repo=git_repo,
                git_branch=git_branch,
                recent_files=[str(BASE_DIR)],
                pending_goals=pending_goals or [],
                last_emotional_state=emotional_state,
                last_user_query=last_query,
                summary_briefing=f"Active in {active_app} on branch {git_branch or 'main'}."
            )

            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                CHECKPOINT_FILE.write_text(json.dumps(asdict(checkpoint), indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[MultimodalStore] Checkpoint save note: {e}")

            return checkpoint

    def get_last_session_checkpoint(self) -> Optional[SessionCheckpoint]:
        """Loads the most recent session checkpoint."""
        with self._lock:
            if not CHECKPOINT_FILE.exists():
                return None
            try:
                data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
                return SessionCheckpoint(**data)
            except Exception as e:
                print(f"[MultimodalStore] Checkpoint load note: {e}")
                return None

    def get_continuation_briefing(self) -> str:
        """
        Generates a friendly context continuation briefing for morning launch
        or wake-up after a break.
        """
        cp = self.get_last_session_checkpoint()
        if not cp:
            return "No previous session checkpoint found. Starting fresh."

        elapsed_hours = (time.time() - cp.timestamp) / 3600.0
        time_elapsed_str = f"{elapsed_hours:.1f} hours ago" if elapsed_hours >= 1.0 else f"{int(elapsed_hours * 60)} minutes ago"

        lines = [
            f"[CONTEXT_CONTINUATION] Last active {time_elapsed_str} ({cp.timestamp_human}).",
            f"Active Workspace: {cp.git_repo or 'ANSH'} (branch: {cp.git_branch or 'main'})",
        ]
        if cp.last_active_app and cp.last_active_app != "Unknown":
            lines.append(f"Last Focused Window: {cp.last_active_app}")
        if cp.last_user_query:
            lines.append(f"Last In-Progress Request: \"{cp.last_user_query[:120]}\"")
        if cp.pending_goals:
            lines.append(f"Unfinished Goals: {', '.join(cp.pending_goals[:3])}")
        return "\n".join(lines)

    def publish_cross_medium_message(self, source_medium: str, message: str, payload: Optional[dict] = None) -> None:
        """
        Broadcasts context updates between Smart Island Desktop, Telegram Bot, and CLI.
        """
        with self._lock:
            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                entry = {
                    "source": source_medium,
                    "timestamp": time.time(),
                    "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": message,
                    "payload": payload or {},
                }
                history: List[dict] = []
                if CROSS_MEDIUM_FILE.exists():
                    try:
                        history = json.loads(CROSS_MEDIUM_FILE.read_text(encoding="utf-8"))
                    except Exception:
                        history = []
                history.append(entry)
                CROSS_MEDIUM_FILE.write_text(json.dumps(history[-50:], indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[MultimodalStore] Cross-medium sync note: {e}")
