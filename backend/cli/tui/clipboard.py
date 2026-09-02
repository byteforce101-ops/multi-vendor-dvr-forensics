"""backend/cli/tui/clipboard.py — Cross-platform OS clipboard access.

Enables pasting system clipboard contents (including copied file paths)
directly into Textual input fields across Windows, WSL, Linux, and macOS.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _get_windows_clipboard() -> str:
    """Retrieve clipboard text on Windows using native ctypes win32 API."""
    try:
        import ctypes
        if not hasattr(ctypes, "windll"):
            return ""

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        CF_UNICODETEXT = 13

        if not user32.OpenClipboard(None):
            return ""
        try:
            h_glb = user32.GetClipboardData(CF_UNICODETEXT)
            if not h_glb:
                return ""
            kernel32.GlobalLock.restype = ctypes.c_void_p
            ptr = kernel32.GlobalLock(h_glb)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(h_glb)
        finally:
            user32.CloseClipboard()
    except Exception:
        return ""


def get_clipboard_text() -> str:
    """Retrieve text from the operating system clipboard."""
    # 1. Try pyperclip
    try:
        import pyperclip
        text = pyperclip.paste()
        if text:
            return text
    except Exception:
        pass

    # 2. Windows native ctypes
    if sys.platform == "win32":
        w_text = _get_windows_clipboard()
        if w_text:
            return w_text

    # 3. WSL environment: query Windows host clipboard via powershell.exe
    if "WSL_DISTRO_NAME" in os.environ or "microsoft" in os.uname().release.lower() if hasattr(os, "uname") else False:
        if shutil.which("powershell.exe"):
            try:
                out = subprocess.check_output(
                    ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                if out:
                    return out.rstrip("\r\n")
            except Exception:
                pass

    # 4. Wayland (wl-paste)
    if shutil.which("wl-paste"):
        try:
            out = subprocess.check_output(
                ["wl-paste", "--no-newline"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1,
            )
            if out:
                return out
        except Exception:
            pass

    # 5. X11 (xclip / xsel)
    if shutil.which("xclip"):
        try:
            out = subprocess.check_output(
                ["xclip", "-selection", "clipboard", "-o"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1,
            )
            if out:
                return out
        except Exception:
            pass

    if shutil.which("xsel"):
        try:
            out = subprocess.check_output(
                ["xsel", "--clipboard", "--output"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1,
            )
            if out:
                return out
        except Exception:
            pass

    # 6. macOS (pbpaste)
    if shutil.which("pbpaste"):
        try:
            out = subprocess.check_output(
                ["pbpaste"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1,
            )
            if out:
                return out
        except Exception:
            pass

    return ""


def set_clipboard_text(text: str) -> None:
    """Copy text to the operating system clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except Exception:
        pass
