"""
core/auto_updater.py - Pure Python Automatic GitHub Updater for ANSH
Author: Anshu Dubey | https://getyoursoft.page.gd

Automatically checks GitHub repository (mastgamerz37-ux/ansh-ai) for new commits and updates local files seamlessly without git dependency.
"""
from __future__ import annotations

import os
import sys
import json
import time
import urllib.request
import urllib.error
import threading
from pathlib import Path
from typing import Callable, Optional

REPO_OWNER = "mastgamerz37-ux"
REPO_NAME = "ansh-ai"
BRANCH = "main"

# Files and folders that should NEVER be overwritten during an auto-update
EXCLUDED_PATTERNS = {
    "keys", "api_keys.json", "license.json", "data/secure", "venv", ".venv",
    "build", "dist", "release", "release_app", "__pycache__", ".git", ".vscode",
    "scratch", "uploads"
}


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _should_skip(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    for p in parts:
        if p in EXCLUDED_PATTERNS or p.endswith(".pyc") or p.endswith(".log"):
            return True
    return False


def get_local_version_file() -> Path:
    base = _get_base_dir()
    v_dir = base / "data"
    v_dir.mkdir(exist_ok=True)
    return v_dir / "version.json"


def get_current_commit_sha() -> str:
    v_file = get_local_version_file()
    if v_file.exists():
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("commit_sha", "")
        except Exception:
            pass
    return ""


def save_current_commit_sha(sha: str) -> None:
    v_file = get_local_version_file()
    try:
        data = {
            "commit_sha": sha,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(v_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[AutoUpdater] Failed to save version info: {e}")


def fetch_latest_commit_sha() -> Optional[str]:
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}"
    req = urllib.request.Request(url, headers={"User-Agent": "ANSH-AutoUpdater"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("sha", "")
    except Exception as e:
        print(f"[AutoUpdater] Check failed: {e}")
    return None


def sync_github_updates(log_fn: Optional[Callable[[str], None]] = None) -> bool:
    def log(msg: str):
        print(f"[AutoUpdater] {msg}")
        if log_fn:
            try:
                log_fn(f"🔄 [Auto-Sync] {msg}")
            except Exception:
                pass

    log("Checking GitHub for updates...")
    remote_sha = fetch_latest_commit_sha()
    if not remote_sha:
        log("Could not fetch remote version from GitHub.")
        return False

    local_sha = get_current_commit_sha()
    if local_sha and local_sha == remote_sha:
        log("Already up to date with latest GitHub commit.")
        return True

    log(f"New update found! Remote SHA: {remote_sha[:7]} (Local: {local_sha[:7] or 'None'})")
    log("Downloading repository file tree from GitHub...")

    tree_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{remote_sha}?recursive=1"
    req = urllib.request.Request(tree_url, headers={"User-Agent": "ANSH-AutoUpdater"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tree_data = json.loads(resp.read().decode("utf-8"))
            items = tree_data.get("tree", [])
    except Exception as e:
        log(f"Failed to fetch file tree: {e}")
        return False

    base_dir = _get_base_dir()
    updated_files = 0

    for item in items:
        if item.get("type") != "blob":
            continue

        rel_path = item.get("path", "")
        if _should_skip(rel_path):
            continue

        file_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{rel_path}"
        dest_path = base_dir / rel_path

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            file_req = urllib.request.Request(file_url, headers={"User-Agent": "ANSH-AutoUpdater"})
            with urllib.request.urlopen(file_req, timeout=10) as f_resp:
                content = f_resp.read()
                dest_path.write_bytes(content)
                updated_files += 1
        except Exception as ex:
            log(f"Failed to update {rel_path}: {ex}")

    save_current_commit_sha(remote_sha)
    log(f"Successfully synced {updated_files} files from GitHub! Current Commit: {remote_sha[:7]}")
    return True


def start_background_updater(log_fn: Optional[Callable[[str], None]] = None, check_interval_seconds: int = 300) -> threading.Thread:
    def _loop():
        # First check at startup after 5 seconds delay
        time.sleep(5)
        while True:
            try:
                sync_github_updates(log_fn)
            except Exception as e:
                print(f"[AutoUpdater] Loop error: {e}")
            time.sleep(check_interval_seconds)

    t = threading.Thread(target=_loop, daemon=True, name="ANSH-AutoUpdater")
    t.start()
    return t
