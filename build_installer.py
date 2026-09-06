"""
build_installer.py - Automated Legal Windows Installer Builder for ANSH - Your Own AI Friend

Performs:
1. Runs build_exe.py to package application into release_app/ansh/
2. Compiles installer/setup.iss into installer/release/ANSH_Setup_v1.0.exe using Inno Setup Compiler
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

# Force UTF-8 stdout for Windows console compatibility
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_command(cmd: str) -> None:
    print(f"[BuildInstaller] Executing: {cmd}")
    subprocess.check_call(cmd, shell=True)


def main():
    base_dir = Path(__file__).resolve().parent
    print("===========================================================")
    print("  ANSH - Your Own AI Friend - Production Installer Builder  ")
    print("  Developer: Anshu Dubey | Website: https://getyoursoft.page.gd")
    print("===========================================================\n")

    # Step 1: Run PyInstaller build
    print("[1/3] Packaging standalone application via build_exe.py...")
    run_command(f"{sys.executable} build_exe.py")

    # Step 2: Verify installer directory & EULA
    print("[2/3] Verifying legal installer scripts & EULA...")
    installer_dir = base_dir / "installer"
    eula_file = installer_dir / "EULA.txt"
    iss_file = installer_dir / "setup.iss"

    if not eula_file.exists() or not iss_file.exists():
        print("[ERROR] Missing EULA.txt or setup.iss in installer/ directory.")
        sys.exit(1)

    # Step 3: Compile Inno Setup Installer
    print("[3/3] Compiling legal Windows Setup Installer (setup.exe)...")
    possible_iscc_paths = [
        r"C:\Users\mastg\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    iscc_path = next((p for p in possible_iscc_paths if os.path.exists(p)), None)

    if iscc_path:
        run_command(f'"{iscc_path}" "{iss_file}"')
        setup_exe = installer_dir / "release" / "ANSH_Setup_v1.0.exe"
        print(f"\n[SUCCESS] Production Setup Installer created at: {setup_exe.absolute()}")
        print("You can distribute ANSH_Setup_v1.0.exe directly to your users!")
    else:
        print("\n[NOTICE] Inno Setup Compiler (ISCC.exe) is not installed on this system.")
        print("To compile installer into ANSH_Setup_v1.0.exe:")
        print("1. Download Inno Setup (Free): https://jrsoftware.org/isdl.php")
        print("2. Run 'python build_installer.py' again.")
        print(f"\nYour application executable is ready in:")
        print(f" - dist/ansh: {(base_dir / 'dist' / 'ansh').absolute()}")
        print(f" - release_app/ansh: {(base_dir / 'release_app' / 'ansh').absolute()}")


if __name__ == "__main__":
    main()
