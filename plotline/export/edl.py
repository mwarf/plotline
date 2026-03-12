"""
plotline.export.edl - CMX 3600 EDL generator.

Generates Edit Decision List files for import into DaVinci Resolve,
Premiere Pro, and other NLEs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from plotline.export.timecode import is_drop_frame_fps, seconds_to_timecode


def _make_reel_name(filename: str, used: set[str], counter: int) -> str:
    """Derive a unique 8-char CMX 3600 reel name from a source filename.

    Uses first 8 alphanumeric chars of the filename stem. On collision,
    tries stem[:7] + single digit, then stem[:6] + 2-digit counter.

    Args:
        filename: Source video filename (e.g. "A_0005C909H260226_CANON.MP4")
        used: Set of reel names already assigned
        counter: Fallback counter for degenerate cases

    Returns:
        Unique 8-character reel name
    """
    stem = Path(filename).stem
    clean = re.sub(r"[^A-Za-z0-9_]", "", stem)
    if not clean:
        clean = f"Reel{counter:04d}"

    candidate = clean[:8]
    if candidate not in used:
        return candidate

    # Collision — try stem[:7] + single digit
    for i in range(1, 10):
        candidate = f"{clean[:7]}{i}"
        if candidate not in used:
            return candidate

    # Try stem[:6] + 2-digit counter
    for i in range(10, 100):
        candidate = f"{clean[:6]}{i:02d}"[:8]
        if candidate not in used:
            return candidate

    # Ultimate fallback
    return f"R{counter:07d}"[:8]


def generate_edl(
    project_name: str,
    selections: list[dict[str, Any]],
    interviews: dict[str, dict[str, Any]],
    handle_frames: int = 12,
) -> str:
    """Generate a CMX 3600 EDL from approved selections.

    Args:
        project_name: Project name for EDL title
        selections: List of approved segment selections
        interviews: Dict mapping interview_id to interview metadata
        handle_frames: Extra frames before/after each clip (default 12)

    Returns:
        EDL content as string
    """
    lines = []

    # Collect all frame rates from selections, pick the most common for record track
    fps_counts: dict[float, int] = {}
    drop_frame = False
    for sel in selections:
        interview = interviews.get(sel.get("interview_id", ""), {})
        sel_fps = interview.get("frame_rate", 24)
        fps_counts[sel_fps] = fps_counts.get(sel_fps, 0) + 1
        if is_drop_frame_fps(sel_fps):
            drop_frame = True

    if fps_counts:
        fps = max(fps_counts, key=lambda f: fps_counts[f])
    else:
        fps = 24

    fcm = "DROP FRAME" if drop_frame else "NON-DROP FRAME"
    lines.append(f"TITLE: Plotline Selects - {project_name}")
    lines.append(f"FCM: {fcm}")
    lines.append("")

    if len(fps_counts) > 1:
        rates = ", ".join(str(r) for r in sorted(fps_counts))
        lines.append(
            f"* WARNING: Mixed frame rates detected ({rates}). Record track uses {fps}fps."
        )
        lines.append("")

    reel_mapping: dict[str, str] = {}
    used_reels: set[str] = set()
    reel_counter = 1
    for sel in selections:
        interview_id = sel.get("interview_id", "")
        if interview_id not in reel_mapping:
            interview = interviews.get(interview_id, {})
            reel_name = _make_reel_name(
                interview.get("filename", interview_id), used_reels, reel_counter
            )
            reel_mapping[interview_id] = reel_name
            used_reels.add(reel_name)
            reel_counter += 1

    if len(reel_mapping) > 1:
        lines.append("* REEL MAPPING:")
        for interview_id, reel_name in reel_mapping.items():
            interview = interviews.get(interview_id, {})
            filename = interview.get("filename", interview_id)
            lines.append(f"* {reel_name} = {filename}")
        lines.append("")

    rec_frame_counter = 3600 * fps

    for i, sel in enumerate(selections, 1):
        interview_id = sel.get("interview_id", "")
        interview = interviews.get(interview_id, {})

        reel = reel_mapping.get(interview_id, "R001")
        interview_fps = interview.get("frame_rate", fps)
        interview_drop = is_drop_frame_fps(interview_fps)

        src_start = sel.get("start", 0)
        src_end = sel.get("end", 0)

        default_handle_sec = handle_frames / interview_fps
        pause_before = sel.get("pause_before_sec")
        pause_after = sel.get("pause_after_sec")
        if pause_before is not None and pause_before > 0:
            smart_handle_in = min(default_handle_sec, pause_before * 0.8)
        elif pause_before is None:
            smart_handle_in = default_handle_sec
        else:
            smart_handle_in = 0.0
        if pause_after is not None and pause_after > 0:
            smart_handle_out = min(default_handle_sec, pause_after * 0.8)
        elif pause_after is None:
            smart_handle_out = default_handle_sec
        else:
            smart_handle_out = 0.0
        padded_start = max(0, src_start - smart_handle_in)
        interview_duration = interview.get("duration_seconds")
        padded_end = src_end + smart_handle_out
        if interview_duration is not None:
            padded_end = min(interview_duration, padded_end)

        source_tc_offset = interview.get("start_timecode")
        if source_tc_offset:
            from plotline.export.timecode import timecode_to_seconds

            offset_seconds = timecode_to_seconds(source_tc_offset, interview_fps)
        else:
            offset_seconds = 0

        absolute_start = offset_seconds + padded_start
        absolute_end = offset_seconds + padded_end

        src_in_tc = seconds_to_timecode(absolute_start, interview_fps, interview_drop)
        src_out_tc = seconds_to_timecode(absolute_end, interview_fps, interview_drop)

        clip_duration_frames = round((padded_end - padded_start) * fps)
        rec_in_tc = seconds_to_timecode(rec_frame_counter / fps, fps, drop_frame)
        rec_out_frame = rec_frame_counter + clip_duration_frames
        rec_out_tc = seconds_to_timecode(rec_out_frame / fps, fps, drop_frame)
        rec_frame_counter = rec_out_frame

        event_line = (
            f"{i:03d}  {reel:<8s} V     C    {src_in_tc} {src_out_tc} {rec_in_tc} {rec_out_tc}"
        )
        lines.append(event_line)

        audio_line_1 = (
            f"{i:03d}  {reel:<8s} A1    C    {src_in_tc} {src_out_tc} {rec_in_tc} {rec_out_tc}"
        )
        audio_line_2 = (
            f"{i:03d}  {reel:<8s} A2    C    {src_in_tc} {src_out_tc} {rec_in_tc} {rec_out_tc}"
        )
        lines.append(audio_line_1)
        lines.append(audio_line_2)

        filename = interview.get("filename", "unknown.mov")
        lines.append(f"* FROM CLIP NAME: {filename}")
        lines.append(f"* SOURCE FILE: {filename}")

        speaker = sel.get("speaker")
        if speaker:
            lines.append(f"* SPEAKER: {speaker}")

        role = sel.get("role", "")
        editorial_notes = sel.get("editorial_notes", "")
        user_notes = sel.get("user_notes", "")
        notes_parts = []
        if editorial_notes:
            notes_parts.append(editorial_notes)
        if user_notes:
            notes_parts.append(f"Note: {user_notes}")
        notes = " | ".join(notes_parts)
        if role or notes:
            comment = f"[{role}] {notes}" if role else notes
            max_comment_len = 200
            if len(comment) > max_comment_len:
                lines.append(f"* COMMENT: {comment[: max_comment_len - 3]}...")
            else:
                lines.append(f"* COMMENT: {comment}")

        lines.append("")

    return "\n".join(lines)


def generate_edl_from_project(
    project_path: Path,
    manifest: dict[str, Any],
    handle_frames: int = 12,
    use_approvals: bool = True,
) -> str:
    """Generate EDL from project data.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        handle_frames: Handle padding in frames
        use_approvals: Whether to filter by approval status

    Returns:
        EDL content as string
    """
    from plotline.io import read_json

    data_dir = project_path / "data"
    selections_path = data_dir / "selections.json"
    approvals_path = project_path / "approvals.json"

    if not selections_path.exists():
        raise FileNotFoundError("No selections found. Run 'plotline arc' first.")

    selections_data = read_json(selections_path)
    all_selections = selections_data.get("segments", [])

    if use_approvals and approvals_path.exists():
        approvals = read_json(approvals_path)
        approved_ids = {
            s["segment_id"] for s in approvals.get("segments", []) if s.get("status") == "approved"
        }
        user_notes_by_id = {
            s["segment_id"]: s.get("user_notes")
            for s in approvals.get("segments", [])
            if s.get("segment_id") and s.get("user_notes")
        }
        selections = []
        for s in all_selections:
            if s["segment_id"] not in approved_ids:
                continue
            sel = dict(s)  # shallow copy — prevents mutating the parsed JSON dicts
            if sel.get("segment_id") in user_notes_by_id:
                sel["user_notes"] = user_notes_by_id[sel["segment_id"]]
            selections.append(sel)
    else:
        selections = list(all_selections)  # copy so sort below doesn't mutate source

    if not selections:
        raise ValueError("No approved selections to export")

    selections.sort(key=lambda s: s.get("position", 0))

    interviews = {}
    for interview in manifest.get("interviews", []):
        interview_copy = dict(interview)
        source_file = interview_copy.get("source_file", "")
        if source_file:
            source_path = Path(source_file)
            if not source_path.is_absolute():
                source_path = project_path / source_file
            interview_copy["source_file"] = str(source_path)
        interviews[interview["id"]] = interview_copy

    return generate_edl(
        project_name=manifest.get("project_name", "plotline"),
        selections=selections,
        interviews=interviews,
        handle_frames=handle_frames,
    )


def generate_alternates_edl_from_project(
    project_path: Path,
    manifest: dict[str, Any],
    handle_frames: int = 12,
) -> str | None:
    """Generate EDL of alternate candidates from arc.json.

    Creates a secondary timeline where alternates are grouped by their
    for_position, allowing editors to easily swap takes in the NLE.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        handle_frames: Handle padding in frames

    Returns:
        EDL content as string, or None if no alternates exist
    """
    from plotline.io import read_json

    data_dir = project_path / "data"
    arc_path = data_dir / "arc.json"
    segments_dir = data_dir / "segments"

    if not arc_path.exists():
        return None

    arc = read_json(arc_path)
    alternates = arc.get("alternate_candidates", [])

    if not alternates:
        return None

    if not segments_dir.exists():
        raise FileNotFoundError(
            f"segments_dir not found: {segments_dir}. "
            "Run stage 2 (transcribe) before generating alternates EDL."
        )

    all_segments = []
    for seg_file in segments_dir.glob("*.json"):
        seg_data = read_json(seg_file)
        all_segments.extend(seg_data.get("segments", []))

    segments_by_id = {s.get("segment_id"): s for s in all_segments if s.get("segment_id")}

    alternate_selections = []
    for alt in alternates:
        seg_id = alt.get("segment_id")
        if not seg_id:
            continue
        source_seg = segments_by_id.get(seg_id)
        if not source_seg:
            continue

        delivery = source_seg.get("delivery", {})
        raw_delivery = delivery.get("raw", {})

        alternate_selections.append(
            {
                "segment_id": seg_id,
                "interview_id": source_seg.get("interview_id", ""),
                "position": alt.get("for_position", 0),
                "start": source_seg.get("start", 0),
                "end": source_seg.get("end", 0),
                "text": source_seg.get("text", ""),
                "speaker": source_seg.get("speaker"),
                "role": f"ALT for pos {alt.get('for_position', '?')}",
                "themes": [],
                "composite_score": delivery.get("composite_score", 0),
                "delivery_label": delivery.get("delivery_label", ""),
                "pause_before_sec": raw_delivery.get("pause_before_sec", 0),
                "pause_after_sec": raw_delivery.get("pause_after_sec", 0),
                "editorial_notes": alt.get("reasoning", ""),
            }
        )

    if not alternate_selections:
        return None

    alternate_selections.sort(key=lambda s: (s["position"], s["start"]))

    interviews = {}
    for interview in manifest.get("interviews", []):
        interviews[interview["id"]] = interview

    return generate_edl(
        project_name=f"{manifest.get('project_name', 'plotline')}_alternates",
        selections=alternate_selections,
        interviews=interviews,
        handle_frames=handle_frames,
    )
