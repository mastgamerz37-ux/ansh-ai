"""
upload_to_github.py — Pure Python GitHub Repository Synchronizer for ANSH
Created & Developed by Anshu Dubey

Features:
- Pure Python using GitHub REST API v3 (no Git installation required).
- Uploads and updates all clean source code, documentation, assets, and configs.
- Automatically creates repository on GitHub if it doesn't already exist.
- Strictly ignores private keys, generators, user configs, credentials, and build binaries.
"""
from __future__ import annotations

import os
import sys
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path


REPO_OWNER = "mastgamerz37-ux"
REPO_NAME = "ansh-ai"
BRANCH = "main"

# Directories and files to strictly ignore
IGNORED_DIR_NAMES = {
    "venv", ".venv", "env", "ENV", "build", "dist", "__pycache__",
    "scratch", ".vscode", ".idea", ".git", "ansh_ai.egg-info",
    "release", "release_app", "AnshAI_Release"
}

IGNORED_EXACT_FILES = {
    "keys/product_keys.txt",
    "keys/generate_keys.py",
    "config/api_keys.json",
    "config/license.json",
    "installer/release/ANSH_Setup_v1.0.exe"
}

IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".exe", ".spec", ".egg", ".swp", ".swo"
}


def should_ignore(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    
    # Check exact file matches
    if normalized in IGNORED_EXACT_FILES:
        return True
        
    parts = normalized.split("/")
    
    # Check ignored directories
    for part in parts:
        if part in IGNORED_DIR_NAMES or part.endswith(".egg-info"):
            return True
            
    # Check extension
    filename = parts[-1]
    ext = os.path.splitext(filename)[1].lower()
    if ext in IGNORED_EXTENSIONS:
        return True
        
    # Ignore OS files
    if filename in (".DS_Store", "Thumbs.db"):
        return True

    return False


def get_all_files(base_dir: Path) -> list[Path]:
    file_list: list[Path] = []
    for root, dirs, files in os.walk(base_dir):
        # Prune ignored directory traversal
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


def ensure_repo_exists(token: str) -> bool:
    """Verifies that the repository exists on GitHub, creates it if missing."""
    check_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    req = urllib.request.Request(
        check_url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ANSH-Uploader"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                return True
    except urllib.error.HTTPError as he:
        if he.code == 404:
            print(f"📦 Repository '{REPO_OWNER}/{REPO_NAME}' not found on GitHub. Creating it now...")
            create_url = "https://api.github.com/user/repos"
            payload = {
                "name": REPO_NAME,
                "description": "ANSH - Your Own AI Friend: Real-time Multimodal Voice Assistant, Smart Island HUD & Autonomous AI System",
                "private": False,
                "auto_init": True
            }
            create_req = urllib.request.Request(
                create_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                    "User-Agent": "ANSH-Uploader"
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(create_req) as create_resp:
                    if create_resp.status in (200, 201):
                        print(f"✅ Successfully created repository '{REPO_OWNER}/{REPO_NAME}'!")
                        return True
            except Exception as e:
                print(f"❌ Failed to automatically create repo: {e}")
                return False
        else:
            print(f"❌ GitHub API Error: {he.code} {he.reason}")
            return False
    except Exception as ex:
        print(f"❌ Connection error: {ex}")
        return False
    return True


def upload_file_to_github(token: str, base_dir: Path, file_path: Path) -> bool:
    rel_path = str(file_path.relative_to(base_dir)).replace("\\", "/")
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{rel_path}"

    try:
        content_bytes = file_path.read_bytes()
        encoded_content = base64.b64encode(content_bytes).decode("utf-8")
    except Exception as e:
        print(f"❌ Failed to read {rel_path}: {e}")
        return False

    # Check if file exists to fetch sha for update
    sha = None
    req_check = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ANSH-Uploader"
        }
    )
    try:
        with urllib.request.urlopen(req_check) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            sha = data.get("sha")
    except urllib.error.HTTPError:
        pass

    payload = {
        "message": f"Release v1.0.0: update {rel_path}",
        "content": encoded_content,
        "branch": BRANCH
    }
    if sha:
        payload["sha"] = sha

    req_upload = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "ANSH-Uploader"
        },
        method="PUT"
    )

    try:
        with urllib.request.urlopen(req_upload) as resp:
            if resp.status in (200, 201):
                return True
    except urllib.error.HTTPError as he:
        print(f"❌ Error uploading {rel_path}: {he.code} {he.reason}")
    except Exception as ex:
        print(f"❌ Error uploading {rel_path}: {ex}")
    return False


def main():
    print("=================================================================")
    print("  ANSH - Your Own AI Friend — GitHub Release Synchronizer        ")
    print("  Developer: Anshu Dubey | Target: mastgamerz37-ux/ansh-ai       ")
    print("=================================================================\n")

    token = input("Enter your GitHub Personal Access Token (PAT): ").strip()
    if not token:
        print("❌ Token cannot be empty. Exiting.")
        sys.exit(1)

    print("\n🔍 Checking GitHub repository access...")
    if not ensure_repo_exists(token):
        print("❌ Could not verify or create repository. Please check your GitHub token permissions.")
        sys.exit(1)

    base_dir = Path(__file__).resolve().parent
    files = get_all_files(base_dir)

    print(f"\n🚀 Found {len(files)} clean production files to sync.\n")
    success_count = 0

    for idx, f in enumerate(files, 1):
        rel = str(f.relative_to(base_dir)).replace("\\", "/")
        print(f"[{idx:02d}/{len(files):02d}] Uploading: {rel}...", end="", flush=True)
        if upload_file_to_github(token, base_dir, f):
            print(" ✅ OK")
            success_count += 1
        else:
            print(" ❌ FAILED")

    print(f"\n🎉 Finished! Uploaded {success_count}/{len(files)} files successfully!")
    print(f"🔗 View your repository: https://github.com/{REPO_OWNER}/{REPO_NAME}\n")


if __name__ == "__main__":
    main()
