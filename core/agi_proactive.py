"""
core/agi_proactive.py — Proactive Intelligence System 2.0 for ANSH

Synthesizes multiple context streams (time of day, clipboard text, active goals,
system hardware load) and evaluates whether to issue a proactive recommendation.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Any, Optional

from actions.proactive import ProactiveEngine
from core.agi_memory import AGIMemoryEngine


class AGIProactiveBrain(ProactiveEngine):
    def __init__(
        self,
        min_silence_secs: int = 600,
        check_cooldown: int = 400,
        memory_engine: Optional[AGIMemoryEngine] = None
    ):
        super().__init__(min_silence_secs=min_silence_secs, check_cooldown=check_cooldown)
        self.memory_engine = memory_engine or AGIMemoryEngine()

    def build_enhanced_prompt(
        self,
        clipboard_text: str = "",
        system_telemetry: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Builds a comprehensive context prompt including memory, active goals, system telemetry, and clipboard.
        """
        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")

        # Memory & active goals
        mem_str = self.memory_engine.retrieve_relevant_context(query="proactive checkin")

        prompt_lines = [
            "[PROACTIVE_CHECK_2.0] You are initiating a context-aware proactive check-in.",
            f"Current time: {time_str}",
            "Memory & Active Goals Context:",
            mem_str if mem_str else "(No stored memory yet)",
        ]

        if clipboard_text:
            snippet = clipboard_text[:250].replace("\n", " ")
            prompt_lines.append(f"Recent Clipboard Snippet: \"{snippet}\"")

        if system_telemetry:
            cpu = system_telemetry.get("cpu_percent", "N/A")
            ram = system_telemetry.get("ram_percent", "N/A")
            prompt_lines.append(f"System Telemetry: CPU {cpu}%, RAM {ram}%")

        prompt_lines.extend([
            "",
            "Instructions:",
            "- Decide if there is a highly relevant, proactive action or helpful observation to share.",
            "- If active goals exist, offer a status update or next step recommendation.",
            "- Keep response concise (1-3 natural sentences).",
            "- If nothing helpful or urgent exists, output strictly '[SILENCE]'."
        ])

        return "\n".join(prompt_lines)
