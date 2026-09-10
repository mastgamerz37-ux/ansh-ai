"""
core/event_bus.py — ANSH Central Event System & Debug Telemetry

Pub-Sub architecture connecting all ANSH subsystems:
- Voice, Vision, Screen Intelligence
- Multi-Agent Hub & Tool Execution
- Security Alerts & Audit Rollbacks
- Affective Mood & Personality Mode shifts
"""
from __future__ import annotations

import json
import sys
import threading
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DATA_DIR = BASE_DIR / "data" / "logs"
EVENT_LOG_FILE = DATA_DIR / "events.jsonl"


class EventType(str, Enum):
    VOICE_INPUT = "voice_input"
    VOICE_OUTPUT = "voice_output"
    VISION_FRAME = "vision_frame"
    SCREEN_CHANGE = "screen_change"
    AGENT_TASK_START = "agent_task_start"
    AGENT_TASK_DONE = "agent_task_done"
    AGENT_HANDOFF = "agent_handoff"
    SECURITY_ALERT = "security_alert"
    ROLLBACK_EXECUTED = "rollback_executed"
    MODE_CHANGED = "mode_changed"
    MOOD_SHIFT = "mood_shift"
    SYSTEM_ALERT = "system_alert"


@dataclass
class AnshEvent:
    event_type: EventType
    payload: Dict[str, Any]
    source: str = "core"
    timestamp: float = field(default_factory=time.time)
    time_str: str = field(default_factory=lambda: time.strftime("%H:%M:%S"))


class EventBus:
    """
    ANSH Central Event Bus.
    Allows real-time decouple communication, UI visualization, and telemetry auditing.
    """

    _instance: Optional[EventBus] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> EventBus:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._subscribers: Dict[EventType, List[Callable[[AnshEvent], None]]] = defaultdict(list)
        self._recent_events: List[AnshEvent] = []

    def subscribe(self, event_type: EventType, callback: Callable[[AnshEvent], None]) -> None:
        """Subscribes a callback to an event type."""
        with self._lock:
            self._subscribers[event_type].append(callback)

    def publish(self, event_type: EventType, payload: Dict[str, Any], source: str = "core") -> AnshEvent:
        """Publishes an event to all subscribers and appends to telemetry history."""
        event = AnshEvent(event_type=event_type, payload=payload, source=source)

        with self._lock:
            self._recent_events.append(event)
            if len(self._recent_events) > 300:
                self._recent_events.pop(0)

            # Notify subscribers
            callbacks = list(self._subscribers.get(event_type, []))

        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"[EventBus] Callback error on {event_type.value}: {e}")

        # Async write to log
        self._append_to_file(event)
        return event

    def _append_to_file(self, event: AnshEvent) -> None:
        try:
            with open(EVENT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "type": event.event_type.value,
                    "source": event.source,
                    "timestamp": event.timestamp,
                    "time": event.time_str,
                    "payload": event.payload,
                }) + "\n")
        except Exception:
            pass

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent events for the debug console or dashboard."""
        with self._lock:
            return [
                {
                    "type": e.event_type.value,
                    "source": e.source,
                    "time": e.time_str,
                    "payload": e.payload,
                }
                for e in self._recent_events[-limit:]
            ]
