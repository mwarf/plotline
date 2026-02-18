"""
plotline.cli - Typer CLI entry point.

Provides all subcommands for the Plotline pipeline.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from plotline import __version__
from plotline.config import create_default_config, write_config
from plotline.project import (
    Project,
    compute_file_hash,
    generate_interview_id,
    probe_video,
)
from plotline.utils import format_duration

app = typer.Typer(
    name="plotline",
    help="AI-assisted documentary editing toolkit.\n\n"
    "Transforms video interviews into DaVinci Resolve timelines through "
    "transcription, delivery analysis, and LLM-powered narrative construction.",
    add_completion=False,
)
console = Console()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
PROFILES_DIR = Path(__file__).parent / "profiles"


def find_project_dir() -> Path | None:
    """Find the project directory by looking for plotline.yaml."""
    current = Path.cwd()
    while current != current.parent:
        if (current / "plotline.yaml").exists():
            return current
        current = current.parent
    return None


def version_callback(value: bool) -> None:
    if value:
        console.print(f"plotline {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Plotline - AI-assisted documentary editing toolkit."""
    pass


# Phase 0: Project Management


@app.command("init")
def init_project(
    name: str = typer.Argument(..., help="Project name"),
    profile: str = typer.Option(
        "documentary",
        "--profile",
        "-p",
        help="Project profile: documentary, brand, or commercial-doc",
    ),
    path: str = typer.Option(".", "--path", "-d", help="Directory to create project in"),
) -> None:
    """Create a new Plotline project.

    Creates a project directory with configuration, prompts, and data structure.
    """
    project_path = Path(path) / name

    if project_path.exists():
        console.print(f"[red]Error: Directory '{project_path}' already exists[/red]")
        raise typer.Exit(1)

    try:
        project = Project(project_path)
        project.create(profile=profile)

        config = create_default_config(name, profile)
        write_config(config, project.config_path)

        if PROMPTS_DIR.exists():
            for prompt_file in PROMPTS_DIR.glob("*.txt"):
                dest = project.prompts_dir / prompt_file.name
                shutil.copy(prompt_file, dest)
            console.print(f"[dim]  Copied prompt templates to {project.prompts_dir}[/dim]")

        console.print(f"[green]✓[/green] Created project '{name}' with profile '{profile}'")
        console.print(f"[dim]  {project_path}[/dim]")
        console.print("\nNext steps:")
        console.print(f"  cd {name}")
        console.print("  plotline add <video_files>")
    except Exception as e:
        console.print(f"[red]Error creating project: {e}[/red]")
        raise typer.Exit(1)


