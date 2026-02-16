"""
plotline.reports.review - Selection review report.

Primary editorial interface for reviewing and approving selected segments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plotline.export.timecode import seconds_to_timecode
from plotline.project import read_json
from plotline.reports.generator import ReportGenerator


def format_duration(seconds: float) -> str:
    """Format seconds as MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def get_delivery_class(score: float) -> str:
    """Get CSS class for delivery score."""
    if score >= 0.7:
        return "filled"
    elif score >= 0.4:
        return "medium"
    return "low"


def generate_review(
    project_path: Path,
    manifest: dict[str, Any],
    output_path: Path | None = None,
    open_browser: bool = False,
) -> Path:
    """Generate the selection review report.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        output_path: Optional output path
        open_browser: Whether to open in browser

    Returns:
        Path to generated report
    """
    if output_path is None:
        output_path = project_path / "reports" / "review.html"

    selections_path = project_path / "data" / "selections.json"
    if not selections_path.exists():
        raise FileNotFoundError("No selections found. Run 'plotline arc' first.")

    selections_data = read_json(selections_path)
    all_segments = selections_data.get("segments", [])

    approvals_path = project_path / "approvals.json"
    approvals = {}
    if approvals_path.exists():
        approvals_data = read_json(approvals_path)
        approvals = {s["segment_id"]: s["status"] for s in approvals_data.get("segments", [])}

    interviews_map = {}
    for interview in manifest.get("interviews", []):
        interviews_map[interview["id"]] = interview

    segments_data = []
    total_duration = 0.0
    approved_count = 0
    rejected_count = 0
    flagged_count = 0

    for segment in all_segments:
        segment_id = segment.get("segment_id", "")
        interview_id = segment.get("interview_id", "")
        interview = interviews_map.get(interview_id, {})
        fps = interview.get("frame_rate", 24)

        start = segment.get("start", 0)
        end = segment.get("end", 0)
        duration = end - start
        total_duration += duration

        status = approvals.get(segment_id, "pending")
        if status == "approved":
            approved_count += 1
        elif status == "rejected":
            rejected_count += 1
        elif status == "flagged":
            flagged_count += 1

        delivery_score = segment.get("composite_score", 0.5)

        audio_path = None
        if interview.get("audio_full_path"):
            audio_path = f"../{interview['audio_full_path']}#t={max(0, start - 2)}"

        segments_data.append(
            {
                "id": segment_id,
                "role": segment.get("role", "body").title(),
                "text": segment.get("text", ""),
                "timecode": f"{seconds_to_timecode(start, fps)} - {seconds_to_timecode(end, fps)}",
                "start": start,
                "end": end,
                "duration": format_duration(duration),
                "themes": segment.get("themes", []),
                "delivery_score": delivery_score,
                "delivery_class": get_delivery_class(delivery_score),
                "delivery_label": segment.get("delivery_label", ""),
                "editorial_notes": segment.get("editorial_notes", ""),
                "status": status,
                "audio_path": audio_path,
            }
        )

    total_segments = len(segments_data)
    reviewed_count = approved_count + rejected_count + flagged_count
    progress_percent = (reviewed_count / total_segments * 100) if total_segments > 0 else 0

    data = {
        "project_name": manifest.get("project_name", "Plotline Project"),
        "total_segments": total_segments,
        "total_duration": format_duration(total_duration),
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "flagged_count": flagged_count,
        "progress_percent": round(progress_percent, 1),
        "segments": segments_data,
    }

    generator = ReportGenerator()
    result_path = generator.render("review.html", data, output_path)

    if open_browser:
        generator.open_in_browser(result_path)

    return result_path
