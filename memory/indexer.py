# indexer.py
# ANSH AI Intelligent Long-Term Memory System — In-Memory Search & Relevance Index
# Fast token-based retrieval with file mtime cache invalidation and multi-factor ranking.

from __future__ import annotations

import math
import os
import re
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from memory.markdown_store import MarkdownStore, MemoryEntry

_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "kya", "hai", "mujhe", "mera", "meri", "mere"
}


def _tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into clean words."""
    cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
    words = cleaned.split()
    return [w for w in words if len(w) > 1 and w not in _STOPWORDS]


@dataclass
class ScoredMemory:
    entry: MemoryEntry
    score: float
    matched_terms: List[str]


class MemoryIndex:
    """
    Maintains an in-memory index with automatic disk change detection via mtime.
    Computes multi-factor relevance ranking (Text Match + Importance + Confidence + Recency + Status).
    """

    def __init__(self, store: MarkdownStore):
        self.store = store
        self._entries: List[MemoryEntry] = []
        self._file_mtimes: Dict[str, float] = {}
        self._lock = threading.RLock()
        self.refresh(force=True)

    def _is_cache_stale(self) -> bool:
        """Check if any markdown file on disk was modified externally."""
        current_files = self.store.list_all_files()
        if len(current_files) != len(self._file_mtimes):
            return True

        for fp in current_files:
            rel = fp.as_posix()
            try:
                mtime = fp.stat().st_mtime
                if rel not in self._file_mtimes or self._file_mtimes[rel] != mtime:
                    return True
            except Exception:
                return True
        return False

    def refresh(self, force: bool = False) -> None:
        """Reload entries from disk if cache is stale or forced."""
        with self._lock:
            if not force and not self._is_cache_stale():
                return

            all_entries: List[MemoryEntry] = []
            new_mtimes: Dict[str, float] = {}

            for fp in self.store.list_all_files():
                rel = fp.as_posix()
                try:
                    new_mtimes[rel] = fp.stat().st_mtime
                    parsed = self.store.parse_file(fp)
                    all_entries.extend(parsed)
                except Exception as e:
                    print(f"[MemoryIndex] Failed reading {fp.name}: {e}")

            self._entries = all_entries
            self._file_mtimes = new_mtimes

    def get_all_entries(self) -> List[MemoryEntry]:
        self.refresh()
        with self._lock:
            return list(self._entries)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        include_historical: bool = False,
        min_importance: Optional[str] = None,
        limit: int = 10,
    ) -> List[ScoredMemory]:
        """
        Search memories with multi-factor relevance scoring.
        """
        self.refresh()
        with self._lock:
            if not query.strip():
                # Return highest priority current memories if query is blank
                candidates = [
                    e for e in self._entries
                    if (include_historical or e.status == "Current")
                    and (not category or e.category.lower() == category.lower())
                ]
                imp_map = {"Critical": 5.0, "High": 3.0, "Medium": 2.0, "Low": 1.0, "Temporary": 0.5}
                scored = [
                    ScoredMemory(entry=e, score=imp_map.get(e.importance, 1.0), matched_terms=[])
                    for e in candidates
                ]
                scored.sort(key=lambda s: s.score, reverse=True)
                return scored[:limit]

            query_tokens = _tokenize(query)
            query_lower = query.lower().strip()
            results: List[ScoredMemory] = []

            imp_weights = {
                "Critical": 2.2,
                "High": 1.6,
                "Medium": 1.0,
                "Low": 0.6,
                "Temporary": 0.3,
            }
            conf_weights = {"High": 1.2, "Medium": 1.0, "Low": 0.7}
            status_weights = {"Current": 1.0, "Historical": 0.35, "Deprecated": 0.05}

            # Pre-filter minimum importance if specified
            imp_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Temporary": 0}
            min_imp_level = imp_rank.get(min_importance or "Temporary", 0)

            now_epoch = time.time()

            for entry in self._entries:
                if not include_historical and entry.status != "Current":
                    continue

                if category and entry.category.lower() != category.lower():
                    continue

                if imp_rank.get(entry.importance, 2) < min_imp_level:
                    continue

                # ── Text Relevance ────────────────────────────────────────────
                topic_lower = entry.topic.lower()
                content_lower = entry.content.lower()
                tags_lower = [t.lower() for t in entry.tags]

                entry_tokens = _tokenize(f"{entry.topic} {entry.content} {' '.join(entry.tags)} {entry.notes}")
                entry_token_set = set(entry_tokens)

                # 1. Exact phrase match boost
                base_score = 0.0
                matched_terms = []

                if query_lower in topic_lower:
                    base_score += 15.0
                    matched_terms.append(query_lower)
                elif query_lower in content_lower:
                    base_score += 8.0
                    matched_terms.append(query_lower)

                # 2. Token overlap & keyword match
                for q_tok in query_tokens:
                    if q_tok in topic_lower:
                        base_score += 6.0
                        matched_terms.append(q_tok)
                    elif q_tok in tags_lower:
                        base_score += 4.5
                        matched_terms.append(q_tok)
                    elif q_tok in entry_token_set:
                        # Frequency in entry
                        freq = entry_tokens.count(q_tok)
                        base_score += 2.0 * math.log(1 + freq)
                        matched_terms.append(q_tok)

                if base_score <= 0:
                    continue

                # 3. Factor in Importance & Confidence
                imp_mul = imp_weights.get(entry.importance, 1.0)
                conf_mul = conf_weights.get(entry.confidence, 1.0)
                stat_mul = status_weights.get(entry.status, 1.0)

                # 4. Factor in Recency (decay over time, but gently)
                dt = None
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(entry.updated, fmt)
                        break
                    except ValueError:
                        pass

                if dt:
                    days_ago = max(0.0, (now_epoch - dt.timestamp()) / 86400.0)
                    recency_mul = 1.0 / (1.0 + (days_ago / 90.0))  # Half-life ~90 days
                else:
                    recency_mul = 0.8

                final_score = base_score * imp_mul * conf_mul * stat_mul * (0.8 + 0.2 * recency_mul)

                results.append(
                    ScoredMemory(
                        entry=entry,
                        score=round(final_score, 3),
                        matched_terms=list(set(matched_terms)),
                    )
                )

            # Sort by score descending
            results.sort(key=lambda s: s.score, reverse=True)
            return results[:limit]
