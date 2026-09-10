"""
memory/knowledge_graph.py — ANSH Personal Knowledge Graph & World-State Context Engine

Maintains an entity-relation graph of user knowledge, active projects, habits,
relationships, and live world-state awareness (current environment, active tasks,
persistent goals).
"""
from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DATA_DIR = BASE_DIR / "data" / "memory"
GRAPH_FILE = DATA_DIR / "knowledge_graph.json"
WORLD_STATE_FILE = DATA_DIR / "world_state.json"


@dataclass
class GraphRelation:
    subject: str
    predicate: str  # e.g., "works_on", "prefers", "authored", "depends_on", "uses"
    object: str
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)


class KnowledgeGraph:
    """
    ANSH Semantic Knowledge Graph & World-State Engine.
    Enables deep contextual recall, entity traversal, and continuous world awareness.
    """

    _instance: Optional[KnowledgeGraph] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> KnowledgeGraph:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.relations: List[GraphRelation] = []
        self.world_state: Dict[str, Any] = {
            "current_workspace": str(BASE_DIR),
            "creator": "Anshu",
            "active_goals": [],
            "focus_mode": False,
            "last_interaction": time.time(),
        }
        self._load_graph()
        self._load_world_state()

    def _load_graph(self) -> None:
        if GRAPH_FILE.exists():
            try:
                data = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
                self.relations = [GraphRelation(**r) for r in data.get("relations", [])]
            except Exception as e:
                print(f"[KnowledgeGraph] ⚠️ Graph load warning: {e}")
                self.relations = []

    def _save_graph(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            payload = {"relations": [asdict(r) for r in self.relations]}
            GRAPH_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[KnowledgeGraph] ⚠️ Graph save error: {e}")

    def _load_world_state(self) -> None:
        if WORLD_STATE_FILE.exists():
            try:
                self.world_state.update(json.loads(WORLD_STATE_FILE.read_text(encoding="utf-8")))
            except Exception:
                pass

    def _save_world_state(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            WORLD_STATE_FILE.write_text(json.dumps(self.world_state, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[KnowledgeGraph] ⚠️ World state save error: {e}")

    def add_relation(self, subject: str, predicate: str, object_entity: str, confidence: float = 1.0) -> None:
        """Adds or updates a semantic triple in the Knowledge Graph."""
        with self._lock:
            s = subject.strip().title()
            p = predicate.strip().lower()
            o = object_entity.strip().title()

            # Avoid duplicates
            for r in self.relations:
                if r.subject == s and r.predicate == p and r.object == o:
                    r.confidence = max(r.confidence, confidence)
                    self._save_graph()
                    return

            self.relations.append(GraphRelation(subject=s, predicate=p, object=o, confidence=confidence))
            self._save_graph()

    def query_entity(self, entity_name: str) -> Dict[str, Any]:
        """Finds all relations connected to the given entity."""
        with self._lock:
            name = entity_name.strip().title()
            outgoing = []
            incoming = []

            for r in self.relations:
                if r.subject == name:
                    outgoing.append({"predicate": r.predicate, "target": r.object, "confidence": r.confidence})
                elif r.object == name:
                    incoming.append({"source": r.subject, "predicate": r.predicate, "confidence": r.confidence})

            return {
                "entity": name,
                "facts": outgoing,
                "referenced_by": incoming,
            }

    def search_graph(self, query: str) -> List[str]:
        """Returns natural language statements matching the search query."""
        with self._lock:
            q = query.lower()
            results = []
            for r in self.relations:
                if q in r.subject.lower() or q in r.predicate.lower() or q in r.object.lower():
                    results.append(f"• {r.subject} {r.predicate.replace('_', ' ')} {r.object}")
            return results

    def update_world_state(self, key: str, value: Any) -> None:
        """Updates continuous environment and session state."""
        with self._lock:
            self.world_state[key] = value
            self.world_state["last_interaction"] = time.time()
            self._save_world_state()

    def get_world_state(self) -> Dict[str, Any]:
        """Returns active world state snapshot."""
        with self._lock:
            return dict(self.world_state)
