"""
telegram_runner.py — Standalone Runner & Configuration Utility for ANSH Telegram Remote.

Usage:
  python telegram_runner.py
  python telegram_runner.py --token <YOUR_BOT_TOKEN>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from core.telegram_bot import get_telegram_bot, load_config, save_config_value


def main():
    parser = argparse.ArgumentParser(description="ANSH Telegram Remote Controller")
    parser.add_argument("--token", type=str, help="Telegram Bot Token from @BotFather")
    parser.add_argument("--chat_id", type=str, help="Your personal Telegram Chat ID")
    args = parser.parse_args()

    cfg = load_config()

    if args.token:
        save_config_value("telegram_bot_token", args.token.strip())
        print(f"✅ Saved telegram_bot_token to config/api_keys.json")

    if args.chat_id:
        save_config_value("telegram_chat_id", args.chat_id.strip())
        print(f"✅ Saved telegram_chat_id to config/api_keys.json")

    cfg = load_config()
    token = cfg.get("telegram_bot_token") or ""
    chat_id = cfg.get("telegram_chat_id") or ""

    if not token:
        print("\n" + "=" * 60)
        print("🤖 ANSH TELEGRAM REMOTE CONTROL SETUP")
        print("=" * 60)
        print("1. Open Telegram on your smartphone.")
        print("2. Search for @BotFather and create a new bot (/newbot).")
        print("3. Copy the Bot Token provided by BotFather.\n")
        try:
            token = input("👉 Enter your Telegram Bot Token: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(0)

        if token:
            save_config_value("telegram_bot_token", token)
            print("✅ Bot Token saved successfully!")
        else:
            print("❌ No token provided. Exiting.")
            sys.exit(1)

    bot = get_telegram_bot()
    bot.update_credentials(token, chat_id)

    print("\n" + "=" * 60)
    print("🚀 Starting ANSH Telegram Remote Bot Service...")
    print(f"🔐 Configured Chat ID: {chat_id if chat_id else 'None (First /start from phone will pair)'}")
    print("=" * 60)

    if not bot.start():
        print("❌ Failed to start bot. Check your bot token and internet connection.")
        sys.exit(1)

    print("🟢 Bot is now LIVE and listening for commands from your phone!")
    print("📱 Open your bot on Telegram and send /start or /help")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🔴 Stopping Telegram bot service...")
        bot.stop()
        print("👋 Service stopped.")


if __name__ == "__main__":
    main()
