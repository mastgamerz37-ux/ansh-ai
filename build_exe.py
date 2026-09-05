import os
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd):
    print(f"Running: {cmd}")
    subprocess.check_call(cmd, shell=True)

def build():
    print("=== Starting PyInstaller Build ===")
    
    # 1. Install pyinstaller if not present
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        run_cmd(f"{sys.executable} -m pip install pyinstaller")

    # 2. Build the command
    # --noconfirm: Overwrite output directory
    # --onefile: Create a single executable
    # --windowed: Do not show a console window
    # --name ansh: Output will be ansh.exe
    # --version-file: Attach developer metadata
    # --add-data: Include necessary folders
    
    separator = ";" if os.name == "nt" else ":"
    
    # List of folders/files to include
    data_flags = [
        f'--add-data "actions{separator}actions"',
        f'--add-data "core{separator}core"',
        f'--add-data "memory{separator}memory"',
        f'--add-data "config{separator}config"',
        f'--add-data "keys{separator}keys"',
        f'--add-data "face.png{separator}."'
    ]
    
    # Ensure empty folders exist so Pyinstaller doesn't fail
    for d in ["actions", "core", "memory", "config", "keys"]:
        Path(d).mkdir(exist_ok=True)
    if not Path("face.png").exists():
        # Create dummy file if face.png is missing just to avoid build crash
        with open("face.png", "wb") as f:
            f.write(b"")

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "ansh",
        "--version-file", "version_info.txt",
    ] + data_flags + ["main.py"]

    cmd_str = " ".join(pyinstaller_cmd)
    
    # 3. Run Build
    run_cmd(cmd_str)
    
    print("=== Build Complete! ===")
    dist_path = Path("dist") / "ansh.exe"
    if dist_path.exists():
        print(f"SUCCESS: Executable created at {dist_path.absolute()}")
        print("You can safely upload this ansh.exe to anyone.")
    else:
        print("ERROR: ansh.exe was not generated. Check the logs.")

if __name__ == "__main__":
    build()
