"""
plotline.reports.dashboard - Pipeline dashboard report.

Shows project status with interview grid and stage progress.
"""

from __future__ import annotations

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


def get_stage_status(stages: dict[str, bool]) -> list[dict[str, Any]]:
    """Convert stage flags to display list."""
    stage_order = [
        ("extracted", "Ext", "Extraction"),
        ("transcribed", "Trn", "Transcription"),
        ("analyzed", "Ana", "Analysis"),
        ("enriched", "Enr", "Enrichment"),
        ("themes", "Thm", "Themes"),
        ("reviewed", "Rev", "Review"),
    ]

    result = []
    for key, initial, name in stage_order:
        status = "completed" if stages.get(key, False) else "pending"
        result.append(
            {
                "key": key,
                "initial": initial,
                "name": name,
                "status": status,
            }
        )
    return result


def count_completed_stages(interviews: list[dict]) -> int:
    """Count interviews with all stages complete."""
    count = 0
    for interview in interviews:
        stages = interview.get("stages", {})
        if all(stages.get(k, False) for k in ["extracted", "transcribed", "analyzed", "enriched"]):
            count += 1
    return count


def get_selected_duration(project_path: Path) -> float:
    """Get total duration of selected segments."""
    selections_path = project_path / "data" / "selections.json"
    if not selections_path.exists():
        return 0.0

    selections = read_json(selections_path)
    segments = selections.get("segments", [])
    return sum(s.get("end", 0) - s.get("start", 0) for s in segments)


def get_segment_count(project_path: Path, interview_id: str) -> int:
    """Get segment count for an interview."""
    segments_path = project_path / "data" / "segments" / f"{interview_id}.json"
    if not segments_path.exists():
        return 0
    segments = read_json(segments_path)
    return segments.get("segment_count", len(segments.get("segments", [])))


def generate_dashboard(
    project_path: Path,
    manifest: dict[str, Any],
    output_path: Path | None = None,
    open_browser: bool = False,
) -> Path:
    """Generate the pipeline dashboard report.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        output_path: Optional output path (defaults to reports/dashboard.html)
        open_browser: Whether to open in browser

    Returns:
        Path to generated report
    """
    if output_path is None:
        output_path = project_path / "reports" / "dashboard.html"

    interviews_data = []
    total_duration = 0.0

    for interview in manifest.get("interviews", []):
        duration = interview.get("duration_seconds", 0)
        total_duration += duration

        interviews_data.append(
            {
                "id": interview["id"],
                "filename": interview.get("filename", interview["id"]),
                "duration": format_duration(duration),
                "segment_count": get_segment_count(project_path, interview["id"]),
                "stages": get_stage_status(interview.get("stages", {})),
            }
        )

    brief_path = project_path / "brief.json"
    has_brief = brief_path.exists()
    brief_data = {}
    if has_brief:
        brief_data = read_json(brief_path)

    data = {
        "project_name": manifest.get("project_name", "Plotline Project"),
        "created": manifest.get("created", "Unknown"),
        "profile": manifest.get("profile", "documentary"),
        "interview_count": len(interviews_data),
        "total_duration": format_duration(total_duration),
        "completed_stages": count_completed_stages(manifest.get("interviews", [])),
        "selected_duration": format_duration(get_selected_duration(project_path)),
        "interviews": interviews_data,
        "has_brief": has_brief,
        "brief_name": brief_data.get("name", "Brief"),
        "brief_summary": brief_data.get("summary", ""),
    }

    generator = ReportGenerator()
    result_path = generator.render("dashboard.html", data, output_path)

    if open_browser:
        generator.open_in_browser(result_path)

    return result_path
