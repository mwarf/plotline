"""
plotline.extract.audio - FFmpeg audio extraction.

Extracts audio from video files, producing two versions:
- 16kHz mono WAV for transcription (Whisper)
- Original sample rate WAV for delivery analysis (librosa)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def extract_audio(
    source_path: Path,
    output_16k: Path,
    output_full: Path,
    console=None,
) -> dict[str, Any]:
    """Extract audio from a video file using FFmpeg.

    Args:
        source_path: Path to source video file
        output_16k: Output path for 16kHz mono WAV (for Whisper)
        output_full: Output path for full-rate WAV (for librosa)
        console: Optional rich console for output

    Returns:
        Dict with extraction results

    Raises:
        ExtractionError: If FFmpeg fails
    """
    from plotline.exceptions import ExtractionError

    output_16k.parent.mkdir(parents=True, exist_ok=True)
    output_full.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "source": str(source_path),
        "audio_16k": str(output_16k),
        "audio_full": str(output_full),
        "success": False,
        "error": None,
    }

    cmd_16k = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_16k),
    ]

    cmd_full = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-acodec",
        "pcm_s24le",
        str(output_full),
    ]

    try:
        if console:
            console.print("[dim]  Extracting 16kHz audio...[/dim]")

        proc = subprocess.run(
            cmd_16k,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise ExtractionError(f"FFmpeg 16kHz extraction failed: {proc.stderr}")

        if console:
            console.print("[dim]  Extracting full-rate audio...[/dim]")

        proc = subprocess.run(
            cmd_full,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise ExtractionError(f"FFmpeg full-rate extraction failed: {proc.stderr}")

        result["success"] = True

        if output_16k.exists():
            result["audio_16k_size"] = output_16k.stat().st_size
        if output_full.exists():
            result["audio_full_size"] = output_full.stat().st_size

    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"Audio extraction failed: {e}") from e

    return result


def extract_all_interviews(
    project_path: Path,
    manifest: dict[str, Any],
    force: bool = False,
    console=None,
) -> dict[str, Any]:
    """Extract audio for all interviews in a project.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        force: Re-extract even if already extracted
        console: Optional rich console for output

    Returns:
        Dict with extraction summary
    """
    from rich.table import Table

    source_dir = project_path / "source"

    results = {
        "extracted": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    table = Table(title="Audio Extraction")
    table.add_column("Interview", style="cyan")
    table.add_column("16kHz", style="green")
    table.add_column("Full Rate", style="green")
    table.add_column("Status", style="yellow")

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]
        source_file = Path(interview["source_file"])

        interview_dir = source_dir / interview_id
        audio_16k = interview_dir / "audio_16k.wav"
        audio_full = interview_dir / "audio_full.wav"

        if interview["stages"].get("extracted") and not force:
            table.add_row(
                interview_id,
                format_size(audio_16k) if audio_16k.exists() else "-",
                format_size(audio_full) if audio_full.exists() else "-",
                "[dim]Skipped (already extracted)[/dim]",
            )
            results["skipped"] += 1
            continue

        if not source_file.exists():
            table.add_row(interview_id, "-", "-", "[red]Source not found[/red]")
            results["failed"] += 1
            results["errors"].append(
                {
                    "interview_id": interview_id,
                    "error": "Source file not found",
                }
            )
            continue

        try:
            interview_dir.mkdir(parents=True, exist_ok=True)

            extract_audio(
                source_path=source_file,
                output_16k=audio_16k,
                output_full=audio_full,
                console=console,
            )

            interview["audio_16k_path"] = str(audio_16k.relative_to(project_path))
            interview["audio_full_path"] = str(audio_full.relative_to(project_path))
            interview["stages"]["extracted"] = True

            table.add_row(
                interview_id,
                format_size(audio_16k),
                format_size(audio_full),
                "[green]✓ Extracted[/green]",
            )
            results["extracted"] += 1

        except Exception as e:
            table.add_row(interview_id, "-", "-", f"[red]Error: {e}[/red]")
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


def format_size(path: Path) -> str:
    """Format file size in human-readable format."""
    if not path.exists():
        return "-"
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
