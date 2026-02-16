"""
plotline.analyze.delivery - Per-segment audio feature extraction.

Extracts delivery metrics (energy, pitch, speech rate, pauses, spectral
features) from audio for each transcript segment using librosa.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


def extract_segment_features(
    audio: np.ndarray,
    sr: int,
    start: float,
    end: float,
    prev_end: float | None = None,
    next_start: float | None = None,
) -> dict[str, Any]:
    """Extract audio features for a single segment.

    Args:
        audio: Full audio signal array
        sr: Sample rate
        start: Segment start time in seconds
        end: Segment end time in seconds
        prev_end: Previous segment end time (for pause_before)
        next_start: Next segment start time (for pause_after)

    Returns:
        Dict of raw audio features
    """
    start_sample = int(start * sr)
    end_sample = int(end * sr)

    start_sample = max(0, start_sample)
    end_sample = min(len(audio), end_sample)

    segment_audio = audio[start_sample:end_sample]

    if len(segment_audio) == 0:
        return {
            "rms_energy": 0.0,
            "pitch_mean_hz": 0.0,
            "pitch_std_hz": 0.0,
            "pitch_contour": [],
            "speech_rate_wpm": 0.0,
            "pause_before_sec": 0.0,
            "pause_after_sec": 0.0,
            "spectral_centroid_mean": 0.0,
            "zero_crossing_rate": 0.0,
        }

    rms_energy = float(np.sqrt(np.mean(segment_audio**2)))

    pitch_mean, pitch_std, pitch_contour = _extract_pitch(segment_audio, sr)

    pause_before = (start - prev_end) if prev_end is not None else 0.0
    pause_after = (next_start - end) if next_start is not None else 0.0
    pause_before = max(0.0, pause_before)
    pause_after = max(0.0, pause_after)

    spectral_centroid = _extract_spectral_centroid(segment_audio, sr)

    zcr = _extract_zero_crossing_rate(segment_audio, sr)

    return {
        "rms_energy": rms_energy,
        "pitch_mean_hz": pitch_mean,
        "pitch_std_hz": pitch_std,
        "pitch_contour": pitch_contour,
        "speech_rate_wpm": 0.0,
        "pause_before_sec": round(pause_before, 3),
        "pause_after_sec": round(pause_after, 3),
        "spectral_centroid_mean": spectral_centroid,
        "zero_crossing_rate": zcr,
    }


def _extract_pitch(audio: np.ndarray, sr: int) -> tuple[float, float, list[float]]:
    """Extract pitch features using librosa.pyin.

    Returns:
        Tuple of (mean_hz, std_hz, contour_list)
    """
    import librosa

    try:
        f0, voiced_flags, _ = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sr,
        )

        voiced_f0 = f0[voiced_flags] if f0 is not None else np.array([])
        voiced_f0 = voiced_f0[~np.isnan(voiced_f0)] if len(voiced_f0) > 0 else np.array([])

        if len(voiced_f0) > 0:
            pitch_mean = float(np.mean(voiced_f0))
            pitch_std = float(np.std(voiced_f0))
        else:
            pitch_mean = 0.0
            pitch_std = 0.0

        contour_frames = max(1, int(len(audio) / sr / 0.5))
        if f0 is not None and len(f0) > 0:
            indices = np.linspace(0, len(f0) - 1, min(contour_frames, len(f0)), dtype=int)
            pitch_contour = [
                round(float(f0[i]), 1) if not np.isnan(f0[i]) else 0.0 for i in indices
            ]
        else:
            pitch_contour = []

        return pitch_mean, pitch_std, pitch_contour

    except Exception:
        return 0.0, 0.0, []


def _extract_spectral_centroid(audio: np.ndarray, sr: int) -> float:
    """Extract mean spectral centroid (brightness)."""
    import librosa

    try:
        centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)
        return float(np.mean(centroids))
    except Exception:
        return 0.0


def _extract_zero_crossing_rate(audio: np.ndarray, sr: int) -> float:
    """Extract mean zero crossing rate (voice texture)."""
    import librosa

    try:
        zcr = librosa.feature.zero_crossing_rate(audio)
        return float(np.mean(zcr))
    except Exception:
        return 0.0


def analyze_interview_delivery(
    audio_path: Path,
    transcript: dict[str, Any],
    console=None,
) -> dict[str, Any]:
    """Analyze delivery for all segments in an interview.

    Args:
        audio_path: Path to full-rate audio WAV
        transcript: Transcript dict with segments
        console: Optional rich console for output

    Returns:
        Delivery analysis dict with per-segment metrics
    """
    import librosa

    from plotline.exceptions import AnalysisError

    if console:
        console.print(f"[dim]  Loading audio: {audio_path.name}[/dim]")

    try:
        audio, sr = librosa.load(str(audio_path), sr=None)
    except Exception as e:
        raise AnalysisError(f"Failed to load audio: {e}")

    segments = transcript.get("segments", [])
    delivery_segments = []

    for i, seg in enumerate(segments):
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        word_count = len(seg.get("words", []))

        prev_end = segments[i - 1].get("end") if i > 0 else None
        next_start = segments[i + 1].get("start") if i < len(segments) - 1 else None

        features = extract_segment_features(
            audio=audio,
            sr=sr,
            start=start,
            end=end,
            prev_end=prev_end,
            next_start=next_start,
        )

        duration = end - start
        if duration > 0 and word_count > 0:
            features["speech_rate_wpm"] = round((word_count / duration) * 60, 1)
        else:
            features["speech_rate_wpm"] = 0.0

        delivery_segments.append(
            {
                "segment_id": seg.get("segment_id", f"seg_{i + 1:03d}"),
                "raw": features,
            }
        )

        if console and (i + 1) % 50 == 0:
            console.print(f"[dim]    Processed {i + 1}/{len(segments)} segments[/dim]")

    return {
        "interview_id": transcript.get("interview_id", "unknown"),
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "segments": delivery_segments,
    }


def analyze_all_interviews(
    project_path: Path,
    manifest: dict[str, Any],
    force: bool = False,
    console=None,
) -> dict[str, Any]:
    """Analyze delivery for all interviews in a project.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        force: Re-analyze even if already done
        console: Optional rich console for output

    Returns:
        Dict with analysis summary
    """
    from rich.table import Table

    from plotline.project import read_json, write_json

    data_dir = project_path / "data"
    transcripts_dir = data_dir / "transcripts"
    delivery_dir = data_dir / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "analyzed": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    table = Table(title="Delivery Analysis")
    table.add_column("Interview", style="cyan")
    table.add_column("Segments", style="green")
    table.add_column("Status", style="yellow")

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]

        if not interview["stages"].get("transcribed"):
            table.add_row(interview_id, "-", "[dim]Skipped (not transcribed)[/dim]")
            results["skipped"] += 1
            continue

        if interview["stages"].get("analyzed") and not force:
            table.add_row(interview_id, "-", "[dim]Skipped (already analyzed)[/dim]")
            results["skipped"] += 1
            continue

        audio_path = project_path / interview.get("audio_full_path", "")
        transcript_path = transcripts_dir / f"{interview_id}.json"

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
                console.print(f"\n[cyan]Analyzing {interview_id}...[/cyan]")

            transcript = read_json(transcript_path)
            delivery = analyze_interview_delivery(
                audio_path=audio_path,
                transcript=transcript,
                console=console,
            )

            output_path = delivery_dir / f"{interview_id}.json"
            write_json(output_path, delivery)

            interview["stages"]["analyzed"] = True

            table.add_row(
                interview_id,
                str(len(delivery["segments"])),
                "[green]✓ Analyzed[/green]",
            )
            results["analyzed"] += 1

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
