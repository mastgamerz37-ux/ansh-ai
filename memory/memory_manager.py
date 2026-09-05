# memory_manager.py
# ANSH AI Intelligent Long-Term Memory System — Compatibility Layer & Facade
# Directs all legacy and modern memory operations to the Markdown MemoryService.

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional

from memory.memory_service import MemoryService


def _service() -> MemoryService:
    return MemoryService.get_instance()


def load_memory() -> Dict[str, Any]:
    """
    Returns full dictionary representation of all memories for compatibility.
    """
    svc = _service()
    entries = svc.index.get_all_entries()

    result: Dict[str, Dict[str, Any]] = {
        "identity": {},
        "preferences": {},
        "projects": {},
        "relationships": {},
        "wishes": {},
        "notes": {},
    }

    category_aliases = {
        "personal": "identity",
        "identity": "identity",
        "preferences": "preferences",
        "projects": "projects",
        "relationships": "relationships",
        "wishes": "wishes",
        "notes": "notes",
        "knowledge": "notes",
        "procedures": "notes",
    }

    for e in entries:
        cat_key = category_aliases.get(e.category.lower(), e.category.lower())
        if cat_key not in result:
            result[cat_key] = {}

        topic_key = e.topic.lower().replace(" ", "_")
        result[cat_key][topic_key] = {
            "value": e.content,
            "updated": e.updated,
            "importance": e.importance,
            "confidence": e.confidence,
            "status": e.status,
        }

    return result


def save_memory(memory: dict) -> None:
    """
    Save or update a dictionary of memories into authoritative Markdown storage.
    """
    if not isinstance(memory, dict):
        return

    svc = _service()
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            if isinstance(entry, dict):
                val = str(entry.get("value", "")).strip()
                imp = entry.get("importance", "Medium")
                conf = entry.get("confidence", "High")
            else:
                val = str(entry).strip()
                imp = "Medium"
                conf = "High"

            if val:
                svc.remember(
                    topic=key.replace("_", " ").title(),
                    content=val,
                    category=cat,
                    importance=imp,
                    confidence=conf,
                )


def update_memory(memory_update: dict) -> dict:
    save_memory(memory_update)
    return load_memory()


def format_memory_for_prompt(memory: Optional[dict] = None) -> str:
    """
    Formats memory context for the system prompt.
    Uses clean, token-efficient, authoritative markdown summary.
    """
    svc = _service()
    core_summary = svc.get_core_identity_summary()
    if not core_summary:
        return ""

    header = "[WHAT YOU KNOW ABOUT THIS PERSON — use naturally, never recite like a list]\n"
    return f"{header}{core_summary}\n"


def remember(
    key: str,
    value: str,
    category: str = "notes",
    importance: str = "Medium",
    confidence: str = "High",
) -> str:
    """
    Direct function to save or update an explicit memory in Markdown storage.
    """
    svc = _service()
    ok, msg = svc.remember(
        topic=key.replace("_", " ").title(),
        content=value,
        category=category,
        importance=importance,
        confidence=confidence,
    )
    return msg


def forget(key: str, category: Optional[str] = None) -> str:
    """
    Direct function to remove an explicit memory from Markdown storage.
    """
    svc = _service()
    ok, msg = svc.forget(topic=key.replace("_", " ").title(), category=category)
    return msg


def search_memory(query: str, category: Optional[str] = None, limit: int = 6) -> str:
    """
    Direct function to query memories.
    """
    svc = _service()
    results = svc.search_memories(query=query, category=category, limit=limit)
    if not results:
        return f"No memories found matching '{query}'."

    lines = [f"Found {len(results)} memory entries for '{query}':"]
    for s in results:
        e = s.entry
        lines.append(f"• [{e.category.title()}] {e.topic} ({e.importance}): {e.content}")
    return "\n".join(lines)


forget_memory = forget