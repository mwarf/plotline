"""
plotline.reports.transcript - Per-interview transcript report.

Generates an interactive HTML report with delivery timeline visualization
and segment breakdown for a single interview.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plotline.export.timecode import seconds_to_timecode
from plotline.project import read_json
from plotline.reports.generator import ReportGenerator
from plotline.utils import format_duration, get_delivery_class


def get_confidence_class(confidence: float) -> str:
    """Get CSS class for transcription confidence."""
    if confidence >= 0.9:
        return "high"
    elif confidence >= 0.7:
        return "medium"
    return "low"


def build_theme_map(themes_data: dict[str, Any] | None) -> dict[str, list[str]]:
    """Build mapping from segment_id to theme names."""
    if not themes_data:
        return {}

    segment_to_themes: dict[str, list[str]] = {}

    for theme in themes_data.get("themes", []):
        theme_name = theme.get("name", "")
        for segment_id in theme.get("segment_ids", []):
            if segment_id not in segment_to_themes:
                segment_to_themes[segment_id] = []
            segment_to_themes[segment_id].append(theme_name)

    return segment_to_themes


def get_theme_color(index: int) -> str:
    """Get a consistent color for a theme by index."""
    colors = [
        "#3b82f6",
        "#8b5cf6",
        "#06b6d4",
        "#22c55e",
        "#f59e0b",
        "#ef4444",
        "#ec4899",
        "#14b8a6",
    ]
    return colors[index % len(colors)]


def generate_transcript(
    project_path: Path,
    manifest: dict[str, Any],
    interview_id: str,
    output_path: Path | None = None,
    open_browser: bool = False,
) -> Path:
    """Generate the per-interview transcript report.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        interview_id: Interview ID to generate report for
        output_path: Optional output path
        open_browser: Whether to open in browser

    Returns:
        Path to generated report
    """
    if output_path is None:
        output_path = project_path / "reports" / f"transcript_{interview_id}.html"

    segments_path = project_path / "data" / "segments" / f"{interview_id}.json"
    if not segments_path.exists():
        raise FileNotFoundError(
            f"No segments found for {interview_id}. Run 'plotline enrich' first."
        )

    segments_data = read_json(segments_path)
    all_segments = segments_data.get("segments", [])

    themes_path = project_path / "data" / "themes" / f"{interview_id}.json"
    themes_data = None
    if themes_path.exists():
        themes_data = read_json(themes_path)

    theme_map = build_theme_map(themes_data)

    interview_meta = None
    for interview in manifest.get("interviews", []):
        if interview.get("id") == interview_id:
            interview_meta = interview
            break

    if not interview_meta:
        interview_meta = {}

    fps = interview_meta.get("frame_rate", 24)
    source_file = interview_meta.get("filename") or interview_meta.get("source_file", "Unknown")
    total_duration = segments_data.get("duration_seconds", 0)

    segments_list = []
    timeline_data = []
    theme_names = set()

    for theme_list in theme_map.values():
        for theme in theme_list:
            theme_names.add(theme)

    sorted_themes = sorted(theme_names)
    theme_colors = {name: get_theme_color(i) for i, name in enumerate(sorted_themes)}

    for i, segment in enumerate(all_segments):
        segment_id = segment.get("segment_id", "")
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        duration = end - start

        delivery = segment.get("delivery", {})
        delivery_score = delivery.get("composite_score", 0.5)
        energy = delivery.get("energy", 0.5)
        speech_rate = delivery.get("speech_rate", 0.5)
        delivery_label = delivery.get("delivery_label", "")

        confidence = segment.get("confidence", 1.0)

        segment_themes = theme_map.get(segment_id, [])

        audio_path = None
        if interview_meta.get("audio_full_path"):
            audio_path = f"../{interview_meta['audio_full_path']}#t={max(0, start - 2)}"

        segments_list.append(
            {
                "id": segment_id,
                "index": i + 1,
                "text": segment.get("text", ""),
                "timecode": (
                    f"{seconds_to_timecode(start, fps)} → {seconds_to_timecode(end, fps)}"
                ),
                "start": start,
                "end": end,
                "duration": format_duration(duration),
                "confidence": confidence,
                "confidence_class": get_confidence_class(confidence),
                "delivery_score": delivery_score,
                "delivery_class": get_delivery_class(delivery_score),
                "delivery_label": delivery_label,
                "energy": energy,
                "speech_rate": speech_rate,
                "themes": segment_themes,
                "theme_colors": [theme_colors.get(t, "#64748b") for t in segment_themes],
                "audio_path": audio_path,
            }
        )

        timeline_data.append(
            {
                "index": i + 1,
                "start": start,
                "end": end,
                "duration": duration,
                "energy": energy,
                "speech_rate": speech_rate,
                "delivery_score": delivery_score,
            }
        )

    total_segments = len(segments_list)
    avg_score = (
        sum(s["delivery_score"] for s in segments_list) / total_segments
        if total_segments > 0
        else 0
    )

    themes_for_template = [{"name": name, "color": theme_colors[name]} for name in sorted_themes]

    data = {
        "project_name": manifest.get("project_name", "Plotline Project"),
        "interview_id": interview_id,
        "source_file": source_file,
        "total_duration": format_duration(total_duration),
        "total_duration_seconds": total_duration,
        "segment_count": total_segments,
        "avg_score": round(avg_score, 2),
        "avg_delivery_class": get_delivery_class(avg_score),
        "themes": themes_for_template,
        "has_themes": len(themes_for_template) > 0,
        "segments": segments_list,
        "timeline_data": timeline_data,
        "has_delivery": any(s.get("delivery_score") != 0.5 for s in segments_list),
    }

    generator = ReportGenerator()
    result_path = generator.render("transcript.html", data, output_path)

    if open_browser:
        generator.open_in_browser(result_path)

    return result_path
