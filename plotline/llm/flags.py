"""
plotline.llm.flags - Cultural sensitivity flagging (LLM Pass).

Sends selected segments through a cultural sensitivity prompt to flag
content that may require community review before publication.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def flag_segments(
    segments: list[dict[str, Any]],
    client: Any,
    template_manager: Any,
    console: Any = None,
) -> dict[str, Any]:
    """Flag culturally sensitive segments via LLM.

    Args:
        segments: List of enriched segment dicts
        client: LLMClient instance
        template_manager: PromptTemplateManager instance
        console: Optional rich console for output

    Returns:
        Dict with flags list from LLM
    """
    from plotline.llm.parsing import parse_llm_json, validate_flags_response

    if not segments:
        return {"flags": []}

    formatted = template_manager.format_transcript_for_prompt(segments)

    variables = {
        "TRANSCRIPT": formatted,
    }

    prompt = template_manager.render("flags.txt", variables)

    if console:
        console.print(f"[dim]  Sending prompt ({len(prompt)} chars)...[/dim]")

    response = client.complete(
        prompt,
        max_tokens=4096,
        temperature=0.3,
        console=console,
    )

    data = parse_llm_json(response)
    validated = validate_flags_response(data)

    return validated


def run_flags(
    project_path: Path,
    manifest: dict[str, Any],
    client: Any,
    template_manager: Any,
    config: Any,
    force: bool = False,
    console: Any = None,
) -> dict[str, Any]:
    """Run cultural sensitivity flagging on selected segments.

    Reads selections.json, sends segments through the flags prompt,
    and updates flagged/flag_reason fields in-place.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        client: LLMClient instance
        template_manager: PromptTemplateManager instance
        config: PlotlineConfig instance
        force: Force run even if cultural_flags is disabled
        console: Optional rich console for output

    Returns:
        Dict with flagging summary
    """
    from plotline.project import read_json, write_json

    if not config.cultural_flags and not force:
        return {
            "flagged": 0,
            "total_segments": 0,
            "skipped": True,
            "reason": "Cultural flags disabled in config",
            "flags": [],
        }

    selections_path = project_path / "data" / "selections.json"
    if not selections_path.exists():
        raise FileNotFoundError("No selections found. Run 'plotline arc' first.")

    selections_data = read_json(selections_path)
    segments = selections_data.get("segments", [])

    if not segments:
        return {
            "flagged": 0,
            "total_segments": 0,
            "skipped": False,
            "reason": "No segments to flag",
            "flags": [],
        }

    for seg in segments:
        seg["flagged"] = False
        seg["flag_reason"] = None

    if console:
        console.print(f"[cyan]Flagging {len(segments)} segments for cultural sensitivity...[/cyan]")

    flags_result = flag_segments(
        segments=segments,
        client=client,
        template_manager=template_manager,
        console=console,
    )

    flags = flags_result.get("flags", [])
    segment_by_id = {s.get("segment_id"): s for s in segments}

    flagged_count = 0
    for flag in flags:
        seg_id = flag.get("segment_id", "")
        segment = segment_by_id.get(seg_id)

        if not segment:
            if console:
                console.print(
                    f"[yellow]  Warning: Flag references unknown "
                    f"segment {seg_id}, skipping[/yellow]"
                )
            continue

        segment["flagged"] = True
        segment["flag_reason"] = flag.get("reason", "Flagged for cultural review")
        flagged_count += 1

    selections_data["flagged_at"] = datetime.now().isoformat(timespec="seconds")
    selections_data["flags_model"] = client.model
    write_json(selections_path, selections_data)

    return {
        "flagged": flagged_count,
        "total_segments": len(segments),
        "skipped": False,
        "reason": None,
        "flags": flags,
    }