@app.command("add")
def add_videos(
    videos: list[str] = typer.Argument(..., help="Video file(s) to add"),
) -> None:
    """Add video files to the project.

    Probes video metadata (duration, frame rate, codec) and registers in manifest.
    """
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        console.print("[dim]Run 'plotline init' first or cd into a project directory[/dim]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    added_count = 0
    skipped_count = 0

    table = Table(title="Adding Videos")
    table.add_column("File", style="cyan")
    table.add_column("Duration", style="green")
    table.add_column("Status", style="yellow")

    for video_path in videos:
        video_file = Path(video_path).expanduser().resolve()

        if not video_file.exists():
            table.add_row(video_file.name, "-", "[red]Not found[/red]")
            skipped_count += 1
            continue

        existing = next(
            (i for i in manifest["interviews"] if i.get("source_file") == str(video_file)),
            None,
        )
        if existing:
            table.add_row(video_file.name, "-", "[dim]Already added[/dim]")
            skipped_count += 1
            continue

        try:
            console.print(f"[dim]Probing {video_file.name}...[/dim]")
            metadata = probe_video(video_file)
            file_hash = compute_file_hash(video_file)

            interview_id = generate_interview_id(manifest)
            interview_entry = {
                "id": interview_id,
                "source_file": str(video_file),
                "filename": video_file.name,
                "file_hash": file_hash,
                "duration_seconds": metadata["duration_seconds"],
                "frame_rate": metadata["frame_rate"],
                "start_timecode": metadata.get("start_timecode"),
                "resolution": metadata.get("resolution"),
                "codec": metadata.get("codec"),
                "sample_rate": metadata.get("sample_rate"),
                "stages": {
                    "extracted": False,
                    "transcribed": False,
                    "analyzed": False,
                    "enriched": False,
                    "themes": False,
                    "reviewed": False,
                },
            }

            manifest["interviews"].append(interview_entry)
            added_count += 1

            duration_str = format_duration(metadata["duration_seconds"])
            table.add_row(video_file.name, duration_str, "[green]Added[/green]")

        except Exception as e:
            table.add_row(video_file.name, "-", f"[red]Error: {e}[/red]")
            skipped_count += 1

    console.print(table)
    project.save_manifest(manifest)

    console.print(f"\n[green]✓[/green] Added {added_count} video(s), skipped {skipped_count}")
    if added_count > 0:
        console.print("\nNext step: [cyan]plotline extract[/cyan]")


# Phase 1: Audio Extraction


@app.command("extract")
def extract_audio_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Re-extract already processed files"),
) -> None:
    """Extract audio from video files."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.validation import (
        check_audio_track,
        check_disk_space,
        validate_interview_duration,
    )

    project = Project(project_dir)
    manifest = project.load_manifest()

    if not manifest.get("interviews"):
        console.print("[yellow]No interviews found. Run 'plotline add' first.[/yellow]")
        raise typer.Exit(0)

    total_size_mb = sum(i.get("duration_seconds", 0) for i in manifest["interviews"]) * 0.15
    disk = check_disk_space(project_dir, int(total_size_mb) + 100)
    if not disk["sufficient"]:
        console.print(
            f"[red]Error: Insufficient disk space. "
            f"Need ~{int(total_size_mb) + 100}MB, have {disk['available_mb']}MB[/red]"
        )
        raise typer.Exit(1)

    for interview in manifest["interviews"]:
        video_path = Path(interview.get("source_file", ""))
        if video_path.exists():
            audio = check_audio_track(video_path)
            if not audio.get("has_audio"):
                console.print(f"[red]Error: {interview['filename']} has no audio track[/red]")
                raise typer.Exit(1)

        duration = validate_interview_duration(interview.get("duration_seconds", 0))
        for warning in duration.get("warnings", []):
            console.print(f"[yellow]Warning: {interview['filename']}: {warning}[/yellow]")

    from plotline.extract.audio import extract_all_interviews

    console.print("[cyan]Extracting audio from video files...[/cyan]\n")

    results = extract_all_interviews(
        project_path=project_dir,
        manifest=manifest,
        force=force,
        console=console,
    )

    project.save_manifest(manifest)

    console.print(
        f"\n[green]✓[/green] Extracted {results['extracted']}, "
        f"skipped {results['skipped']}, failed {results['failed']}"
    )

    if results["extracted"] > 0:
        console.print("\nNext step: [cyan]plotline transcribe[/cyan]")

    if results["failed"] > 0:
        raise typer.Exit(1)


# Phase 2: Transcription


@app.command("transcribe")
def transcribe(
    model: str = typer.Option("medium", "--model", "-m", help="Whisper model size"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language code (auto-detect if not set)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Re-transcribe already processed files"
    ),
    backend: str = typer.Option(
        "mlx", "--backend", "-b", help="Whisper backend (mlx, faster, cpp)"
    ),
) -> None:
    """Transcribe audio using Whisper."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    if not manifest.get("interviews"):
        console.print("[yellow]No interviews found. Run 'plotline add' first.[/yellow]")
        raise typer.Exit(0)

    from plotline.transcribe.engine import transcribe_all_interviews

    console.print(f"[cyan]Transcribing with {backend} ({model} model)...[/cyan]\n")

    results = transcribe_all_interviews(
        project_path=project_dir,
        manifest=manifest,
        model=model,
        language=language,
        backend=backend,
        force=force,
        console=console,
    )

    project.save_manifest(manifest)

    console.print(
        f"\n[green]✓[/green] Transcribed {results['transcribed']}, "
        f"skipped {results['skipped']}, failed {results['failed']}"
    )

    if results["transcribed"] > 0:
        console.print("\nNext step: [cyan]plotline analyze[/cyan] (delivery analysis)")

    if results["failed"] > 0:
        raise typer.Exit(1)


# Phase 3: Delivery Analysis


