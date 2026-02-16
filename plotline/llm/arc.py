"""
plotline.llm.arc - Narrative arc construction (LLM Pass 3).

Selects and orders segments into a coherent narrative structure.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def build_narrative_arc(
    synthesis: dict[str, Any],
    all_segments: list[dict[str, Any]],
    client: Any,
    template_manager: Any,
    config: Any,
    brief: dict[str, Any] | None = None,
    console=None,
) -> dict[str, Any]:
    """Build narrative arc from synthesis and segments.

    Args:
        synthesis: synthesis.json content
        all_segments: List of all enriched segments from all interviews
        client: LLMClient instance
        template_manager: PromptTemplateManager instance
        config: PlotlineConfig instance
        brief: Optional creative brief dict
        console: Optional rich console for output

    Returns:
        Arc dict with ordered segments
    """
    from plotline.llm.parsing import parse_llm_json, validate_arc_response
    from plotline.llm.templates import format_synthesis_for_prompt

    segments_by_id = {}
    for seg in all_segments:
        segments_by_id[seg["segment_id"]] = seg

    top_segments = sorted(
        all_segments,
        key=lambda s: s.get("delivery", {}).get("composite_score", 0),
        reverse=True,
    )[:100]

    transcript_str = template_manager.format_transcript_for_prompt(top_segments)

    target_duration = config.target_duration_seconds
    target_minutes = target_duration // 60

    variables = {
        "SYNTHESIS": format_synthesis_for_prompt(synthesis),
        "TRANSCRIPT": transcript_str,
        "TARGET_DURATION": f"{target_minutes} minutes",
        "PROFILE": config.project_profile,
        "INTERVIEW_COUNT": len(set(s.get("interview_id", "") for s in all_segments)),
    }

    if brief:
        variables["NARRATIVE_BRIEF"] = template_manager.format_brief_for_prompt(brief)

    prompt = template_manager.render("arc.txt", variables)

    if console:
        console.print(f"[dim]  Sending arc prompt ({len(prompt)} chars)...[/dim]")

    response = client.complete(prompt, max_tokens=4096, temperature=0.7, console=console)

    data = parse_llm_json(response)
    validated = validate_arc_response(data, target_duration)

    return {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "llm_model": client.model,
        **validated,
    }


def create_selections_from_arc(
    arc: dict[str, Any],
    all_segments: list[dict[str, Any]],
    project_name: str,
) -> dict[str, Any]:
    """Create selections.json from arc data.

    Args:
        arc: arc.json content
        all_segments: List of all enriched segments
        project_name: Project name

    Returns:
        Selections dict ready for export
    """
    segments_by_id = {}
    for seg in all_segments:
        segments_by_id[seg["segment_id"]] = seg

    selections = []
    total_duration = 0

    for arc_item in arc.get("arc", []):
        segment_id = arc_item["segment_id"]
        source_seg = segments_by_id.get(segment_id, {})

        duration = source_seg.get("end", 0) - source_seg.get("start", 0)
        total_duration += duration

        selection = {
            "segment_id": segment_id,
            "interview_id": arc_item.get("interview_id", source_seg.get("interview_id", "")),
            "position": arc_item.get("position", len(selections) + 1),
            "start": source_seg.get("start", 0),
            "end": source_seg.get("end", 0),
            "text": source_seg.get("text", ""),
            "role": arc_item.get("role", ""),
            "themes": arc_item.get("themes", []),
            "composite_score": source_seg.get("delivery", {}).get("composite_score", 0),
            "delivery_label": source_seg.get("delivery", {}).get("delivery_label", ""),
            "editorial_notes": arc_item.get("editorial_notes", ""),
            "pacing": arc_item.get("pacing", ""),
            "brief_message": arc_item.get("brief_message"),
            "status": "pending",
            "flagged": False,
            "flag_reason": None,
            "user_notes": None,
        }
        selections.append(selection)

    return {
        "project_name": project_name,
        "selection_count": len(selections),
        "estimated_duration_seconds": round(total_duration, 1),
        "segments": selections,
    }


def run_arc_construction(
    project_path: Path,
    manifest: dict[str, Any],
    client: Any,
    template_manager: Any,
    config: Any,
    force: bool = False,
    console=None,
) -> dict[str, Any]:
    """Run narrative arc construction.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        client: LLMClient instance
        template_manager: PromptTemplateManager instance
        config: PlotlineConfig instance
        force: Re-run even if already done
        console: Optional rich console for output

    Returns:
        Dict with arc results
    """
    from plotline.project import read_json, write_json

    data_dir = project_path / "data"
    segments_dir = data_dir / "segments"
    synthesis_path = data_dir / "synthesis.json"
    arc_path = data_dir / "arc.json"
    selections_path = data_dir / "selections.json"

    brief = None
    brief_path = project_path / "brief.json"
    if brief_path.exists():
        brief = read_json(brief_path)

    if not synthesis_path.exists():
        if console:
            console.print("[yellow]Synthesis not found. Run 'plotline synthesize' first.[/yellow]")
        return {"status": "failed", "reason": "no_synthesis"}

    if arc_path.exists() and not force:
        if console:
            console.print("[dim]Arc already exists. Use --force to re-run.[/dim]")
        return {"status": "skipped", "reason": "already_exists"}

    all_segments = []
    for interview in manifest.get("interviews", []):
        segments_path = segments_dir / f"{interview['id']}.json"
        if segments_path.exists():
            data = read_json(segments_path)
            all_segments.extend(data.get("segments", []))

    if not all_segments:
        return {"status": "failed", "reason": "no_segments"}

    synthesis = read_json(synthesis_path)

    if console:
        console.print(f"\n[cyan]Building narrative arc from {len(all_segments)} segments...[/cyan]")

    arc = build_narrative_arc(
        synthesis=synthesis,
        all_segments=all_segments,
        client=client,
        template_manager=template_manager,
        config=config,
        brief=brief,
        console=console,
    )

    arc["project_name"] = manifest.get("project_name", "unknown")
    write_json(arc_path, arc)

    selections = create_selections_from_arc(
        arc=arc,
        all_segments=all_segments,
        project_name=manifest.get("project_name", "unknown"),
    )
    write_json(selections_path, selections)

    if console:
        seg_count = len(arc.get("arc", []))
        duration = arc.get("estimated_duration_seconds", 0)
        mins = int(duration // 60)
        secs = int(duration % 60)
        console.print(f"\n[green]✓[/green] Selected {seg_count} segments (~{mins}:{secs:02d})")
        usage = client.get_token_usage()
        if usage["total_tokens"] > 0:
            console.print(f"[dim]Token usage: {usage['total_tokens']:,} total[/dim]")

    return {
        "status": "success",
        "segments_selected": len(arc.get("arc", [])),
        "estimated_duration": arc.get("estimated_duration_seconds", 0),
    }
