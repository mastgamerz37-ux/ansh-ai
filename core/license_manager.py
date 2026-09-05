"""
core/license_manager.py — Licensing & 3-Day Free Trial Engine for ANSH - Your Own AI Friend

Rules:
1. First Launch gives 3 Days Free Trial (72 hours).
2. After 3 Days, full application access locks until a valid Product Activation Key is entered.
3. Product Keys are verified via cryptographic SHA-256 hashes matching keys/valid_keys.json.
4. Once activated, full unlimited access is saved in config/license.json.
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import sys
from pathlib import Path
from typing import Dict, Any, Tuple


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
LICENSE_FILE = BASE_DIR / "config" / "license.json"
KEYS_HASH_FILE = BASE_DIR / "keys" / "valid_keys.json"

TRIAL_DURATION_SECONDS = 3 * 24 * 3600  # 3 days = 259,200 seconds


class LicenseManager:
    def __init__(self):
        self.license_file = LICENSE_FILE
        self.keys_hash_file = KEYS_HASH_FILE
        self._ensure_license_file()

    def _ensure_license_file(self) -> None:
        self.license_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.license_file.exists():
            data = {
                "first_launch_time": time.time(),
                "activated": False,
                "activated_key_hash": "",
                "activation_date": "",
            }
            try:
                self.license_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
            except Exception as e:
                print(f"[LicenseManager] Error creating license file: {e}")

    def _load_license(self) -> Dict[str, Any]:
        self._ensure_license_file()
        try:
            return json.loads(self.license_file.read_text(encoding="utf-8"))
        except Exception:
            return {
                "first_launch_time": time.time(),
                "activated": False,
                "activated_key_hash": "",
                "activation_date": "",
            }

    def _save_license(self, data: Dict[str, Any]) -> None:
        try:
            self.license_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[LicenseManager] Error saving license file: {e}")

    def _load_valid_hashes(self) -> Dict[str, bool]:
        if self.keys_hash_file.exists():
            try:
                data = json.loads(self.keys_hash_file.read_text(encoding="utf-8"))
                return data.get("valid_hashes", {})
            except Exception as e:
                print(f"[LicenseManager] Error loading valid key hashes: {e}")
        return {}

    def get_trial_status(self) -> Tuple[bool, float, str]:
        """
        Returns: (is_trial_active: bool, seconds_remaining: float, formatted_time_left: str)
        """
        lic = self._load_license()
        if lic.get("activated", False):
            return True, float("inf"), "Activated Product Key"

        first_launch = lic.get("first_launch_time", time.time())
        elapsed = time.time() - first_launch
        remaining = TRIAL_DURATION_SECONDS - elapsed

        if remaining <= 0:
            return False, 0.0, "Trial Expired (0 Days Left)"

        days = int(remaining // 86400)
        hours = int((remaining % 86400) // 3600)
        minutes = int((remaining % 3600) // 60)

        if days >= 1:
            time_left = f"{days} Day{'s' if days > 1 else ''} {hours} Hour{'s' if hours != 1 else ''} Remaining"
        else:
            time_left = f"{hours} Hours {minutes} Mins Remaining"

        return True, remaining, time_left

    def is_license_valid(self) -> bool:
        """
        Returns True if either valid product key is activated OR within 3-day trial.
        """
        lic = self._load_license()
        if lic.get("activated", False):
            return True

        is_active, remaining, _ = self.get_trial_status()
        return is_active

    def activate_product_key(self, product_key: str) -> Tuple[bool, str]:
        """
        Validates product key and activates ANSH.
        """
        cleaned_key = product_key.strip().upper().replace(" ", "")
        if not cleaned_key:
            return False, "Please enter a product key."

        if not cleaned_key.startswith("ANSH-"):
            return False, "Invalid product key format. Key must start with 'ANSH-' (e.g. ANSH-XXXX-XXXX-XXXX)."

        key_hash = hashlib.sha256(cleaned_key.encode("utf-8")).hexdigest()
        valid_hashes = self._load_valid_hashes()

        if key_hash in valid_hashes:
            lic = self._load_license()
            lic["activated"] = True
            lic["activated_key_hash"] = key_hash
            lic["activation_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save_license(lic)
            print(f"[LicenseManager] Product key activated successfully! Hash: {key_hash[:12]}...")
            return True, "Product key activated successfully! Full access unlocked."

        return False, "Invalid product key. Please check your key or contact support."
