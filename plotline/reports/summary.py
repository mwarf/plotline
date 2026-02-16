"""
plotline.reports.summary - Project summary report.

Executive summary of project with interview contributions, themes, and highlights.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from plotline.project import read_json
from plotline.reports.generator import ReportGenerator


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM or MM:SS."""
    if seconds >= 3600:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    minutes = int(seconds // 60)
    return f"{minutes}m"


def generate_summary(
    project_path: Path,
    manifest: dict[str, Any],
    output_path: Path | None = None,
    open_browser: bool = False,
) -> Path:
    """Generate the project summary report.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        output_path: Optional output path
        open_browser: Whether to open in browser

    Returns:
        Path to generated report
    """
    if output_path is None:
        output_path = project_path / "reports" / "summary.html"

    interviews_data = []
    total_duration = 0.0
    interviews_map = {}

    for interview in manifest.get("interviews", []):
        duration = interview.get("duration_seconds", 0)
        total_duration += duration
        interviews_map[interview["id"]] = interview

    selections_path = project_path / "data" / "selections.json"
    selected_segments = []
    selected_duration = 0.0

    if selections_path.exists():
        selections_data = read_json(selections_path)
        selected_segments = selections_data.get("segments", [])
        selected_duration = sum(s.get("end", 0) - s.get("start", 0) for s in selected_segments)

    segment_counts: dict[str, int] = {}
    for seg in selected_segments:
        iid = seg.get("interview_id", "")
        segment_counts[iid] = segment_counts.get(iid, 0) + 1

    for interview in manifest.get("interviews", []):
        seg_count = segment_counts.get(interview["id"], 0)
        duration = interview.get("duration_seconds", 0)
        contribution = (seg_count / len(selected_segments) * 100) if selected_segments else 0

        interviews_data.append(
            {
                "id": interview["id"],
                "filename": interview.get("filename", interview["id"]),
                "duration": format_duration(duration),
                "segment_count": seg_count,
                "contribution_percent": round(contribution, 1),
            }
        )

    themes_data = []
    synthesis_path = project_path / "data" / "synthesis.json"
    if synthesis_path.exists():
        synthesis = read_json(synthesis_path)
        for theme in synthesis.get("themes", [])[:10]:
            themes_data.append(
                {
                    "name": theme.get("name", ""),
                    "size": min(3, (theme.get("segment_count", 0) // 5) + 1),
                }
            )

    arc_segments = []
    for seg in selected_segments[:20]:
        role = seg.get("role", "body").lower()
        arc_segments.append(
            {
                "role": seg.get("role", "Body"),
                "role_class": "hook"
                if role == "hook"
                else "resolution"
                if role == "resolution"
                else "body",
                "text": seg.get("text", "")[:100]
                + ("..." if len(seg.get("text", "")) > 100 else ""),
            }
        )

    highlights = []
    sorted_segments = sorted(
        selected_segments, key=lambda s: s.get("composite_score", 0), reverse=True
    )
    for seg in sorted_segments[:5]:
        interview = interviews_map.get(seg.get("interview_id", ""), {})
        highlights.append(
            {
                "score": f"{seg.get('composite_score', 0):.2f}",
                "text": seg.get("text", "")[:80],
                "filename": interview.get("filename", "Unknown"),
            }
        )

    brief_path = project_path / "brief.json"
    brief_data = {}
    if brief_path.exists():
        brief_data = read_json(brief_path)

    data = {
        "project_name": manifest.get("project_name", "Plotline Project"),
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "interview_count": len(manifest.get("interviews", [])),
        "total_source_duration": format_duration(total_duration),
        "selected_segment_count": len(selected_segments),
        "selected_duration": format_duration(selected_duration),
        "interviews": interviews_data,
        "themes": themes_data,
        "arc_segments": arc_segments,
        "highlights": highlights,
        "has_brief": bool(brief_data),
        "brief_name": brief_data.get("name", "Brief"),
        "brief_messages": brief_data.get("key_messages", [])[:5],
    }

    generator = ReportGenerator()
    result_path = generator.render("summary.html", data, output_path)

    if open_browser:
        generator.open_in_browser(result_path)

    return result_path
