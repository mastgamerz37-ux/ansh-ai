"""
actions/study_mode.py — ANSH Study & Learning Intelligence Engine

Provides:
- Study Mode (Interactive chapter & concept tutor)
- High-yield Notes Generation (from text or topics)
- Doubt Solving & Concept Breakdown
- Flashcards & Interactive Quiz Mode
- Weak Topic Detection & Revision Planning
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.task_llm import call_task_llm


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DATA_DIR = BASE_DIR / "data" / "study"
PROGRESS_FILE = DATA_DIR / "study_progress.json"


@dataclass
class Flashcard:
    id: int
    front: str
    back: str
    hint: Optional[str] = None


@dataclass
class QuizQuestion:
    question_number: int
    question: str
    options: List[str]
    correct_option_index: int
    explanation: str


class StudyEngine:
    """
    ANSH Study & Learning Engine.
    Acts as an ultra-smart personal tutor, creating notes, quizzes, flashcards,
    and tracking weak areas for active recall.
    """

    _instance: Optional[StudyEngine] = None

    @classmethod
    def get_instance(cls) -> StudyEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.progress: Dict[str, Any] = self._load_progress()

    def _load_progress(self) -> Dict[str, Any]:
        if PROGRESS_FILE.exists():
            try:
                return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"topics": {}, "quizzes_taken": 0, "flashcards_reviewed": 0}

    def _save_progress(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            PROGRESS_FILE.write_text(json.dumps(self.progress, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[StudyEngine] Progress save note: {e}")

    def generate_notes(self, topic: str, source_content: Optional[str] = None) -> str:
        """Generates comprehensive, high-yield study notes with key terms and examples."""
        system_prompt = (
            "You are ANSH's Master Teacher & Academic Intelligence Engine.\n"
            "Generate structured, high-yield study notes on the given topic.\n"
            "Format with:\n"
            "1. 📌 Core Mental Model (Intuitive summary in 2 sentences)\n"
            "2. 🔑 Key Concepts & Definitions\n"
            "3. ⚡ Rules, Formulas, or Code Examples\n"
            "4. 💡 Real-world Analogies / Hinglish mnemonic tips\n"
            "5. ⚠️ Common Traps & Exam Pitfalls\n"
            "6. 📝 Quick 3-Question Self-Check"
        )
        user_prompt = f"Topic: {topic}"
        if source_content:
            user_prompt += f"\n\nSource Material/Text:\n{source_content[:4000]}"

        return call_task_llm(prompt=user_prompt, system=system_prompt, temperature=0.3)

    def solve_doubt(self, doubt: str, topic_context: Optional[str] = None) -> str:
        """Solves an academic doubt step-by-step with intuitive analogies."""
        system_prompt = (
            "You are ANSH in Teacher Mode. Explain the user's doubt clearly, patiently, "
            "and intuitively. Use simple analogies, clear steps, and Hinglish encouragement."
        )
        prompt = f"Doubt: {doubt}"
        if topic_context:
            prompt += f"\nContext: {topic_context}"

        return call_task_llm(prompt=prompt, system=system_prompt, temperature=0.4)

    def generate_quiz(self, topic: str, num_questions: int = 5) -> List[QuizQuestion]:
        """Generates multiple choice quiz questions with explanations for active recall."""
        system_prompt = (
            "You are an assessment engine. Return a JSON object with a 'questions' array.\n"
            "Each question has:\n"
            "- question_number (int)\n"
            "- question (str)\n"
            "- options (list of 4 strings)\n"
            "- correct_option_index (int: 0, 1, 2, or 3)\n"
            "- explanation (str)"
        )
        prompt = f"Generate {num_questions} conceptual MCQ quiz questions on: {topic}"
        try:
            raw = call_task_llm(prompt=prompt, system=system_prompt, json_mode=True, temperature=0.3)
            data = json.loads(raw)
            questions: List[QuizQuestion] = []
            for q in data.get("questions", []):
                questions.append(QuizQuestion(
                    question_number=q.get("question_number", len(questions) + 1),
                    question=q.get("question", ""),
                    options=q.get("options", []),
                    correct_option_index=q.get("correct_option_index", 0),
                    explanation=q.get("explanation", ""),
                ))
            return questions
        except Exception as e:
            print(f"[StudyEngine] Quiz generation error: {e}")
            return []

    def generate_flashcards(self, topic: str, count: int = 8) -> List[Flashcard]:
        """Generates flashcards (Front: Concept, Back: Explanation/Formula)."""
        system_prompt = (
            "Generate flashcards for spaced repetition. Return JSON with 'flashcards' list of objects:\n"
            "- id (int)\n"
            "- front (str: concept or question)\n"
            "- back (str: crisp answer or definition)\n"
            "- hint (str or null)"
        )
        prompt = f"Create {count} high-yield flashcards for: {topic}"
        try:
            raw = call_task_llm(prompt=prompt, system=system_prompt, json_mode=True, temperature=0.3)
            data = json.loads(raw)
            cards = [Flashcard(**c) for c in data.get("flashcards", [])]
            return cards
        except Exception as e:
            print(f"[StudyEngine] Flashcard error: {e}")
            return []

    def record_quiz_result(self, topic: str, score: float, total: int, weak_subtopics: Optional[List[str]] = None) -> str:
        """Records student performance, updating mastery score and weak areas."""
        pct = (score / total) * 100.0 if total > 0 else 0.0
        topics_data = self.progress.setdefault("topics", {})
        topic_entry = topics_data.setdefault(topic, {
            "attempts": 0,
            "best_score_pct": 0.0,
            "last_score_pct": 0.0,
            "weak_points": [],
            "last_reviewed": time.time(),
        })

        topic_entry["attempts"] += 1
        topic_entry["last_score_pct"] = round(pct, 1)
        topic_entry["best_score_pct"] = max(topic_entry["best_score_pct"], round(pct, 1))
        if weak_subtopics:
            existing_weak = set(topic_entry.get("weak_points", []))
            existing_weak.update(weak_subtopics)
            topic_entry["weak_points"] = list(existing_weak)

        self.progress["quizzes_taken"] = self.progress.get("quizzes_taken", 0) + 1
        self._save_progress()

        return (
            f"📊 Quiz recorded for {topic}! Score: {int(score)}/{total} ({pct:.1f}%).\n"
            f"Mastery rating: {'🌟 Mastery' if pct >= 80 else '⚠️ Needs Revision' if pct < 60 else '👍 Proficient'}."
        )
