"""
core/affective_engine.py — ANSH Affective & Emotional Intelligence Engine
Provides real-time multimodal emotion perception, dynamic personality adaptation,
subtle sentiment analysis, and mood history tracking across user sessions.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DATA_DIR = BASE_DIR / "data" / "secure"
MOOD_HISTORY_PATH = DATA_DIR / "mood_history.json"


class EmotionalState(str, Enum):
    NEUTRAL = "neutral"
    JOYFUL_CASUAL = "joyful_casual"
    FOCUSED_SERIOUS = "focused_serious"
    FRUSTRATED_STRESSED = "frustrated_stressed"
    TIRED_EXHAUSTED = "tired_exhausted"
    CURIOUS_EXCITED = "curious_excited"


class PersonalityMode(str, Enum):
    NORMAL = "normal"              # Balanced witty savage friend
    DEVELOPER = "developer"        # Tech-focused, git/code/terminal oriented, ultra-concise
    TEACHER = "teacher"            # Patient, pedagogical, structured explanations, analogies
    ANALYST = "analyst"            # Data-driven, objective, comparative, bulleted breakdown
    FUN = "fun"                    # Maximum savage roasts, gaming banter, playful Hinglish humor
    PROFESSIONAL = "professional"  # Formal, polite, zero roast, executive briefing style


@dataclass
class EmotionSnapshot:
    state: EmotionalState
    confidence: float
    valence: float  # -1.0 (negative) to +1.0 (positive)
    arousal: float  # 0.0 (calm/lethargic) to 1.0 (highly excited/agitated)
    timestamp: float = field(default_factory=time.time)
    dominant_cues: List[str] = field(default_factory=list)
    source: str = "multimodal"  # "text", "voice", "vision", or "multimodal"


@dataclass
class PersonalityProfile:
    sarcasm_level: float  # 0.0 (strictly empathetic & professional) to 1.0 (full savage roast mode)
    empathy_level: float  # 0.0 to 1.0
    verbosity_bias: float  # -1.0 (extremely concise) to +1.0 (thorough / elaborative)
    tone_description: str
    suggested_vernacular_fillers: List[str]
    system_prompt_modifier: str


class AffectiveEngine:
    """
    ANSH Affective & Emotional Intelligence System.
    Monitors user interactions across text, voice prosody, and visual cues to continuously
    adapt ANSH's attitude, sarcasm level, tone, and empathy.
    """

    _instance: Optional[AffectiveEngine] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> AffectiveEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.current_state: EmotionalState = EmotionalState.NEUTRAL
        self.active_mode: PersonalityMode = PersonalityMode.NORMAL
        self.current_valence: float = 0.0
        self.current_arousal: float = 0.3
        self.last_update_time: float = time.time()
        self.history: List[Dict[str, Any]] = []
        self._load_history()

        # Compile pattern matchers for fast semantic sentiment analysis
        self._frustration_patterns = [
            re.compile(r"\b(why\s+(won't|doesn't|isn't)|broken|stupid|fail(ed|ing)?|annoying|hate|error|stuck|bug|crash(ed)?|damn|argh|wtf|ugh)\b", re.IGNORECASE),
            re.compile(r"\b(not\s+working|tired\s+of|again\?|waste\s+of\s+time|irritat(ed|ing)|sick\s+of)\b", re.IGNORECASE),
            re.compile(r"(!{2,}|\?{2,})"),  # multiple punctuation marks
        ]
        self._fatigue_patterns = [
            re.compile(r"\b(tired|exhausted|sleepy|headache|late\s+night|long\s+day|need\s+(sleep|break|coffee)|burning\s+out)\b", re.IGNORECASE),
            re.compile(r"\b(drowsy|yawn|drained|can't\s+think|my\s+eyes\s+hurt)\b", re.IGNORECASE),
        ]
        self._joy_casual_patterns = [
            re.compile(r"\b(haha|lol|lmao|nice|awesome|great|cool|roast\s+me|bro|bhai|fun|party|vibes|amazing|kya\s+baat)\b", re.IGNORECASE),
            re.compile(r"(😂|🤣|🔥|🎉|😎|❤️|✨)"),
        ]
        self._focus_patterns = [
            re.compile(r"\b(refactor|deploy|optimize|fix\s+this|analyze|implement|architecture|review\s+code|pipeline|database)\b", re.IGNORECASE),
            re.compile(r"\b(quick|hurry|production|urgent|critical|deadline)\b", re.IGNORECASE),
        ]
        self._curiosity_patterns = [
            re.compile(r"\b(how\s+does|what\s+if|tell\s+me\s+about|explain|could\s+we|curious|interesting|wonder)\b", re.IGNORECASE),
            re.compile(r"\b(teach\s+me|deep\s+dive|research|explore)\b", re.IGNORECASE),
        ]

    def set_personality_mode(self, mode: PersonalityMode) -> str:
        """Explicitly switch ANSH's personality mode (Normal, Developer, Teacher, Analyst, Fun, Professional)."""
        with self._lock:
            self.active_mode = mode
            return f"🎭 ANSH Personality Mode switched to: {mode.value.upper()}"

    def resolve_referential_pronouns(self, user_text: str, last_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Resolves ambiguous conversational references ('ye', 'woh', 'isko', 'usko', 'this', 'that')
        to their explicit entity names from recent working context.
        """
        if not user_text or not last_context:
            return user_text

        resolved = user_text
        target_name = last_context.get("last_target") or last_context.get("active_file") or last_context.get("active_app")

        if target_name:
            # Replace common Hindi/English demonstrative pronouns
            patterns = [
                (r"\b(isko|ise|iss cheez ko)\b", f"'{target_name}'"),
                (r"\b(usko|use|uss cheez ko)\b", f"'{target_name}'"),
                (r"\b(ye|yeh)\b(?=\s+(kya|chalao|kholo|band|delete|copy|run|open|close))", f"'{target_name}'"),
                (r"\b(woh|voh)\b(?=\s+(kya|chalao|kholo|band|delete|copy|run|open|close))", f"'{target_name}'"),
                (r"\b(this|that)\b(?=\s+(one|file|app|window|task))", f"'{target_name}'"),
            ]
            for pat, repl in patterns:
                resolved = re.sub(pat, repl, resolved, flags=re.IGNORECASE)

        return resolved


    def _load_history(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if MOOD_HISTORY_PATH.exists():
                data = json.loads(MOOD_HISTORY_PATH.read_text(encoding="utf-8"))
                self.history = data.get("snapshots", [])[-200:]
                if self.history:
                    latest = self.history[-1]
                    self.current_state = EmotionalState(latest.get("state", EmotionalState.NEUTRAL.value))
                    self.current_valence = latest.get("valence", 0.0)
                    self.current_arousal = latest.get("arousal", 0.3)
        except Exception as e:
            print(f"[AffectiveEngine] ⚠️ History load warning: {e}")
            self.history = []

    def _save_history(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            payload = {
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "current_state": self.current_state.value,
                "snapshots": self.history[-200:],
            }
            MOOD_HISTORY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[AffectiveEngine] ⚠️ History save warning: {e}")

    def analyze_text_sentiment(self, text: str) -> EmotionSnapshot:
        """Analyzes text for subtle sentiment, valence, and emotional state."""
        if not text or not text.strip():
            return EmotionSnapshot(state=self.current_state, confidence=0.5, valence=self.current_valence, arousal=self.current_arousal, source="text")

        cues: List[str] = []
        frust_score = sum(len(p.findall(text)) for p in self._frustration_patterns)
        fatigue_score = sum(len(p.findall(text)) for p in self._fatigue_patterns)
        joy_score = sum(len(p.findall(text)) for p in self._joy_casual_patterns)
        focus_score = sum(len(p.findall(text)) for p in self._focus_patterns)
        curious_score = sum(len(p.findall(text)) for p in self._curiosity_patterns)

        # Compute emotional valence and arousal
        valence = 0.0
        arousal = 0.3

        if frust_score > 0:
            cues.append(f"frustration_keywords({frust_score})")
            valence -= min(1.0, frust_score * 0.4)
            arousal += min(0.6, frust_score * 0.25)

        if fatigue_score > 0:
            cues.append(f"fatigue_markers({fatigue_score})")
            valence -= min(0.4, fatigue_score * 0.2)
            arousal = max(0.1, arousal - fatigue_score * 0.2)

        if joy_score > 0:
            cues.append(f"joy_humor({joy_score})")
            valence += min(1.0, joy_score * 0.35)
            arousal += min(0.5, joy_score * 0.2)

        if focus_score > 0:
            cues.append(f"focus_technical({focus_score})")
            arousal += min(0.4, focus_score * 0.15)

        if curious_score > 0:
            cues.append(f"curiosity({curious_score})")
            valence += 0.2
            arousal += 0.3

        # Clamp valence and arousal
        valence = max(-1.0, min(1.0, valence))
        arousal = max(0.0, min(1.0, arousal))

        # Classify state
        state = EmotionalState.NEUTRAL
        confidence = 0.6

        if frust_score >= 1 and frust_score >= joy_score:
            state = EmotionalState.FRUSTRATED_STRESSED
            confidence = min(0.95, 0.6 + frust_score * 0.15)
        elif fatigue_score >= 1:
            state = EmotionalState.TIRED_EXHAUSTED
            confidence = min(0.9, 0.65 + fatigue_score * 0.15)
        elif joy_score >= 1:
            state = EmotionalState.JOYFUL_CASUAL
            confidence = min(0.95, 0.65 + joy_score * 0.15)
        elif focus_score >= 2:
            state = EmotionalState.FOCUSED_SERIOUS
            confidence = min(0.85, 0.6 + focus_score * 0.1)
        elif curious_score >= 1:
            state = EmotionalState.CURIOUS_EXCITED
            confidence = 0.75

        return EmotionSnapshot(
            state=state,
            confidence=confidence,
            valence=round(valence, 2),
            arousal=round(arousal, 2),
            dominant_cues=cues,
            source="text"
        )

    def update_multimodal_state(
        self,
        text: Optional[str] = None,
        facial_expression: Optional[str] = None,
        voice_prosody_pitch_variance: Optional[float] = None,
        is_speech_fast: Optional[bool] = None,
    ) -> PersonalityProfile:
        """
        Ingests multimodal signals (text, vision, audio prosody) and dynamically
        updates ANSH's active emotional state and personality profile.
        """
        with self._lock:
            snapshot: Optional[EmotionSnapshot] = None
            if text:
                snapshot = self.analyze_text_sentiment(text)

            # Vision override/boost if facial expression detected
            if facial_expression:
                expr_lower = facial_expression.lower()
                if any(k in expr_lower for k in ("smile", "laugh", "happy")):
                    if snapshot:
                        snapshot.valence = min(1.0, snapshot.valence + 0.3)
                        if snapshot.state in (EmotionalState.NEUTRAL, EmotionalState.FOCUSED_SERIOUS):
                            snapshot.state = EmotionalState.JOYFUL_CASUAL
                elif any(k in expr_lower for k in ("frown", "angry", "stressed", "tense")):
                    if snapshot:
                        snapshot.valence = max(-1.0, snapshot.valence - 0.3)
                        snapshot.state = EmotionalState.FRUSTRATED_STRESSED
                elif any(k in expr_lower for k in ("yawn", "sleepy", "eyes_closed", "fatigue")):
                    if snapshot:
                        snapshot.state = EmotionalState.TIRED_EXHAUSTED

            # Apply state decay / transition
            if snapshot:
                self.current_state = snapshot.state
                self.current_valence = snapshot.valence
                self.current_arousal = snapshot.arousal
                self.last_update_time = time.time()

                # Record in history
                self.history.append({
                    "timestamp": time.time(),
                    "state": self.current_state.value,
                    "valence": self.current_valence,
                    "arousal": self.current_arousal,
                    "cues": snapshot.dominant_cues,
                    "source": snapshot.source,
                })
                if len(self.history) % 5 == 0:
                    self._save_history()

            return self.get_personality_profile()

    def get_personality_profile(self) -> PersonalityProfile:
        """
        Generates the real-time personality profile and prompt instructions
        based on the user's active emotional state.
        """
        state = self.current_state

        if state == EmotionalState.FRUSTRATED_STRESSED:
            return PersonalityProfile(
                sarcasm_level=0.0,
                empathy_level=0.95,
                verbosity_bias=-0.3,
                tone_description="Calm, deeply reassuring, laser-focused problem solver with zero sarcasm.",
                suggested_vernacular_fillers=["Main hoon na boss", "Fret not", "Relax bhai, dekhte hain ise", "Let me handle this completely"],
                system_prompt_modifier=(
                    "[DYNAMIC PERSONALITY ADAPTATION - FRUSTRATION/STRESS DETECTED]:\n"
                    "- The user is feeling frustrated, stressed, or hitting a roadblock.\n"
                    "- IMMEDIATELY SUPPRESS all playful roasts, sarcasm, or teasing.\n"
                    "- Speak in a calm, soothing, highly competent and reassuring tone.\n"
                    "- Execute solutions directly, clearly, and step-by-step with zero fluff."
                )
            )

        elif state == EmotionalState.TIRED_EXHAUSTED:
            return PersonalityProfile(
                sarcasm_level=0.1,
                empathy_level=1.0,
                verbosity_bias=-0.5,
                tone_description="Gentle, caring, low-energy and helpful companion.",
                suggested_vernacular_fillers=["Thak gaye ho lagta hai", "Take it easy", "Bhai thoda break le lo", "Main handle kar leta hoon"],
                system_prompt_modifier=(
                    "[DYNAMIC PERSONALITY ADAPTATION - FATIGUE DETECTED]:\n"
                    "- The user is tired, exhausted, or working late.\n"
                    "- Speak gently, softly, and keep responses concise and restful.\n"
                    "- Offer to automate mundane steps so they don't have to strain."
                )
            )

        elif state == EmotionalState.FOCUSED_SERIOUS:
            return PersonalityProfile(
                sarcasm_level=0.2,
                empathy_level=0.4,
                verbosity_bias=-0.6,
                tone_description="Ultra-crisp, efficient, high-cadence engineering partner.",
                suggested_vernacular_fillers=["On it", "Done", "Directly executing", "Got it boss"],
                system_prompt_modifier=(
                    "[DYNAMIC PERSONALITY ADAPTATION - DEEP FOCUS / URGENT TASK]:\n"
                    "- The user is deeply locked into coding/work with high urgency.\n"
                    "- Keep answers laser-focused, ultra-brief, and technically exact.\n"
                    "- Skip pleasantries and execute directly."
                )
            )

        elif state == EmotionalState.JOYFUL_CASUAL:
            return PersonalityProfile(
                sarcasm_level=0.9,
                empathy_level=0.5,
                verbosity_bias=0.2,
                tone_description="Full attitude, playfully savage, hilarious roasts, and high-energy Hinglish swag.",
                suggested_vernacular_fillers=["Arey bhai bhai!", "Sahi hai boss", "Kya baat hai!", "Listen up", "Abe yaar!"],
                system_prompt_modifier=(
                    "[DYNAMIC PERSONALITY ADAPTATION - PLAYFUL & SAVAGE MODE ACTIVE]:\n"
                    "- The user is relaxed, happy, or having fun!\n"
                    "- Unleash your full ANSH savage attitude, sharp humor, bold comebacks, and friendly roasts!\n"
                    "- Use energetic Hinglish expressions and witty punchlines while nailing the task 100%."
                )
            )

        elif state == EmotionalState.CURIOUS_EXCITED:
            return PersonalityProfile(
                sarcasm_level=0.4,
                empathy_level=0.7,
                verbosity_bias=0.5,
                tone_description="Insightful, intellectually curious, encouraging mentor.",
                suggested_vernacular_fillers=["Yeh badhiya sawaal hai!", "Check this out", "Arey mast concept hai"],
                system_prompt_modifier=(
                    "[DYNAMIC PERSONALITY ADAPTATION - INTELLECTUAL CURIOSITY]:\n"
                    "- The user is curious and exploring an interesting problem or new technology.\n"
                    "- Provide deep, fascinating insights, clear mental models, and creative suggestions."
                )
            )

        else:  # NEUTRAL
            return PersonalityProfile(
                sarcasm_level=0.6,
                empathy_level=0.6,
                verbosity_bias=0.0,
                tone_description="Balanced, witty, confident, and proactive AI friend.",
                suggested_vernacular_fillers=["Haan boss", "Bilkul", "Listen up", "Check this out"],
                system_prompt_modifier=(
                    "[DYNAMIC PERSONALITY ADAPTATION - BALANCED]:\n"
                    "- Stay natural, friendly, confident, and ready for action."
                )
            )
