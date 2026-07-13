"""File operation utilities for JARVIS."""

from __future__ import annotations

import os
import shutil
import logging

logger = logging.getLogger(__name__)


def copy_file(source: str = "", destination: str = "") -> str:
    """Copy a file from source to destination.

    Args:
        source: Path to the file to copy.
        destination: Path to copy the file to. If empty, copies to Desktop.
    """
    source = (source or "").strip()
    if not source:
        return "No source file specified."

    if not os.path.exists(source):
        return f"File not found: {source}"

    if not destination:
        destination = os.path.join(os.path.expanduser("~"), "Desktop", os.path.basename(source))

    try:
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        shutil.copy2(source, destination)
        return f"Copied to: {destination}"
    except Exception as e:
        logger.exception("Failed to copy file")
        return f"Copy failed: {e}"


def rename_file(source: str = "", new_name: str = "") -> str:
    """Rename a file.

    Args:
        source: Path to the file to rename.
        new_name: New filename (not full path).
    """
    source = (source or "").strip()
    new_name = (new_name or "").strip()

    if not source:
        return "No file specified."

    if not os.path.exists(source):
        return f"File not found: {source}"

    if not new_name:
        return "No new name specified."

    try:
        directory = os.path.dirname(source)
        destination = os.path.join(directory, new_name)
        os.rename(source, destination)
        return f"Renamed to: {destination}"
    except Exception as e:
        logger.exception("Failed to rename file")
        return f"Rename failed: {e}"
