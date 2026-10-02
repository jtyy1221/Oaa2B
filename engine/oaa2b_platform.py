#!/usr/bin/env python3
"""The OS-specific parts of the Oaa2B engine, picked by sys.platform. macOS behaviour is unchanged.

  * online_only(root)   cloud placeholders whose bytes are not on local disk yet
  * write_text(p, text) UTF-8 with LF endings on every OS, so a note is byte-identical on Mac and Windows

Python 3.9 standard library only.
"""
import os
import subprocess
import sys

MAC = sys.platform == "darwin"
WINDOWS = sys.platform == "win32"
HOST = "mac" if MAC else "windows" if WINDOWS else sys.platform   # heartbeat `relay:` field
NAME = "Mac" if MAC else "Windows PC" if WINDOWS else "relay computer"

# FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_OFFLINE
WIN_PLACEHOLDER = 0x400000 | 0x40000 | 0x1000


def online_only(root):
    """True when some file under root is an online-only placeholder."""
    if MAC:
        r = subprocess.run(["find", str(root), "-flags", "+dataless", "-print", "-quit"], capture_output=True, text=True)
        return bool(r.stdout.strip())
    if WINDOWS:
        for p in root.rglob("*"):
            try:
                if p.is_file() and os.stat(p).st_file_attributes & WIN_PLACEHOLDER:
                    return True
            except OSError:
                continue
    return False


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
