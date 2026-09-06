"""
publish_to_pypi.py — PyPI Publisher for ANSH - Your Own AI Friend
Created & Developed by Anshu Dubey

Uploads built distributions (dist/*.whl and dist/*.tar.gz) to PyPI.
"""
import sys
import subprocess
from pathlib import Path


def main():
    print("=================================================================")
    print("  ANSH - Your Own AI Friend — PyPI Publisher                     ")
    print("  Package: ansh-ai v1.0.0 | Developer: Anshu Dubey               ")
    print("=================================================================\n")

    dist_dir = Path(__file__).resolve().parent / "dist"
    files = list(dist_dir.glob("ansh_ai-1.0.0*"))
    if not files:
        print("❌ No distribution files found in dist/. Please run 'python -m build' first.")
        sys.exit(1)

    print(f"📦 Found {len(files)} packages ready in dist/:")
    for f in files:
        print(f"  - {f.name} ({f.stat().st_size / 1024:.1f} KB)")

    print("\nℹ️  To publish to PyPI:")
    print("   1. Create a free account at https://pypi.org if you don't have one.")
    print("   2. Go to Account Settings -> 'API tokens' -> 'Add API token'.")
    print("   3. Copy your API token (starts with 'pypi-...').\n")

    token = input("Enter your PyPI API Token (pypi-...): ").strip()
    if not token:
        print("❌ Token cannot be empty. Exiting.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "twine", "upload",
        "--username", "__token__",
        "--password", token,
        str(dist_dir / "*")
    ]

    print("\n🚀 Uploading to PyPI...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n🎉 SUCCESS! Package 'ansh-ai' is now live on PyPI!")
        print("👉 Users worldwide can now install it via: pip install ansh-ai\n")
    else:
        print("\n❌ Upload failed. Please check your PyPI token and permissions.")


if __name__ == "__main__":
    main()
