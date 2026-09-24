"""
upload_to_github.py — High-Performance Pure Python GitHub Repository Synchronizer for ANSH
Created & Developed by Anshu Dubey | https://getyoursoft.vercel.app

Features:
- Uses requests.Session for connection reuse (eliminates WinError 10060 socket timeouts).
- Pre-fetches remote Git tree in 1 single call to compare SHAs: skips identical files instantly.
- Automatic retry on network hiccups or timeouts (up to 3 attempts with backoff).
- Automatically purges sensitive/ignored files on GitHub if previously uploaded.
- Strictly protects all private keys, credentials, local databases, and biometrics.
"""
from __future__ import annotations

import os
import sys
import json
import time
import base64
import hashlib
from pathlib import Path
import requests

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_OWNER = "mastgamerz37-ux"
REPO_NAME = "ansh-ai"
BRANCH = "main"

# Directories to strictly ignore
IGNORED_DIR_NAMES = {
    "venv", ".venv", "env", "ENV", "build", "dist", "__pycache__",
    "scratch", ".vscode", ".idea", ".git", "ansh_ai.egg-info", "ansh_assistant.egg-info",
    "release", "release_app", "AnshAI_Release", "certs", "shadow_backups"
}

# Sensitive path prefixes to strictly ignore
IGNORED_PATH_PREFIXES = (
    "data/secure",
    "data/voice_samples",
    "data/shadow_backups",
    "data/logs",
    "memory/storage",
    "config/certs",
)

# Specific files to strictly ignore (credentials, generators, local state)
IGNORED_EXACT_FILES = {
    "keys.txt",
    "keys/product_keys.txt",
    "keys/generate_keys.py",
    "config/api_keys.json",
    "config/license.json",
    ".license",
    "Untitled-1.txt",
    "validation.json",
    "installer/release/ANSH_Setup_v1.0.exe",
    "core/.env",
    ".env",
}

# File extensions to strictly ignore
IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".exe", ".spec", ".egg", ".swp", ".swo",
    ".key", ".crt", ".pem", ".npz", ".wav", ".log", ".jsonl"
}


