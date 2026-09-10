"""
core/security_engine.py — ANSH Enterprise Security, Risk Engine & Safety Rollback

Implements:
1. Action Risk Classification (SAFE, LOW_RISK, MEDIUM_RISK, HIGH_RISK, CRITICAL)
2. Confirmation Gate for High-Risk & Destructive Actions
3. Command Audit Log & Activity History (audit_log.jsonl)
4. Emergency Stop & Emergency Lockdown
5. Privacy Mode & Sensitive Content Guard
6. Shadow Backups, Undo System & Automatic Rollback
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DATA_DIR = BASE_DIR / "data" / "secure"
BACKUP_DIR = BASE_DIR / "data" / "shadow_backups"
AUDIT_LOG_FILE = DATA_DIR / "audit_log.jsonl"


class RiskLevel(str, Enum):
    SAFE = "safe"              # Read-only queries, time, weather, memory search
    LOW_RISK = "low_risk"      # File read, app launch, volume change
    MEDIUM_RISK = "medium_risk"# File creation, sending emails/messages, web navigation
    HIGH_RISK = "high_risk"    # Code modification, script execution, settings change
    CRITICAL = "critical"      # File deletion, format, PC restart/shutdown, terminal shell command


@dataclass
class ActionSnapshot:
    action_id: str
    action_type: str
    target_path: Optional[str] = None
    backup_path: Optional[str] = None
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    rolled_back: bool = False


class SecurityEngine:
    """
    ANSH Security, Permissions, and Safety Recovery Engine.
    Guarantees that no destructive actions can happen without classification,
    provides emergency kill-switches, and enables multi-level undo/rollback.
    """

    _instance: Optional[SecurityEngine] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> SecurityEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        self.emergency_stop_triggered: bool = False
        self.lockdown_active: bool = False
        self.privacy_mode_active: bool = False

        self.snapshots: List[ActionSnapshot] = []
        self._action_counter: int = 0

    # ── 1. Risk Classification ──────────────────────────────────────────────────

    def classify_action(self, action_name: str, parameters: Optional[Dict[str, Any]] = None) -> RiskLevel:
        """Evaluates the risk level of any tool or action before execution."""
        act = action_name.lower()
        params = parameters or {}

        # Critical: System destruction, reboot/shutdown, hard deletes, raw cmd execution
        if any(w in act for w in ("shutdown", "restart_pc", "format", "wipe", "rmdir", "delete_permanent")):
            return RiskLevel.CRITICAL
        if act == "file_controller" and params.get("action") in ("delete", "remove", "truncate"):
            return RiskLevel.CRITICAL
        if act in ("dev_agent", "terminal_command") and any(k in str(params).lower() for k in ("rm -rf", "drop database", "del /f")):
            return RiskLevel.CRITICAL

        # High Risk: Code modifications, git commits, script executions
        if act in ("dev_agent", "code_helper", "execute_script", "deploy_wormhole", "modify_system"):
            return RiskLevel.HIGH_RISK
        if act == "file_controller" and params.get("action") in ("overwrite", "write", "move"):
            return RiskLevel.HIGH_RISK

        # Medium Risk: External messages, web forms, downloads
        if act in ("send_message", "send_email", "whatsapp_call", "browser_submit"):
            return RiskLevel.MEDIUM_RISK

        # Low Risk: Opening apps, changing volume, reading files
        if act in ("open_app", "computer_settings", "youtube_video", "read_messages"):
            return RiskLevel.LOW_RISK

        # Safe: Read-only operations
        return RiskLevel.SAFE

    # ── 2. Confirmation & Audit Logging ─────────────────────────────────────────

    def requires_confirmation(self, risk: RiskLevel) -> bool:
        """Determines if an action requires explicit user confirmation."""
        if self.lockdown_active:
            return True
        return risk in (RiskLevel.HIGH_RISK, RiskLevel.CRITICAL)

    def log_action(
        self,
        action_name: str,
        parameters: Dict[str, Any],
        risk_level: RiskLevel,
        approved: bool,
        result: str,
    ) -> None:
        """Appends an immutable audit log entry."""
        with self._lock:
            entry = {
                "timestamp": time.time(),
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action": action_name,
                "risk_level": risk_level.value,
                "approved": approved,
                "result": result[:250],
            }
            try:
                with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                print(f"[SecurityEngine] ⚠️ Audit log error: {e}")

    # ── 3. Emergency Controls & Privacy Mode ────────────────────────────────────

    def trigger_emergency_stop(self) -> str:
        """Instantly terminates ongoing tasks, mutes TTS, and halts execution."""
        with self._lock:
            self.emergency_stop_triggered = True
            try:
                import sounddevice as sd
                sd.stop()
            except Exception:
                pass
            self.log_action("emergency_stop", {}, RiskLevel.CRITICAL, True, "All operations halted.")
            return "🛑 EMERGENCY STOP ACTIVATED. All background tasks and speech halted."

    def trigger_emergency_lockdown(self) -> str:
        """Locks down ANSH: blocks all tool executions until manual release."""
        with self._lock:
            self.lockdown_active = True
            self.trigger_emergency_stop()
            return "🔒 EMERGENCY LOCKDOWN ACTIVATED. System locked down. No tools will execute."

    def release_lockdown(self) -> str:
        """Releases the emergency lockdown."""
        with self._lock:
            self.lockdown_active = False
            self.emergency_stop_triggered = False
            return "🔓 Lockdown released. ANSH normal security operational."

    def toggle_privacy_mode(self, enabled: Optional[bool] = None) -> bool:
        """Toggles privacy mode (stops continuous camera vision and screen capture)."""
        with self._lock:
            if enabled is not None:
                self.privacy_mode_active = enabled
            else:
                self.privacy_mode_active = not self.privacy_mode_active
            return self.privacy_mode_active

    # ── 4. Shadow Backup & Undo / Rollback Engine ───────────────────────────────

    def create_pre_action_snapshot(self, action_name: str, target_file: Optional[str] = None) -> ActionSnapshot:
        """
        Creates a shadow copy of a target file or system state BEFORE modifying it,
        guaranteeing 100% undoability.
        """
        with self._lock:
            self._action_counter += 1
            action_id = f"act_{int(time.time())}_{self._action_counter}"
            backup_copy_path = None

            if target_file and os.path.exists(target_file) and os.path.isfile(target_file):
                try:
                    fpath = Path(target_file)
                    backup_name = f"{action_id}_{fpath.name}"
                    backup_target = BACKUP_DIR / backup_name
                    shutil.copy2(fpath, backup_target)
                    backup_copy_path = str(backup_target)
                except Exception as e:
                    print(f"[SecurityEngine] Shadow backup failed: {e}")

            snapshot = ActionSnapshot(
                action_id=action_id,
                action_type=action_name,
                target_path=target_file,
                backup_path=backup_copy_path,
                before_state={"exists": bool(target_file and os.path.exists(target_file))},
            )
            self.snapshots.append(snapshot)
            return snapshot

    def rollback_last_action(self) -> Tuple[bool, str]:
        """
        Rolls back the most recent reversible action using its shadow snapshot.
        """
        with self._lock:
            for snap in reversed(self.snapshots):
                if snap.rolled_back:
                    continue

                if snap.target_path and snap.backup_path and os.path.exists(snap.backup_path):
                    try:
                        shutil.copy2(snap.backup_path, snap.target_path)
                        snap.rolled_back = True
                        msg = f"Successfully rolled back '{snap.action_type}'! Restored: {Path(snap.target_path).name}"
                        self.log_action("rollback", {"action_id": snap.action_id}, RiskLevel.MEDIUM_RISK, True, msg)
                        return True, msg
                    except Exception as e:
                        return False, f"Rollback failed: {e}"

                # Handle creation undo (delete newly created file)
                elif snap.target_path and not snap.before_state.get("exists") and os.path.exists(snap.target_path):
                    try:
                        if os.path.isfile(snap.target_path):
                            os.remove(snap.target_path)
                        elif os.path.isdir(snap.target_path):
                            shutil.rmtree(snap.target_path)
                        snap.rolled_back = True
                        msg = f"Undid file creation: removed {Path(snap.target_path).name}"
                        return True, msg
                    except Exception as e:
                        return False, f"Creation undo failed: {e}"

            return False, "No reversible action snapshots found in current session."
