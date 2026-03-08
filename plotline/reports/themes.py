"""
plotline.reports.themes - Theme Explorer report.

Interactive HTML report for exploring segments grouped by theme,
with filtering, sorting, search, and cross-interview unified theme views.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plotline.export.timecode import seconds_to_timecode
from plotline.io import read_json
from plotline.reports.generator import ReportGenerator
from plotline.utils import format_duration, get_delivery_class, THEME_COLORS, get_theme_color


def _build_segment_lookup(
    project_path: Path,
    manifest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build a lookup dict from segment_id -> segment data with interview context."""
    lookup: dict[str, dict[str, Any]] = {}
    interviews_map = {i["id"]: i for i in manifest.get("interviews", [])}

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]
        segments_path = project_path / "data" / "segments" / f"{interview_id}.json"
        if not segments_path.exists():
            continue

        segments_data = read_json(segments_path)
        fps = interview.get("frame_rate", 24)

        for seg in segments_data.get("segments", []):
            seg_id = seg.get("segment_id", "")
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            delivery = seg.get("delivery", {})
            delivery_score = delivery.get("composite_score", 0.5)

            audio_path = None
            if interview.get("audio_full_path"):
                audio_path = f"../{interview['audio_full_path']}#t={max(0, start - 2)}"

            lookup[seg_id] = {
                "id": seg_id,
                "text": seg.get("text", ""),
                "timecode": (
                    f"{seconds_to_timecode(start, fps)} → {seconds_to_timecode(end, fps)}"
                ),
                "start": start,
                "end": end,
                "duration": format_duration(end - start),
                "interview_id": interview_id,
                "interview_filename": interview.get("filename", interview_id),
                "delivery_score": round(delivery_score, 2),
                "delivery_class": get_delivery_class(delivery_score),
                "delivery_label": delivery.get("delivery_label", ""),
                "audio_path": audio_path,
                "themes": [],
                "theme_colors": [],
            }

    return lookup


def generate_themes_report(
    project_path: Path,
    manifest: dict[str, Any],
    output_path: Path | None = None,
    open_browser: bool = False,
) -> Path:
    """Generate the theme explorer report.

    Uses synthesis.json unified themes when available (cross-interview),
    falls back to raw per-interview themes otherwise.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        output_path: Optional output path (defaults to reports/themes.html)
        open_browser: Whether to open in browser

    Returns:
        Path to generated report

    Raises:
        FileNotFoundError: If no theme data exists
    """
    if output_path is None:
        output_path = project_path / "reports" / "themes.html"

    # Build segment lookup from all interviews
    segment_lookup = _build_segment_lookup(project_path, manifest)

    # Determine theme source: synthesis (preferred) or per-interview
    synthesis_path = project_path / "data" / "synthesis.json"
    themes_dir = project_path / "data" / "themes"

    use_synthesis = synthesis_path.exists()
    has_per_interview = themes_dir.exists() and any(themes_dir.glob("*.json"))

    if not use_synthesis and not has_per_interview:
        raise FileNotFoundError("No theme data found. Run 'plotline themes' first.")

    themes_list: list[dict[str, Any]] = []
    intersections: list[dict[str, Any]] = []
    all_theme_segment_ids: dict[str, list[str]] = {}  # theme_name -> [seg_ids]

    if use_synthesis:
        synthesis = read_json(synthesis_path)
        for i, utheme in enumerate(synthesis.get("unified_themes", [])):
            name = utheme.get("name", f"Theme {i + 1}")
            seg_ids = utheme.get("all_segment_ids", [])
            color = get_theme_color(i)

            themes_list.append(
                {
                    "id": utheme.get("unified_theme_id", f"utheme_{i + 1:03d}"),
                    "name": name,
                    "description": utheme.get("description", ""),
                    "strength": 0.8,  # Synthesis doesn't have per-theme strength
                    "emotional_character": utheme.get("perspectives", ""),
                    "segment_count": len(seg_ids),
                    "segment_ids": seg_ids,
                    "color": color,
                    "source_count": len(utheme.get("source_themes", [])),
                }
            )
            all_theme_segment_ids[name] = seg_ids

            # Tag segments with this theme
            for seg_id in seg_ids:
                if seg_id in segment_lookup:
                    segment_lookup[seg_id]["themes"].append(name)
                    segment_lookup[seg_id]["theme_colors"].append(color)
    else:
        # Fall back to per-interview themes
        theme_index = 0
        for theme_file in sorted(themes_dir.glob("*.json")):
            theme_data = read_json(theme_file)
            for theme in theme_data.get("themes", []):
                name = theme.get("name", f"Theme {theme_index + 1}")
                seg_ids = theme.get("segment_ids", [])
                color = get_theme_color(theme_index)

                themes_list.append(
                    {
                        "id": theme.get("theme_id", f"theme_{theme_index + 1:03d}"),
                        "name": name,
                        "description": theme.get("description", ""),
                        "strength": theme.get("strength", 0.5),
                        "emotional_character": theme.get("emotional_character", ""),
                        "segment_count": len(seg_ids),
                        "segment_ids": seg_ids,
                        "color": color,
                        "source_count": 1,
                    }
                )
                all_theme_segment_ids[name] = seg_ids

                for seg_id in seg_ids:
                    if seg_id in segment_lookup:
                        segment_lookup[seg_id]["themes"].append(name)
                        segment_lookup[seg_id]["theme_colors"].append(color)

                theme_index += 1

        # Collect intersections from per-interview theme files
        for theme_file in sorted(themes_dir.glob("*.json")):
            theme_data = read_json(theme_file)
            for intersection in theme_data.get("intersections", []):
                seg_id = intersection.get("segment_id", "")
                if seg_id in segment_lookup:
                    intersections.append(
                        {
                            "segment_id": seg_id,
                            "theme_ids": intersection.get("themes", []),
                            "note": intersection.get("note", ""),
                            "segment": segment_lookup[seg_id],
                        }
                    )

    # Find intersection segments (in 2+ themes) if not already collected
    if use_synthesis or not intersections:
        for seg_id, seg_data in segment_lookup.items():
            if len(seg_data["themes"]) >= 2:
                intersections.append(
                    {
                        "segment_id": seg_id,
                        "theme_names": seg_data["themes"],
                        "note": "",
                        "segment": seg_data,
                    }
                )

    # Sort themes by segment count (largest first)
    themes_list.sort(key=lambda t: t["segment_count"], reverse=True)

    # Build flat segments list (only those assigned to at least one theme)
    themed_segments = [seg for seg in segment_lookup.values() if len(seg["themes"]) > 0]
    themed_segments.sort(key=lambda s: s["delivery_score"], reverse=True)

    # Interview list for filter
    interview_ids = sorted(set(s["interview_id"] for s in themed_segments))
    interviews = [
        {
            "id": iid,
            "filename": next(
                (i.get("filename", iid) for i in manifest.get("interviews", []) if i["id"] == iid),
                iid,
            ),
        }
        for iid in interview_ids
    ]

    data = {
        "project_name": manifest.get("project_name", "Plotline Project"),
        "themes": themes_list,
        "segments": themed_segments,
        "intersections": intersections,
        "interviews": interviews,
        "total_themes": len(themes_list),
        "total_segments": len(themed_segments),
        "total_intersections": len(intersections),
        "has_synthesis": use_synthesis,
    }

    generator = ReportGenerator()
    result_path = generator.render("themes.html", data, output_path, manifest=manifest)

    if open_browser:
        generator.open_in_browser(result_path)

    return result_path
