"""
plotline.enrich.merge - Merge transcript and delivery data.

Creates unified enriched segments.json per interview that combines
transcript text, word-level timestamps, and delivery metrics.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def merge_transcript_and_delivery(
    transcript: dict[str, Any],
    delivery: dict[str, Any],
    interview_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge transcript and delivery data into enriched segments.

    Args:
        transcript: Transcript dict with segments
        delivery: Delivery analysis dict with segments
        interview_metadata: Optional interview metadata from manifest

    Returns:
        Enriched segments dict
    """
    transcript_segments = {s["segment_id"]: s for s in transcript.get("segments", [])}
    delivery_segments = {s["segment_id"]: s for s in delivery.get("segments", [])}

    enriched_segments = []

    for segment_id, tseg in transcript_segments.items():
        dseg = delivery_segments.get(segment_id, {})

        enriched = {
            "segment_id": segment_id,
            "start": tseg.get("start", 0),
            "end": tseg.get("end", 0),
            "text": tseg.get("text", ""),
            "words": tseg.get("words", []),
            "confidence": tseg.get("confidence", 0),
            "corrected": tseg.get("corrected", False),
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
        "duration_seconds": transcript.get("duration_seconds", 0),
        "segment_count": len(enriched_segments),
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

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        force: Re-enrich even if already done
        console: Optional rich console for output

    Returns:
        Dict with enrichment summary
    """
    from rich.table import Table

    from plotline.project import read_json, write_json

    data_dir = project_path / "data"
    transcripts_dir = data_dir / "transcripts"
    delivery_dir = data_dir / "delivery"
    segments_dir = data_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "enriched": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    table = Table(title="Enrichment")
    table.add_column("Interview", style="cyan")
    table.add_column("Segments", style="green")
    table.add_column("Status", style="yellow")

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]

        if not interview["stages"].get("analyzed"):
            table.add_row(interview_id, "-", "[dim]Skipped (not analyzed)[/dim]")
            results["skipped"] += 1
            continue

        if interview["stages"].get("enriched") and not force:
            table.add_row(interview_id, "-", "[dim]Skipped (already enriched)[/dim]")
            results["skipped"] += 1
            continue

        transcript_path = transcripts_dir / f"{interview_id}.json"
        delivery_path = delivery_dir / f"{interview_id}.json"

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

        if not delivery_path.exists():
            table.add_row(interview_id, "-", "[red]Delivery analysis not found[/red]")
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
            )

            output_path = segments_dir / f"{interview_id}.json"
            write_json(output_path, enriched)

            interview["stages"]["enriched"] = True

            table.add_row(
                interview_id,
                str(enriched["segment_count"]),
                "[green]✓ Enriched[/green]",
            )
            results["enriched"] += 1

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
