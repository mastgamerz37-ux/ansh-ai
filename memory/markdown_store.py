# markdown_store.py
# ANSH AI Intelligent Long-Term Memory System — Storage Layer
# Authoritative human-readable Markdown storage with atomic writes and path safety.

from __future__ import annotations

import os
import re
import sys
import tempfile
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


MEMORY_STORAGE_DIR = _get_base_dir() / "memory" / "storage"
_LOCK = threading.RLock()


@dataclass
class MemoryEntry:
    topic: str
    content: str
    category: str = "notes"
    importance: str = "Medium"     # Critical | High | Medium | Low | Temporary
    confidence: str = "High"       # High | Medium | Low
    status: str = "Current"        # Current | Historical | Deprecated
    created: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    file_path: Optional[str] = None


    def to_markdown(self) -> str:
        lines = [f"## {self.topic}"]
        lines.append(f"- **Content**: {self.content.strip()}")
        lines.append(f"- **Importance**: {self.importance}")
        lines.append(f"- **Confidence**: {self.confidence}")
        lines.append(f"- **Status**: {self.status}")
        lines.append(f"- **Created**: {self.created}")
        lines.append(f"- **Last Updated**: {self.updated}")
        if self.tags:
            lines.append(f"- **Tags**: {', '.join(self.tags)}")
        if self.notes:
            lines.append(f"- **Notes**: {self.notes.strip()}")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


