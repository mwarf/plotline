"""
plotline.llm.parsing - LLM output JSON parsing with validation.

Handles parsing LLM responses into structured JSON with error recovery.
"""

from __future__ import annotations

import json
import re
from typing import Any

from plotline.exceptions import LLMResponseError


def extract_json_from_response(response: str) -> str:
    """Extract JSON from LLM response with multiple strategies.

    Args:
        response: Raw LLM response text

    Returns:
        Extracted JSON string (may be incomplete if truncated)

    Raises:
        LLMResponseError: If no JSON object start found
    """
    text = response.strip()

    # Remove markdown code blocks
    if "```" in text:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

    # Find the start of the JSON object
    start_idx = text.find("{")
    if start_idx == -1:
        raise LLMResponseError("No JSON object found in response")

    # Try to find a complete JSON object with balanced braces
    # This handles cases where there's text after the JSON
    depth = 0
    in_string = False
    escape_next = False
    end_idx = None

    for i, char in enumerate(text[start_idx:], start_idx):
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end_idx = i + 1
                break

    if end_idx:
        return text[start_idx:end_idx]

    # No complete JSON found - return everything from { for repair attempts
    return text[start_idx:]


def repair_json(text: str) -> str:
    """Attempt to repair common JSON issues.

    Args:
        text: JSON string with potential issues

    Returns:
        Repaired JSON string
    """
    # Remove trailing commas before } or ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    # Fix unescaped newlines in strings (basic attempt)
    text = re.sub(r'(?<!\\)\n(?=[^"]*"[^"]*$)', "\\n", text)

    # Fix missing closing braces - count open vs close
    open_braces = text.count("{")
    close_braces = text.count("}")
    open_brackets = text.count("[")
    close_brackets = text.count("]")

    # Add missing closing characters
    if open_brackets > close_brackets:
        text += "]" * (open_brackets - close_brackets)
    if open_braces > close_braces:
        text += "}" * (open_braces - close_braces)

    return text


def parse_llm_json(response: str) -> dict[str, Any]:
    """Parse JSON from LLM response with error recovery.

    Handles common issues:
    - Markdown code blocks (```json ... ```)
    - Trailing commas
    - Missing braces
    - Text before/after JSON

    Args:
        response: Raw LLM response text

    Returns:
        Parsed JSON dict

    Raises:
        LLMResponseError: If parsing fails
    """
    text = extract_json_from_response(response)

    # First attempt: parse as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Second attempt: repair and retry
    repaired = repair_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Third attempt: try to truncate at last valid position
    # Strategy: Find the last complete object in an array (looking for }, patterns)
    # or the last complete key-value pair

    # Try to find last complete object in an array
    last_complete_object = text.rfind("},")
    if last_complete_object > 0:
        truncated = text[: last_complete_object + 1]  # Keep the }
        # Close any open structures
        open_braces = truncated.count("{") - truncated.count("}")
        open_brackets = truncated.count("[") - truncated.count("]")
        truncated += "]" * max(0, open_brackets) + "}" * max(0, open_braces)

        try:
            return json.loads(truncated)
        except json.JSONDecodeError:
            pass

    # Try to find last complete string value (ending with ",)
    last_valid = text.rfind('",')
    if last_valid > 0:
        truncated = text[: last_valid + 1]  # Keep the closing quote
        # Close any open structures
        open_braces = truncated.count("{") - truncated.count("}")
        open_brackets = truncated.count("[") - truncated.count("]")
        truncated += "]" * max(0, open_brackets) + "}" * max(0, open_braces)

        try:
            return json.loads(truncated)
        except json.JSONDecodeError:
            pass

    raise LLMResponseError(
        f"Failed to parse LLM response as JSON after repair attempts.\n\n"
        f"Response (first 500 chars):\n{text[:500]}"
    )


