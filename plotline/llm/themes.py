"""
plotline.llm.themes - Theme extraction (LLM Pass 1).

Identifies major themes, recurring ideas, and emotional threads
in interview transcripts.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def extract_themes_for_interview(
    segments: dict[str, Any],
    client: Any,
    template_manager: Any,
    profile: str = "documentary",
    brief: dict[str, Any] | None = None,
    language: str | None = None,
    console=None,
) -> dict[str, Any]:
    """Extract themes from a single interview.

    Args:
        segments: Enriched segments dict for the interview
        client: LLMClient instance
        template_manager: PromptTemplateManager instance
        profile: Project profile name
        brief: Optional creative brief dict
        language: ISO 639-1 language code for non-English transcripts
        console: Optional rich console for output

    Returns:
        Themes dict with extracted themes and intersections
    """
    from plotline.llm.parsing import parse_llm_json, validate_themes_response
    from plotline.llm.templates import build_language_instruction

    template_name = "themes_brand.txt" if profile == "brand" and brief else "themes.txt"

    variables = {
        "TRANSCRIPT": template_manager.format_transcript_for_prompt(segments.get("segments", [])),
        "PROFILE": profile,
        "INTERVIEW_ID": segments.get("interview_id", "unknown"),
    }

    lang_instruction = build_language_instruction(language)
    if lang_instruction:
        variables["LANGUAGE_INSTRUCTION"] = lang_instruction

    if brief:
        variables["NARRATIVE_BRIEF"] = template_manager.format_brief_for_prompt(brief)

    prompt = template_manager.render(template_name, variables)

    if console:
        console.print(f"[dim]  Sending prompt ({len(prompt)} chars)...[/dim]")

    response = client.complete(prompt, max_tokens=4096, temperature=0.7, console=console)

    data = parse_llm_json(response)
    validated = validate_themes_response(data, segments.get("interview_id", ""))

    result = {
        "interview_id": segments.get("interview_id", "unknown"),
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "llm_model": client.model,
        **validated,
    }

    if brief:
        result["brief_modified_at"] = brief.get("modified_at")

    return result


def extract_themes_all_interviews(
    project_path: Path,
    manifest: dict[str, Any],
    client: Any,
    template_manager: Any,
    config: Any,
    force: bool = False,
    language: str | None = None,
    console=None,
) -> dict[str, Any]:
    """Extract themes for all interviews in a project.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        client: LLMClient instance
        template_manager: PromptTemplateManager instance
        config: PlotlineConfig instance
        force: Re-extract even if already done
        language: ISO 639-1 language code for non-English transcripts
        console: Optional rich console for output

    Returns:
        Dict with extraction summary
    """
    from rich.table import Table

    from plotline.project import read_json, write_json

    data_dir = project_path / "data"
    segments_dir = data_dir / "segments"
    themes_dir = data_dir / "themes"
    themes_dir.mkdir(parents=True, exist_ok=True)

    brief = None
    brief_path = project_path / "brief.json"
    if brief_path.exists():
        brief = read_json(brief_path)
        brief["modified_at"] = datetime.fromtimestamp(brief_path.stat().st_mtime).isoformat(
            timespec="seconds"
        )

    results = {
        "extracted": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    table = Table(title="Theme Extraction (Pass 1)")
    table.add_column("Interview", style="cyan")
    table.add_column("Themes", style="green")
    table.add_column("Status", style="yellow")

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]

        if not interview["stages"].get("enriched"):
            table.add_row(interview_id, "-", "[dim]Skipped (not enriched)[/dim]")
            results["skipped"] += 1
            continue

        if interview["stages"].get("themes") and not force:
            table.add_row(interview_id, "-", "[dim]Skipped (already extracted)[/dim]")
            results["skipped"] += 1
            continue

        segments_path = segments_dir / f"{interview_id}.json"
        if not segments_path.exists():
            table.add_row(interview_id, "-", "[red]Segments not found[/red]")
            results["failed"] += 1
            results["errors"].append(
                {
                    "interview_id": interview_id,
                    "error": "Segments file not found",
                }
            )
            continue

        try:
            if console:
                console.print(f"\n[cyan]Extracting themes for {interview_id}...[/cyan]")

            segments = read_json(segments_path)

            themes = extract_themes_for_interview(
                segments=segments,
                client=client,
                template_manager=template_manager,
                profile=config.project_profile,
                brief=brief,
                language=language,
                console=console,
            )

            output_path = themes_dir / f"{interview_id}.json"
            write_json(output_path, themes)

            interview["stages"]["themes"] = True

            theme_count = len(themes.get("themes", []))
            table.add_row(
                interview_id,
                str(theme_count),
                "[green]✓ Extracted[/green]",
            )
            results["extracted"] += 1

        except Exception as e:
            table.add_row(interview_id, "-", f"[red]Error: {e}[/red]")
            results["failed"] += 1
            results["errors"].append(
                {
                    "interview_id": interview_id,
                    "error": str(e),
                }
            )

    if console:
        console.print(table)
        usage = client.get_token_usage()
        if usage["total_tokens"] > 0:
            console.print(f"[dim]Token usage: {usage['total_tokens']:,} total[/dim]")

    return results
