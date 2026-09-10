"""
memory/auto_remember.py — Continuous Autonomous Memory Engine for ANSH

Ensures ANSH NEVER forgets anything the user says:
1. Automatically logs all user utterances & assistant replies into persistent episodic memory (conversations.jsonl & conversations.md).
2. Automatically extracts facts, preferences, identity, projects, relationships, and notes using high-precision multilingual patterns (Hindi, Hinglish, English).
3. Automatically commits durable facts to authoritative Markdown Memory & Semantic Knowledge Graph without requiring explicit commands.
4. Provides searchable conversational history so even informal past dialogue can be recalled immediately.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from memory.memory_service import MemoryService
from memory.knowledge_graph import KnowledgeGraph


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
STORAGE_DIR = BASE_DIR / "memory" / "storage"
CONVERSATION_MD = STORAGE_DIR / "conversations.md"
CONVERSATION_JSONL = STORAGE_DIR / "conversations.jsonl"
_LOCK = threading.RLock()


# Pre-compiled high-precision multilingual extraction patterns for Hindi, Hinglish, and English
PATTERNS_EXPLICIT_NOTE = [
    re.compile(r"\b(?:remember\s+that|remember|note\s+that|yaad\s+rakhna|yaad\s+rakho|yeh\s+yaad\s+rakho|kabhi\s+mat\s+bhulna|dhyan\s+rakhna)\s*(?:ki|that|yeh)?\s+([^.!?\n]+)", re.IGNORECASE),
]

PATTERNS_NAME = [
    re.compile(r"\b(?:my\s+name\s+is|mera\s+naam|naam\s+hai|call\s+me|mujhe\s+bolte\s+hain)\s*(?:hai|is|:)?\s*([A-Za-z\u0900-\u097f\s]+?)(?:\s+hai|\s+is)?$", re.IGNORECASE),
]

PATTERNS_LOCATION = [
    re.compile(r"\b(?:i\s+am\s+from|i\s+live\s+in|location\s+is)\s+([A-Za-z\u0900-\u097f\s]+)", re.IGNORECASE),
    re.compile(r"\b(?:main)\s+([A-Za-z\u0900-\u097f\s]+?)\s+(?:se\s+hoon|me\s+rehta\s+hoon|mein\s+rehta\s+hoon|me\s+rehti\s+hoon|mein\s+rehti\s+hoon)\b", re.IGNORECASE),
]

PATTERNS_OCCUPATION = [
    re.compile(r"\b(?:i\s+am\s+a|main\s+ek)\s+([A-Za-z\u0900-\u097f\s]+)\s+(?:developer|engineer|coder|designer|student|doctor|founder|programmer)", re.IGNORECASE),
]

PATTERNS_PREF_HINDI = [
    re.compile(r"\b(?:mujhe|mujhko)\s+(.+?)\s+(?:bahut\s+)?(pasand\s+hai|pasand\s+nahi\s+hai|achha\s+lagta\s+hai|accha\s+lagta\s+hai|pasand\s+h|accha\s+lagta\s+h)\b", re.IGNORECASE),
]

PATTERNS_PREF_EN_LIKE = [
    re.compile(r"\b(?:i\s+like|i\s+love|i\s+prefer)\s+([^.!?,\n]+)", re.IGNORECASE),
]

PATTERNS_PREF_EN_DISLIKE = [
    re.compile(r"\b(?:i\s+hate|i\s+dislike|i\s+don't\s+like|i\s+do\s+not\s+like)\s+([^.!?,\n]+)", re.IGNORECASE),
]

PATTERNS_FAV_HI = [
    re.compile(r"\b(?:mera|meri|my)\s+(?:favorite|favourite)\s+([a-zA-Z\s]+?)\s+([^.!?,\n]+?)\s+(?:hai|h)$", re.IGNORECASE),
]

PATTERNS_FAV_EN = [
    re.compile(r"\b(?:my|mera|meri)\s+(?:favorite|favourite)\s+([a-zA-Z\s]+?)\s+(?:is|=|:)\s+([^.!?,\n]+)", re.IGNORECASE),
]

PATTERNS_PROJECTS = [
    re.compile(r"\b(?:main|hum)\s+(.+?)\s+(?:pe\s+kaam\s+kar\s+rha\s+hoon|pe\s+work\s+kar\s+rha\s+hoon|bana\s+rha\s+hoon|build\s+kar\s+rha\s+hoon|bana\s+rahe\s+hain|build\s+kar\s+rahe\s+hain)\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+am\s+working\s+on|working\s+on|building|developing)\s+([a-zA-Z0-9_\-\s]+)", re.IGNORECASE),
    re.compile(r"\b(?:my\s+project\s+is|mera\s+project\s+hai|project\s+name\s+is)\s+([a-zA-Z0-9_\-\s]+)", re.IGNORECASE),
    re.compile(r"\b(?:mera\s+project)\s+([a-zA-Z0-9_\-\s]+?)\s+(?:hai|h)$", re.IGNORECASE),
]

PATTERNS_RELATIONSHIPS = [
    re.compile(r"\b(my\s+friend|mera\s+dost|my\s+brother|mera\s+bhai|my\s+sister|meri\s+behen|my\s+father|mere\s+papa|my\s+mother|meri\s+mummy|meri\s+girlfriend|meri\s+wife|mera\s+partner)\s+(?:is|hai|named)?\s*([A-Za-z\u0900-\u097f]+)(?:\s+hai|\s+is)?", re.IGNORECASE),
]

PATTERNS_POSSESSIONS = [
    re.compile(r"\b(?:mere\s+paas|i\s+have)\s+([^.!?,\n]+?)(?:\s+hai|\s+h)?$", re.IGNORECASE),
    re.compile(r"\b(?:mera\s+laptop|mera\s+phone|meri\s+car|meri\s+bike|mera\s+pc)\s+([^.!?,\n]+?)(?:\s+hai|\s+is|\s+h)?$", re.IGNORECASE),
]


class AutoRememberEngine:
    """
    Continuous Autonomous Memory Ingestion Engine.
    Passively monitors all user interaction and ensures no statement,
    preference, project detail, or identity fact is ever forgotten.
    """

    _instance: Optional[AutoRememberEngine] = None

    @classmethod
    def get_instance(cls) -> AutoRememberEngine:
        if cls._instance is None:
            with _LOCK:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.mem_svc = MemoryService.get_instance()
        self.kg = KnowledgeGraph.get_instance()
        self.recent_turns: List[Dict[str, str]] = []
        self._load_recent_conversations()

    def _load_recent_conversations(self) -> None:
        """Loads last 25 conversational turns into working memory cache."""
        if CONVERSATION_JSONL.exists():
            try:
                with open(CONVERSATION_JSONL, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-25:]:
                        if line.strip():
                            self.recent_turns.append(json.loads(line.strip()))
            except Exception as e:
                print(f"[AutoRemember] ⚠️ Conversation history read note: {e}")

    def append_conversation_turn(self, speaker: str, text: str) -> None:
        """Persists every conversational turn into episodic memory log."""
        if not text or not text.strip():
            return

        with _LOCK:
            now_iso = datetime.now().isoformat()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = {"speaker": speaker, "text": text.strip(), "timestamp": now_str}
            self.recent_turns.append(entry)
            if len(self.recent_turns) > 40:
                self.recent_turns.pop(0)

            # 1. Append to JSONL for fast programmatic indexing
            try:
                with open(CONVERSATION_JSONL, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass

            # 2. Append to human-readable Markdown episodic journal
            try:
                date_header = datetime.now().strftime("### Session: %Y-%m-%d")
                write_header = not CONVERSATION_MD.exists() or date_header not in CONVERSATION_MD.read_text(encoding="utf-8")
                with open(CONVERSATION_MD, "a", encoding="utf-8") as f:
                    if write_header:
                        f.write(f"\n\n{date_header}\n\n")
                    f.write(f"- **[{now_str}] {speaker.title()}**: {text.strip()}\n")
            except Exception:
                pass

    def extract_and_store_facts(self, text: str) -> List[Dict[str, str]]:
        """
        Extracts semantic facts from user text and immediately commits them
        to authoritative Markdown memory and Knowledge Graph.
        """
        extracted: List[Dict[str, str]] = []
        clean_text = text.strip()

        # 1. Explicit Reminders ("remember that X", "yaad rakhna ki X")
        for p in PATTERNS_EXPLICIT_NOTE:
            m = p.search(clean_text)
            if m:
                fact = m.group(1).strip()
                if len(fact) > 3:
                    self.mem_svc.remember(
                        topic=f"Note: {fact[:35]}",
                        content=fact,
                        category="notes",
                        importance="High",
                        confidence="High"
                    )
                    extracted.append({"category": "notes", "content": fact})

        # 2. Identity & Name ("mera naam X hai", "my name is X")
        for p in PATTERNS_NAME:
            m = p.search(clean_text)
            if m:
                val = m.group(1).strip()
                if val and len(val) >= 2:
                    self.mem_svc.remember(
                        topic="User Name",
                        content=f"User's name is {val}",
                        category="personal",
                        importance="Critical",
                        confidence="High"
                    )
                    self.kg.add_relation("User", "name", val, confidence=1.0)
                    extracted.append({"category": "personal", "content": val})

        # 3. Location ("main Delhi se hoon", "main Noida me rehta hoon", "i live in X")
        for p in PATTERNS_LOCATION:
            m = p.search(clean_text)
            if m:
                loc = m.group(1).strip()
                if loc and len(loc) >= 2:
                    self.mem_svc.remember(
                        topic="Current Location",
                        content=f"User location: {loc}",
                        category="personal",
                        importance="High",
                        confidence="High"
                    )
                    self.kg.add_relation("User", "lives_in", loc, confidence=1.0)
                    extracted.append({"category": "personal", "content": loc})

        # 4. Occupation ("main ek software engineer hoon", "i am a developer")
        for p in PATTERNS_OCCUPATION:
            m = p.search(clean_text)
            if m:
                occ = clean_text
                self.mem_svc.remember(
                    topic="Profession",
                    content=occ,
                    category="personal",
                    importance="High",
                    confidence="High"
                )
                extracted.append({"category": "personal", "content": occ})

        # 5. Preferences (Hindi: "mujhe coffee pasand hai", "mujhe karela pasand nahi hai")
        for p in PATTERNS_PREF_HINDI:
            m = p.search(clean_text)
            if m:
                item = m.group(1).strip()
                sentiment = m.group(2).strip().lower()
                is_dislike = "nahi" in sentiment
                pref_type = "Dislikes" if is_dislike else "Likes"
                if len(item) >= 2:
                    self.mem_svc.remember(
                        topic=f"Preference: {item.title()}",
                        content=f"User {pref_type.lower()}: {item}",
                        category="preferences",
                        importance="High",
                        confidence="High"
                    )
                    self.kg.add_relation("User", pref_type.lower(), item, confidence=0.95)
                    extracted.append({"category": "preferences", "content": f"{pref_type}: {item}"})

        # 6. Preferences (English likes & dislikes)
        for p in PATTERNS_PREF_EN_LIKE:
            m = p.search(clean_text)
            if m:
                item = m.group(1).strip()
                if len(item) >= 2:
                    self.mem_svc.remember(
                        topic=f"Preference: {item[:30].title()}",
                        content=f"User likes: {item}",
                        category="preferences",
                        importance="High",
                        confidence="High"
                    )
                    self.kg.add_relation("User", "likes", item, confidence=0.95)
                    extracted.append({"category": "preferences", "content": f"Likes: {item}"})

        for p in PATTERNS_PREF_EN_DISLIKE:
            m = p.search(clean_text)
            if m:
                item = m.group(1).strip()
                if len(item) >= 2:
                    self.mem_svc.remember(
                        topic=f"Dislike: {item[:30].title()}",
                        content=f"User dislikes: {item}",
                        category="preferences",
                        importance="High",
                        confidence="High"
                    )
                    self.kg.add_relation("User", "dislikes", item, confidence=0.95)
                    extracted.append({"category": "preferences", "content": f"Dislikes: {item}"})

        # 7. Favorites (Hindi: "mera favorite color blue hai")
        for p in PATTERNS_FAV_HI:
            m = p.search(clean_text)
            if m:
                fav_cat = m.group(1).strip().title()
                fav_val = m.group(2).strip()
                if len(fav_val) >= 2:
                    self.mem_svc.remember(
                        topic=f"Favorite {fav_cat}",
                        content=f"User favorite {fav_cat.lower()} is {fav_val}",
                        category="preferences",
                        importance="High",
                        confidence="High"
                    )
                    self.kg.add_relation("User", f"favorite_{fav_cat.lower()}", fav_val, confidence=1.0)
                    extracted.append({"category": "preferences", "content": f"Favorite {fav_cat}: {fav_val}"})

        # 8. Favorites (English: "my favorite food is biryani")
        for p in PATTERNS_FAV_EN:
            m = p.search(clean_text)
            if m:
                fav_cat = m.group(1).strip().title()
                fav_val = m.group(2).strip()
                if len(fav_val) >= 2:
                    self.mem_svc.remember(
                        topic=f"Favorite {fav_cat}",
                        content=f"User favorite {fav_cat.lower()} is {fav_val}",
                        category="preferences",
                        importance="High",
                        confidence="High"
                    )
                    self.kg.add_relation("User", f"favorite_{fav_cat.lower()}", fav_val, confidence=1.0)
                    extracted.append({"category": "preferences", "content": f"Favorite {fav_cat}: {fav_val}"})

        # 9. Projects (Hindi & English: "main ek website bana rha hoon", "working on X")
        for p in PATTERNS_PROJECTS:
            m = p.search(clean_text)
            if m:
                proj = m.group(len(m.groups())).strip()
                if len(proj) >= 3:
                    self.mem_svc.remember(
                        topic=f"Project: {proj[:35].title()}",
                        content=f"User active project: {proj}. Context: {clean_text}",
                        category="projects",
                        importance="High",
                        confidence="High"
                    )
                    self.kg.add_relation("User", "works_on", proj, confidence=1.0)
                    extracted.append({"category": "projects", "content": proj})

        # 10. Relationships ("mera dost Rohan hai", "my brother is Rohit", "mera bhai Amit")
        for p in PATTERNS_RELATIONSHIPS:
            m = p.search(clean_text)
            if m:
                rel_type = m.group(1).strip().title()
                person_name = m.group(2).strip()
                if len(person_name) >= 2:
                    self.mem_svc.remember(
                        topic=f"{rel_type}: {person_name.title()}",
                        content=f"{clean_text}",
                        category="relationships",
                        importance="High",
                        confidence="High"
                    )
                    self.kg.add_relation("User", rel_type.lower(), person_name, confidence=1.0)
                    extracted.append({"category": "relationships", "content": f"{rel_type}: {person_name}"})

        # 11. Possessions & Gadgets ("mere paas iPhone hai", "mera laptop MacBook hai")
        for p in PATTERNS_POSSESSIONS:
            m = p.search(clean_text)
            if m:
                gadget = m.group(1).strip()
                if len(gadget) >= 2:
                    self.mem_svc.remember(
                        topic=f"Hardware & Assets: {gadget[:30].title()}",
                        content=clean_text,
                        category="notes",
                        importance="Medium",
                        confidence="High"
                    )
                    extracted.append({"category": "notes", "content": gadget})

        # 12. Fallback Informational Statements
        # If user shares an informative statement that isn't a question or system command
        if not extracted:
            words = clean_text.split()
            is_question = clean_text.endswith("?") or any(clean_text.lower().startswith(q) for q in (
                "kya", "kaun", "kahan", "kab", "kaise", "kyun", "what", "who", "where", "when", "how", "why", "can you", "could you"
            ))
            is_command = any(clean_text.lower().startswith(cmd) for cmd in (
                "open", "kholo", "chalao", "play", "search", "close", "band karo", "shutdown", "restart", "send", "call"
            ))
            if len(words) >= 4 and not is_question and not is_command:
                has_self_ref = any(w in clean_text.lower() for w in (
                    "mera", "meri", "mere", "mujhe", "main", "hum", "my", "i have", "i want", "i am", "we", "our"
                ))
                if has_self_ref:
                    topic_title = " ".join(words[:4]).title()
                    self.mem_svc.remember(
                        topic=f"User Fact: {topic_title}",
                        content=clean_text,
                        category="notes",
                        importance="Medium",
                        confidence="High"
                    )
                    extracted.append({"category": "notes", "content": clean_text})

        return extracted

    def ingest_turn_async(self, user_text: str, assistant_response: Optional[str] = None) -> None:
        """
        Non-blocking ingestion called on every conversational turn.
        Runs fact extraction in a background worker so voice TTS is never delayed.
        """
        def _worker():
            try:
                # 1. Log episodic turn
                if user_text and user_text.strip():
                    self.append_conversation_turn("user", user_text)
                if assistant_response and assistant_response.strip():
                    self.append_conversation_turn("ansh", assistant_response)

                # 2. Extract and persist semantic facts
                if user_text and user_text.strip():
                    facts = self.extract_and_store_facts(user_text)
                    if facts:
                        print(f"[AutoRemember] 🧠 Auto-saved {len(facts)} memory facts from user utterance!")

                # 3. Publish to EventBus
                try:
                    from core.event_bus import EventBus, EventType
                    EventBus.get_instance().publish(
                        EventType.VOICE_INPUT,
                        {"user_text": user_text, "facts_extracted": len(facts) if 'facts' in locals() else 0},
                        source="auto_remember"
                    )
                except Exception:
                    pass
            except Exception as e:
                print(f"[AutoRemember] ⚠️ Background ingestion error: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def get_recent_conversation_summary(self, max_turns: int = 6) -> str:
        """Returns recent dialogue turns to maintain unbroken conversation context."""
        with _LOCK:
            if not self.recent_turns:
                return ""
            lines = ["RECENT CONVERSATION HISTORY:"]
            for turn in self.recent_turns[-max_turns:]:
                lines.append(f"- {turn.get('speaker', 'user').title()}: {turn.get('text', '')}")
            return "\n".join(lines)

    def search_conversation_history(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """Searches past conversation logs for occurrences of words or topics."""
        q_lower = query.lower().strip()
        matches: List[Dict[str, str]] = []
        if not q_lower:
            return matches

        with _LOCK:
            # 1. Search in-memory cache first (recent)
            for turn in reversed(self.recent_turns):
                if q_lower in turn.get("text", "").lower():
                    matches.append(turn)
                    if len(matches) >= limit:
                        return matches

            # 2. Fallback search in JSONL file
            if CONVERSATION_JSONL.exists() and len(matches) < limit:
                try:
                    with open(CONVERSATION_JSONL, "r", encoding="utf-8") as f:
                        for line in reversed(f.readlines()):
                            if line.strip():
                                entry = json.loads(line.strip())
                                if q_lower in entry.get("text", "").lower() and entry not in matches:
                                    matches.append(entry)
                                    if len(matches) >= limit:
                                        break
                except Exception:
                    pass

        return matches
