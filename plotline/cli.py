"""
plotline.cli - Typer CLI entry point.

Provides all subcommands for the Plotline pipeline.
"""

from __future__ import annotations

import os
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
        "-V",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable debug logging",
    ),
) -> None:
    """Plotline - AI-assisted documentary editing toolkit."""
    from plotline.logging import configure_logging

    configure_logging(verbose)


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
                    "diarized": False,
                    "analyzed": False,
                    "enriched": False,
                    "themes": False,
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

    from plotline.config import load_config

    config = load_config(project_dir)

    # Fall back to config values when CLI flags use defaults
    if language is None:
        language = config.whisper_language
    if model == "medium":
        model = config.whisper_model
    if backend == "mlx":
        backend = config.whisper_backend

    project = Project(project_dir)
    manifest = project.load_manifest()

    if not manifest.get("interviews"):
        console.print("[yellow]No interviews found. Run 'plotline add' first.[/yellow]")
        raise typer.Exit(0)

    from plotline.transcribe.engine import transcribe_all_interviews

    lang_display = language or "auto-detect"
    console.print(
        f"[cyan]Transcribing with {backend} ({model} model, language: {lang_display})...[/cyan]\n"
    )

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


# Phase 2.5: Speaker Diarization


@app.command("diarize")
def diarize_speakers(
    num_speakers: int | None = typer.Option(
        None, "--num-speakers", "-n", help="Exact number of speakers (if known)"
    ),
    min_speakers: int = typer.Option(2, "--min-speakers", help="Minimum speakers to detect"),
    max_speakers: int = typer.Option(5, "--max-speakers", help="Maximum speakers to detect"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-diarize already processed files"),
) -> None:
    """Identify speakers in audio using pyannote.audio (optional stage).

    Requires pyannote.audio to be installed: pip install plotline[diarization]
    Requires a HuggingFace token with accepted model terms.
    """
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    if not manifest.get("interviews"):
        console.print("[yellow]No interviews found. Run 'plotline add' first.[/yellow]")
        raise typer.Exit(0)

    try:
        from plotline.diarize.engine import diarize_all_interviews
    except ImportError:
        console.print("[red]Error: diarization dependencies not installed[/red]")
        console.print("[dim]Install with: pip install plotline[diarization][/dim]")
        raise typer.Exit(1)

    from plotline.config import load_config

    config = load_config(project_dir)

    model = config.diarization_model
    if num_speakers is None:
        num_speakers = config.diarization_num_speakers
    if min_speakers == 2:
        min_speakers = config.diarization_min_speakers
    if max_speakers == 5:
        max_speakers = config.diarization_max_speakers

    console.print(f"[cyan]Running speaker diarization with {model}...[/cyan]\n")

    results = diarize_all_interviews(
        project_path=project_dir,
        manifest=manifest,
        model=model,
        num_speakers=num_speakers,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        force=force,
        console=console,
    )

    project.save_manifest(manifest)

    console.print(
        f"\n[green]✓[/green] Diarized {results['diarized']}, "
        f"skipped {results['skipped']}, failed {results['failed']}"
    )

    if results["diarized"] > 0:
        console.print("\nSpeaker names can be customized in [cyan]speakers.yaml[/cyan]")
        console.print("Next step: [cyan]plotline analyze[/cyan] (delivery analysis)")

    if results["failed"] > 0:
        raise typer.Exit(1)


@app.command("speakers")
def manage_speakers(
    list_speakers: bool = typer.Option(False, "--list", "-l", help="List detected speakers"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Open speakers.yaml in editor"),
    preview: bool = typer.Option(
        False, "--preview", "-p", help="Preview speakers with role heuristics"
    ),
    speaker_id: str | None = typer.Argument(None, help="Speaker ID to modify"),
    set_name: str | None = typer.Option(None, "--name", "-n", help="Set speaker display name"),
    set_role: str | None = typer.Option(
        None, "--role", "-r", help="Set role (interviewer/subject/unknown)"
    ),
    exclude: bool = typer.Option(False, "--exclude", help="Exclude speaker from EDL/pipeline"),
    include: bool = typer.Option(False, "--include", help="Include speaker in EDL/pipeline"),
) -> None:
    """Manage speaker names, roles, and filtering.

    Examples:
        plotline speakers --list
        plotline speakers --preview
        plotline speakers --edit
        plotline speakers SPEAKER_00 --name "Host" --role interviewer --exclude
        plotline speakers SPEAKER_01 --name "Jane Doe" --role subject --include
    """
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.diarize.speakers import (
        DEFAULT_COLORS,
        format_duration as format_speaker_duration,
        get_all_speakers_from_project,
        get_speaker_statistics,
        identify_speaker_role,
        load_speaker_config,
        save_speaker_config,
    )

    speakers_file = project_dir / "speakers.yaml"

    if edit:
        import subprocess

        if not speakers_file.exists():
            console.print("[yellow]No speakers.yaml found. Run 'plotline diarize' first.[/yellow]")
            raise typer.Exit(1)

        import sys

        if sys.platform == "win32":
            default_editor = "notepad"
        else:
            default_editor = "nano"
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", default_editor))
        subprocess.run([editor, str(speakers_file)])
        console.print(f"[green]✓[/green] Edited {speakers_file}")
        return

    if preview:
        speakers = get_all_speakers_from_project(project_dir)
        if not speakers:
            console.print("[yellow]No speakers detected yet.[/yellow]")
            console.print("[dim]Run 'plotline diarize' to detect speakers.[/dim]")
            return

        table = Table(title="Speaker Preview (with heuristics)")
        table.add_column("ID", style="cyan")
        table.add_column("Segments", style="dim")
        table.add_column("Duration", style="dim")
        table.add_column("Heuristic", style="yellow")
        table.add_column("Suggested", style="green")

        for spk_id in sorted(speakers.keys()):
            stats = get_speaker_statistics(project_dir, spk_id)
            heuristic = identify_speaker_role(stats)

            table.add_row(
                spk_id,
                str(stats["segment_count"]),
                format_speaker_duration(stats["total_duration"]),
                heuristic["reason"],
                f"Exclude? {'Y' if heuristic['suggest_exclude'] else 'N'}",
            )

        console.print(table)
        console.print(
            "\n[dim]To exclude interviewer: plotline speakers <ID> --role interviewer --exclude[/dim]"
        )
        return

    if speaker_id:
        config = load_speaker_config(project_dir)

        if set_name or set_role or exclude or include:
            if set_role and set_role not in ("interviewer", "subject", "unknown"):
                console.print(
                    "[red]Error: Role must be 'interviewer', 'subject', or 'unknown'[/red]"
                )
                raise typer.Exit(1)

            existing = config.speakers.get(speaker_id, {})
            if not existing:
                idx = 0
                if speaker_id.startswith("SPEAKER_"):
                    try:
                        idx = int(speaker_id.split("_")[1])
                    except (IndexError, ValueError):
                        pass
                existing = {
                    "name": f"Speaker {idx + 1}",
                    "color": DEFAULT_COLORS[idx % len(DEFAULT_COLORS)],
                    "role": "unknown",
                    "include_in_edl": True,
                }

            if set_name:
                existing["name"] = set_name
            if set_role:
                existing["role"] = set_role
            if exclude:
                existing["include_in_edl"] = False
            if include:
                existing["include_in_edl"] = True

            config.speakers[speaker_id] = existing
            save_speaker_config(config, speakers_file)

            role = existing.get("role", "unknown")
            in_edl = existing.get("include_in_edl", True)
            console.print(
                f"[green]✓[/green] Updated {speaker_id}: name={existing.get('name')}, role={role}, include_in_edl={in_edl}"
            )
        else:
            info = config.get_speaker_info(speaker_id)
            if info:
                console.print(f"\n[bold]{speaker_id}[/bold]")
                console.print(f"  Name: {info.name}")
                console.print(f"  Role: {info.role}")
                console.print(f"  Include in EDL: {info.include_in_edl}")
                console.print(f"  Color: {info.color}")
            else:
                console.print(f"[yellow]Speaker {speaker_id} not found in configuration[/yellow]")
                console.print("[dim]Run 'plotline speakers --list' to see available speakers[/dim]")
        return

    speakers = get_all_speakers_from_project(project_dir)
    if not speakers:
        console.print("[yellow]No speakers detected yet.[/yellow]")
        console.print("[dim]Run 'plotline diarize' to detect speakers in your interviews.[/dim]")
        return

    config = load_speaker_config(project_dir)

    table = Table(title="Speakers")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Role", style="yellow")
    table.add_column("In EDL", style="dim")
    table.add_column("Color", style="dim")

    for spk_id in sorted(speakers.keys()):
        info = config.get_speaker_info(spk_id)
        if info:
            table.add_row(
                spk_id,
                info.name,
                info.role,
                "✓" if info.include_in_edl else "✗",
                info.color,
            )
        else:
            table.add_row(
                spk_id,
                speakers[spk_id].get("name", spk_id),
                "unknown",
                "✓",
                speakers[spk_id].get("color", "#808080"),
            )

    console.print(table)

    excluded = config.get_excluded_speakers()
    if excluded:
        console.print(f"\n[yellow]Excluded from EDL: {', '.join(excluded)}[/yellow]")

    if speakers_file.exists():
        console.print(f"\n[dim]Edit: {speakers_file}[/dim]")
        console.print("[dim]Preview: plotline speakers --preview[/dim]")
    else:
        console.print("\n[dim]Run 'plotline diarize' to create speakers.yaml[/dim]")


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

    brief_path = project_dir / "brief.json"
    if not brief_path.exists():
        console.print("[yellow]Warning: No brief attached. Using generic prompts.[/yellow]")
        console.print("[dim]Attach a brief with: plotline brief <file>[/dim]\n")

    staleness_warnings = _check_brief_staleness(project_dir)
    for warning in staleness_warnings:
        console.print(f"[yellow]Warning: {warning}[/yellow]")

    from plotline.config import load_config
    from plotline.llm.client import create_client_from_config
    from plotline.llm.templates import PromptTemplateManager, detect_project_language
    from plotline.llm.themes import extract_themes_all_interviews

    config = load_config(project_dir)
    client = create_client_from_config(config)
    template_manager = PromptTemplateManager(project_dir / "prompts")
    language = detect_project_language(manifest)

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
        language=language,
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

    brief_path = project_dir / "brief.json"
    if not brief_path.exists():
        console.print("[yellow]Warning: No brief attached. Using generic prompts.[/yellow]")
        console.print("[dim]Attach a brief with: plotline brief <file>[/dim]\n")

    staleness_warnings = _check_brief_staleness(project_dir)
    for warning in staleness_warnings:
        console.print(f"[yellow]Warning: {warning}[/yellow]")

    from plotline.config import load_config
    from plotline.llm.client import create_client_from_config
    from plotline.llm.synthesis import run_synthesis
    from plotline.llm.templates import PromptTemplateManager, detect_project_language

    config = load_config(project_dir)
    client = create_client_from_config(config)
    template_manager = PromptTemplateManager(project_dir / "prompts")
    language = detect_project_language(manifest)

    console.print("[cyan]Synthesizing themes across interviews...[/cyan]")

    results = run_synthesis(
        project_path=project_dir,
        manifest=manifest,
        client=client,
        template_manager=template_manager,
        config=config,
        force=force,
        language=language,
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

    brief_path = project_dir / "brief.json"
    if not brief_path.exists():
        console.print("[yellow]Warning: No brief attached. Using generic prompts.[/yellow]")
        console.print("[dim]Attach a brief with: plotline brief <file>[/dim]\n")

    staleness_warnings = _check_brief_staleness(project_dir)
    for warning in staleness_warnings:
        console.print(f"[yellow]Warning: {warning}[/yellow]")

    from plotline.config import load_config
    from plotline.llm.arc import run_arc_construction
    from plotline.llm.client import create_client_from_config
    from plotline.llm.templates import PromptTemplateManager, detect_project_language

    config = load_config(project_dir)
    client = create_client_from_config(config)
    template_manager = PromptTemplateManager(project_dir / "prompts")
    language = detect_project_language(manifest)

    console.print("[cyan]Building narrative arc...[/cyan]")

    results = run_arc_construction(
        project_path=project_dir,
        manifest=manifest,
        client=client,
        template_manager=template_manager,
        config=config,
        force=force,
        language=language,
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
    alternates: bool = typer.Option(
        False, "--alternates", help="Export alternate candidates as secondary timeline"
    ),
) -> None:
    """Export timeline to EDL or FCPXML for DaVinci Resolve/Premiere Pro.

    Generates frame-accurate timeline with handle padding. By default exports
    only approved segments from the review report.

    Use --alternates to export the alternate candidates from the arc as a
    secondary timeline, useful for comparing takes in the NLE.
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

    if alternates:
        if format == "fcpxml":
            console.print(
                "[yellow]Warning: --alternates only supports EDL format. "
                "Using EDL regardless of --format flag.[/yellow]"
            )
        from plotline.export.edl import generate_alternates_edl_from_project

        content = generate_alternates_edl_from_project(
            project_path=project_dir,
            manifest=manifest,
            handle_frames=handle,
        )
        if content is None:
            console.print("[yellow]No alternate candidates found in arc.json[/yellow]")
            raise typer.Exit(0)
        project_name = manifest.get("project_name", "plotline")
        ext = ".edl"
        if output:
            output_path = Path(output)
        else:
            output_path = project_dir / "export" / f"{project_name}_alternates{ext}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓[/green] Exported alternates to {output_path}")
        console.print(f"[dim]  Format: EDL, Handle: {handle} frames[/dim]")
        return

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
        output_path = project_dir / "export" / f"{project_name}{ext}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    console.print(f"[green]✓[/green] Exported to {output_path}")
    console.print(f"[dim]  Format: {format.upper()}, Handle: {handle} frames[/dim]")


# Phase 6.5: Approvals


def _load_approvals(project_dir: Path) -> dict:
    """Load or create approvals data."""
    from plotline.project import read_json

    approvals_path = project_dir / "approvals.json"
    if approvals_path.exists():
        return read_json(approvals_path)
    return {"segments": []}


def _save_approvals(project_dir: Path, approvals: dict) -> None:
    """Save approvals data."""
    from datetime import datetime

    from plotline.project import write_json

    approvals_path = project_dir / "approvals.json"
    approvals["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(approvals_path, approvals)


def _validate_segment_exists(segment_id: str, selections: dict) -> bool:
    """Check if a segment ID exists in selections."""
    for seg in selections.get("segments", []):
        if seg.get("segment_id") == segment_id:
            return True
    return False


def _get_all_segment_ids(selections: dict) -> set[str]:
    """Get all segment IDs from selections."""
    return {
        seg.get("segment_id") for seg in selections.get("segments", []) if seg.get("segment_id")
    }


def _update_approval_status(approvals: dict, segment_id: str, status: str) -> bool:
    """Update segment approval status. Returns True if changed."""
    approval_map = {s["segment_id"]: s for s in approvals.get("segments", [])}

    if segment_id in approval_map:
        if approval_map[segment_id].get("status") == status:
            return False
        approval_map[segment_id]["status"] = status
    else:
        approval_map[segment_id] = {"segment_id": segment_id, "status": status}

    approvals["segments"] = list(approval_map.values())
    return True


@app.command("approve")
def approve_segment(
    segment_id: str | None = typer.Argument(None, help="Segment ID to approve"),
    interview: str | None = typer.Option(
        None, "--interview", "-i", help="Approve all from interview"
    ),
    all_segments: bool = typer.Option(False, "--all", "-a", help="Approve all pending segments"),
    threshold: float | None = typer.Option(
        None, "--threshold", "-t", help="Auto-approve segments with score >= threshold"
    ),
) -> None:
    """Approve segments for export."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.project import read_json

    selections_path = project_dir / "data" / "selections.json"
    if not selections_path.exists():
        console.print("[red]Error: No selections found. Run 'plotline arc' first.[/red]")
        raise typer.Exit(1)

    selections = read_json(selections_path)
    approvals = _load_approvals(project_dir)
    all_segment_ids = _get_all_segment_ids(selections)

    approved_count = 0

    if segment_id:
        if segment_id not in all_segment_ids:
            console.print(f"[red]Error: Segment '{segment_id}' not found in selections[/red]")
            raise typer.Exit(1)
        if _update_approval_status(approvals, segment_id, "approved"):
            approved_count = 1
            console.print(f"[green]✓[/green] Approved: {segment_id}")

    elif interview:
        for seg in selections.get("segments", []):
            if seg.get("interview_id") == interview:
                if _update_approval_status(approvals, seg["segment_id"], "approved"):
                    approved_count += 1
        console.print(f"[green]✓[/green] Approved {approved_count} segment(s) from {interview}")

    elif all_segments and threshold is not None:
        for seg in selections.get("segments", []):
            score = seg.get("composite_score", 0)
            if score >= threshold:
                if _update_approval_status(approvals, seg["segment_id"], "approved"):
                    approved_count += 1
        console.print(
            f"[green]✓[/green] Approved {approved_count} segment(s) with score >= {threshold}"
        )

    elif all_segments:
        for seg in selections.get("segments", []):
            if _update_approval_status(approvals, seg["segment_id"], "approved"):
                approved_count += 1
        console.print(f"[green]✓[/green] Approved {approved_count} segment(s)")

    else:
        console.print(
            "[red]Error: Specify segment_id, --interview, --all, or --all --threshold[/red]"
        )
        console.print("[dim]Examples:[/dim]")
        console.print("[dim]  plotline approve interview_001_seg_001[/dim]")
        console.print("[dim]  plotline approve --interview interview_001[/dim]")
        console.print("[dim]  plotline approve --all[/dim]")
        console.print("[dim]  plotline approve --all --threshold 0.8[/dim]")
        raise typer.Exit(1)

    _save_approvals(project_dir, approvals)


@app.command("reject")
def reject_segment(
    segment_id: str | None = typer.Argument(None, help="Segment ID to reject"),
    interview: str | None = typer.Option(
        None, "--interview", "-i", help="Reject all from interview"
    ),
    all_segments: bool = typer.Option(False, "--all", "-a", help="Reject all pending segments"),
) -> None:
    """Reject segments from export."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.project import read_json

    selections_path = project_dir / "data" / "selections.json"
    if not selections_path.exists():
        console.print("[red]Error: No selections found. Run 'plotline arc' first.[/red]")
        raise typer.Exit(1)

    selections = read_json(selections_path)
    approvals = _load_approvals(project_dir)
    all_segment_ids = _get_all_segment_ids(selections)

    rejected_count = 0

    if segment_id:
        if segment_id not in all_segment_ids:
            console.print(f"[red]Error: Segment '{segment_id}' not found in selections[/red]")
            raise typer.Exit(1)
        if _update_approval_status(approvals, segment_id, "rejected"):
            rejected_count = 1
            console.print(f"[red]✗[/red] Rejected: {segment_id}")

    elif interview:
        for seg in selections.get("segments", []):
            if seg.get("interview_id") == interview:
                if _update_approval_status(approvals, seg["segment_id"], "rejected"):
                    rejected_count += 1
        console.print(f"[red]✗[/red] Rejected {rejected_count} segment(s) from {interview}")

    elif all_segments:
        for seg in selections.get("segments", []):
            if _update_approval_status(approvals, seg["segment_id"], "rejected"):
                rejected_count += 1
        console.print(f"[red]✗[/red] Rejected {rejected_count} segment(s)")

    else:
        console.print("[red]Error: Specify segment_id, --interview, or --all[/red]")
        raise typer.Exit(1)

    _save_approvals(project_dir, approvals)


@app.command("unapprove")
def unapprove_segment(
    segment_id: str | None = typer.Argument(None, help="Segment ID to reset"),
    interview: str | None = typer.Option(
        None, "--interview", "-i", help="Reset all from interview"
    ),
    all_segments: bool = typer.Option(False, "--all", "-a", help="Reset all segments"),
) -> None:
    """Reset segment approval status to pending."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.project import read_json

    selections_path = project_dir / "data" / "selections.json"
    if not selections_path.exists():
        console.print("[red]Error: No selections found. Run 'plotline arc' first.[/red]")
        raise typer.Exit(1)

    selections = read_json(selections_path)
    approvals = _load_approvals(project_dir)
    all_segment_ids = _get_all_segment_ids(selections)

    reset_count = 0

    if segment_id:
        if segment_id not in all_segment_ids:
            console.print(f"[red]Error: Segment '{segment_id}' not found in selections[/red]")
            raise typer.Exit(1)
        if _update_approval_status(approvals, segment_id, "pending"):
            reset_count = 1
            console.print(f"[dim]○[/dim] Reset: {segment_id}")

    elif interview:
        for seg in selections.get("segments", []):
            if seg.get("interview_id") == interview:
                if _update_approval_status(approvals, seg["segment_id"], "pending"):
                    reset_count += 1
        console.print(f"[dim]○[/dim] Reset {reset_count} segment(s) from {interview}")

    elif all_segments:
        for seg in selections.get("segments", []):
            if _update_approval_status(approvals, seg["segment_id"], "pending"):
                reset_count += 1
        console.print(f"[dim]○[/dim] Reset {reset_count} segment(s)")

    else:
        console.print("[red]Error: Specify segment_id, --interview, or --all[/red]")
        raise typer.Exit(1)

    _save_approvals(project_dir, approvals)


@app.command("approvals")
def show_approvals() -> None:
    """Show approval summary."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.project import read_json

    selections_path = project_dir / "data" / "selections.json"
    if not selections_path.exists():
        console.print("[red]Error: No selections found. Run 'plotline arc' first.[/red]")
        raise typer.Exit(1)

    selections = read_json(selections_path)
    approvals = _load_approvals(project_dir)

    approval_map = {}
    for s in approvals.get("segments", []):
        seg_id = s.get("segment_id")
        if seg_id:
            approval_map[seg_id] = s.get("status", "pending")

    selection_segments = selections.get("segments", [])
    total = len(selection_segments)
    approved = sum(
        1 for s in selection_segments if approval_map.get(s.get("segment_id")) == "approved"
    )
    rejected = sum(
        1 for s in selection_segments if approval_map.get(s.get("segment_id")) == "rejected"
    )
    pending = total - approved - rejected

    console.print(f"\n[bold]Approval Summary[/bold]")
    console.print(f"  Total segments: {total}")
    console.print(f"  [green]Approved: {approved}[/green]")
    console.print(f"  [red]Rejected: {rejected}[/red]")
    console.print(f"  [dim]Pending: {pending}[/dim]")

    if total > 0:
        progress = int((approved + rejected) / total * 100)
        console.print(f"\n  Progress: {progress}%")

    if approved > 0:
        console.print(f"\n[dim]Export with: plotline export[/dim]")


# Phase 7: Reports


def _build_status_json(manifest: dict, project_dir: Path) -> dict:
    """Build status data as JSON for scripting."""
    from plotline.config import load_config

    interviews = manifest.get("interviews", [])
    interviews_data = []

    for interview in interviews:
        stages = interview.get("stages", {}).copy()
        completed = sum(1 for v in stages.values() if v)
        total = len(stages)
        interviews_data.append(
            {
                "id": interview.get("id"),
                "duration_seconds": interview.get("duration_seconds", 0),
                "stages": stages,
                "completed_stages": completed,
                "total_stages": total,
                "progress_percent": int(completed / total * 100) if total > 0 else 0,
            }
        )

    total_stages = sum(i["completed_stages"] for i in interviews_data)
    max_stages = sum(i["total_stages"] for i in interviews_data)
    overall_pct = int(total_stages / max_stages * 100) if max_stages > 0 else 0

    config = load_config(project_dir)

    return {
        "project_name": manifest.get("project_name", "Unknown"),
        "profile": config.project_profile,
        "interviews": interviews_data,
        "total_stages_completed": total_stages,
        "total_stages_possible": max_stages,
        "overall_progress_percent": overall_pct,
    }


def _suggest_next_stage(manifest: dict) -> str:
    """Suggest the next pipeline stage to run."""
    stage_order = ["extract", "transcribe", "analyze", "enrich", "themes", "synthesize", "arc"]
    stage_key_map = {
        "extract": "extracted",
        "transcribe": "transcribed",
        "analyze": "analyzed",
        "enrich": "enriched",
        "themes": "themes",
        "synthesize": None,
        "arc": None,
    }

    for stage in stage_order:
        stage_key = stage_key_map.get(stage)
        if stage_key is None:
            project_level_files = {
                "synthesize": manifest.get("data", {}).get("synthesis"),
                "arc": manifest.get("data", {}).get("selections"),
            }
            if not project_level_files.get(stage):
                return stage
            continue

        all_done = all(
            i.get("stages", {}).get(stage_key, False) for i in manifest.get("interviews", [])
        )
        if not all_done:
            return stage

    return "review"


def _has_completed_llm_stages(manifest: dict) -> bool:
    """Check if any LLM stages have been completed."""
    for interview in manifest.get("interviews", []):
        stages = interview.get("stages", {})
        if stages.get("themes"):
            return True
    return False


def _check_brief_staleness(project_dir: Path) -> list[str]:
    """Check if brief was modified after LLM stages ran. Returns warning messages."""
    from datetime import datetime, timezone

    warnings = []
    brief_path = project_dir / "brief.json"

    if not brief_path.exists():
        return []

    brief_mtime = brief_path.stat().st_mtime
    brief_time = datetime.fromtimestamp(brief_mtime, tz=timezone.utc)

    synthesis_path = project_dir / "data" / "synthesis.json"
    if synthesis_path.exists():
        from plotline.project import read_json

        synthesis = read_json(synthesis_path)
        synth_time_str = synthesis.get("synthesized_at")
        if synth_time_str:
            try:
                synth_time = datetime.fromisoformat(synth_time_str)
                if synth_time.tzinfo is None:
                    synth_time = synth_time.replace(tzinfo=timezone.utc)
                if brief_time > synth_time:
                    warnings.append(
                        "Brief modified after synthesis. Re-run: plotline run --from themes"
                    )
            except (ValueError, TypeError):
                pass

    arc_path = project_dir / "data" / "arc.json"
    if arc_path.exists():
        from plotline.project import read_json

        arc = read_json(arc_path)
        arc_time_str = arc.get("built_at")
        if arc_time_str:
            try:
                arc_time = datetime.fromisoformat(arc_time_str)
                if arc_time.tzinfo is None:
                    arc_time = arc_time.replace(tzinfo=timezone.utc)
                if brief_time > arc_time:
                    warnings.append("Brief modified after arc. Re-run: plotline run --from arc")
            except (ValueError, TypeError):
                pass

    return warnings


def _generate_all_reports(
    project_dir: Path, manifest: dict, config, open_browser: bool = False
) -> Path:
    """Generate all reports for a project. Returns path to dashboard."""
    from plotline.reports.compare import generate_compare_report
    from plotline.reports.coverage import generate_coverage
    from plotline.reports.dashboard import generate_dashboard
    from plotline.reports.review import generate_review
    from plotline.reports.summary import generate_summary
    from plotline.reports.themes import generate_themes_report
    from plotline.reports.transcript import generate_transcript

    output_path = generate_dashboard(
        project_path=project_dir, manifest=manifest, open_browser=False
    )

    try:
        generate_review(project_path=project_dir, manifest=manifest, open_browser=False)
    except FileNotFoundError:
        pass

    try:
        generate_summary(project_path=project_dir, manifest=manifest, open_browser=False)
    except FileNotFoundError:
        pass

    try:
        generate_coverage(project_path=project_dir, manifest=manifest, open_browser=False)
    except FileNotFoundError:
        pass

    try:
        generate_themes_report(project_path=project_dir, manifest=manifest, open_browser=False)
    except FileNotFoundError:
        pass

    try:
        generate_compare_report(
            project_path=project_dir, manifest=manifest, config=config, open_browser=False
        )
    except FileNotFoundError:
        pass

    interviews = manifest.get("interviews")
    if isinstance(interviews, list):
        for interview in interviews:
            if isinstance(interview, dict) and "id" in interview:
                try:
                    generate_transcript(
                        project_path=project_dir,
                        manifest=manifest,
                        interview_id=interview["id"],
                        open_browser=False,
                    )
                except FileNotFoundError:
                    pass

    if open_browser:
        from plotline.reports.generator import ReportGenerator

        ReportGenerator().open_in_browser(output_path)

    return output_path


@app.command("status")
def show_status(
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open dashboard in browser"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show project status and pipeline progress."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    project = Project(project_dir)
    manifest = project.load_manifest()

    if json_output:
        import json

        status_data = _build_status_json(manifest, project_dir)
        console.print_json(json.dumps(status_data, indent=2))
        return

    from plotline.config import load_config

    config = load_config(project_dir)

    console.print(f"\n[bold cyan]Project: {manifest.get('project_name', 'Unknown')}[/bold cyan]")
    console.print(f"[dim]Profile: {config.project_profile}[/dim]\n")

    interviews = manifest.get("interviews", [])
    if not interviews:
        console.print("[yellow]No interviews found. Run 'plotline add' first.[/yellow]")
        return

    table = Table(title="Interviews")
    table.add_column("ID", style="cyan")
    table.add_column("Duration", style="green")
    table.add_column("Progress", style="yellow")
    table.add_column("Stages", style="dim")

    for interview in interviews:
        stages = interview.get("stages", {})
        completed = sum(1 for v in stages.values() if v)
        total = len(stages)
        pct = int(completed / total * 100) if total > 0 else 0

        bar_filled = pct // 10
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        completed_stages = [k for k, v in stages.items() if v]
        stage_str = ", ".join(completed_stages) if completed_stages else "-"
        if len(stage_str) > 35:
            stage_str = stage_str[:32] + "..."

        table.add_row(
            interview.get("id", "unknown"),
            format_duration(interview.get("duration_seconds", 0)),
            f"{bar} {pct}%",
            stage_str,
        )

    console.print(table)

    total_stages = sum(sum(1 for v in i.get("stages", {}).values() if v) for i in interviews)
    max_stages = sum(len(i.get("stages", {})) for i in interviews)
    overall_pct = int(total_stages / max_stages * 100) if max_stages > 0 else 0

    console.print(
        f"\n[bold]Overall Progress: {overall_pct}%[/bold] ({total_stages}/{max_stages} stages)"
    )

    if overall_pct < 100:
        next_stage = _suggest_next_stage(manifest)
        console.print(f"\n[dim]Next: plotline {next_stage}[/dim]")
    else:
        console.print(f"\n[dim]Ready: plotline review && plotline export[/dim]")

    if open_browser:
        from plotline.reports.dashboard import generate_dashboard

        output_path = project_dir / "reports" / "dashboard.html"
        generate_dashboard(
            project_path=project_dir,
            manifest=manifest,
            output_path=output_path,
            open_browser=True,
        )
    else:
        console.print("[dim]Run with --open to view dashboard in browser[/dim]")


@app.command("info")
def show_info() -> None:
    """Display project configuration and metadata."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    from plotline.config import load_config
    from plotline.project import read_json

    project = Project(project_dir)
    manifest = project.load_manifest()
    config = load_config(project_dir)

    console.print(f"\n[bold cyan]Project: {config.project_name}[/bold cyan]")
    console.print(f"  Profile: {config.project_profile}")
    console.print(f"  Created: {manifest.get('created', 'Unknown')}")

    interviews = manifest.get("interviews", [])
    total_duration = sum(i.get("duration_seconds", 0) for i in interviews)
    console.print(f"\n[bold]Interviews: {len(interviews)}[/bold]")
    console.print(f"  Total duration: {format_duration(total_duration)}")

    languages = set(i.get("detected_language") for i in interviews if i.get("detected_language"))
    if languages:
        console.print(f"  Languages: {', '.join(sorted(languages))}")

    brief_path = project_dir / "brief.json"
    if brief_path.exists():
        brief = read_json(brief_path)
        console.print(f"\n[bold]Brief: Attached[/bold]")
        console.print(f"  Key messages: {len(brief.get('key_messages', []))}")
        target = brief.get("target_duration")
        if target:
            console.print(f"  Target duration: {target}")
    else:
        console.print(f"\n[bold]Brief: Not attached[/bold]")

    selections_path = project_dir / "data" / "selections.json"
    if selections_path.exists():
        selections = read_json(selections_path)
        seg_count = len(selections.get("segments", []))
        est_duration = selections.get("estimated_duration_seconds", 0)
        console.print(f"\n[bold]Selections: {seg_count} segments[/bold]")
        console.print(f"  Estimated duration: {format_duration(est_duration)}")

        approvals_path = project_dir / "approvals.json"
        if approvals_path.exists():
            approvals = read_json(approvals_path)
            approved = sum(
                1 for s in approvals.get("segments", []) if s.get("status") == "approved"
            )
            console.print(f"  Approved: {approved}/{seg_count}")

    console.print(f"\n[bold]Configuration:[/bold]")
    console.print(f"  LLM: {config.llm_backend} ({config.llm_model})")
    console.print(f"  Whisper: {config.whisper_backend} ({config.whisper_model})")
    console.print(f"  Target duration: {config.target_duration_seconds}s")
    console.print(f"  Diarization: {'Enabled' if config.diarization_enabled else 'Disabled'}")
    console.print(f"  Cultural flags: {'Enabled' if config.cultural_flags else 'Disabled'}")


@app.command("report")
def generate_report(
    report_type: str = typer.Argument(
        "dashboard",
        help="Report type (dashboard, transcript, review, summary, coverage, themes, compare, all)",
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
        elif report_type == "themes":
            from plotline.reports.themes import generate_themes_report

            output_path = generate_themes_report(
                project_path=project_dir,
                manifest=manifest,
                open_browser=open_browser,
            )
        elif report_type == "compare":
            from plotline.reports.compare import generate_compare_report
            from plotline.config import load_config

            config = load_config(project_dir)

            output_path = generate_compare_report(
                project_path=project_dir,
                manifest=manifest,
                config=config,
                open_browser=open_browser,
            )
        elif report_type == "all":
            from plotline.config import load_config

            config = load_config(project_dir)

            output_path = _generate_all_reports(
                project_dir, manifest, config, open_browser=open_browser
            )

            console.print("[green]✓[/green] Generated all reports")
            return
        else:
            console.print(f"[red]Unknown report type: {report_type}[/red]")
            console.print(
                "[dim]Valid types: dashboard, review, summary, transcript, coverage, themes, compare, all[/dim]"
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

    from datetime import datetime

    from plotline.brief import parse_brief, save_brief

    brief_path = Path(brief_file).expanduser().resolve()

    try:
        brief = parse_brief(brief_path)
        output_path = project_dir / "brief.json"
        save_brief(brief, output_path)

        project = Project(project_dir)
        manifest = project.load_manifest()
        manifest["brief"] = {
            "attached_at": datetime.now().isoformat(timespec="seconds"),
            "source_file": str(brief_path),
            "key_messages_count": len(brief.get("key_messages", [])),
        }
        project.save_manifest(manifest)

        console.print(f"[green]✓[/green] Brief parsed and saved to {output_path}")
        console.print(f"[dim]  Source: {brief_path}[/dim]")
        console.print(f"[dim]  Key messages: {len(brief.get('key_messages', []))}[/dim]")

        if _has_completed_llm_stages(manifest):
            console.print("\n[yellow]Warning: Brief attached after LLM analysis.[/yellow]")
            console.print("[dim]Re-run with: plotline run --from themes[/dim]")

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

    from plotline.config import load_config

    config = load_config(project_dir)

    stages = [
        "extract",
        "transcribe",
        "diarize",
        "analyze",
        "enrich",
        "themes",
        "synthesize",
        "arc",
    ]
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
            transcribe(
                model=config.whisper_model,
                language=config.whisper_language,
                force=False,
                backend=config.whisper_backend,
            )
        elif stage == "diarize":
            if config.diarization_enabled:
                diarize_speakers(force=False)

                speakers_file = project_dir / "speakers.yaml"
                if speakers_file.exists():
                    from plotline.diarize.speakers import load_speaker_config

                    speaker_config = load_speaker_config(project_dir)

                    if not any(
                        info.get("role") not in (None, "unknown")
                        for info in speaker_config.speakers.values()
                    ):
                        console.print(
                            "\n[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]"
                        )
                        console.print(
                            "[yellow]Diarization complete! Configure speakers before LLM analysis.[/yellow]"
                        )
                        console.print(
                            "[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]\n"
                        )
                        console.print(
                            "  [cyan]plotline speakers --preview[/cyan]     # Identify who is who"
                        )
                        console.print(
                            "  [cyan]plotline speakers <ID> --exclude[/cyan]  # Exclude interviewer"
                        )
                        console.print(
                            "  [cyan]plotline run[/cyan]                # Continue pipeline\n"
                        )

                        from rich.prompt import Confirm

                        should_continue = Confirm.ask(
                            "Continue without configuring speakers?", default=False
                        )
                        if not should_continue:
                            console.print(
                                "\n[dim]Pipeline paused. Configure speakers and run 'plotline run' to continue.[/dim]"
                            )
                            raise typer.Exit(0)
            else:
                console.print("[dim]Diarization disabled in config, skipping...[/dim]")
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

    if config.cultural_flags:
        console.print("[dim]Stage: cultural flags[/dim]")
        cultural_flags_cmd(force=False)
        console.print()

    console.print("[dim]Stage: reports[/dim]")

    project = Project(project_dir)
    manifest = project.load_manifest()

    _generate_all_reports(project_dir, manifest, config, open_browser=False)

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
    from plotline.llm.templates import PromptTemplateManager, detect_project_language

    config = load_config(project_dir)
    client = create_client_from_config(config)
    template_manager = PromptTemplateManager(project_dir / "prompts")
    language = detect_project_language(manifest)

    results = run_flags(
        project_path=project_dir,
        manifest=manifest,
        client=client,
        template_manager=template_manager,
        config=config,
        force=force,
        language=language,
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

                    with open(tf, encoding="utf-8") as f:
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

                    with open(sf, encoding="utf-8") as f:
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


@app.command("diagnose")
def diagnose_project(
    fix: bool = typer.Option(False, "--fix", help="Attempt to fix issues (not implemented)"),
) -> None:
    """Diagnose pipeline issues and suggest fixes."""
    project_dir = find_project_dir()
    if not project_dir:
        console.print("[red]Error: Not in a Plotline project directory[/red]")
        raise typer.Exit(1)

    import json

    issues = []

    project = Project(project_dir)
    manifest = project.load_manifest()

    for interview in manifest.get("interviews", []):
        source_str = interview.get("source_file", "")
        if source_str:
            source = Path(source_str)
            if not source.exists():
                issues.append(
                    {
                        "type": "missing_source",
                        "interview": interview.get("id", "unknown"),
                        "message": f"Source file not found: {source}",
                        "fix": None,
                    }
                )

    for interview in manifest.get("interviews", []):
        stages = interview.get("stages", {})
        interview_id = interview.get("id", "unknown")

        if stages.get("extracted"):
            audio_path = interview.get("audio_16k_path")
            if audio_path:
                full_path = project_dir / audio_path
                if not full_path.exists():
                    issues.append(
                        {
                            "type": "missing_audio",
                            "interview": interview_id,
                            "message": "Audio marked as extracted but file missing",
                            "fix": "plotline extract --force",
                        }
                    )

        if stages.get("transcribed"):
            transcript_path = project_dir / "data" / "transcripts" / f"{interview_id}.json"
            if not transcript_path.exists():
                issues.append(
                    {
                        "type": "missing_transcript",
                        "interview": interview_id,
                        "message": "Transcript marked as done but file missing",
                        "fix": "plotline transcribe --force",
                    }
                )

    data_dir = project_dir / "data"
    if data_dir.exists():
        for json_file in data_dir.rglob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                issues.append(
                    {
                        "type": "corrupted_json",
                        "file": str(json_file.relative_to(project_dir)),
                        "message": f"Invalid JSON: {e}",
                        "fix": f"plotline run --from {infer_stage_from_path(json_file)}",
                    }
                )
            except Exception as e:
                issues.append(
                    {
                        "type": "read_error",
                        "file": str(json_file.relative_to(project_dir)),
                        "message": f"Cannot read file: {e}",
                        "fix": None,
                    }
                )

    themes_dir = project_dir / "data" / "themes"
    if themes_dir.exists():
        for theme_file in themes_dir.glob("*.json"):
            try:
                with open(theme_file, encoding="utf-8") as f:
                    data = json.load(f)
                if not data.get("themes"):
                    issues.append(
                        {
                            "type": "incomplete_llm",
                            "file": str(theme_file.relative_to(project_dir)),
                            "message": "Theme extraction returned empty themes",
                            "fix": "plotline themes --force",
                        }
                    )
            except Exception:
                pass

    synthesis_path = project_dir / "data" / "synthesis.json"
    if synthesis_path.exists():
        try:
            with open(synthesis_path, encoding="utf-8") as f:
                data = json.load(f)
            if not data.get("unified_themes") and not data.get("best_takes"):
                issues.append(
                    {
                        "type": "incomplete_llm",
                        "file": "data/synthesis.json",
                        "message": "Synthesis returned no themes or best takes",
                        "fix": "plotline synthesize --force",
                    }
                )
        except Exception:
            pass

    if not issues:
        console.print("[green]✓ No issues found[/green]")
        return

    table = Table(title=f"Found {len(issues)} Issue(s)")
    table.add_column("Type", style="cyan")
    table.add_column("Location", style="yellow")
    table.add_column("Message", style="red")
    table.add_column("Suggested Fix", style="green")

    for issue in issues:
        table.add_row(
            issue.get("type", "unknown"),
            issue.get("interview") or issue.get("file", "-"),
            issue.get("message", ""),
            issue.get("fix") or "Manual fix required",
        )

    console.print(table)

    if fix:
        console.print(
            "\n[yellow]Auto-fix not implemented. Run suggested commands manually.[/yellow]"
        )

    raise typer.Exit(1)


def infer_stage_from_path(file_path: Path) -> str:
    """Infer pipeline stage from file path."""
    path_str = str(file_path).lower()
    if "transcript" in path_str:
        return "transcribe"
    elif "delivery" in path_str:
        return "analyze"
    elif "segments" in path_str:
        return "enrich"
    elif "themes" in path_str:
        return "themes"
    elif "synthesis" in path_str:
        return "synthesize"
    elif "arc" in path_str or "selections" in path_str:
        return "arc"
    else:
        return "extract"


if __name__ == "__main__":
    app()
