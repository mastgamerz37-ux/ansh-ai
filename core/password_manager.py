"""
core/password_manager.py — Secure Password Hashing & Authentication Manager for ANSH

Uses Argon2id (with fallback to PBKDF2-HMAC-SHA256) for salted password hashing.
Stores hashes securely in data/secure/security_config.json without exposing secrets.
"""
from __future__ import annotations

import os
import re
import json
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Tuple

from config.security_config import SECURITY_CONFIG_PATH

try:
    from argon2 import PasswordHasher
    _ARGON2_AVAILABLE = True
    _ph = PasswordHasher()
except ImportError:
    _ARGON2_AVAILABLE = False
    _ph = None


def normalize_password_input(text: str) -> str:
    """
    Normalizes spoken/typed password inputs for robust matching.
    Converts digit words (one -> 1), strips punctuation, and lowercases.
    """
    if not text:
        return ""

    clean = text.strip().lower()

    # Common spoken digit mappings
    word_to_digit = {
        "zero": "0", "one": "1", "two": "2", "to": "2", "too": "2",
        "three": "3", "four": "4", "for": "4", "five": "5",
        "six": "6", "seven": "7", "eight": "8", "ate": "8",
        "nine": "9"
    }

    # Replace words bounded by spaces/punctuation
    words = re.findall(r'\b\w+\b', clean)
    normalized_words = [word_to_digit.get(w, w) for w in words]
    
    # Return both joined string and original cleaned string
    return "".join(normalized_words)


def _hash_pbkdf2(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
    if not salt_hex:
        salt = secrets.token_bytes(16)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)

    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    hash_hex = derived.hex()
    return hash_hex, salt_hex


class PasswordManager:
    """
    Manages security password hashing, verification, and persistence.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or SECURITY_CONFIG_PATH
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_config()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[PasswordManager] Failed to load config: {e}")
        return {}

    def _save_config(self, data: dict):
        try:
            self.config_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[PasswordManager] Failed to save config: {e}")

    def is_password_set(self) -> bool:
        """Returns True if a security password hash is configured."""
        data = self._load_config()
        return bool(data.get("password_hash"))

    def set_password(self, password: str) -> bool:
        """
        Hashes and stores the new security password.
        """
        if not password or len(password.strip()) == 0:
            return False

        norm_pwd = normalize_password_input(password)
        data = self._load_config()

        if _ARGON2_AVAILABLE and _ph:
            hash_str = _ph.hash(norm_pwd)
            data["algo"] = "argon2id"
            data["password_hash"] = hash_str
            data.pop("salt", None)
        else:
            hash_str, salt_str = _hash_pbkdf2(norm_pwd)
            data["algo"] = "pbkdf2_sha256"
            data["password_hash"] = hash_str
            data["salt"] = salt_str

        self._save_config(data)
        print("[PasswordManager] Security password updated successfully.")
        return True

    def verify_password(self, input_password: str) -> bool:
        """
        Verifies spoken or entered password against stored hash.
        """
        if not input_password or not self.is_password_set():
            return False

        data = self._load_config()
        stored_hash = data.get("password_hash")
        algo = data.get("algo", "pbkdf2_sha256")
        norm_pwd = normalize_password_input(input_password)

        if not stored_hash or not norm_pwd:
            return False

        try:
            if algo == "argon2id" and _ARGON2_AVAILABLE and _ph:
                return _ph.verify(stored_hash, norm_pwd)
            elif algo == "pbkdf2_sha256":
                salt = data.get("salt")
                calc_hash, _ = _hash_pbkdf2(norm_pwd, salt)
                return secrets.compare_digest(calc_hash, stored_hash)
            else:
                salt = data.get("salt")
                calc_hash, _ = _hash_pbkdf2(norm_pwd, salt)
                return secrets.compare_digest(calc_hash, stored_hash)
        except Exception:
            return False
