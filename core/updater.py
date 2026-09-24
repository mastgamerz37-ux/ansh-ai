"""
core/updater.py — GitHub Auto-Update Controller for ANSH
Developer: Anshu Dubey | https://getyoursoft.vercel.app

Provides programmatic access to check for updates, compare commit SHAs,
and perform background or foreground repository synchronizations.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional, Dict, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core.auto_updater import (
    REPO_OWNER,
    REPO_NAME,
    BRANCH,
    get_current_commit_sha,
    fetch_latest_commit_sha,
    sync_github_updates,
    start_background_updater,
    get_local_version_file,
)


def get_version_summary() -> Dict[str, Any]:
    """Returns local commit SHA, remote commit SHA, and update availability."""
    local_sha = get_current_commit_sha()
    remote_sha = fetch_latest_commit_sha()
    has_update = bool(remote_sha and local_sha != remote_sha)
    return {
        "local_sha": local_sha,
        "remote_sha": remote_sha,
        "has_update": has_update,
        "repo": f"{REPO_OWNER}/{REPO_NAME}",
        "branch": BRANCH,
    }


def check_for_updates() -> Tuple[bool, str]:
    """
    Returns (has_update, message).
    Safe to call from UI or terminal.
    """
    try:
        info = get_version_summary()
        local_sha = info["local_sha"]
        remote_sha = info["remote_sha"]

        if not remote_sha:
            return False, "Could not contact GitHub update server."

        if local_sha and local_sha == remote_sha:
            return False, f"ANSH is up to date (Commit: {local_sha[:7]})."

        return True, f"Update available! Remote: {remote_sha[:7]} (Current: {local_sha[:7] if local_sha else 'None'})."
    except Exception as e:
        return False, f"Update check failed: {e}"


def perform_update(log_callback: Optional[Callable[[str], None]] = None) -> bool:
    """Performs safe, in-place update from GitHub repository."""
    return sync_github_updates(log_fn=log_callback)


def run_cli_update():
    """CLI runner called by update.ps1 or ansh update."""
    print("[ANSH Updater] Checking for updates on GitHub...")
    has_update, msg = check_for_updates()
    print(f"[ANSH Updater] {msg}")
    if has_update:
        print("[ANSH Updater] Applying updates...")
        ok = perform_update()
        if ok:
            print("[ANSH Updater] [OK] Update applied successfully.")
        else:
            print("[ANSH Updater] [!] Could not complete update.")
    else:
        print("[ANSH Updater] [OK] Already up to date.")


if __name__ == "__main__":
    run_cli_update()