@app.command("analyze")
def analyze_delivery(
    force: bool = typer.Option(False, "--force", "-f", help="Re-analyze already processed files"),
) -> None:
    """Analyze emotional delivery metrics for transcripts."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    if not manifest.get("interviews"):
        console.print("[yellow]No interviews found. Run 'plotline add' first.[/yellow]")
        raise typer.Exit(0)

    from plotline.analyze.delivery import analyze_all_interviews
    from plotline.analyze.scoring import score_all_interviews
    from plotline.config import load_config

    config = load_config(project_dir)
    weights = {
        "energy": config.delivery_weights.energy,
        "pitch_variation": config.delivery_weights.pitch_variation,
        "speech_rate": config.delivery_weights.speech_rate,
        "pause_weight": config.delivery_weights.pause_weight,
        "spectral_brightness": config.delivery_weights.spectral_brightness,
        "voice_texture": config.delivery_weights.voice_texture,
    }

    console.print(
        "[cyan]Analyzing delivery metrics (energy, pitch, speech rate, pauses)...[/cyan]\n"
    )

    results = analyze_all_interviews(
        project_path=project_dir,
        manifest=manifest,
        force=force,
        console=console,
    )

    console.print("\n[cyan]Computing composite delivery scores...[/cyan]\n")

    score_results = score_all_interviews(
        project_path=project_dir,
        manifest=manifest,
        weights=weights,
        force=force,
        console=console,
    )

    project.save_manifest(manifest)

    total_analyzed = results["analyzed"]
    total_failed = results["failed"] + score_results["failed"]

    console.print(
        f"\n[green]✓[/green] Analyzed {total_analyzed} interview(s), failed {total_failed}"
    )

    if total_analyzed > 0:
        console.print("\nNext step: [cyan]plotline enrich[/cyan] (merge transcript + delivery)")

    if total_failed > 0:
        raise typer.Exit(1)


# Phase 4: Enrichment


@app.command("enrich")
def enrich(
    force: bool = typer.Option(False, "--force", "-f", help="Re-enrich already processed data"),
) -> None:
    """Merge transcript and delivery data into enriched segments."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    if not manifest.get("interviews"):
        console.print("[yellow]No interviews found. Run 'plotline add' first.[/yellow]")
        raise typer.Exit(0)

    from plotline.enrich.merge import enrich_all_interviews

    console.print("[cyan]Merging transcript and delivery data...[/cyan]\n")

    results = enrich_all_interviews(
        project_path=project_dir,
        manifest=manifest,
        force=force,
        console=console,
    )

    project.save_manifest(manifest)

    console.print(
        f"\n[green]✓[/green] Enriched {results['enriched']}, "
        f"skipped {results['skipped']}, failed {results['failed']}"
    )

    if results["enriched"] > 0:
        console.print("\nNext step: [cyan]plotline themes[/cyan] (LLM theme extraction)")

    if results["failed"] > 0:
        raise typer.Exit(1)


# Phase 5: LLM Analysis


@app.command("themes")
def extract_themes(
    interview: str | None = typer.Option(None, "--interview", "-i", help="Specific interview ID"),
    all_interviews: bool = typer.Option(False, "--all", "-a", help="Process all interviews"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-extract even if already done"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show prompt without sending to LLM"),
) -> None:
    """Run theme extraction (LLM Pass 1)."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    if not manifest.get("interviews"):
        console.print("[yellow]No interviews found. Run 'plotline add' first.[/yellow]")
        raise typer.Exit(0)

    from plotline.config import load_config
    from plotline.llm.client import create_client_from_config
    from plotline.llm.templates import PromptTemplateManager
    from plotline.llm.themes import extract_themes_all_interviews

    config = load_config(project_dir)
    client = create_client_from_config(config)
    template_manager = PromptTemplateManager(project_dir / "prompts")

    if dry_run:
        console.print("[yellow]Dry run mode - not sending to LLM[/yellow]")
        return

    console.print("[cyan]Extracting themes from interviews...[/cyan]\n")

    results = extract_themes_all_interviews(
        project_path=project_dir,
        manifest=manifest,
        client=client,
        template_manager=template_manager,
        config=config,
        force=force,
        console=console,
    )

    project.save_manifest(manifest)

    console.print(
        f"\n[green]✓[/green] Extracted themes from {results['extracted']}, "
        f"skipped {results['skipped']}, failed {results['failed']}"
    )

    if results["extracted"] > 0:
        console.print("\nNext step: [cyan]plotline synthesize[/cyan]")

    if results["failed"] > 0:
        raise typer.Exit(1)


@app.command("synthesize")
def synthesize_themes_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Re-run even if already done"),
) -> None:
    """Synthesize themes across interviews (LLM Pass 2)."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    from plotline.config import load_config
    from plotline.llm.client import create_client_from_config
    from plotline.llm.synthesis import run_synthesis
    from plotline.llm.templates import PromptTemplateManager

    config = load_config(project_dir)
    client = create_client_from_config(config)
    template_manager = PromptTemplateManager(project_dir / "prompts")

    console.print("[cyan]Synthesizing themes across interviews...[/cyan]")

    results = run_synthesis(
        project_path=project_dir,
        manifest=manifest,
        client=client,
        template_manager=template_manager,
        config=config,
        force=force,
        console=console,
    )

    if results.get("status") == "success":
        console.print("\nNext step: [cyan]plotline arc[/cyan]")
    elif results.get("reason") == "themes_not_complete":
        raise typer.Exit(1)


