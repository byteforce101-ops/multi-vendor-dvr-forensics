#!/usr/bin/env bash
set -e

echo "======================================================="
echo "  Installing TraceX DVR Forensics Platform CLI        "
echo "======================================================="

if command -v pipx >/dev/null 2>&1; then
    echo "[+] Found pipx. Installing in an isolated environment..."
    pipx install git+https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git --force
elif command -v python3 >/dev/null 2>&1; then
    echo "[+] Installing via python3 pip..."
    python3 -m pip install --upgrade git+https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git
elif command -v python >/dev/null 2>&1; then
    echo "[+] Installing via python pip..."
    python -m pip install --upgrade git+https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git
else
    echo "[!] Error: Neither Python nor pipx was found on your system."
    echo "    Please install Python 3.11+ and retry."
    exit 1
fi

echo ""
echo "======================================================="
echo "  Installation Successful!                             "
echo "  Run 'tracex' or 'dvrforensics' from any terminal.    "
echo "======================================================="
