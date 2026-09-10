"""
setup_keys.py — API Keys & License Configuration Utility for ANSH
Created & Developed for Anshu Dubey

Usage:
  python setup_keys.py                    # Interactive setup & status check
  python setup_keys.py --gemini <KEY>     # Set & test Gemini API Key
  python setup_keys.py --groq <KEY>       # Set & test Groq API Key
  python setup_keys.py --activate <KEY>   # Activate product key
"""
from __future__ import annotations

import os
import sys
import json
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
ENV_PATH = BASE_DIR / "core" / ".env"
LICENSE_PATH = BASE_DIR / "config" / "license.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(updates: dict):
    cfg = load_config()
    cfg.update(updates)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")


def sync_to_env(gemini_key: str | None = None, groq_key: str | None = None):
    lines = []
    if ENV_PATH.exists():
        try:
            for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip() and not line.strip().startswith(("GEMINI_API_KEY", "GROQ_API_KEY", "gemini_api_key", "groq_api_key")):
                    lines.append(line)
        except Exception:
            pass

    if gemini_key:
        lines.append(f"GEMINI_API_KEY={gemini_key}")
    if groq_key:
        lines.append(f"GROQ_API_KEY={groq_key}")

    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_gemini_key(api_key: str) -> tuple[bool, str]:
    if not api_key or not api_key.strip():
        return False, "API key is empty."
    
    clean_key = api_key.strip()
    if not (clean_key.startswith("AIzaSy") or clean_key.startswith("AQ.") or len(clean_key) >= 20):
        return False, (
            f"Key format warning: '{clean_key[:8]}...' does not start with 'AIzaSy' or 'AQ.'. "
            "Gemini API keys typically start with 'AIzaSy' or 'AQ.'. "
            "Get one from: https://aistudio.google.com/app/apikey"
        )

    try:
        from google import genai
        client = genai.Client(api_key=clean_key)
        resp = client.models.generate_content(
            model="gemini-3.6-flash",
            contents="Say 'OK' in one word"
        )
        return True, f"Success! Google AI responded: {resp.text.strip()}"
    except Exception as e:
        return False, f"Connection failed: {e}"


def test_groq_key(api_key: str) -> tuple[bool, str]:
    if not api_key or not api_key.strip():
        return False, "Groq API key is empty."

    clean_key = api_key.strip()
    try:
        from groq import Groq
        client = Groq(api_key=clean_key)
        resp = client.chat.completions.create(
            model="groq/compound-mini",
            messages=[{"role": "user", "content": "Say 'OK' in one word"}]
        )
        return True, f"Success! Groq responded: {resp.choices[0].message.content.strip()}"
    except Exception as e:
        return False, f"Connection failed: {e}"