class MarkdownStore:
    """
    Manages safe reading, writing, updating, and deletion of Markdown memory files.
    Ensures zero data loss with atomic writes and enforces path traversal guards.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        self.root = (root_dir or MEMORY_STORAGE_DIR).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_or_name: str) -> Path:
        """Resolve and prevent path traversal outside root storage directory."""
        clean_name = relative_or_name.strip().replace("\\", "/")
        if not clean_name.endswith(".md"):
            clean_name += ".md"
        target = (self.root / clean_name).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError(f"Security Alert: Path traversal attempt detected: {relative_or_name}")
        return target

    def _category_to_filename(self, category: str) -> str:
        """Map category to logical markdown filename or folder/file."""
        cat = category.strip().lower().replace(" ", "_")
        # Support nested categories like "projects/school_management"
        if "/" in cat:
            parts = [re.sub(r"[^a-zA-Z0-9_-]", "", p) for p in cat.split("/") if p]
            return "/".join(parts) + ".md"
        safe = re.sub(r"[^a-zA-Z0-9_-]", "", cat)
        return f"{safe or 'notes'}.md"

    def parse_file(self, file_path: Path) -> List[MemoryEntry]:
        """Parse a markdown file into structured MemoryEntry objects."""
        if not file_path.exists() or not file_path.is_file():
            return []

        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[MarkdownStore] Failed reading {file_path.name}: {e}")
            return []

        entries: List[MemoryEntry] = []
        rel_path = file_path.relative_to(self.root).as_posix()
        default_cat = file_path.stem.replace("_", " ")

        # Match sections starting with ## Topic
        sections = re.split(r"\n(?=##\s+)", text)
        for sec in sections:
            sec = sec.strip()
            if not sec.startswith("##"):
                continue

            lines = sec.splitlines()
            topic_line = lines[0].lstrip("#").strip()
            if not topic_line:
                continue

            content = ""
            importance = "Medium"
            confidence = "High"
            status = "Current"
            created = datetime.now().strftime("%Y-%m-%d")
            updated = created
            tags: List[str] = []
            notes = ""

            for line in lines[1:]:
                line = line.strip()
                if re.match(r"^-\s*\*{1,2}(Content|Value)\*{1,2}:\s*", line, re.IGNORECASE):
                    content = re.sub(r"^-\s*\*{1,2}(Content|Value)\*{1,2}:\s*", "", line, flags=re.IGNORECASE).strip()
                elif re.match(r"^-\s*\*{1,2}Importance\*{1,2}:\s*", line, re.IGNORECASE):
                    importance = re.sub(r"^-\s*\*{1,2}Importance\*{1,2}:\s*", "", line, flags=re.IGNORECASE).strip().title()
                elif re.match(r"^-\s*\*{1,2}Confidence\*{1,2}:\s*", line, re.IGNORECASE):
                    confidence = re.sub(r"^-\s*\*{1,2}Confidence\*{1,2}:\s*", "", line, flags=re.IGNORECASE).strip().title()
                elif re.match(r"^-\s*\*{1,2}Status\*{1,2}:\s*", line, re.IGNORECASE):
                    status = re.sub(r"^-\s*\*{1,2}Status\*{1,2}:\s*", "", line, flags=re.IGNORECASE).strip().title()
                elif re.match(r"^-\s*\*{1,2}Created\*{1,2}:\s*", line, re.IGNORECASE):
                    created = re.sub(r"^-\s*\*{1,2}Created\*{1,2}:\s*", "", line, flags=re.IGNORECASE).strip()
                elif re.match(r"^-\s*\*{1,2}Last Updated\*{1,2}:\s*", line, re.IGNORECASE):
                    updated = re.sub(r"^-\s*\*{1,2}Last Updated\*{1,2}:\s*", "", line, flags=re.IGNORECASE).strip()
                elif re.match(r"^-\s*\*{1,2}Tags\*{1,2}:\s*", line, re.IGNORECASE):
                    raw_tags = re.sub(r"^-\s*\*{1,2}Tags\*{1,2}:\s*", "", line, flags=re.IGNORECASE).strip()
                    tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
                elif re.match(r"^-\s*\*{1,2}Notes\*{1,2}:\s*", line, re.IGNORECASE):
                    notes = re.sub(r"^-\s*\*{1,2}Notes\*{1,2}:\s*", "", line, flags=re.IGNORECASE).strip()
                elif not content and line and not line.startswith("- **") and not line.startswith("- *"):
                    # Fallback for plain paragraph content
                    content += (" " + line if content else line)

            if not content:
                content = topic_line

            entries.append(
                MemoryEntry(
                    topic=topic_line,
                    content=content,
                    category=default_cat,
                    importance=importance if importance in ("Critical", "High", "Medium", "Low", "Temporary") else "Medium",
                    confidence=confidence if confidence in ("High", "Medium", "Low") else "High",
                    status=status if status in ("Current", "Historical", "Deprecated") else "Current",
                    created=created,
                    updated=updated,
                    tags=tags,
                    notes=notes,
                    file_path=rel_path,
                )
            )

        return entries

    def list_all_files(self) -> List[Path]:
        """List all .md files in the storage hierarchy."""
        if not self.root.exists():
            return []
        return sorted(list(self.root.rglob("*.md")))

    def load_all_entries(self) -> List[MemoryEntry]:
        """Load all memory entries from all markdown files."""
        with _LOCK:
            all_entries = []
            for file_path in self.list_all_files():
                all_entries.extend(self.parse_file(file_path))
            return all_entries

    def write_entries_to_file(self, target_path: Path, category_title: str, entries: List[MemoryEntry]) -> bool:
        """
        Atomically write a list of entries to a markdown file using temporary swap.
        """
        with _LOCK:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            header = f"# {category_title.replace('_', ' ').title()}\n\n"
            content_blocks = [header]

            # Sort entries by Status (Current first), then Importance (Critical > High > Medium > Low), then Last Updated
            imp_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Temporary": 4}
            stat_rank = {"Current": 0, "Historical": 1, "Deprecated": 2}

            sorted_entries = sorted(
                entries,
                key=lambda e: (
                    stat_rank.get(e.status, 9),
                    imp_rank.get(e.importance, 9),
                    e.updated or "",
                ),
            )

            for entry in sorted_entries:
                content_blocks.append(entry.to_markdown())

            final_text = "\n".join(content_blocks).strip() + "\n"

            # Atomic file replacement
            tmp_fd, tmp_path = tempfile.mkstemp(dir=target_path.parent, prefix="mem_", suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    f.write(final_text)
                os.replace(tmp_path, str(target_path))
                return True
            except Exception as e:
                print(f"[MarkdownStore] Atomic write failed for {target_path.name}: {e}")
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                return False

    def upsert_entry(self, entry: MemoryEntry, category_override: Optional[str] = None) -> bool:
        """
        Insert or update a memory entry in the appropriate markdown file.
        """
        with _LOCK:
            cat = category_override or entry.category or "notes"
            rel_file = self._category_to_filename(cat)
            file_path = self._resolve_safe_path(rel_file)

            existing_entries = self.parse_file(file_path)
            updated = False

            topic_key = entry.topic.strip().lower()

            for i, ex in enumerate(existing_entries):
                if ex.topic.strip().lower() == topic_key:
                    # Update existing
                    entry.created = ex.created  # Keep original creation date
                    entry.updated = datetime.now().strftime("%Y-%m-%d")
                    entry.file_path = rel_file
                    existing_entries[i] = entry
                    updated = True
                    break

            if not updated:
                entry.file_path = rel_file
                entry.updated = datetime.now().strftime("%Y-%m-%d")
                existing_entries.append(entry)

            cat_title = cat.split("/")[-1].replace("_", " ").title()
            return self.write_entries_to_file(file_path, cat_title, existing_entries)

    def delete_entry(self, topic: str, category: Optional[str] = None) -> bool:
        """
        Delete a memory entry by topic from a specific category or across all files.
        """
        with _LOCK:
            topic_key = topic.strip().lower()
            files_to_check = []

            if category:
                rel_file = self._category_to_filename(category)
                file_path = self._resolve_safe_path(rel_file)
                if file_path.exists():
                    files_to_check.append(file_path)
            else:
                files_to_check = self.list_all_files()

            deleted_any = False
            for fp in files_to_check:
                entries = self.parse_file(fp)
                new_entries = [e for e in entries if e.topic.strip().lower() != topic_key]
                if len(new_entries) != len(entries):
                    cat_title = fp.stem.replace("_", " ").title()
                    if new_entries:
                        self.write_entries_to_file(fp, cat_title, new_entries)
                    else:
                        try:
                            fp.unlink()
                        except Exception:
                            pass
                    deleted_any = True

            return deleted_any