@app.command("arc")
def build_arc_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Re-build even if already done"),
) -> None:
    """Build narrative arc (LLM Pass 3)."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    from plotline.config import load_config
    from plotline.llm.arc import run_arc_construction
    from plotline.llm.client import create_client_from_config
    from plotline.llm.templates import PromptTemplateManager

    config = load_config(project_dir)
    client = create_client_from_config(config)
    template_manager = PromptTemplateManager(project_dir / "prompts")

    console.print("[cyan]Building narrative arc...[/cyan]")

    results = run_arc_construction(
        project_path=project_dir,
        manifest=manifest,
        client=client,
        template_manager=template_manager,
        config=config,
        force=force,
        console=console,
    )

    if results.get("status") == "success":
        console.print(
            "\nNext step: [cyan]plotline export[/cyan] or review with [cyan]plotline review[/cyan]"
        )
    elif results.get("reason") in ("no_synthesis", "no_segments"):
        raise typer.Exit(1)


# Phase 6: Export


@app.command("export")
def export_timeline(
    format: str = typer.Option(
        "edl",
        "--format",
        "-f",
        help="Export format: edl (CMX 3600 for DaVinci/Premiere), fcpxml (Final Cut Pro XML)",
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    handle: int = typer.Option(
        12, "--handle", "-H", help="Handle frames padding (default 12 = 0.5s at 24fps)"
    ),
    all_segments: bool = typer.Option(
        False, "--all", "-a", help="Export all segments, ignore approval status"
    ),
) -> None:
    """Export timeline to EDL or FCPXML for DaVinci Resolve/Premiere Pro.

    Generates frame-accurate timeline with handle padding. By default exports
    only approved segments from the review report.
    """
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    format = format.lower()
    if format not in ("edl", "fcpxml"):
        console.print(f"[red]Error: Unknown format '{format}'. Use 'edl' or 'fcpxml'.[/red]")
        raise typer.Exit(1)

    try:
        if format == "edl":
            from plotline.export.edl import generate_edl_from_project

            content = generate_edl_from_project(
                project_path=project_dir,
                manifest=manifest,
                handle_frames=handle,
                use_approvals=not all_segments,
            )
            ext = ".edl"
        else:
            from plotline.export.fcpxml import generate_fcpxml_from_project

            content = generate_fcpxml_from_project(
                project_path=project_dir,
                manifest=manifest,
                handle_frames=handle,
                use_approvals=not all_segments,
            )
            ext = ".fcpxml"
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[dim]Run 'plotline arc' first to generate selections.[/dim]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[dim]Approve segments with 'plotline review' or use --all.[/dim]")
        raise typer.Exit(1)

    if output:
        output_path = Path(output)
    else:
        project_name = manifest.get("project_name", "plotline")
        output_path = project_dir / "exports" / f"{project_name}{ext}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    console.print(f"[green]✓[/green] Exported to {output_path}")
    console.print(f"[dim]  Format: {format.upper()}, Handle: {handle} frames[/dim]")


# Phase 7: Reports


@app.command("status")
def show_status(
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open in browser"),
) -> None:
    """Show project status and pipeline progress."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.reports.dashboard import generate_dashboard

    project = Project(project_dir)
    manifest = project.load_manifest()

    output_path = project_dir / "reports" / "dashboard.html"

    try:
        generate_dashboard(
            project_path=project_dir,
            manifest=manifest,
            output_path=output_path,
            open_browser=open_browser,
        )
        console.print(f"[green]✓[/green] Dashboard generated: {output_path}")
        if open_browser:
            console.print("[dim]Opening in browser...[/dim]")
        else:
            console.print("[dim]Run with --open to view in browser[/dim]")
    except Exception as e:
        console.print(f"[red]Error generating dashboard: {e}[/red]")
        raise typer.Exit(1)


