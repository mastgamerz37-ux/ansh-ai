"""
core/cli_interface.py - Claude & Gemini Style Large Terminal Interface for ANSH
Author: Anshu Dubey | https://getyoursoft.page.gd

Renders a premium terminal banner with large ASCII logo, auto-updater status,
and interactively prompts for API keys, nickname, and product key if missing.
"""
from __future__ import annotations

import os
import sys
import platform
from memory.config_manager import (
    get_gemini_key, save_api_keys, is_valid_gemini_key,
    get_groq_key, save_groq_key, is_valid_groq_key,
    get_user_name, get_assistant_name, save_assistant_config
)

# Force UTF-8 encoding for stdout on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Enable ANSI colors on Windows PowerShell / CMD
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# ANSI Color Codes
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_cli_banner() -> None:
    os_name = platform.system()
    python_ver = platform.python_version()

    banner = f"""
{CYAN}{BOLD}
   █████╗ ███╗   ██╗███████╗██╗  ██╗
  ██╔══██╗████╗  ██║██╔════╝██║  ██║   {GREEN}ANSH AI — Your Own AI Friend{CYAN}
  ███████║██╔██╗ ██║███████╗███████║   {YELLOW}v1.0.0 (Production Release){CYAN}
  ██╔══██║██║╚██╗██║╚════██║██╔══██║   Developer: {YELLOW}Anshu Dubey{CYAN}
  ██║  ██║██║ ╚████║███████║██║  ██║   Website: {YELLOW}https://getyoursoft.page.gd{CYAN}
  ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝   Platform: {BLUE}{os_name} (Python {python_ver}){CYAN}
===============================================================================
{RESET}{DIM}  Autonomous Multimodal Voice Assistant • HUD Interface • Real-Time AI Engine{RESET}
{GREEN}  🔄 [Auto-Sync] Auto-Updater Enabled (GitHub @ mastgamerz37-ux/ansh-ai){RESET}
"""
    try:
        print(banner)
    except Exception:
        plain_banner = (
            "===============================================================================\n"
            "  A N S H   A I - Your Own AI Friend (v1.0.0 Production Release)\n"
            "  Developer: Anshu Dubey | Website: https://getyoursoft.page.gd\n"
            f"  Platform:  {os_name} (Python {python_ver})\n"
            "  Auto-Sync: Enabled (GitHub @ mastgamerz37-ux/ansh-ai)\n"
            "==============================================================================="
        )
        print(plain_banner)


def ensure_terminal_credentials() -> None:
    """Interactively prompts the user in terminal for Gemini API Key, Groq API Key, Nickname, and Product Key if trial expired."""
    print_cli_banner()

    gemini_key = get_gemini_key()
    groq_key = get_groq_key()
    user_name = get_user_name()
    assistant_name = get_assistant_name()

    needs_update = False

    # 1. Prompt for Gemini API Key
    if not is_valid_gemini_key(gemini_key):
        print(f"\n{YELLOW}{BOLD}🔑 [SETUP REQUIRED] Gemini API Key is missing or invalid.{RESET}")
        print(f"{DIM}Get your free API key at: https://aistudio.google.com/app/apikey{RESET}")
        while True:
            key_input = input(f"{CYAN}{BOLD}Enter Gemini API Key: {RESET}").strip()
            if is_valid_gemini_key(key_input):
                save_api_keys(key_input)
                gemini_key = key_input
                print(f"{GREEN}✓ Gemini API Key saved successfully!{RESET}\n")
                needs_update = True
                break
            else:
                print(f"{RED}❌ Invalid API key. Please enter a valid Gemini API key.{RESET}")
    else:
        print(f"{GREEN}✓ Gemini API Key:{RESET} {CYAN}{gemini_key[:8]}...{gemini_key[-4:]}{RESET}")

    # 2. Prompt for Groq API Key (Mandatory)
    if not is_valid_groq_key(groq_key):
        print(f"\n{YELLOW}{BOLD}⚡ [SETUP REQUIRED] Groq API Key is missing or invalid.{RESET}")
        print(f"{DIM}Get your free API key at: https://console.groq.com/keys{RESET}")
        while True:
            groq_input = input(f"{CYAN}{BOLD}Enter Groq API Key: {RESET}").strip()
            if is_valid_groq_key(groq_input):
                save_groq_key(groq_input)
                groq_key = groq_input
                print(f"{GREEN}✓ Groq API Key saved successfully!{RESET}\n")
                needs_update = True
                break
            else:
                print(f"{RED}❌ Invalid Groq API key. Please enter a valid Groq API key.{RESET}")
    else:
        print(f"{GREEN}✓ Groq API Key:{RESET}   {CYAN}{groq_key[:8]}...{groq_key[-4:]}{RESET}")

    # 3. Prompt for User Nickname
    if not user_name:
        print(f"\n{YELLOW}👤 [PROFILE] Tell ANSH what to call you!{RESET}")
        name_input = input(f"{CYAN}{BOLD}Enter your Name / Nickname: {RESET}").strip()
        if name_input:
            save_assistant_config(assistant_name, name_input)
            user_name = name_input
            print(f"{GREEN}✓ Welcome, {user_name}! Your profile has been updated.{RESET}\n")
            needs_update = True
        else:
            print(f"{DIM}Using default greeting (Sir / Efendim).{RESET}\n")
    else:
        print(f"{GREEN}✓ User Profile:{RESET}   {CYAN}{user_name}{RESET}")

    # 4. Check 3-Day Free Trial & Product Key Activation
    try:
        from core.license_manager import LicenseManager
        lic_mgr = LicenseManager()
        is_active, remaining, time_left = lic_mgr.get_trial_status()

        if remaining == float("inf"):
            print(f"{GREEN}✓ License Status:{RESET} {GREEN}Activated Product Key (Full Unlimited Access){RESET}")
        elif is_active:
            print(f"{GREEN}✓ License Status:{RESET} {YELLOW}3-Day Free Trial Active ({time_left}){RESET}")
        else:
            print(f"\n{RED}{BOLD}⚠️ [TRIAL EXPIRED] Your 3-Day Free Trial Has Expired!{RESET}")
            print(f"{DIM}To continue using ANSH, get a Product Activation Key at: https://getyoursoft.page.gd{RESET}\n")
            while True:
                pk_input = input(f"{CYAN}{BOLD}Enter Product Activation Key (ANSH-XXXX-XXXX-XXXX): {RESET}").strip()
                success, msg = lic_mgr.activate_product_key(pk_input)
                if success:
                    print(f"{GREEN}✓ {msg}{RESET}\n")
                    break
                else:
                    print(f"{RED}❌ {msg}{RESET}")
    except Exception as e:
        print(f"[License] Check notice: {e}")

    print(f"\n{GREEN}{BOLD}🚀 [READY] Launching ANSH AI System...{RESET}\n")