def validate_themes_response(data: dict[str, Any], interview_id: str) -> dict[str, Any]:
    """Validate and normalize theme extraction response.

    Args:
        data: Parsed JSON from LLM
        interview_id: Expected interview ID for segment validation

    Returns:
        Validated and normalized themes dict

    Raises:
        LLMResponseError: If validation fails
    """
    if "themes" not in data:
        raise LLMResponseError("Theme extraction response missing 'themes' key")

    raw_themes = data["themes"]
    if not isinstance(raw_themes, list):
        raise LLMResponseError(f"'themes' must be a list, got {type(raw_themes).__name__}")

    themes = []
    for i, theme in enumerate(raw_themes):
        if not isinstance(theme, dict):
            raise LLMResponseError(f"Theme {i} must be an object, got {type(theme).__name__}")

        if not theme.get("name"):
            raise LLMResponseError(f"Theme {i} missing 'name'")

        # Safely coerce strength to float
        strength_raw = theme.get("strength", 0.5)
        try:
            strength = float(strength_raw)
        except (ValueError, TypeError):
            strength = 0.5

        # Validate and filter segment_ids
        raw_segment_ids = theme.get("segment_ids", [])
        if not isinstance(raw_segment_ids, list):
            raw_segment_ids = []
        valid_segment_ids = [
            sid for sid in raw_segment_ids if isinstance(sid, str) and sid.startswith(interview_id)
        ]

        normalized = {
            "theme_id": theme.get("theme_id", f"theme_{i + 1:03d}"),
            "name": theme["name"],
            "description": theme.get("description", ""),
            "segment_ids": valid_segment_ids,
            "emotional_character": theme.get("emotional_character", ""),
            "strength": strength,
        }

        if theme.get("brief_alignment"):
            normalized["brief_alignment"] = theme["brief_alignment"]

        themes.append(normalized)

    # Validate intersections
    raw_intersections = data.get("intersections", [])
    if not isinstance(raw_intersections, list):
        raw_intersections = []
    intersections = []
    for intersection in raw_intersections:
        if not isinstance(intersection, dict):
            continue
        seg_id = intersection.get("segment_id", "")
        if isinstance(seg_id, str) and seg_id.startswith(interview_id):
            intersections.append(
                {
                    "segment_id": seg_id,
                    "themes": intersection.get("themes", [])
                    if isinstance(intersection.get("themes"), list)
                    else [],
                    "note": intersection.get("note", "")
                    if isinstance(intersection.get("note"), str)
                    else "",
                }
            )

    result = {
        "themes": themes,
        "intersections": intersections,
    }

    # Validate off_message_segments
    raw_off_message = data.get("off_message_segments", [])
    if isinstance(raw_off_message, list):
        off_message_segments = []
        for seg in raw_off_message:
            if isinstance(seg, dict):
                seg_id = seg.get("segment_id", "")
                if isinstance(seg_id, str) and seg_id.startswith(interview_id):
                    off_message_segments.append(
                        {
                            "segment_id": seg_id,
                            "reason": seg.get("reason", "")
                            if isinstance(seg.get("reason"), str)
                            else "",
                        }
                    )
        if off_message_segments:
            result["off_message_segments"] = off_message_segments

    return result


def validate_synthesis_response(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize synthesis response.

    Args:
        data: Parsed JSON from LLM

    Returns:
        Validated synthesis dict

    Raises:
        LLMResponseError: If validation fails
    """
    if "unified_themes" not in data:
        raise LLMResponseError("Synthesis response missing 'unified_themes' key")

    unified_themes = []
    for i, theme in enumerate(data["unified_themes"]):
        normalized = {
            "unified_theme_id": theme.get("unified_theme_id", f"utheme_{i + 1:03d}"),
            "name": theme.get("name", "Unnamed"),
            "description": theme.get("description", ""),
            "source_themes": theme.get("source_themes", []),
            "all_segment_ids": theme.get("all_segment_ids", []),
            "perspectives": theme.get("perspectives", ""),
            "brief_alignment": theme.get("brief_alignment"),
        }
        unified_themes.append(normalized)

    result = {
        "unified_themes": unified_themes,
        "best_takes": data.get("best_takes", []),
    }

    return result


def validate_arc_response(
    data: dict[str, Any],
    target_duration: int,
) -> dict[str, Any]:
    """Validate and normalize arc response.

    Args:
        data: Parsed JSON from LLM
        target_duration: Expected target duration in seconds

    Returns:
        Validated arc dict

    Raises:
        LLMResponseError: If validation fails
    """
    if "arc" not in data:
        raise LLMResponseError("Arc response missing 'arc' key")

    arc = []
    for i, item in enumerate(data["arc"]):
        if not item.get("segment_id"):
            raise LLMResponseError(f"Arc item {i} missing 'segment_id'")

        normalized = {
            "position": item.get("position", i + 1),
            "segment_id": item["segment_id"],
            "interview_id": item.get("interview_id", ""),
            "role": item.get("role", "unknown"),
            "themes": item.get("themes", []),
            "editorial_notes": item.get("editorial_notes", ""),
            "pacing": item.get("pacing", ""),
            "brief_message": item.get("brief_message"),
        }
        arc.append(normalized)

    result = {
        "target_duration_seconds": data.get("target_duration_seconds", target_duration),
        "estimated_duration_seconds": data.get("estimated_duration_seconds", 0),
        "narrative_mode": data.get("narrative_mode", "emergent"),
        "arc": arc,
        "coverage_gaps": data.get("coverage_gaps", []),
        "alternate_candidates": data.get("alternate_candidates", []),
    }

    return result


def validate_flags_response(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize cultural flags response.

    Args:
        data: Parsed JSON from LLM

    Returns:
        Validated flags dict
    """
    flags = []
    for flag in data.get("flags", []):
        normalized = {
            "segment_id": flag.get("segment_id", ""),
            "reason": flag.get("reason", ""),
            "review_type": flag.get("review_type", "cultural_advisor"),
            "severity": flag.get("severity", "review_recommended"),
        }
        flags.append(normalized)

    return {"flags": flags}
