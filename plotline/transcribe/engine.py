"""
plotline.transcribe.engine - Whisper transcription engine.

Uses mlx-whisper (primary) for Apple Silicon or falls back to
other Whisper backends. Produces segment-level transcripts with
word-level timestamps.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def transcribe_audio(
    audio_path: Path,
    model: str = "medium",
    language: str | None = None,
    backend: str = "mlx",
    console=None,
) -> dict[str, Any]:
    """Transcribe audio file using Whisper.

    Args:
        audio_path: Path to audio file (16kHz WAV recommended)
        model: Whisper model size (tiny, base, small, medium, large)
        language: Language code (auto-detect if None)
        backend: Whisper backend (mlx, faster, cpp)
        console: Optional rich console for output

    Returns:
        Transcript dict with segments and metadata

    Raises:
        TranscriptionError: If transcription fails
    """
    from plotline.exceptions import TranscriptionError

    if console:
        console.print(f"[dim]  Loading {model} model...[/dim]")

    try:
        if backend == "mlx":
            result = _transcribe_mlx(audio_path, model, language)
        elif backend == "faster":
            result = _transcribe_faster(audio_path, model, language)
        elif backend == "cpp":
            result = _transcribe_cpp(audio_path, model, language)
        else:
            raise TranscriptionError(f"Unknown backend: {backend}")

        return result

    except TranscriptionError:
        raise
    except Exception as e:
        raise TranscriptionError(f"Transcription failed: {e}") from e


def _transcribe_mlx(
    audio_path: Path,
    model: str,
    language: str | None,
) -> dict[str, Any]:
    """Transcribe using mlx-whisper."""
    try:
        import mlx_whisper
    except ImportError as e:
        raise ImportError("mlx-whisper not installed. Install with: pip install mlx-whisper") from e

    model_name = f"mlx-community/whisper-{model}-mlx"

    kwargs = {
        "path_or_hf_repo": model_name,
        "word_timestamps": True,
    }
    if language:
        kwargs["language"] = language

    result = mlx_whisper.transcribe(str(audio_path), **kwargs)

    return _parse_whisper_result(result, model, language)


def _transcribe_faster(
    audio_path: Path,
    model: str,
    language: str | None,
) -> dict[str, Any]:
    """Transcribe using faster-whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ImportError(
            "faster-whisper not installed. Install with: pip install faster-whisper"
        ) from e

    model_instance = WhisperModel(model, device="auto", compute_type="auto")

    kwargs = {"word_timestamps": True}
    if language:
        kwargs["language"] = language

    segments, info = model_instance.transcribe(str(audio_path), **kwargs)

    result = {
        "language": info.language,
        "language_probability": info.language_probability,
        "segments": [],
    }

    for segment in segments:
        seg_dict = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "confidence": getattr(segment, "avg_logprob", 0),
            "words": [],
        }
        if segment.words:
            for word in segment.words:
                seg_dict["words"].append(
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability,
                    }
                )
        result["segments"].append(seg_dict)

    return _parse_whisper_result(result, model, language)


def _transcribe_cpp(
    audio_path: Path,
    model: str,
    language: str | None,
) -> dict[str, Any]:
    """Transcribe using whisper.cpp."""
    raise NotImplementedError("whisper.cpp backend not yet implemented")


def _parse_whisper_result(
    result: dict[str, Any],
    model: str,
    language: str | None,
) -> dict[str, Any]:
    """Parse Whisper result into our transcript format."""
    segments = []

    for i, seg in enumerate(result.get("segments", [])):
        words = []
        for w in seg.get("words", []):
            word_data = {
                "word": w.get("word", w.get("text", "")),
                "start": w.get("start", 0),
                "end": w.get("end", 0),
            }
            if "probability" in w:
                word_data["probability"] = w["probability"]
            words.append(word_data)

        confidence = seg.get("avg_logprob", seg.get("confidence", 0))
        if confidence < 0:
            confidence = (confidence + 1) / 1

        segment_data = {
            "segment_id": f"seg_{i + 1:03d}",
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "text": seg.get("text", "").strip(),
            "confidence": round(confidence, 2),
            "corrected": False,
            "words": words,
        }
        segments.append(segment_data)

    return {
        "model": model,
        "language": result.get("language", language or "unknown"),
        "segments": segments,
        "transcribed_at": datetime.now().isoformat(timespec="seconds"),
    }


def transcribe_all_interviews(
    project_path: Path,
    manifest: dict[str, Any],
    model: str = "medium",
    language: str | None = None,
    backend: str = "mlx",
    force: bool = False,
    console=None,
) -> dict[str, Any]:
    """Transcribe all interviews in a project.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        model: Whisper model size
        language: Language code (auto-detect if None)
        backend: Whisper backend
        force: Re-transcribe even if already done
        console: Optional rich console for output

    Returns:
        Dict with transcription summary
    """
    from rich.table import Table

    from plotline.project import write_json

    data_dir = project_path / "data"
    transcripts_dir = data_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "transcribed": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    table = Table(title="Transcription")
    table.add_column("Interview", style="cyan")
    table.add_column("Segments", style="green")
    table.add_column("Duration", style="green")
    table.add_column("Status", style="yellow")

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]

        if not interview["stages"].get("extracted"):
            table.add_row(interview_id, "-", "-", "[dim]Skipped (not extracted)[/dim]")
            results["skipped"] += 1
            continue

        if interview["stages"].get("transcribed") and not force:
            table.add_row(interview_id, "-", "-", "[dim]Skipped (already transcribed)[/dim]")
            results["skipped"] += 1
            continue

        audio_path = project_path / interview["audio_16k_path"]
        if not audio_path.exists():
            table.add_row(interview_id, "-", "-", "[red]Audio file not found[/red]")
            results["failed"] += 1
            results["errors"].append(
                {
                    "interview_id": interview_id,
                    "error": "Audio file not found",
                }
            )
            continue

        try:
            if console:
                console.print(f"\n[cyan]Transcribing {interview_id}...[/cyan]")

            transcript = transcribe_audio(
                audio_path=audio_path,
                model=model,
                language=language,
                backend=backend,
                console=console,
            )

            transcript["interview_id"] = interview_id
            transcript["duration_seconds"] = interview.get("duration_seconds", 0)

            for seg in transcript["segments"]:
                seg["segment_id"] = f"{interview_id}_seg_{seg['segment_id'].split('_')[1]}"

            output_path = transcripts_dir / f"{interview_id}.json"
            write_json(output_path, transcript)

            interview["stages"]["transcribed"] = True

            duration = (
                format_duration(transcript["segments"][-1]["end"])
                if transcript["segments"]
                else "0:00"
            )
            table.add_row(
                interview_id,
                str(len(transcript["segments"])),
                duration,
                "[green]✓ Transcribed[/green]",
            )
            results["transcribed"] += 1

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


def format_duration(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
