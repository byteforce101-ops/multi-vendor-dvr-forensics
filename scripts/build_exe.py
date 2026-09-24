"""Script to compile TraceX DVR/NVR Forensics into a standalone Windows .exe executable."""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()


def build_exe():
    print("=" * 70)
    print("  TraceX DVR Forensics — Standalone Windows .exe Builder")
    print("=" * 70)
    print()

    # 1. Check PyInstaller
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} is available.")
    except ImportError:
        print("[INFO] PyInstaller not installed. Installing now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Run PyInstaller with tracex.spec
    spec_file = ROOT_DIR / "tracex.spec"
    if not spec_file.exists():
        print(f"[ERROR] Spec file not found at {spec_file}")
        sys.exit(1)

    print(f"\n[INFO] Compiling from {spec_file} ...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file),
    ]

    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode == 0:
        dist_exe = ROOT_DIR / "dist" / "TraceX-DVR-Forensics.exe"
        print("\n" + "=" * 70)
        print("  BUILD SUCCESSFUL!")
        print("=" * 70)
        print(f"\nExecutable created at:\n  {dist_exe}\n")
        print("You can distribute this single .exe file to any Windows machine.")
    else:
        print("\n[ERROR] Build failed with exit code:", result.returncode)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build_exe()
