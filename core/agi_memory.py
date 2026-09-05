"""
core/agi_memory.py — Advanced Semantic Knowledge Engine & Goal Memory for ANSH

Provides:
1. Automated Fact & Preference Extraction from user speech/text and tool outputs using TaskLLM.
2. Active Goal Working Memory tracking (multi-step plan state, intermediate results).
3. Keyword & Semantic context retrieval for system prompt injection.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from memory.memory_manager import (
    load_memory, remember, search_memory, format_memory_for_prompt
)
from core.task_llm import call_task_llm


class AGIMemoryEngine:
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "memory"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.goals_file = self.data_dir / "agi_active_goals.json"
        self._active_goals: Dict[str, Dict[str, Any]] = self._load_goals()

    def _load_goals(self) -> Dict[str, Dict[str, Any]]:
        if self.goals_file.exists():
            try:
                return json.loads(self.goals_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_goals(self) -> None:
        try:
            self.goals_file.write_text(json.dumps(self._active_goals, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[AGIMemory] Error saving active goals: {e}")

    def extract_and_store_facts(self, user_input: str, assistant_response: str = "") -> List[str]:
        """
        Uses TaskLLM to analyze conversation turns and extract key user facts, preferences, or project updates.
        Saves extracted facts into the long-term memory store.
        """
        if not user_input or len(user_input.strip()) < 10:
            return []

        prompt = (
            "Analyze the following conversation turn between a User and ANSH (AI Assistant).\n"
            "Extract any NEW, long-term worth remembering facts about the user (e.g., preferences, name, projects, hobbies, system setups).\n"
            "Return JSON in this format: {\"facts\": [{\"topic\": \"Topic Name\", \"content\": \"Fact detail\", \"category\": \"preferences|projects|identity|notes\"}]}\n"
            "If no durable facts exist, return {\"facts\": []}.\n\n"
            f"User Input: {user_input}\n"
            f"Assistant Output: {assistant_response}\n"
        )

        try:
            raw = call_task_llm(prompt=prompt, json_mode=True, temperature=0.2, max_tokens=500)
            data = json.loads(raw)
            facts = data.get("facts", [])
            saved_topics = []
            for f in facts:
                topic = f.get("topic", "").strip()
                content = f.get("content", "").strip()
                cat = f.get("category", "notes").lower()
                if topic and content:
                    remember(key=topic, value=content, category=cat, importance="Medium")
                    saved_topics.append(topic)
            return saved_topics
        except Exception as e:
            print(f"[AGIMemory] Fact extraction skipped/failed: {e}")
            return []

    def save_goal_state(self, goal_id: str, goal_title: str, steps: List[Dict[str, Any]], current_step: int, status: str) -> None:
        """
        Updates working memory state for an active multi-step goal.
        """
        self._active_goals[goal_id] = {
            "title": goal_title,
            "steps": steps,
            "current_step": current_step,
            "status": status,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_goals()

    def get_goal_state(self, goal_id: str) -> Optional[Dict[str, Any]]:
        return self._active_goals.get(goal_id)

    def clear_goal_state(self, goal_id: str) -> None:
        if goal_id in self._active_goals:
            del self._active_goals[goal_id]
            self._save_goals()

    def get_all_active_goals(self) -> List[Dict[str, Any]]:
        return [
            {"goal_id": gid, **gdata}
            for gid, gdata in self._active_goals.items()
            if gdata.get("status") in ("in_progress", "paused", "planning")
        ]

    def retrieve_relevant_context(self, query: str) -> str:
        """
        Retrieves formatted memory context relevant to the user query and appends active goals context.
        """
        mem_summary = format_memory_for_prompt()
        search_res = search_memory(query=query, limit=3)
        active_goals = self.get_all_active_goals()

        context_parts = []
        if mem_summary:
            context_parts.append(mem_summary)
        if search_res and "No memories found" not in search_res:
            context_parts.append(f"[RELEVANT MEMORIES FOR '{query}']\n{search_res}")
        if active_goals:
            goals_str = "\n".join([f"- Goal '{g['title']}' (Step {g['current_step']}/{len(g['steps'])}) Status: {g['status']}" for g in active_goals])
            context_parts.append(f"[ACTIVE AUTONOMOUS GOALS]\n{goals_str}")

        return "\n\n".join(context_parts)
