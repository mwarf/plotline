"""
plotline.llm.synthesis - Cross-interview synthesis (LLM Pass 2).

Synthesizes themes across all interviews, identifying shared themes,
complementary perspectives, and best takes.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def synthesize_themes(
    themes_data: list[dict[str, Any]],
    client: Any,
    template_manager: Any,
    interview_count: int,
    brief: dict[str, Any] | None = None,
    console=None,
) -> dict[str, Any]:
    """Synthesize themes across all interviews.

    Args:
        themes_data: List of themes.json content for each interview
        client: LLMClient instance
        template_manager: PromptTemplateManager instance
        interview_count: Number of interviews
        brief: Optional creative brief dict
        console: Optional rich console for output

    Returns:
        Synthesis dict with unified themes and best takes
    """
    from plotline.llm.parsing import parse_llm_json, validate_synthesis_response
    from plotline.llm.templates import format_theme_map_for_prompt

    theme_maps = "\n\n".join(format_theme_map_for_prompt(t) for t in themes_data)

    variables = {
        "THEME_MAP": theme_maps,
        "INTERVIEW_COUNT": interview_count,
    }

    if brief:
        variables["NARRATIVE_BRIEF"] = template_manager.format_brief_for_prompt(brief)

    prompt = template_manager.render("synthesize.txt", variables)

    if console:
        console.print(f"[dim]  Sending synthesis prompt ({len(prompt)} chars)...[/dim]")

    response = client.complete(prompt, max_tokens=4096, temperature=0.7, console=console)

    data = parse_llm_json(response)
    validated = validate_synthesis_response(data)

    return {
        "synthesized_at": datetime.now().isoformat(timespec="seconds"),
        "llm_model": client.model,
        **validated,
    }


def run_synthesis(
    project_path: Path,
    manifest: dict[str, Any],
    client: Any,
    template_manager: Any,
    config: Any,
    force: bool = False,
    console=None,
) -> dict[str, Any]:
    """Run synthesis across all interviews.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        client: LLMClient instance
        template_manager: PromptTemplateManager instance
        config: PlotlineConfig instance
        force: Re-run even if already done
        console: Optional rich console for output

    Returns:
        Dict with synthesis results
    """
    from plotline.project import read_json, write_json

    data_dir = project_path / "data"
    themes_dir = data_dir / "themes"
    synthesis_path = data_dir / "synthesis.json"

    brief = None
    brief_path = project_path / "brief.json"
    if brief_path.exists():
        brief = read_json(brief_path)

    all_have_themes = all(
        interview["stages"].get("themes") for interview in manifest.get("interviews", [])
    )

    if not all_have_themes:
        if console:
            console.print("[yellow]Not all interviews have themes extracted.[/yellow]")
            console.print("[yellow]Run 'plotline themes --all' first.[/yellow]")
        return {"status": "skipped", "reason": "themes_not_complete"}

    if synthesis_path.exists() and not force:
        if console:
            console.print("[dim]Synthesis already exists. Use --force to re-run.[/dim]")
        return {"status": "skipped", "reason": "already_exists"}

    themes_data = []
    for interview in manifest.get("interviews", []):
        themes_path = themes_dir / f"{interview['id']}.json"
        if themes_path.exists():
            themes_data.append(read_json(themes_path))

    if not themes_data:
        return {"status": "failed", "reason": "no_themes_found"}

    if console:
        console.print(f"\n[cyan]Synthesizing themes from {len(themes_data)} interviews...[/cyan]")

    synthesis = synthesize_themes(
        themes_data=themes_data,
        client=client,
        template_manager=template_manager,
        interview_count=len(themes_data),
        brief=brief,
        console=console,
    )

    synthesis["project_name"] = manifest.get("project_name", "unknown")
    write_json(synthesis_path, synthesis)

    if console:
        unified_count = len(synthesis.get("unified_themes", []))
        console.print(f"\n[green]✓[/green] Identified {unified_count} unified themes")
        usage = client.get_token_usage()
        if usage["total_tokens"] > 0:
            console.print(f"[dim]Token usage: {usage['total_tokens']:,} total[/dim]")

    return {
        "status": "success",
        "unified_themes": len(synthesis.get("unified_themes", [])),
        "best_takes": len(synthesis.get("best_takes", [])),
    }