def check_status():
    cfg = load_config()
    print("=" * 65)
    print("       ⚡ ANSH — Configuration & Diagnostic Status ⚡")
    print("=" * 65)

    # 1. License
    from core.license_manager import LicenseManager
    lm = LicenseManager()
    is_valid, rem, time_str = lm.get_trial_status()
    lic = lm._load_license()
    if lic.get("activated"):
        print(f"🔒 Lifetime License:    ✅ ACTIVATED (Full Unlimited Access)")
    elif is_valid:
        print(f"⏳ Trial License:       ⚠️ ACTIVE ({time_str})")
    else:
        print(f"❌ License:             🔴 EXPIRED — Activation required")

    # 2. Groq
    groq_key = cfg.get("groq_api_key", "")
    if groq_key:
        print(f"⚡ Groq API Key:        Found ({groq_key[:10]}...{groq_key[-4:]})")
        ok, msg = test_groq_key(groq_key)
        if ok:
            print(f"   Groq Status:        ✅ CONNECTED & WORKING (Sub-agent planner active)")
        else:
            print(f"   Groq Status:        ❌ {msg}")
    else:
        print(f"⚡ Groq API Key:        ❌ NOT CONFIGURED")

    # 3. Gemini
    gem_key = cfg.get("gemini_api_key") or cfg.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
    if gem_key and gem_key != "YOUR_GEMINI_API_KEY":
        print(f"✨ Gemini API Key:      Found ({gem_key[:10]}...{gem_key[-4:]})")
        ok, msg = test_gemini_key(gem_key)
        if ok:
            print(f"   Gemini Status:      ✅ CONNECTED & WORKING (Live audio/vision active)")
        else:
            print(f"   Gemini Status:      ⚠️ {msg}")
    else:
        print(f"✨ Gemini API Key:      ❌ NOT CONFIGURED (Required for Live Voice)")
        print(f"   Get a FREE key at:  👉 https://aistudio.google.com/app/apikey")

    # 4. Fish Audio / Voice Model
    fish_key = cfg.get("fish_audio_api_key", "")
    voice_name = cfg.get("fish_audio_voice_name", "Verity (Male)")
    voice_id = cfg.get("fish_audio_voice_id", "711cf3ed00ab441a8f54a45058047b7a")
    tts_eng = cfg.get("tts_engine", "fish_audio")
    if fish_key:
        print(f"🎙️ Fish Audio Key:     Found ({fish_key[:12]}...{fish_key[-4:]})")
        print(f"   Voice Model:        ✅ {voice_name} ({voice_id})")
        print(f"   TTS Engine:         ✅ {tts_eng}")
    else:
        print(f"🎙️ TTS Engine:          {tts_eng}")

    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Configure API keys and activation for ANSH")
    parser.add_argument("--gemini", type=str, help="Set Gemini API Key")
    parser.add_argument("--groq", type=str, help="Set Groq API Key")
    parser.add_argument("--fish", type=str, help="Set Fish Audio API Key")
    parser.add_argument("--activate", type=str, help="Activate with Product Key (e.g. ANSH-XXXX-XXXX-XXXX)")
    parser.add_argument("--status", action="store_true", help="Show current status")

    args = parser.parse_args()

    if args.activate:
        from core.license_manager import LicenseManager
        lm = LicenseManager()
        ok, msg = lm.activate_product_key(args.activate)
        print(f"[License] {msg}")
        return

    if args.gemini:
        k = args.gemini.strip()
        print(f"Testing Gemini Key: {k[:8]}...")
        ok, msg = test_gemini_key(k)
        if ok:
            print(f"✅ Key verified! {msg}")
        else:
            print(f"⚠️ {msg}")
        save_config({"gemini_api_key": k, "api_key": k})
        sync_to_env(gemini_key=k)
        print("✅ Saved to config/api_keys.json")
        return

    if args.groq:
        k = args.groq.strip()
        print(f"Testing Groq Key: {k[:8]}...")
        ok, msg = test_groq_key(k)
        if ok:
            print(f"✅ Key verified! {msg}")
        else:
            print(f"⚠️ {msg}")
        save_config({"groq_api_key": k})
        sync_to_env(groq_key=k)
        print("✅ Saved to config/api_keys.json")
        return

    if args.fish:
        k = args.fish.strip()
        save_config({
            "fish_audio_api_key": k,
            "fish_audio_voice_id": "711cf3ed00ab441a8f54a45058047b7a",
            "fish_audio_voice_name": "Verity (Male - 711cf3ed)",
            "tts_engine": "fish_audio"
        })
        print(f"✅ Saved Fish Audio Key ({k[:10]}...) with Verity voice model to config/api_keys.json")
        return

    if args.status:
        check_status()
        return

    # Interactive mode
    check_status()
    print("\nActions:")
    print("1. Set Gemini API Key (from https://aistudio.google.com/app/apikey)")
    print("2. Set Groq API Key (from https://console.groq.com/keys)")
    print("3. Set Fish Audio API Key (Verity Voice Model)")
    print("4. Activate Lifetime Product Key")
    print("5. Exit")

    choice = input("\nSelect an option (1-5): ").strip()
    if choice == "1":
        k = input("Enter Gemini API Key (starts with AIzaSy or AQ.): ").strip()
        if k:
            ok, msg = test_gemini_key(k)
            if ok:
                print(f"✅ {msg}")
            else:
                print(f"⚠️ {msg}")
            save_config({"gemini_api_key": k, "api_key": k})
            sync_to_env(gemini_key=k)
            print("✅ Saved to config/api_keys.json")
    elif choice == "2":
        k = input("Enter Groq API Key (starts with gsk_): ").strip()
        if k:
            ok, msg = test_groq_key(k)
            if ok:
                print(f"✅ {msg}")
            else:
                print(f"⚠️ {msg}")
            save_config({"groq_api_key": k})
            sync_to_env(groq_key=k)
            print("✅ Saved to config/api_keys.json")
    elif choice == "3":
        k = input("Enter Fish Audio API Key (starts with sk-fish-): ").strip()
        if k:
            save_config({
                "fish_audio_api_key": k,
                "fish_audio_voice_id": "711cf3ed00ab441a8f54a45058047b7a",
                "fish_audio_voice_name": "Verity (Male - 711cf3ed)",
                "tts_engine": "fish_audio"
            })
            print("✅ Saved Fish Audio Key with Verity voice model to config/api_keys.json")
    elif choice == "4":
        k = input("Enter Product Key (e.g. ANSH-XXXX-XXXX-XXXX): ").strip()
        if k:
            from core.license_manager import LicenseManager
            lm = LicenseManager()
            ok, msg = lm.activate_product_key(k)
            print(f"[License] {msg}")


if __name__ == "__main__":
    main()