@app.command("report")
def generate_report(
    report_type: str = typer.Argument(
        "dashboard",
        help="Report type (dashboard, transcript, review, summary, coverage)",
    ),
    interview: str | None = typer.Option(
        None, "--interview", "-i", help="Interview ID for transcript report"
    ),
    open_browser: bool = typer.Option(True, "--open", "-o", help="Open in browser"),
) -> None:
    """Generate HTML report."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    try:
        if report_type == "dashboard" or report_type == "status":
            from plotline.reports.dashboard import generate_dashboard

            output_path = generate_dashboard(
                project_path=project_dir,
                manifest=manifest,
                open_browser=open_browser,
            )
        elif report_type == "review":
            from plotline.reports.review import generate_review

            output_path = generate_review(
                project_path=project_dir,
                manifest=manifest,
                open_browser=open_browser,
            )
        elif report_type == "summary":
            from plotline.reports.summary import generate_summary

            output_path = generate_summary(
                project_path=project_dir,
                manifest=manifest,
                open_browser=open_browser,
            )
        elif report_type == "transcript":
            if not interview:
                console.print("[red]Error: --interview/-i required for transcript report[/red]")
                console.print("[dim]Usage: plotline report transcript -i interview_001[/dim]")
                raise typer.Exit(1)
            from plotline.reports.transcript import generate_transcript

            output_path = generate_transcript(
                project_path=project_dir,
                manifest=manifest,
                interview_id=interview,
                open_browser=open_browser,
            )
        elif report_type == "coverage":
            from plotline.reports.coverage import generate_coverage

            output_path = generate_coverage(
                project_path=project_dir,
                manifest=manifest,
                open_browser=open_browser,
            )
        else:
            console.print(f"[red]Unknown report type: {report_type}[/red]")
            console.print(
                "[dim]Valid types: dashboard, review, summary, transcript, coverage[/dim]"
            )
            raise typer.Exit(1)

        console.print(f"[green]✓[/green] {report_type.title()} report: {output_path}")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/red]")
        raise typer.Exit(1)


@app.command("review")
def open_review(
    open_browser: bool = typer.Option(True, "--open", "-o", help="Open in browser"),
) -> None:
    """Open the selection review report."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.reports.review import generate_review

    project = Project(project_dir)
    manifest = project.load_manifest()

    try:
        output_path = generate_review(
            project_path=project_dir,
            manifest=manifest,
            open_browser=open_browser,
        )
        console.print(f"[green]✓[/green] Review report: {output_path}")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[dim]Run 'plotline arc' first to generate selections.[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error generating review: {e}[/red]")
        raise typer.Exit(1)


# Phase 8: Brief Integration


@app.command("brief")
def attach_brief(
    brief_file: str = typer.Argument(..., help="Path to brief file (Markdown or YAML)"),
    show: bool = typer.Option(False, "--show", help="Display parsed brief"),
) -> None:
    """Attach and parse a creative brief."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.brief import parse_brief, save_brief

    brief_path = Path(brief_file).expanduser().resolve()

    try:
        brief = parse_brief(brief_path)
        output_path = project_dir / "brief.json"
        save_brief(brief, output_path)

        console.print(f"[green]✓[/green] Brief parsed and saved to {output_path}")
        console.print(f"[dim]  Source: {brief_path}[/dim]")
        console.print(f"[dim]  Key messages: {len(brief.get('key_messages', []))}[/dim]")

        if show:
            import json

            console.print("\n[cyan]Parsed brief:[/cyan]")
            console.print(json.dumps(brief, indent=2, ensure_ascii=False))

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error parsing brief: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Phase 9: Integration


@app.command("run")
def run_pipeline(
    from_stage: str | None = typer.Option(
        None,
        "--from",
        help="Start from stage: extract, transcribe, analyze, enrich, themes, synthesize, arc",
    ),
) -> None:
    """Run the full pipeline from extract to arc.

    Executes all stages sequentially, skipping already-completed stages.
    Use --from to resume from a specific stage.
    """
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    stages = ["extract", "transcribe", "analyze", "enrich", "themes", "synthesize", "arc"]
    stage_map = {s: i for i, s in enumerate(stages)}

    if from_stage and from_stage not in stage_map:
        console.print(f"[red]Unknown stage: {from_stage}[/red]")
        console.print(f"[dim]Valid stages: {', '.join(stages)}[/dim]")
        raise typer.Exit(1)

    start_idx = stage_map.get(from_stage, 0) if from_stage else 0

    console.print("[cyan]Running full pipeline...[/cyan]\n")

    for stage in stages[start_idx:]:
        console.print(f"[dim]Stage: {stage}[/dim]")
        if stage == "extract":
            extract_audio_cmd(force=False)
        elif stage == "transcribe":
            transcribe(force=False)
        elif stage == "analyze":
            analyze_delivery(force=False)
        elif stage == "enrich":
            enrich(force=False)
        elif stage == "themes":
            extract_themes(force=False)
        elif stage == "synthesize":
            synthesize_themes_cmd(force=False)
        elif stage == "arc":
            build_arc_cmd(force=False)
        console.print()

    # Post-pipeline: cultural sensitivity flagging (if enabled)
    from plotline.config import load_config

    config = load_config(project_dir)
    if config.cultural_flags:
        console.print("[dim]Stage: cultural flags[/dim]")
        cultural_flags_cmd(force=False)
        console.print()

    console.print("[green]✓[/green] Pipeline complete!")
    console.print("\nNext steps:")
    console.print("  [cyan]plotline review[/cyan] - Review and approve selections")
    console.print("  [cyan]plotline export[/cyan] - Export timeline to EDL/FCPXML")


@app.command("flags")
def cultural_flags_cmd(
    force: bool = typer.Option(
        False, "--force", "-f", help="Run even if cultural_flags is disabled in config"
    ),
) -> None:
    """Run cultural sensitivity flagging on selected segments (LLM Pass 4).

    Sends selected segments through an LLM prompt to flag content that may
    require community review before publication.  Updates selections.json
    in-place with flagged/flag_reason fields.
    """
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    from plotline.config import load_config
    from plotline.llm.client import create_client_from_config
    from plotline.llm.flags import run_flags
    from plotline.llm.templates import PromptTemplateManager

    config = load_config(project_dir)
    client = create_client_from_config(config)
    template_manager = PromptTemplateManager(project_dir / "prompts")

    results = run_flags(
        project_path=project_dir,
        manifest=manifest,
        client=client,
        template_manager=template_manager,
        config=config,
        force=force,
        console=console,
    )

    if results.get("skipped"):
        console.print(f"[yellow]Skipped:[/yellow] {results['reason']}")
        console.print("[dim]Use --force to run anyway.[/dim]")
        return

    flagged = results["flagged"]
    total = results["total_segments"]
    console.print(f"\n[green]✓[/green] Flagging complete: {flagged}/{total} segments flagged")

    if flagged > 0:
        console.print(
            "[dim]Review flagged segments in selections.json or via plotline review[/dim]"
        )


@app.command("compare")
def compare_takes(
    message: str | None = typer.Option(
        None, "--message", "-m", help="Filter to a specific key message"
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open report in browser"),
) -> None:
    """Compare best takes across interviews for the same theme."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.config import load_config
    from plotline.reports.compare import generate_compare_report

    project = Project(project_dir)
    manifest = project.load_manifest()
    config = load_config(project_dir)

    synthesis_path = project_dir / "data" / "synthesis.json"
    if not synthesis_path.exists():
        console.print("[red]Error: No synthesis found[/red]")
        console.print(
            "[dim]Run 'plotline synthesize' first to generate best-take comparisons.[/dim]"
        )
        raise typer.Exit(1)

    console.print("[cyan]Generating best-take comparison report...[/cyan]")

    try:
        output_path = generate_compare_report(
            project_path=project_dir,
            manifest=manifest,
            config=config,
            message_filter=message,
            open_browser=open_browser,
        )
        console.print(f"[green]✓[/green] Comparison report: {output_path}")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error generating comparison: {e}[/red]")
        raise typer.Exit(1)


@app.command("doctor")
def run_doctor() -> None:
    """Check dependencies and environment setup."""
    console.print("[cyan]Running preflight checks...[/cyan]\n")

    from plotline.exceptions import DependencyError
    from plotline.validation import (
        check_ffmpeg,
        check_ollama_running,
    )

    table = Table(title="Dependency Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Version/Details")

    all_passed = True

    try:
        versions = check_ffmpeg()
        table.add_row("FFmpeg", "✓ Installed", versions.get("ffmpeg_version", "unknown"))
        table.add_row("FFprobe", "✓ Installed", versions.get("ffprobe_version", "unknown"))
    except DependencyError as e:
        table.add_row("FFmpeg", "✗ Missing", e.install_hint or "")
        all_passed = False

    try:
        from plotline.config import load_config

        project_dir = find_project_dir()
        if project_dir:
            config = load_config(project_dir)
            if config.llm_backend == "ollama":
                ollama = check_ollama_running(config.llm_model)
                if ollama["running"]:
                    model_status = "✓ Running"
                    if ollama.get("model_available"):
                        model_status += f" ({config.llm_model})"
                    else:
                        model_status += f" (model '{config.llm_model}' not pulled)"
                        all_passed = False
                    table.add_row("Ollama", model_status, ", ".join(ollama.get("models", [])))
                else:
                    table.add_row("Ollama", "✗ Not running", ollama.get("error", ""))
                    all_passed = False
            else:
                table.add_row("LLM Backend", config.llm_backend, config.llm_model)
        else:
            table.add_row("LLM", "—", "Not in a project directory")
    except Exception as e:
        table.add_row("LLM", "?", str(e))

    console.print(table)

    if all_passed:
        console.print("\n[green]✓ All checks passed[/green]")
    else:
        console.print("\n[yellow]⚠ Some checks failed[/yellow]")
        console.print("[dim]Fix the issues above before running the pipeline[/dim]")
        raise typer.Exit(1)


@app.command("validate")
def validate_data(
    data_type: str = typer.Argument(
        "all", help="Data type to validate (all, config, transcript, segments)"
    ),
) -> None:
    """Validate data integrity."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.config import load_config
    from plotline.validation import run_preflight_checks

    config = load_config(project_dir)

    console.print(f"[cyan]Validating {data_type}...[/cyan]\n")

    if data_type in ("all", "config"):
        try:
            _ = load_config(project_dir)
            console.print("[green]✓[/green] config: Valid")
        except Exception as e:
            console.print(f"[red]✗[/red] config: {e}")

    if data_type in ("all", "transcript"):
        data_dir = project_dir / "data"
        transcripts_dir = data_dir / "transcripts"
        if transcripts_dir.exists():
            for tf in transcripts_dir.glob("*.json"):
                try:
                    import json

                    with open(tf) as f:
                        data = json.load(f)
                    seg_count = len(data.get("segments", []))
                    console.print(f"[green]✓[/green] transcript {tf.name}: {seg_count} segments")
                except Exception as e:
                    console.print(f"[red]✗[/red] transcript {tf.name}: {e}")
        else:
            console.print("[dim]— No transcripts found[/dim]")

    if data_type in ("all", "segments"):
        segments_dir = project_dir / "data" / "segments"
        if segments_dir.exists():
            for sf in segments_dir.glob("*.json"):
                try:
                    import json

                    with open(sf) as f:
                        data = json.load(f)
                    seg_count = len(data.get("segments", []))
                    console.print(f"[green]✓[/green] segments {sf.name}: {seg_count} segments")
                except Exception as e:
                    console.print(f"[red]✗[/red] segments {sf.name}: {e}")

    if data_type == "all":
        results = run_preflight_checks(project_dir, config)
        if results["passed"]:
            console.print("\n[green]✓ All validations passed[/green]")
        else:
            console.print("\n[yellow]⚠ Some validations failed[/yellow]")


if __name__ == "__main__":
    app()
