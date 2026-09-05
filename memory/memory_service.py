# memory_service.py
# ANSH AI Intelligent Long-Term Memory System — Core Service & Orchestration
# Manages extraction, validation, duplicate/conflict resolution, context-budgeted retrieval, and safety.

from __future__ import annotations

import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from memory.markdown_store import MarkdownStore, MemoryEntry, MEMORY_STORAGE_DIR
from memory.indexer import MemoryIndex, ScoredMemory


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_OLD_JSON_PATH = _get_base_dir() / "memory" / "long_term.json"
_LOCK = threading.RLock()


# Prompt injection blacklist patterns inside retrieved memories
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"\[system_prompt\]", re.IGNORECASE),
    re.compile(r"\[admin_override\]", re.IGNORECASE),
]


def _sanitize_memory_content(text: str) -> str:
    """Sanitize retrieved memory to prevent prompt injection."""
    sanitized = text
    for pat in _INJECTION_PATTERNS:
        sanitized = pat.sub("[filtered text]", sanitized)
    return sanitized.strip()


class MemoryService:
    """
    High-level memory orchestration service for ANSH AI.
    """

    _instance: Optional[MemoryService] = None

    @classmethod
    def get_instance(cls) -> MemoryService:
        if cls._instance is None:
            with _LOCK:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self, storage_dir: Optional[Path] = None):
        self.store = MarkdownStore(storage_dir or MEMORY_STORAGE_DIR)
        self.index = MemoryIndex(self.store)
        self._ensure_migrated()

    def _ensure_migrated(self) -> None:
        """Migrate legacy long_term.json if markdown storage is empty."""
        with _LOCK:
            existing_files = self.store.list_all_files()
            if not existing_files and _OLD_JSON_PATH.exists():
                try:
                    data = json.loads(_OLD_JSON_PATH.read_text(encoding="utf-8"))
                    print("[MemoryService] Migrating long_term.json to authoritative Markdown storage...")
                    self._migrate_json(data)
                    self.index.refresh(force=True)
                    print("[MemoryService] Migration complete! Markdown memory ready.")
                except Exception as e:
                    print(f"[MemoryService] Migration error: {e}")

    def _migrate_json(self, data: dict) -> None:
        """Transform JSON schema into categorized Markdown memory files."""
        category_map = {
            "identity": ("personal", "Critical"),
            "preferences": ("preferences", "High"),
            "projects": ("projects", "High"),
            "relationships": ("relationships", "Medium"),
            "wishes": ("wishes", "Medium"),
            "notes": ("notes", "Medium"),
        }

        for cat_key, items in data.items():
            if not isinstance(items, dict):
                continue

            target_cat, default_imp = category_map.get(cat_key, (cat_key, "Medium"))
            entries: List[MemoryEntry] = []

            for topic_key, item_val in items.items():
                if isinstance(item_val, dict):
                    val = str(item_val.get("value", "")).strip()
                    updated = str(item_val.get("updated", datetime.now().strftime("%Y-%m-%d")))
                else:
                    val = str(item_val).strip()
                    updated = datetime.now().strftime("%Y-%m-%d")

                if not val:
                    continue

                topic_title = topic_key.replace("_", " ").title()
                entries.append(
                    MemoryEntry(
                        topic=topic_title,
                        content=val,
                        category=target_cat,
                        importance=default_imp,
                        confidence="High",
                        status="Current",
                        created=updated,
                        updated=updated,
                    )
                )

            if entries:
                file_path = self.store._resolve_safe_path(f"{target_cat}.md")
                self.store.write_entries_to_file(file_path, target_cat.title(), entries)

    # ── CRUD Operations ─────────────────────────────────────────────────────────

    def remember(
        self,
        topic: str,
        content: str,
        category: str = "notes",
        importance: str = "Medium",
        confidence: str = "High",
        tags: Optional[List[str]] = None,
        notes: str = "",
        auto_resolve_conflict: bool = True,
    ) -> Tuple[bool, str]:
        """
        Learn or update a memory with automatic duplicate and conflict detection.
        """
        with _LOCK:
            topic_clean = topic.strip()
            content_clean = content.strip()
            if not topic_clean or not content_clean:
                return False, "Topic and content cannot be empty."

            cat_clean = category.strip().lower().replace(" ", "_") or "notes"
            imp_clean = importance.strip().title()
            if imp_clean not in ("Critical", "High", "Medium", "Low", "Temporary"):
                imp_clean = "Medium"

            conf_clean = confidence.strip().title()
            if conf_clean not in ("High", "Medium", "Low"):
                conf_clean = "High"

            # Check for existing entries matching topic
            all_entries = self.index.get_all_entries()
            matched_entry: Optional[MemoryEntry] = None

            for ex in all_entries:
                if ex.topic.strip().lower() == topic_clean.lower():
                    matched_entry = ex
                    break

            if matched_entry:
                # 1. Duplicate check (exact content match)
                if matched_entry.content.strip().lower() == content_clean.lower():
                    # Content is unchanged; touch updated date and boost confidence if needed
                    matched_entry.updated = datetime.now().strftime("%Y-%m-%d %H:%M")
                    if conf_clean == "High" and matched_entry.confidence != "High":
                        matched_entry.confidence = "High"
                    self.store.upsert_entry(matched_entry, category_override=matched_entry.category)
                    self.index.refresh(force=True)
                    return True, f"Memory confirmed & refreshed: [{matched_entry.category}] {topic_clean}"

                # 2. Conflict / Update check (same topic, different content)
                if auto_resolve_conflict:
                    old_content = matched_entry.content.replace("- **Notes**:", "").strip()
                    old_updated = matched_entry.updated.replace("- **Last Updated**:", "").strip()
                    history_note = f"Previously ({old_updated}): {old_content[:150]}"
                    if matched_entry.notes:
                        clean_prev_notes = matched_entry.notes.replace("- **Notes**:", "").strip()
                        history_note = f"{clean_prev_notes} | {history_note}"

                    updated_entry = MemoryEntry(
                        topic=topic_clean,
                        content=content_clean,
                        category=cat_clean or matched_entry.category,
                        importance=imp_clean or matched_entry.importance,
                        confidence=conf_clean,
                        status="Current",
                        created=matched_entry.created,
                        updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                        tags=tags or matched_entry.tags,
                        notes=notes or history_note,
                    )
                    self.store.upsert_entry(updated_entry, category_override=updated_entry.category)
                    self.index.refresh(force=True)
                    return True, f"Memory updated with previous history recorded: [{updated_entry.category}] {topic_clean}"

            # 3. Create fresh entry
            new_entry = MemoryEntry(
                topic=topic_clean,
                content=content_clean,
                category=cat_clean,
                importance=imp_clean,
                confidence=conf_clean,
                status="Current",
                created=datetime.now().strftime("%Y-%m-%d %H:%M"),
                updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                tags=tags or [],
                notes=notes or "",
            )
            self.store.upsert_entry(new_entry, category_override=cat_clean)
            self.index.refresh(force=True)
            return True, f"Saved to memory: [{cat_clean}] {topic_clean}"

    def search_memories(
        self,
        query: str,
        category: Optional[str] = None,
        include_historical: bool = False,
        limit: int = 8,
    ) -> List[ScoredMemory]:
        """Search memory index using semantic & keyword relevance ranking."""
        return self.index.search(
            query=query,
            category=category,
            include_historical=include_historical,
            limit=limit,
        )

    def forget(self, topic: str, category: Optional[str] = None) -> Tuple[bool, str]:
        """Delete or deprecate a memory entry."""
        with _LOCK:
            success = self.store.delete_entry(topic=topic, category=category)
            if success:
                self.index.refresh(force=True)
                return True, f"Forgotten: '{topic}'"
            return False, f"Memory entry not found for '{topic}'"

    # ── Context Generation for Prompts ──────────────────────────────────────────

    def get_core_identity_summary(self) -> str:
        """
        Returns high-priority identity and core preferences for initial system prompt.
        Compact and token-efficient.
        """
        self.index.refresh()
        entries = self.index.get_all_entries()
        core_lines = []

        # Personal identity items
        for e in entries:
            if e.category in ("personal", "identity") and e.status == "Current":
                core_lines.append(f"- {e.topic}: {e.content}")

        # High/Critical preferences
        pref_lines = []
        for e in entries:
            if e.category in ("preferences",) and e.importance in ("Critical", "High") and e.status == "Current":
                pref_lines.append(f"- {e.topic}: {e.content}")

        res = []
        if core_lines:
            res.append("CORE USER IDENTITY:\n" + "\n".join(core_lines))
        if pref_lines:
            res.append("CORE PREFERENCES:\n" + "\n".join(pref_lines[:15]))

        return "\n\n".join(res)

    def retrieve_context_for_prompt(
        self,
        query: str,
        max_chars: int = 3500,
        min_score: float = 2.0,
    ) -> str:
        """
        Search and package relevant memory for context injection with clear injection delimiters.
        Respects context budget.
        """
        if not query.strip():
            return ""

        scored = self.search_memories(query=query, limit=12)
        filtered = [s for s in scored if s.score >= min_score]
        if not filtered:
            return ""

        blocks = []
        current_chars = 0

        for sm in filtered:
            e = sm.entry
            topic_s = _sanitize_memory_content(e.topic)
            content_s = _sanitize_memory_content(e.content)
            cat_s = e.category.replace("_", " ").title()

            block = f"[{cat_s}] {topic_s}: {content_s}"
            if e.notes:
                notes_s = _sanitize_memory_content(e.notes)
                block += f" (History: {notes_s})"

            if current_chars + len(block) > max_chars:
                break

            blocks.append(block)
            current_chars += len(block) + 2

        if not blocks:
            return ""

        return (
            "\nBEGIN RETRIEVED MEMORY\n"
            "(Contextual information retrieved from long-term memory. Use naturally when answering.)\n"
            + "\n".join(f"• {b}" for b in blocks)
            + "\nEND RETRIEVED MEMORY\n"
        )

    def get_overview(self) -> Dict[str, Any]:
        """Inspect all categories, file counts, and top topics."""
        self.index.refresh()
        entries = self.index.get_all_entries()
        cats: Dict[str, List[str]] = {}

        for e in entries:
            c = e.category
            if c not in cats:
                cats[c] = []
            cats[c].append(f"{e.topic} [{e.importance}]")

        return {
            "total_entries": len(entries),
            "categories": {k: {"count": len(v), "topics": v[:15]} for k, v in cats.items()},
            "storage_path": str(self.store.root),
        }
