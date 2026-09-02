#!/usr/bin/env python3
"""TraceX DVR Forensics Platform — Root Entry Point.

Can be launched via:
    python3 main.py             # Launches interactive TUI
    tracex                      # Launches interactive TUI
    dvrforensics                # Launches interactive TUI
    python3 main.py --help      # Lists CLI commands
    python3 main.py pipeline    # Guided step-by-step file analysis wizard
"""

from backend.cli.main import app

if __name__ == "__main__":
    app()
