"""
core/local_engine.py — ANSH Embedded Local SLM & Offline Reliability Engine

Provides offline local model execution (Ollama, LM Studio, llama.cpp)
and rule-based deterministic fallback for zero-network reliability.
Ensures ANSH can control the PC, inspect files, check time/telemetry,
and search local memory even when disconnected from the internet.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def is_internet_available(timeout: float = 1.5) -> bool:
    """Fast check for internet connectivity via reliable DNS/HTTP ping."""
    try:
        requests.get("https://1.1.1.1", timeout=timeout)
        return True
    except Exception:
        try:
            requests.get("https://www.google.com", timeout=timeout)
            return True
        except Exception:
            return False


def is_local_slm_available(endpoint_url: str = "http://localhost:11434") -> bool:
    """Checks if local Ollama or OpenAI-compatible server is running."""
    try:
        r = requests.get(f"{endpoint_url}/api/tags", timeout=1.0)
        return r.status_code == 200
    except Exception:
        try:
            r = requests.get(f"{endpoint_url}/v1/models", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False


def call_local_slm(
    prompt: str,
    system: Optional[str] = None,
    model: str = "llama3.2",
    endpoint_url: str = "http://localhost:11434",
    temperature: float = 0.5,
) -> str:
    """
    Executes an inference request against the local Ollama instance.
    """
    cfg = _load_config()
    target_url = cfg.get("local_llm_url", endpoint_url)
    target_model = cfg.get("local_llm_model", model)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": target_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }

    try:
        resp = requests.post(f"{target_url}/api/chat", json=payload, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            return (data.get("message", {}).get("content") or "").strip()
    except Exception as e:
        print(f"[LocalEngine] ⚠️ Local SLM inference error: {e}")

    # Deterministic Offline Rule-Based Fallback if local SLM is not running
    return _offline_rule_fallback(prompt)


def _offline_rule_fallback(prompt: str) -> str:
    """
    Deterministic rule-based response engine when totally offline and without local LLM.
    """
    p = prompt.lower()
    if "time" in p or "date" in p:
        return f"Current time is {time.strftime('%I:%M %p, %A, %B %d, %Y')}."
    if "battery" in p or "cpu" in p or "ram" in p or "status" in p:
        from actions.computer_settings import computer_settings
        return str(computer_settings({"action": "status"}))
    if "volume" in p:
        return "I can adjust volume offline. Say 'volume up' or 'volume 50'."
    if "wifi" in p or "internet" in p:
        return "You appear to be offline right now. Local controls and cached files are fully operational."

    return (
        "ANSH is running in Offline Mode. I can control your PC, manage files, "
        "and access local memory without internet."
    )
