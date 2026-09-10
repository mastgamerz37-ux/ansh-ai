import json
import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR    = get_base_dir()
CONFIG_DIR  = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def load_api_keys() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to load api_keys.json: {e}")
        return {}


def save_api_keys(gemini_api_key: str) -> None:
    ensure_config_dir()
    data = load_api_keys()
    clean_k = gemini_api_key.strip()
    data["gemini_api_key"] = clean_k
    data["api_key"] = clean_k
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_gemini_key() -> str | None:
    cfg = load_api_keys()
    return cfg.get("gemini_api_key") or cfg.get("api_key")


def get_groq_key() -> str | None:
    return load_api_keys().get("groq_api_key")


def is_valid_groq_key(key: str | None) -> bool:
    if not key or not isinstance(key, str):
        return False
    k = key.strip()
    if len(k) < 15:
        return False
    if any(dummy in k for dummy in ("YOUR_GROQ", "YOUR_KEY", "dummy", "Enter", "gsk_...")):
        return False
    return True


def save_groq_key(groq_api_key: str) -> None:
    ensure_config_dir()
    data = load_api_keys()
    data["groq_api_key"] = groq_api_key.strip()
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def is_valid_gemini_key(key: str | None) -> bool:
    if not key or not isinstance(key, str):
        return False
    k = key.strip()
    if len(k) < 15:
        return False
    if any(dummy in k for dummy in ("YOUR_GEM", "YOUR_KEY", "dummy", "Enter", "aiza…")):
        return False
    return True


def is_configured() -> bool:
    return is_valid_gemini_key(get_gemini_key())


def get_fish_audio_key() -> str | None:
    return load_api_keys().get("fish_audio_api_key")


def get_fish_audio_voice_id() -> str:
    return load_api_keys().get("fish_audio_voice_id", "711cf3ed00ab441a8f54a45058047b7a")


def save_fish_audio_config(api_key: str, voice_id: str = "711cf3ed00ab441a8f54a45058047b7a", voice_name: str = "Verity (Male - 711cf3ed)") -> None:
    ensure_config_dir()
    data = load_api_keys()
    data["fish_audio_api_key"] = api_key.strip()
    data["fish_audio_voice_id"] = voice_id.strip()
    data["fish_audio_voice_name"] = voice_name.strip()
    data["tts_engine"] = "fish_audio"
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_assistant_name() -> str:
    """Return the configured assistant name, or 'ANSH' if not set."""
    return load_api_keys().get("assistant_name", "ANSH") or "ANSH"


def get_user_name() -> str:
    """Return the configured user name for addressing."""
    return load_api_keys().get("user_name", "")


def save_assistant_config(assistant_name: str, user_name: str) -> None:
    """Persist assistant name and user name to config."""
    ensure_config_dir()
    data = load_api_keys()
    data["assistant_name"] = assistant_name.strip() or "ANSH"
    data["user_name"] = user_name.strip()
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_brief_enabled() -> bool:
    return load_api_keys().get("morning_brief_enabled", True)


def save_brief_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data = load_api_keys()
    data["morning_brief_enabled"] = enabled
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")