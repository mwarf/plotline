"""
plotline.enrich.merge - Merge transcript and delivery data.

Creates unified enriched segments.json per interview that combines
transcript text, word-level timestamps, delivery metrics, and speaker filtering.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from plotline.diarize.speakers import SpeakerConfig


def merge_transcript_and_delivery(
    transcript: dict[str, Any],
    delivery: dict[str, Any],
    interview_metadata: dict[str, Any] | None = None,
    speaker_config: "SpeakerConfig | None" = None,
) -> dict[str, Any]:
    """Merge transcript and delivery data into enriched segments.

    If speaker_config is provided, segments from excluded speakers
    are filtered out and not included in the enriched output.

    Args:
        transcript: Transcript dict with segments
        delivery: Delivery analysis dict with segments
        interview_metadata: Optional interview metadata from manifest
        speaker_config: Optional speaker configuration for filtering

    Returns:
        Enriched segments dict with filtering applied if configured
    """
    transcript_segments = {s["segment_id"]: s for s in transcript.get("segments", [])}
    delivery_segments = {s["segment_id"]: s for s in delivery.get("segments", [])}

    enriched_segments = []
    filtered_count = 0
    filtered_by_speaker: dict[str, int] = {}

    for segment_id, tseg in transcript_segments.items():
        speaker = tseg.get("speaker")

        if speaker_config and speaker:
            if not speaker_config.should_include_speaker(speaker):
                filtered_count += 1
                filtered_by_speaker[speaker] = filtered_by_speaker.get(speaker, 0) + 1
                continue

        dseg = delivery_segments.get(segment_id, {})

        enriched = {
            "segment_id": segment_id,
            "start": tseg.get("start", 0),
            "end": tseg.get("end", 0),
            "text": tseg.get("text", ""),
            "words": tseg.get("words", []),
            "confidence": tseg.get("confidence", 0),
            "corrected": tseg.get("corrected", False),
            "speaker": speaker,
        }

        delivery_data = dseg.get("normalized", {})
        delivery_data["composite_score"] = dseg.get("composite_score", 0)
        delivery_data["delivery_label"] = dseg.get("delivery_label", "")
        enriched["delivery"] = delivery_data

        enriched_segments.append(enriched)

    enriched_segments.sort(key=lambda s: s["start"])

    result = {
        "interview_id": transcript.get("interview_id", "unknown"),
        "source_file": interview_metadata.get("filename") if interview_metadata else None,
        "language": transcript.get("language"),
        "duration_seconds": transcript.get("duration_seconds", 0),
        "segment_count": len(enriched_segments),
        "filtered_count": filtered_count,
        "filtered_by_speaker": filtered_by_speaker if filtered_count > 0 else {},
        "enriched_at": datetime.now().isoformat(timespec="seconds"),
        "segments": enriched_segments,
    }

    return result


def enrich_all_interviews(
    project_path: Path,
    manifest: dict[str, Any],
    force: bool = False,
    console=None,
) -> dict[str, Any]:
    """Enrich all interviews in a project.

    Applies speaker filtering if speakers are configured and excluded.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        force: Re-enrich even if already done
        console: Optional rich console for output

    Returns:
        Dict with enrichment summary
    """
    from rich.table import Table

    from plotline.diarize.speakers import load_speaker_config
    from plotline.project import read_json, write_json

    data_dir = project_path / "data"
    transcripts_dir = data_dir / "transcripts"
    delivery_dir = data_dir / "delivery"
    segments_dir = data_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    speaker_config = load_speaker_config(project_path)
    excluded_speakers = speaker_config.get_excluded_speakers()

    results = {
        "enriched": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
        "total_filtered": 0,
    }

    table = Table(title="Enrichment")
    table.add_column("Interview", style="cyan")
    table.add_column("Segments", style="green")
    table.add_column("Filtered", style="yellow")
    table.add_column("Status", style="yellow")

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]

        if not interview["stages"].get("analyzed"):
            table.add_row(interview_id, "-", "-", "[dim]Skipped (not analyzed)[/dim]")
            results["skipped"] += 1
            continue

        if interview["stages"].get("enriched") and not force:
            table.add_row(interview_id, "-", "-", "[dim]Skipped (already enriched)[/dim]")
            results["skipped"] += 1
            continue

        transcript_path = transcripts_dir / f"{interview_id}.json"
        delivery_path = delivery_dir / f"{interview_id}.json"

        if not transcript_path.exists():
            table.add_row(interview_id, "-", "-", "[red]Transcript not found[/red]")
            results["failed"] += 1
            results["errors"].append(
                {
                    "interview_id": interview_id,
                    "error": "Transcript not found",
                }
            )
            continue

        if not delivery_path.exists():
            table.add_row(interview_id, "-", "-", "[red]Delivery not found[/red]")
            results["failed"] += 1
            results["errors"].append(
                {
                    "interview_id": interview_id,
                    "error": "Delivery analysis not found",
                }
            )
            continue

        try:
            transcript = read_json(transcript_path)
            delivery = read_json(delivery_path)

            enriched = merge_transcript_and_delivery(
                transcript=transcript,
                delivery=delivery,
                interview_metadata=interview,
                speaker_config=speaker_config if excluded_speakers else None,
            )

            output_path = segments_dir / f"{interview_id}.json"
            write_json(output_path, enriched)

            interview["stages"]["enriched"] = True

            filtered_str = (
                str(enriched.get("filtered_count", 0))
                if enriched.get("filtered_count", 0) > 0
                else "-"
            )
            results["total_filtered"] += enriched.get("filtered_count", 0)

            table.add_row(
                interview_id,
                str(enriched["segment_count"]),
                filtered_str,
                "[green]✓ Enriched[/green]",
            )
            results["enriched"] += 1

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
        if results["total_filtered"] > 0:
            console.print(
                f"\n[dim]Filtered {results['total_filtered']} segments from excluded speakers[/dim]"
            )

    return results
