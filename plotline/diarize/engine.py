"""
plotline.diarize.engine - pyannote.audio diarization engine.

Runs speaker diarization on audio files using pyannote.audio models.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any


def get_hf_token(console=None) -> str:
    """Get HuggingFace token from environment, cache, or prompt.

    Args:
        console: Optional rich console for output

    Returns:
        HuggingFace token string

    Raises:
        ValueError: If token cannot be obtained
    """
    token = os.getenv("HUGGINGFACE_TOKEN")
    if token:
        return token

    cache_path = Path.home() / ".plotline" / "hf_token"
    if cache_path.exists():
        return cache_path.read_text().strip()

    if console:
        from rich.prompt import Prompt

        console.print("[yellow]HuggingFace token required for speaker diarization.[/yellow]")
        console.print("")
        console.print("Get a token at: [cyan]https://huggingface.co/settings/tokens[/cyan]")
        console.print("")
        console.print("You must accept the user conditions at:")
        console.print("  - [cyan]https://huggingface.co/pyannote/segmentation-3.0[/cyan]")
        console.print("  - [cyan]https://huggingface.co/pyannote/speaker-diarization-3.1[/cyan]")
        console.print("")

        token = Prompt.ask("Enter your HuggingFace token", password=True)

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(token)
        console.print(f"[dim]Token cached at {cache_path}[/dim]")

        return token

    raise ValueError(
        "HuggingFace token required. Set HUGGINGFACE_TOKEN environment variable "
        "or run interactively to be prompted."
    )


def get_device() -> str:
    """Get the best available device for inference.

    Returns:
        Device string: 'mps', 'cuda', or 'cpu'
    """
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def diarize_audio(
    audio_path: Path,
    model: str = "pyannote/speaker-diarization-3.1",
    hf_token: str | None = None,
    num_speakers: int | None = None,
    min_speakers: int = 2,
    max_speakers: int = 5,
    console=None,
) -> dict[str, Any]:
    """Run speaker diarization on an audio file.

    Args:
        audio_path: Path to audio file
        model: pyannote model name
        hf_token: HuggingFace token (obtained from env/prompt if None)
        num_speakers: Exact number of speakers (if known)
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
        console: Optional rich console for output

    Returns:
        Diarization result dict with segments and speakers

    Raises:
        ImportError: If pyannote.audio is not installed
        ValueError: If HF token is required but not available
    """
    try:
        import torch
        from pyannote.audio import Pipeline
    except ImportError as e:
        raise ImportError(
            "pyannote.audio not installed. Install with: pip install plotline[diarization]"
        ) from e

    if hf_token is None:
        hf_token = get_hf_token(console)

    if console:
        console.print(f"[dim]  Loading diarization model...[/dim]")

    pipeline = Pipeline.from_pretrained(model, use_auth_token=hf_token)

    device = get_device()
    if console:
        console.print(f"[dim]  Using device: {device}[/dim]")
    pipeline.to(torch.device(device))

    kwargs = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    else:
        kwargs["min_speakers"] = min_speakers
        kwargs["max_speakers"] = max_speakers

    if console:
        from pyannote.audio.pipelines.utils.hook import ProgressHook

        with ProgressHook() as hook:
            diarization = pipeline(str(audio_path), hook=hook, **kwargs)
    else:
        diarization = pipeline(str(audio_path), **kwargs)

    speakers = set()
    segments = []

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speakers.add(speaker)
        segments.append(
            {
                "start": turn.start,
                "end": turn.end,
                "duration": turn.duration,
                "speaker": speaker,
            }
        )

    return {
        "model": model,
        "diarized_at": datetime.now().isoformat(timespec="seconds"),
        "num_speakers_detected": len(speakers),
        "speakers": sorted(speakers),
        "segments": segments,
    }


def diarize_all_interviews(
    project_path: Path,
    manifest: dict[str, Any],
    model: str = "pyannote/speaker-diarization-3.1",
    num_speakers: int | None = None,
    min_speakers: int = 2,
    max_speakers: int = 5,
    force: bool = False,
    console=None,
) -> dict[str, Any]:
    """Run diarization on all interviews in a project.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        model: pyannote model name
        num_speakers: Exact number of speakers (if known)
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
        force: Re-diarize even if already done
        console: Optional rich console for output

    Returns:
        Dict with diarization summary
    """
    from rich.table import Table

    from plotline.diarize.align import assign_speakers_to_transcript
    from plotline.diarize.speakers import (
        generate_default_colors,
        load_speaker_config,
        save_speaker_config,
    )
    from plotline.project import read_json, write_json

    data_dir = project_path / "data"
    diarization_dir = data_dir / "diarization"
    diarization_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir = data_dir / "transcripts"

    results = {
        "diarized": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    table = Table(title="Speaker Diarization")
    table.add_column("Interview", style="cyan")
    table.add_column("Speakers", style="green")
    table.add_column("Status", style="yellow")

    hf_token = None

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]

        if not interview["stages"].get("transcribed"):
            table.add_row(interview_id, "-", "[dim]Skipped (not transcribed)[/dim]")
            results["skipped"] += 1
            continue

        if interview["stages"].get("diarized") and not force:
            table.add_row(interview_id, "-", "[dim]Skipped (already diarized)[/dim]")
            results["skipped"] += 1
            continue

        audio_path = project_path / interview["audio_16k_path"]
        if not audio_path.exists():
            table.add_row(interview_id, "-", "[red]Audio file not found[/red]")
            results["failed"] += 1
            results["errors"].append(
                {
                    "interview_id": interview_id,
                    "error": "Audio file not found",
                }
            )
            continue

        transcript_path = transcripts_dir / f"{interview_id}.json"
        if not transcript_path.exists():
            table.add_row(interview_id, "-", "[red]Transcript not found[/red]")
            results["failed"] += 1
            results["errors"].append(
                {
                    "interview_id": interview_id,
                    "error": "Transcript not found",
                }
            )
            continue

        try:
            if console:
                console.print(f"\n[cyan]Diarizing {interview_id}...[/cyan]")

            if hf_token is None:
                hf_token = get_hf_token(console)

            diarization_result = diarize_audio(
                audio_path=audio_path,
                model=model,
                hf_token=hf_token,
                num_speakers=num_speakers,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
                console=console,
            )

            diarization_result["interview_id"] = interview_id

            diarization_path = diarization_dir / f"{interview_id}.json"
            write_json(diarization_path, diarization_result)

            transcript = read_json(transcript_path)
            updated_transcript = assign_speakers_to_transcript(
                transcript=transcript,
                diarization=diarization_result,
            )
            write_json(transcript_path, updated_transcript)

            speakers_file = project_path / "speakers.yaml"
            if not speakers_file.exists():
                speaker_config = load_speaker_config(project_path)
                detected_speakers = diarization_result["speakers"]
                colors = generate_default_colors()

                for i, speaker_id in enumerate(detected_speakers):
                    if speaker_id not in speaker_config.speakers:
                        speaker_config.speakers[speaker_id] = {
                            "name": f"Speaker {i + 1}",
                            "color": colors[i % len(colors)],
                        }

                save_speaker_config(speaker_config, speakers_file)
                if console:
                    console.print(
                        f"[dim]  Created speakers.yaml with {len(detected_speakers)} speakers[/dim]"
                    )

            interview["stages"]["diarized"] = True

            table.add_row(
                interview_id,
                str(diarization_result["num_speakers_detected"]),
                "[green]✓ Diarized[/green]",
            )
            results["diarized"] += 1

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

    return results
