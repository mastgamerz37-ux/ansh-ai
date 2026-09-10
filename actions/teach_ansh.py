"""
actions/teach_ansh.py — "Teach ANSH Mode" Workflow Recorder & Playback Engine

Allows the user to demonstrate a workflow step-by-step or by natural description,
record the action sequence, save it with custom triggers/conditions, and replay it
autonomously in the future.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DATA_DIR = BASE_DIR / "data" / "workflows"
RECORDINGS_FILE = DATA_DIR / "custom_workflows.json"
HISTORY_FILE = DATA_DIR / "automation_history.jsonl"


@dataclass
class WorkflowStep:
    step_id: int
    action_type: str  # "app", "hotkey", "click", "type", "url", "shell", "volume", "wait"
    target: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    delay_seconds: float = 0.5


@dataclass
class CustomWorkflow:
    workflow_id: str
    name: str
    description: str
    trigger_phrase: str
    condition: Optional[str] = None  # e.g., "battery < 20", "time == 09:00", "cpu > 90"
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    execution_count: int = 0
    last_run: Optional[float] = None


class TeachAnshEngine:
    """
    Teach ANSH Workflow Engine.
    Enables recording, saving, scheduling, and playing back user demonstrations.
    """

    _instance: Optional[TeachAnshEngine] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> TeachAnshEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.workflows: Dict[str, CustomWorkflow] = {}
        self.active_recording: Optional[CustomWorkflow] = None
        self.is_recording: bool = False
        self._load_workflows()

    def _load_workflows(self) -> None:
        if RECORDINGS_FILE.exists():
            try:
                data = json.loads(RECORDINGS_FILE.read_text(encoding="utf-8"))
                for wid, wdict in data.items():
                    steps = [WorkflowStep(**s) for s in wdict.get("steps", [])]
                    wdict["steps"] = steps
                    self.workflows[wid] = CustomWorkflow(**wdict)
            except Exception as e:
                print(f"[TeachAnsh] ⚠️ Workflow load warning: {e}")
                self.workflows = {}

    def _save_workflows(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            export_dict = {}
            for wid, wf in self.workflows.items():
                d = asdict(wf)
                export_dict[wid] = d
            RECORDINGS_FILE.write_text(json.dumps(export_dict, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[TeachAnsh] ⚠️ Workflow save error: {e}")

    def start_recording(self, name: str, trigger_phrase: str, description: str = "", condition: Optional[str] = None) -> str:
        """Starts recording a new workflow demonstrated by the user."""
        with self._lock:
            wid = f"wf_{int(time.time())}"
            self.active_recording = CustomWorkflow(
                workflow_id=wid,
                name=name,
                description=description or f"Workflow for {name}",
                trigger_phrase=trigger_phrase,
                condition=condition,
                steps=[],
            )
            self.is_recording = True
            return f"🔴 TEACH ANSH RECORDING STARTED for '{name}'. Perform your actions or describe each step. Call stop_recording when done."

    def record_step(
        self,
        action_type: str,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        description: str = "",
        delay: float = 0.5,
    ) -> str:
        """Records a single action step into the active demonstration."""
        with self._lock:
            if not self.is_recording or not self.active_recording:
                return "No recording session currently active. Call start_recording first."

            step_idx = len(self.active_recording.steps) + 1
            step = WorkflowStep(
                step_id=step_idx,
                action_type=action_type,
                target=target,
                parameters=parameters or {},
                description=description or f"Step {step_idx}: {action_type} {target}",
                delay_seconds=delay,
            )
            self.active_recording.steps.append(step)
            return f"Step {step_idx} recorded: {step.description}"

    def stop_recording(self) -> str:
        """Stops the active recording, saves the workflow, and makes it available for replay."""
        with self._lock:
            if not self.is_recording or not self.active_recording:
                return "No active recording to stop."

            wf = self.active_recording
            self.workflows[wf.workflow_id] = wf
            self._save_workflows()
            self.active_recording = None
            self.is_recording = False
            return (
                f"✅ TEACH ANSH RECORDING SAVED! '{wf.name}' ({len(wf.steps)} steps).\n"
                f"Trigger phrase: \"{wf.trigger_phrase}\". You can now say this anytime to execute the workflow!"
            )

    def play_workflow(self, workflow_id_or_trigger: str) -> Tuple[bool, str]:
        """
        Replays a saved custom workflow step-by-step.
        """
        with self._lock:
            target_wf: Optional[CustomWorkflow] = None
            query = workflow_id_or_trigger.lower()

            for wf in self.workflows.values():
                if wf.workflow_id == workflow_id_or_trigger or wf.trigger_phrase.lower() in query or query in wf.name.lower():
                    target_wf = wf
                    break

            if not target_wf:
                return False, f"Workflow matching '{workflow_id_or_trigger}' not found."

            from actions.automation_engine import execute_action
            errors: List[str] = []
            executed_steps = 0

            for step in target_wf.steps:
                try:
                    # Map step to automation engine action
                    step_dict = {
                        "type": step.action_type,
                        "target": step.target,
                        **step.parameters,
                    }
                    execute_action(step_dict)
                    executed_steps += 1
                    if step.delay_seconds > 0:
                        time.sleep(step.delay_seconds)
                except Exception as step_err:
                    errors.append(f"Step {step.step_id} ({step.description}) failed: {step_err}")

            target_wf.execution_count += 1
            target_wf.last_run = time.time()
            self._save_workflows()

            # Record in history
            try:
                hist_entry = {
                    "timestamp": time.time(),
                    "workflow_id": target_wf.workflow_id,
                    "name": target_wf.name,
                    "steps_total": len(target_wf.steps),
                    "steps_success": executed_steps,
                    "errors": errors,
                }
                with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(hist_entry) + "\n")
            except Exception:
                pass

            if errors:
                return False, f"Workflow completed with errors: {'; '.join(errors)}"
            return True, f"Workflow '{target_wf.name}' completed successfully ({executed_steps} steps)."

    def list_workflows(self) -> List[Dict[str, Any]]:
        """Returns all registered custom workflows."""
        with self._lock:
            return [
                {
                    "id": wf.workflow_id,
                    "name": wf.name,
                    "trigger": wf.trigger_phrase,
                    "steps_count": len(wf.steps),
                    "condition": wf.condition,
                    "execution_count": wf.execution_count,
                }
                for wf in self.workflows.values()
            ]
