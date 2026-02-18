"""
plotline.io - JSON read/write helpers, atomic file writes.

Centralized I/O utilities for all pipeline stages.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    """Read JSON file with UTF-8 encoding.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """Write JSON file atomically with pretty formatting.

    Writes to a temp file first, then renames to prevent corruption
    on interruption.

    Args:
        path: Destination path for JSON file
        data: Data to write
        indent: Indentation level for pretty printing (default: 2)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp_path = Path(tmp.name)
        try:
            json.dump(data, tmp, indent=indent, ensure_ascii=False)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
    tmp_path.rename(path)


def read_text(path: Path) -> str:
    """Read text file with UTF-8 encoding.

    Args:
        path: Path to text file

    Returns:
        File contents as string
    """
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path: Path, content: str) -> None:
    """Write text file atomically.

    Args:
        path: Destination path
        content: Text content to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp_path = Path(tmp.name)
        try:
            tmp.write(content)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
    tmp_path.rename(path)
