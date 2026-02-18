"""
plotline.reports.compare - Best-take comparison report.

Generates an interactive HTML report for comparing best takes across interviews.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plotline.compare import run_compare
from plotline.export.timecode import seconds_to_timecode
from plotline.reports.generator import ReportGenerator


def format_duration(seconds: float) -> str:
    """Format seconds as MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def generate_compare_report(
    project_path: Path,
    manifest: dict[str, Any],
    config: Any,
    message_filter: str | None = None,
    output_path: Path | None = None,
    open_browser: bool = False,
) -> Path:
    """Generate the best-take comparison report.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        config: Resolved PlotlineConfig
        message_filter: Optional filter for specific key message
        output_path: Optional output path
        open_browser: Whether to open in browser

    Returns:
        Path to generated report
    """
    if output_path is None:
        output_path = project_path / "reports" / "compare.html"

    compare_data = run_compare(
        project_path=project_path,
        manifest=manifest,
        config=config,
        message_filter=message_filter,
    )

    groups_data = []
    for group in compare_data.get("groups", []):
        candidates_data = []
        for candidate in group.get("candidates", []):
            fps = candidate.get("frame_rate", 24)
            start = candidate.get("start", 0)
            end = candidate.get("end", 0)

            candidates_data.append(
                {
                    "segment_id": candidate.get("segment_id", ""),
                    "interview_id": candidate.get("interview_id", ""),
                    "text": candidate.get("text", ""),
                    "timecode": (
                        f"{seconds_to_timecode(start, fps)} - {seconds_to_timecode(end, fps)}"
                    ),
                    "duration": format_duration(candidate.get("duration", 0)),
                    "rank": candidate.get("rank", 0),
                    "composite_score": candidate.get("composite_score", 0),
                    "cross_score": candidate.get("cross_score", 0),
                    "content_alignment": candidate.get("content_alignment"),
                    "conciseness_score": candidate.get("conciseness_score"),
                    "reasoning": candidate.get("reasoning", ""),
                    "delivery_label": candidate.get("delivery_label", ""),
                    "delivery_class": candidate.get("delivery_class", "medium"),
                    "audio_path": candidate.get("audio_path"),
                    "is_best": candidate.get("rank") == 1,
                }
            )

        groups_data.append(
            {
                "topic": group.get("topic", ""),
                "brief_message": group.get("brief_message"),
                "perspectives": group.get("perspectives", ""),
                "source_theme_count": group.get("source_theme_count", 0),
                "candidates": candidates_data,
                "candidate_count": len(candidates_data),
            }
        )

    key_messages = []
    brief_path = project_path / "brief.json"
    if brief_path.exists():
        from plotline.project import read_json

        brief = read_json(brief_path)
        key_messages = brief.get("key_messages", [])

    data = {
        "project_name": compare_data.get("project_name", "Plotline Project"),
        "groups": groups_data,
        "total_groups": len(groups_data),
        "total_candidates": sum(g["candidate_count"] for g in groups_data),
        "interview_count": compare_data.get("interview_count", 0),
        "has_brief": compare_data.get("has_brief", False),
        "key_messages": key_messages,
        "message_filter": message_filter,
    }

    generator = ReportGenerator()
    result_path = generator.render("compare.html", data, output_path)

    if open_browser:
        generator.open_in_browser(result_path)

    return result_path
