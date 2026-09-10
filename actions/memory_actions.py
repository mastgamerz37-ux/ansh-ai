# memory_actions.py
# ANSH AI Intelligent Long-Term Memory System — Action Handlers for Gemini Live API

from __future__ import annotations

from typing import Optional, Dict, Any
from memory.memory_service import MemoryService


def save_memory_action(
    parameters: dict,
    player=None,
    speak=None,
) -> str:
    """
    Handles saving or updating long-term memory.
    """
    params = parameters or {}
    topic = params.get("topic") or params.get("key") or ""
    content = params.get("content") or params.get("value") or ""
    category = params.get("category", "notes")
    importance = params.get("importance", "Medium")
    confidence = params.get("confidence", "High")
    tags = params.get("tags")
    notes = params.get("notes", "")

    if not topic or not content:
        return "Cannot save memory: topic and content must be provided."

    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    svc = MemoryService.get_instance()
    success, msg = svc.remember(
        topic=topic,
        content=content,
        category=category,
        importance=importance,
        confidence=confidence,
        tags=tags,
        notes=notes,
    )

    if player:
        player.write_log(f"[Memory] {msg[:60]}")

    return msg


def search_memory_action(
    parameters: dict,
    player=None,
    speak=None,
) -> str:
    """
    Handles searching long-term memory across structured categories and conversation logs.
    """
    params = parameters or {}
    query = params.get("query") or params.get("topic") or params.get("question") or ""
    category = params.get("category")
    limit = int(params.get("limit", 6))

    if not query.strip():
        return "Please specify a query to search in memory."

    if player:
        player.write_log(f"[Memory] Searching: {query[:30]}...")

    svc = MemoryService.get_instance()
    results = svc.search_memories(query=query, category=category, limit=limit)

    lines = []
    if results:
        lines.append(f"Found {len(results)} relevant structured memories:")
        for sm in results:
            e = sm.entry
            note_str = f" [History: {e.notes}]" if e.notes else ""
            lines.append(f"• [{e.category.title()}] {e.topic} ({e.importance}): {e.content}{note_str}")

    # Also search recent conversational dialogue for informal user statements
    try:
        from memory.auto_remember import AutoRememberEngine
        conv_matches = AutoRememberEngine.get_instance().search_conversation_history(query=query, limit=3)
        if conv_matches:
            lines.append("\nRelevant Past Conversation Dialogue:")
            for c in conv_matches:
                spk = c.get("speaker", "user").title()
                txt = c.get("text", "")
                ts = c.get("timestamp", "")
                lines.append(f"• [{ts}] {spk}: \"{txt}\"")
    except Exception:
        pass

    if not lines:
        return f"No memories or past conversation found matching '{query}'."

    return "\n".join(lines)


def forget_memory_action(
    parameters: dict,
    player=None,
    speak=None,
) -> str:
    """
    Handles forgetting or deleting a memory entry.
    """
    params = parameters or {}
    topic = params.get("topic") or params.get("key") or params.get("query") or ""
    category = params.get("category")

    if not topic.strip():
        return "Please specify the memory topic to forget."

    svc = MemoryService.get_instance()
    success, msg = svc.forget(topic=topic, category=category)

    if player:
        player.write_log(f"[Memory] {msg}")

    return msg


def list_memories_action(
    parameters: dict,
    player=None,
    speak=None,
) -> str:
    """
    Handles inspecting memory categories and stored topics.
    """
    svc = MemoryService.get_instance()
    overview = svc.get_overview()

    lines = [f"Total memories stored: {overview['total_entries']} across {len(overview['categories'])} categories:"]
    for cat, info in overview["categories"].items():
        lines.append(f"\n📁 **{cat.title()}** ({info['count']} items):")
        for top in info["topics"]:
            lines.append(f"  - {top}")

    return "\n".join(lines)
