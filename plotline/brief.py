"""
plotline.brief - Creative brief parser.

Parses Markdown or YAML briefs into structured data for LLM prompts.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def normalize_key_messages(messages: list[Any]) -> list[dict[str, str]]:
    """Normalize key messages to {id, text} objects.

    Ensures all key messages have consistent structure with id and text fields.
    Strings are wrapped into objects with auto-generated sequential IDs.

    Args:
        messages: List of key messages (strings or {id, text} dicts)

    Returns:
        List of dicts with 'id' and 'text' keys
    """
    normalized = []
    for i, msg in enumerate(messages):
        if isinstance(msg, str):
            normalized.append(
                {
                    "id": f"msg_{i + 1:03d}",
                    "text": msg.strip(),
                }
            )
        elif isinstance(msg, dict):
            text = msg.get("text", "")
            if msg.get("id"):
                normalized.append({"id": msg["id"], "text": text})
            else:
                normalized.append(
                    {
                        "id": f"msg_{i + 1:03d}",
                        "text": text,
                    }
                )
    return normalized


def parse_markdown_brief(content: str) -> dict[str, Any]:
    """Parse a Markdown brief into structured data.

    Looks for standard headings: Key Messages, Audience, Target Duration,
    Tone Direction, Must Include, Avoid.

    Args:
        content: Markdown content

    Returns:
        Structured brief dict
    """
    result: dict[str, Any] = {
        "key_messages": [],
        "audience": None,
        "target_duration": None,
        "tone_direction": None,
        "must_include_topics": [],
        "avoid_topics": [],
    }

    sections = re.split(r"\n#{1,3}\s+", content)

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().split("\n")
        if not lines:
            continue

        heading = lines[0].lower().strip()
        body = "\n".join(lines[1:]).strip()

        if "key message" in heading:
            items = re.findall(r"[-*]\s+(.+)", body)
            if items:
                result["key_messages"] = [i.strip() for i in items]
            elif body:
                result["key_messages"] = [body]
        elif "audience" in heading:
            result["audience"] = body
        elif "duration" in heading or "length" in heading:
            result["target_duration"] = body
        elif "tone" in heading:
            result["tone_direction"] = body
        elif "must include" in heading or "must cover" in heading:
            items = re.findall(r"[-*]\s+(.+)", body)
            result["must_include_topics"] = [i.strip() for i in items] if items else [body]
        elif "avoid" in heading:
            items = re.findall(r"[-*]\s+(.+)", body)
            result["avoid_topics"] = [i.strip() for i in items] if items else [body]

    return result


def parse_yaml_brief(content: str) -> dict[str, Any]:
    """Parse a YAML brief into structured data.

    Args:
        content: YAML content

    Returns:
        Structured brief dict
    """
    data = yaml.safe_load(content) or {}

    result: dict[str, Any] = {
        "key_messages": data.get("key_messages", data.get("keyMessages", [])),
        "audience": data.get("audience"),
        "target_duration": data.get("target_duration", data.get("targetDuration")),
        "tone_direction": data.get("tone_direction", data.get("toneDirection")),
        "must_include_topics": data.get("must_include_topics", data.get("mustIncludeTopics", [])),
        "avoid_topics": data.get("avoid_topics", data.get("avoidTopics", [])),
    }

    if isinstance(data, dict):
        for key in ["name", "title", "summary", "project"]:
            if key in data:
                result[key] = data[key]

    return result


def parse_brief(brief_path: Path) -> dict[str, Any]:
    """Parse a brief file (Markdown or YAML).

    Args:
        brief_path: Path to brief file

    Returns:
        Structured brief dict

    Raises:
        FileNotFoundError: If brief file doesn't exist
        ValueError: If brief has no key messages
    """
    if not brief_path.exists():
        raise FileNotFoundError(f"Brief file not found: {brief_path}")

    content = brief_path.read_text(encoding="utf-8")

    if brief_path.suffix.lower() in (".yaml", ".yml"):
        result = parse_yaml_brief(content)
    else:
        result = parse_markdown_brief(content)

    result["source_file"] = str(brief_path)
    result["name"] = result.get("name", brief_path.stem)

    if result.get("key_messages"):
        result["key_messages"] = normalize_key_messages(result["key_messages"])

    if not result.get("key_messages"):
        raise ValueError("Brief must contain at least one key message")

    return result


def save_brief(brief: dict[str, Any], output_path: Path) -> None:
    """Save parsed brief to JSON.

    Args:
        brief: Parsed brief dict
        output_path: Path to save JSON
    """
    from datetime import UTC, datetime

    from plotline.io import write_json

    brief["parsed_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    write_json(output_path, brief)
