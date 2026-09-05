"""
config/security_config.py — Centralized Voice Security & Authentication Settings for ANSH
"""
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
SECURE_DATA_DIR = BASE_DIR / "data" / "secure"
OWNER_PROFILE_PATH = SECURE_DATA_DIR / "owner_voice_profile.npz"
SECURITY_CONFIG_PATH = SECURE_DATA_DIR / "security_config.json"

# Voice Verification Settings
VOICE_AUTH_ENABLED: bool = True
VOICE_VERIFICATION_THRESHOLD: float = 0.82
MIN_SPEECH_DURATION_SEC: float = 0.4
TARGET_ENROLLMENT_SAMPLES: int = 5

# Session & Password Settings
AUTH_SESSION_TIMEOUT: float = 300.0  # 5 minutes
MAX_PASSWORD_ATTEMPTS: int = 3
REQUIRE_REVERIFICATION_FOR_SENSITIVE_COMMANDS: bool = True

# Ensure secure directory exists on module import
SECURE_DATA_DIR.mkdir(parents=True, exist_ok=True)
