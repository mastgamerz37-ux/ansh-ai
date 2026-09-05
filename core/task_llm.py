"""
core/task_llm.py — Dual AI Engine Dispatcher for ANSH.

Routing Strategy:
- Communication (Live Voice, Real-time Audio, Vision): Gemini Live (google-genai)
- Sub-Tasks & Actions (Code generation, dev agent, scripts, summarization, extraction, intent parsing):
  Primary: Groq (Ultra-fast LLMs like llama-3.3-70b-versatile, llama-3.1-8b-instant)
  Fallback: Gemini 2.5 Flash (if Groq key is missing, invalid, or rate-limited)
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

DEFAULT_GROQ_MODEL = "groq/compound-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[TaskLLM] ⚠️ Failed to load config: {e}")
    return {}


def save_config(updates: dict) -> None:
    try:
        data = load_config()
        data.update(updates)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(data, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[TaskLLM] ⚠️ Failed to save config: {e}")


def get_groq_api_key() -> str | None:
    cfg = load_config()
    key = cfg.get("groq_api_key") or os.environ.get("GROQ_API_KEY")
    if key and isinstance(key, str) and key.strip() and key.strip() != "YOUR_GROQ_API_KEY":
        return key.strip()
    return None


def get_gemini_api_key() -> str | None:
    cfg = load_config()
    key = cfg.get("gemini_api_key") or cfg.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if key and isinstance(key, str) and key.strip():
        return key.strip()
    return None


def _call_groq(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    from groq import Groq

    api_key = get_groq_api_key()
    if not api_key:
        raise ValueError("Groq API key not found.")

    client = Groq(api_key=api_key)
    selected_model = DEFAULT_GROQ_MODEL

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {
        "model": selected_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    return (choice.message.content or "").strip()


def _call_gemini(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
) -> str:
    from google import genai
    from google.genai import types

    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("Gemini API key not found.")

    client = genai.Client(api_key=api_key)
    selected_model = DEFAULT_GEMINI_MODEL

    config = types.GenerateContentConfig(
        system_instruction=system if system else None,
        temperature=temperature,
    )

    response = client.models.generate_content(
        model=selected_model,
        contents=prompt,
        config=config,
    )
    return (response.text or "").strip()


def call_task_llm(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    prefer_gemini: bool = False,
) -> str:
    """
    Execute task with Groq (primary) or Gemini (fallback).
    """
    groq_key = get_groq_api_key()

    if groq_key and not prefer_gemini:
        try:
            return _call_groq(
                prompt=prompt,
                system=system,
                model=model,
                json_mode=json_mode,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"[TaskLLM] ⚠️ Groq call failed ({e}). Falling back to Gemini...")

    # Fallback to Gemini
    return _call_gemini(
        prompt=prompt,
        system=system,
        model=DEFAULT_GEMINI_MODEL if model == DEFAULT_GROQ_MODEL else model,
        temperature=temperature,
    )


class _TaskResponse:
    def __init__(self, text: str):
        self.text = text


class TaskLLMClient:
    """
    Drop-in compatibility client for actions that previously called:
    client.generate_content(prompt) or client.models.generate_content(...)
    """

    def __init__(self, model: str | None = None):
        self.model = model

    def generate_content(self, contents: Any, config: Any = None) -> _TaskResponse:
        system = None
        if config and hasattr(config, "system_instruction"):
            system = str(config.system_instruction)

        # Handle contents (can be string or list)
        prompt_str = ""
        if isinstance(contents, str):
            prompt_str = contents
        elif isinstance(contents, list):
            # Check if any multimodal parts exist (e.g. image part)
            has_multimodal = any(
                hasattr(p, "inline_data") or (isinstance(p, dict) and "inline_data" in p)
                for p in contents
            )
            if has_multimodal:
                # Delegate multimodal tasks directly to Gemini
                from google import genai
                from google.genai import types
                c = genai.Client(api_key=get_gemini_api_key())
                cfg = config or types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
                res = c.models.generate_content(
                    model=DEFAULT_GEMINI_MODEL,
                    contents=contents,
                    config=cfg,
                )
                return _TaskResponse(res.text or "")

            text_parts = []
            for part in contents:
                if isinstance(part, str):
                    text_parts.append(part)
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                else:
                    text_parts.append(str(part))
            prompt_str = "\n".join(text_parts)
        else:
            prompt_str = str(contents)

        text = call_task_llm(prompt=prompt_str, system=system, model=self.model)
        return _TaskResponse(text)


def get_task_llm(model: str | None = None) -> TaskLLMClient:
    """Returns a TaskLLMClient instance configured for Groq with Gemini fallback."""
    return TaskLLMClient(model=model)
