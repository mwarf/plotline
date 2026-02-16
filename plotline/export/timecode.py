"""
plotline.export.timecode - Timecode math utilities.

Handles conversion between seconds and timecodes, including drop-frame
and non-drop-frame formats for various frame rates.
"""

from __future__ import annotations


def seconds_to_ndf_timecode(seconds: float, fps: float) -> str:
    """Convert float seconds to non-drop-frame timecode.

    Args:
        seconds: Time in seconds
        fps: Frames per second (23.976, 24, 25, 30, etc.)

    Returns:
        Timecode string in HH:MM:SS:FF format
    """
    total_frames = round(seconds * fps)
    frames_per_second = round(fps)

    ff = total_frames % frames_per_second
    total_seconds = total_frames // frames_per_second
    ss = total_seconds % 60
    mm = (total_seconds // 60) % 60
    hh = total_seconds // 3600

    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def seconds_to_df_timecode(seconds: float) -> str:
    """Convert float seconds to 29.97 drop-frame timecode.

    Drop-frame skips frame numbers :00 and :01 at every minute mark
    except every 10th minute (00, 10, 20, 30, 40, 50).

    Args:
        seconds: Time in seconds

    Returns:
        Timecode string in HH:MM:SS;FF format (semicolon indicates drop-frame)
    """
    fps = 29.97
    frame_count = round(seconds * fps)

    d = frame_count // 17982
    m = frame_count % 17982

    if m < 2:
        adjustment = 0
    else:
        adjustment = 2 * ((m - 2) // 1798)

    adjusted_frames = frame_count + 18 * d + adjustment

    ff = adjusted_frames % 30
    ss = (adjusted_frames // 30) % 60
    mm = (adjusted_frames // 1800) % 60
    hh = adjusted_frames // 108000

    return f"{hh:02d}:{mm:02d}:{ss:02d};{ff:02d}"


def seconds_to_timecode(seconds: float, fps: float, drop_frame: bool = False) -> str:
    """Convert seconds to timecode based on frame rate.

    Args:
        seconds: Time in seconds
        fps: Frames per second
        drop_frame: Whether to use drop-frame (for 29.97fps)

    Returns:
        Timecode string
    """
    if drop_frame and abs(fps - 29.97) < 0.01:
        return seconds_to_df_timecode(seconds)
    return seconds_to_ndf_timecode(seconds, fps)


def ndf_timecode_to_seconds(timecode: str, fps: float) -> float:
    """Convert non-drop-frame timecode to seconds.

    Args:
        timecode: Timecode string in HH:MM:SS:FF format
        fps: Frames per second

    Returns:
        Time in seconds
    """
    parts = timecode.replace(";", ":").split(":")
    hh, mm, ss, ff = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])

    total_frames = (hh * 3600 + mm * 60 + ss) * round(fps) + ff
    return total_frames / fps


def df_timecode_to_seconds(timecode: str) -> float:
    """Convert 29.97 drop-frame timecode to seconds.

    Args:
        timecode: Timecode string in HH:MM:SS;FF format

    Returns:
        Time in seconds
    """
    parts = timecode.replace(":", ";").split(";")
    hh, mm, ss, ff = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])

    total_frames = hh * 108000 + mm * 1800 + ss * 30 + ff - 2 * (mm - mm // 10)

    return total_frames / 29.97


def timecode_to_seconds(timecode: str, fps: float) -> float:
    """Convert timecode to seconds, auto-detecting drop-frame.

    Args:
        timecode: Timecode string
        fps: Frames per second

    Returns:
        Time in seconds
    """
    is_drop_frame = ";" in timecode

    if is_drop_frame:
        return df_timecode_to_seconds(timecode)
    return ndf_timecode_to_seconds(timecode, fps)


def is_drop_frame_fps(fps: float) -> bool:
    """Check if frame rate requires drop-frame timecode.

    Args:
        fps: Frames per second

    Returns:
        True if drop-frame should be used
    """
    return abs(fps - 29.97) < 0.01


def frames_to_timecode(total_frames: int, fps: float, drop_frame: bool = False) -> str:
    """Convert frame count to timecode.

    Args:
        total_frames: Total number of frames
        fps: Frames per second
        drop_frame: Whether to use drop-frame

    Returns:
        Timecode string
    """
    seconds = total_frames / fps
    return seconds_to_timecode(seconds, fps, drop_frame)


def timecode_to_frames(timecode: str, fps: float) -> int:
    """Convert timecode to frame count.

    Args:
        timecode: Timecode string
        fps: Frames per second

    Returns:
        Frame count
    """
    seconds = timecode_to_seconds(timecode, fps)
    return round(seconds * fps)
