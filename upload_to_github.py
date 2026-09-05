"""
upload_to_github.py — Pure Python GitHub Uploader for ANSH - Your Own AI Friend

Uploads repository files directly to GitHub using the GitHub REST API (No Git CLI required!).
Skips any files/folders defined in .gitignore (such as keys/ product keys and secrets).
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

# Folders / Files to ignore
IGNORED_PATTERNS = {
    "keys", "venv", ".venv", "env", "build", "dist", "__pycache__",
    "scratch", ".vscode", ".idea", "api_keys.json", "license.json", ".git"
}


def should_ignore(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    for p in parts:
        if p in IGNORED_PATTERNS or p.endswith(".pyc") or p.endswith(".exe"):
            return True
    return False


def get_all_files(base_dir: Path) -> list[Path]:
    file_list = []
    for root, dirs, files in os.walk(base_dir):
        # Prune ignored dirs
        dirs[:] = [d for d in dirs if not should_ignore(str(Path(root, d).relative_to(base_dir)))]
        for file in files:
            full_path = Path(root, file)
            rel_path = str(full_path.relative_to(base_dir))
            if not should_ignore(rel_path):
                file_list.append(full_path)
    return file_list


def upload_file_to_github(token: str, base_dir: Path, file_path: Path) -> bool:
    rel_path = str(file_path.relative_to(base_dir)).replace("\\", "/")
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{rel_path}"

    try:
        content_bytes = file_path.read_bytes()
        encoded_content = base64.b64encode(content_bytes).decode("utf-8")
    except Exception as e:
        print(f"❌ Failed to read {rel_path}: {e}")
        return False

    # Check if file exists to get SHA for update
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
        pass  # File does not exist yet

    payload = {
        "message": f"Upload {rel_path} - ANSH Production Release by Anshu Dubey",
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
                print(f"✅ Uploaded: {rel_path}")
                return True
    except urllib.error.HTTPError as he:
        print(f"❌ Error uploading {rel_path}: {he.code} {he.reason}")
    except Exception as ex:
        print(f"❌ Error uploading {rel_path}: {ex}")
    return False


def main():
    print("===========================================================")
    print("  ANSH - Your Own AI Friend — Pure Python GitHub Uploader  ")
    print("===========================================================\n")

    token = input("Enter your GitHub Personal Access Token (PAT): ").strip()
    if not token:
        print("❌ Token cannot be empty. Exiting.")
        sys.exit(1)

    base_dir = Path(__file__).resolve().parent
    files = get_all_files(base_dir)

    print(f"\nFound {len(files)} clean production files to upload (keys/ & secrets skipped).\n")
    success_count = 0

    for f in files:
        if upload_file_to_github(token, base_dir, f):
            success_count += 1

    print(f"\n🎉 Finished! Uploaded {success_count}/{len(files)} files to https://github.com/{REPO_OWNER}/{REPO_NAME}")


if __name__ == "__main__":
    main()