def should_ignore(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.strip("/")

    # Check exact file matches
    if normalized in IGNORED_EXACT_FILES:
        return True

    # Check path prefixes (e.g. data/secure, memory/storage, config/certs)
    for prefix in IGNORED_PATH_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True

    parts = normalized.split("/")
    filename = parts[-1]

    # Check scratch, untitled, or env files
    if (
        filename.startswith("Untitled")
        or filename.startswith(".env")
        or filename.endswith(".env")
        or filename == ".license"
        or filename.endswith(".license")
    ):
        return True

    # Check ignored directories
    for part in parts:
        if part in IGNORED_DIR_NAMES or part.endswith(".egg-info"):
            return True

    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext in IGNORED_EXTENSIONS:
        return True

    # Ignore OS files
    if filename in (".DS_Store", "Thumbs.db", "desktop.ini"):
        return True

    return False


def git_blob_sha(content_bytes: bytes) -> str:
    """Calculates standard Git Blob SHA-1."""
    header = f"blob {len(content_bytes)}\0".encode("utf-8")
    return hashlib.sha1(header + content_bytes).hexdigest()


def get_all_files(base_dir: Path) -> list[Path]:
    file_list: list[Path] = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [
            d for d in dirs
            if not should_ignore(str(Path(root, d).relative_to(base_dir)))
        ]
        for file in files:
            full_path = Path(root, file)
            rel_path = str(full_path.relative_to(base_dir))
            if not should_ignore(rel_path):
                file_list.append(full_path)
    return file_list


def ensure_repo_exists(session: requests.Session, token: str) -> bool:
    check_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    try:
        resp = session.get(check_url, timeout=15)
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            print(f"📦 Repository '{REPO_OWNER}/{REPO_NAME}' not found. Creating it on GitHub...")
            create_url = "https://api.github.com/user/repos"
            payload = {
                "name": REPO_NAME,
                "description": "ANSH - Your Own AI Friend: Real-time Multimodal Voice Assistant, Smart Island HUD & Autonomous AI System",
                "private": False,
                "auto_init": True
            }
            c_resp = session.post(create_url, json=payload, timeout=20)
            if c_resp.status_code in (200, 201):
                print(f"✅ Successfully created repository '{REPO_OWNER}/{REPO_NAME}'!")
                return True
            print(f"❌ Failed to create repo: {c_resp.status_code} {c_resp.text}")
            return False
        print(f"❌ GitHub API Error: {resp.status_code} {resp.text}")
        return False
    except Exception as ex:
        print(f"❌ Connection error: {ex}")
        return False


def get_remote_tree(session: requests.Session) -> dict[str, str]:
    """Fetches dictionary of {remote_path: sha} in a single HTTP call."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{BRANCH}?recursive=1"
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code == 200:
            tree = resp.json().get("tree", [])
            return {item["path"]: item["sha"] for item in tree if item["type"] == "blob"}
    except Exception as e:
        print(f"[Warn] Could not fetch remote tree: {e}")
    return {}


def purge_remote_sensitive_files(session: requests.Session, remote_tree: dict[str, str]) -> int:
    """Detects and deletes any sensitive or unwanted files that exist on GitHub."""
    to_delete = {path: sha for path, sha in remote_tree.items() if should_ignore(path)}
    if not to_delete:
        return 0

    print(f"\n🛡️  Cleaning up {len(to_delete)} sensitive/unwanted files from GitHub repository...")
    deleted_count = 0
    for path, sha in to_delete.items():
        del_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
        payload = {
            "message": f"Security: remove sensitive file {path}",
            "sha": sha,
            "branch": BRANCH
        }
        for attempt in range(3):
            try:
                resp = session.delete(del_url, json=payload, timeout=20)
                if resp.status_code in (200, 204):
                    print(f"  🗑️  Purged from GitHub: {path}")
                    deleted_count += 1
                    break
                time.sleep(1)
            except Exception:
                time.sleep(2)
    return deleted_count


def upload_file_to_github(
    session: requests.Session,
    base_dir: Path,
    file_path: Path,
    existing_sha: str | None = None
) -> bool:
    rel_path = str(file_path.relative_to(base_dir)).replace("\\", "/")
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{rel_path}"

    try:
        content_bytes = file_path.read_bytes()
        encoded_content = base64.b64encode(content_bytes).decode("utf-8")
    except Exception as e:
        print(f"❌ Failed to read {rel_path}: {e}")
        return False

    payload = {
        "message": f"Sync: update {rel_path}",
        "content": encoded_content,
        "branch": BRANCH
    }
    if existing_sha:
        payload["sha"] = existing_sha

    # Retry up to 3 times on connection hiccup or timeout
    for attempt in range(1, 4):
        try:
            resp = session.put(url, json=payload, timeout=30)
            if resp.status_code in (200, 201):
                return True
            if resp.status_code == 409:
                # SHA conflict: re-fetch SHA and retry once
                check = session.get(url, timeout=15)
                if check.status_code == 200:
                    payload["sha"] = check.json().get("sha")
                    retry_resp = session.put(url, json=payload, timeout=30)
                    if retry_resp.status_code in (200, 201):
                        return True
            print(f"❌ HTTP {resp.status_code} ({resp.reason}) on attempt {attempt}")
        except (requests.Timeout, requests.ConnectionError) as net_err:
            if attempt < 3:
                time.sleep(2 * attempt)
            else:
                print(f"❌ Network timeout on {rel_path}: {net_err}")
        except Exception as ex:
            print(f"❌ Error uploading {rel_path}: {ex}")
            break
    return False


def get_default_token() -> str:
    env_path = Path(__file__).resolve().parent / "core" / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("GITHUB_API_KEY="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        return val
        except Exception:
            pass
    return ""


def main():
    print("=================================================================")
    print("  ANSH - Your Own AI Friend — GitHub Release Synchronizer        ")
    print("  Developer: Anshu Dubey | Target: mastgamerz37-ux/ansh-ai       ")
    print("=================================================================\n")

    default_token = get_default_token()
    if default_token:
        masked = default_token[:4] + "..." + default_token[-4:]
        user_input = input(f"Enter GitHub PAT [Press ENTER to use token from core/.env ({masked})]: ").strip()
        token = user_input if user_input else default_token
    else:
        token = input("Enter your GitHub Personal Access Token (PAT): ").strip()

    if not token:
        print("❌ Token cannot be empty. Exiting.")
        sys.exit(1)

    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ANSH-Uploader"
    })

    print("\n🔍 Checking GitHub repository access...")
    if not ensure_repo_exists(session, token):
        print("❌ Could not verify repository. Check your PAT permissions.")
        sys.exit(1)

    print("🌳 Fetching remote file tree from GitHub...")
    remote_tree = get_remote_tree(session)
    print(f"   Found {len(remote_tree)} existing files on remote branch '{BRANCH}'.")

    # Step 1: Purge any sensitive files that were uploaded in previous partial runs
    purged = purge_remote_sensitive_files(session, remote_tree)
    if purged > 0:
        print(f"✅ Cleaned {purged} sensitive files from GitHub!\n")
        # Refresh tree after purge
        remote_tree = get_remote_tree(session)

    # Step 2: Upload clean files
    base_dir = Path(__file__).resolve().parent
    local_files = get_all_files(base_dir)
    print(f"🚀 Found {len(local_files)} clean production files to sync.\n")

    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, f in enumerate(local_files, 1):
        rel = str(f.relative_to(base_dir)).replace("\\", "/")
        try:
            content = f.read_bytes()
            local_sha = git_blob_sha(content)
        except Exception:
            local_sha = None

        remote_sha = remote_tree.get(rel)

        # Skip if identical on GitHub
        if remote_sha and local_sha and remote_sha == local_sha:
            skipped_count += 1
            print(f"[{idx:03d}/{len(local_files):03d}] {rel} -> ⏩ [Skipped - Up to date]")
            continue

        print(f"[{idx:03d}/{len(local_files):03d}] Uploading: {rel}...", end="", flush=True)
        if upload_file_to_github(session, base_dir, f, existing_sha=remote_sha):
            print(" ✅ OK")
            uploaded_count += 1
        else:
            print(" ❌ FAILED")
            failed_count += 1

    print(f"\n=================================================================")
    print(f"  🎉 Sync Complete! ")
    print(f"  - Uploaded: {uploaded_count} files")
    print(f"  - Already Up to Date: {skipped_count} files")
    if failed_count:
        print(f"  - Failed: {failed_count} files")
    print(f"  🔗 View your repository: https://github.com/{REPO_OWNER}/{REPO_NAME}")
    print(f"=================================================================\n")


if __name__ == "__main__":
    main()
