import os
import subprocess
import sys

root_dir = os.path.dirname(os.path.abspath(__file__))

# Check if a local virtualenv exists
venv_python_win = os.path.join(root_dir, ".venv", "Scripts", "python.exe")
venv_python_posix = os.path.join(root_dir, ".venv", "bin", "python")

if os.path.exists(venv_python_win):
    py_bin = venv_python_win
elif os.path.exists(venv_python_posix):
    py_bin = venv_python_posix
else:
    py_bin = sys.executable

cmd = [
    py_bin,
    "-m",
    "uvicorn",
    "backend.api.main:app",
    "--reload",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--app-dir",
    root_dir,
]

sys.exit(subprocess.call(cmd))
