"""
core/license_manager.py — Licensing & Evaluation Engine for ANSH - Your Own AI Friend

Rules:
1. First Launch gives 3 Days Free Trial (72 hours).
2. After 3 Days, full application access locks until a valid Product Activation Key or Trial Key is entered.
3. Supports:
   - Free Evaluation Trial Keys: ANSH-TRAL-XXXX-XXXX (issued on GetYourSoft website after login)
   - Commercial Keys: Monthly (ANSH-M-...), Lifetime (ANSH-L-...), Classic (ANSH-XXXX-...)
4. Verification Pipeline:
   a. Local SHA-256 hash lookup in keys/valid_keys.json (fast offline path).
   b. Live Cloud API verification (https://getyoursoft.vercel.app/api/verify-license) with fallback.
   c. Resilient offline evaluation key format fallback.
5. Once activated, state is preserved in config/license.json.
"""
from __future__ import annotations

import os
import re
import json
import time
import hashlib
import sys
import platform
import urllib.request
import urllib.parse
import urllib.error
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

VERIFY_ENDPOINTS = [
    "https://getyoursoft.vercel.app/api/verify-license",
    "https://ansh-ai-backend.vercel.app/api/verify-license",
]


def _get_machine_fingerprint() -> str:
    """Generates a stable machine fingerprint for license & trial binding."""
    try:
        import uuid
        node = uuid.getnode()
        system = platform.system() + platform.machine()
        return hashlib.sha256(f"{node}_{system}".encode("utf-8")).hexdigest()[:16]
    except Exception:
        return "machine_default"


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

    def _load_valid_hashes(self) -> Dict[str, Any]:
        if self.keys_hash_file.exists():
            try:
                data = json.loads(self.keys_hash_file.read_text(encoding="utf-8"))
                return data.get("valid_hashes", {})
            except Exception as e:
                print(f"[LicenseManager] Error loading valid key hashes: {e}")
        return {}

    def _save_valid_hash(self, key_hash: str, meta: Dict[str, Any]) -> None:
        """Appends newly verified key hash locally so subsequent checks succeed offline."""
        try:
            hashes = self._load_valid_hashes()
            hashes[key_hash] = meta
            self.keys_hash_file.parent.mkdir(parents=True, exist_ok=True)
            self.keys_hash_file.write_text(json.dumps({"valid_hashes": hashes}, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[LicenseManager] Error saving valid hash: {e}")

    def get_trial_status(self) -> Tuple[bool, float, str]:
        """
        Returns: (is_trial_active: bool, seconds_remaining: float, formatted_time_left: str)
        """
        lic = self._load_license()
        if lic.get("activated", False):
            return True, float("inf"), "Activated Product Key"

        trial_exp = lic.get("trial_expires_at")
        if trial_exp:
            remaining = trial_exp - time.time()
        else:
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
        Returns True if either valid product key is activated OR within active trial window.
        """
        lic = self._load_license()
        if lic.get("activated", False):
            return True

        is_active, _, _ = self.get_trial_status()
        return is_active

    def _verify_online(self, clean_key: str, machine_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Queries the live cloud verification API."""
        encoded_key = urllib.parse.quote(clean_key)
        encoded_machine = urllib.parse.quote(machine_id)

        for endpoint in VERIFY_ENDPOINTS:
            url = f"{endpoint}?key={encoded_key}&machineId={encoded_machine}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ANSH-AI-Licensing/1.0",
                    "Accept": "application/json"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return True, data
            except urllib.error.HTTPError as e:
                try:
                    err_data = json.loads(e.read().decode("utf-8"))
                    return False, err_data
                except Exception:
                    return False, {"valid": False, "error": f"Verification server returned HTTP {e.code}"}
            except Exception:
                continue

        return False, {"network_error": True, "error": "Could not connect to license verification server."}

    def activate_product_key(self, product_key: str) -> Tuple[bool, str]:
        """
        Validates product key (Commercial or Free Trial) and activates ANSH.
        """
        cleaned_key = str(product_key).strip().upper().replace(" ", "")
        if not cleaned_key:
            return False, "Please enter a product key."

        if not cleaned_key.startswith("ANSH-"):
            return False, "Invalid product key format. Key must start with 'ANSH-' (e.g. ANSH-XXXX-XXXX-XXXX or ANSH-TRAL-XXXX-XXXX)."

        key_hash = hashlib.sha256(cleaned_key.encode("utf-8")).hexdigest()
        machine_id = _get_machine_fingerprint()

        # Step 1: Instant local hash check (offline fast path for pre-generated keys)
        valid_hashes = self._load_valid_hashes()
        if key_hash in valid_hashes:
            lic = self._load_license()
            lic["activated"] = True
            lic["activated_key"] = cleaned_key
            lic["activated_key_hash"] = key_hash
            lic["activation_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
            lic["plan"] = "Commercial License"
            self._save_license(lic)
            print(f"[LicenseManager] Product key activated locally via hash: {key_hash[:12]}...")
            return True, "Product key activated successfully! Full access unlocked."

        # Step 2: Live Cloud Verification via GetYourSoft API
        online_success, res_data = self._verify_online(cleaned_key, machine_id)
        if online_success and res_data.get("valid"):
            key_type = res_data.get("type", "commercial")
            lic = self._load_license()

            if key_type == "trial":
                # Evaluation 72-Hour Trial Key from website
                lic["activated"] = False
                lic["trial_active"] = True
                lic["trial_key"] = cleaned_key
                lic["trial_expires_at"] = time.time() + (72 * 3600)
                lic["first_launch_time"] = time.time()
                self._save_license(lic)
                msg = res_data.get("message", "Free 72-Hour Evaluation Trial activated successfully! Enjoy ANSH AI.")
                print(f"[LicenseManager] Trial key activated via cloud: {cleaned_key}")
                return True, msg

            else:
                # Commercial License (Monthly or Lifetime)
                lic["activated"] = True
                lic["activated_key"] = cleaned_key
                lic["activated_key_hash"] = key_hash
                lic["activation_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                lic["plan"] = res_data.get("plan", "Commercial License")
                self._save_license(lic)
                self._save_valid_hash(key_hash, {"plan": lic["plan"], "active": True})
                print(f"[LicenseManager] Commercial key activated via cloud: {cleaned_key}")
                return True, f"Product key activated successfully! {lic['plan']} unlocked."

        # If cloud specifically rejected the key with valid=False and an error
        if not online_success and not res_data.get("network_error"):
            err_msg = res_data.get("error", "Invalid product key. Please check your key or contact support.")
            return False, err_msg

        # Step 3: Resilient Offline Fallback (when user has no internet access)
        # Check if it's a validly structured Evaluation Trial Key: ANSH-TRAL-XXXX-XXXX
        trial_pattern = r"^ANSH-TR(AL)?-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        if re.match(trial_pattern, cleaned_key):
            lic = self._load_license()
            lic["activated"] = False
            lic["trial_active"] = True
            lic["trial_key"] = cleaned_key
            lic["trial_expires_at"] = time.time() + (72 * 3600)
            lic["first_launch_time"] = time.time()
            self._save_license(lic)
            print(f"[LicenseManager] Trial key activated offline: {cleaned_key}")
            return True, "Evaluation trial key accepted! 72 hours of access unlocked."

        # Check standard commercial pattern offline: ANSH-[M|L]-XXXX-XXXX-XXXX
        comm_pattern = r"^ANSH-([ML]-)?[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        if re.match(comm_pattern, cleaned_key):
            return False, "Could not reach the verification server to validate this new product key. Please connect to the internet and try again."

        return False, "Invalid product key. Please check your key or visit https://getyoursoft.vercel.app to get one."
