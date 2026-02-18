"""Tests for plotline.export module."""

import pytest

from plotline.export.edl import generate_edl
from plotline.export.fcpxml import (
    generate_fcpxml,
    get_fcpxml_format,
    path_to_file_url,
    seconds_to_fcpxml_time,
)
from plotline.export.timecode import (
    frames_to_timecode,
    is_drop_frame_fps,
    seconds_to_timecode,
    timecode_to_frames,
    timecode_to_seconds,
)


class TestTimecode:
    def test_is_drop_frame_fps(self):
        assert is_drop_frame_fps(29.97) is True
        assert is_drop_frame_fps(23.976) is False
        assert is_drop_frame_fps(24) is False
        assert is_drop_frame_fps(25) is False
        assert is_drop_frame_fps(30) is False

    def test_seconds_to_timecode_24fps(self):
        tc = seconds_to_timecode(0, 24, drop_frame=False)
        assert tc == "00:00:00:00"

        tc = seconds_to_timecode(3600, 24, drop_frame=False)
        assert tc == "01:00:00:00"

        tc = seconds_to_timecode(65.5, 24, drop_frame=False)
        assert tc == "00:01:05:12"

    def test_seconds_to_timecode_2997_drop_frame(self):
        tc = seconds_to_timecode(0, 29.97, drop_frame=True)
        assert tc == "00:00:00;00"

        tc = seconds_to_timecode(60, 29.97, drop_frame=True)
        assert tc == "00:00:59;28"

    def test_timecode_to_seconds_24fps(self):
        assert timecode_to_seconds("00:00:00:00", 24) == 0
        assert timecode_to_seconds("01:00:00:00", 24) == 3600
        assert timecode_to_seconds("00:01:05:12", 24) == pytest.approx(65.5)

    def test_timecode_to_frames(self):
        assert timecode_to_frames("00:00:00:00", 24) == 0
        assert timecode_to_frames("00:00:01:00", 24) == 24
        assert timecode_to_frames("00:01:00:00", 24) == 1440

    def test_frames_to_timecode(self):
        assert frames_to_timecode(0, 24, drop_frame=False) == "00:00:00:00"
        assert frames_to_timecode(24, 24, drop_frame=False) == "00:00:01:00"
        assert frames_to_timecode(1440, 24, drop_frame=False) == "00:01:00:00"


class TestEDL:
    def test_generate_edl_basic(self):
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 25.0,
                "role": "hook",
                "text": "This is a test segment",
                "editorial_notes": "Good take",
            }
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "interview1.mp4",
                "source_file": "/path/to/interview1.mp4",
                "frame_rate": 24,
                "duration_seconds": 120,
            }
        }

        edl = generate_edl(
            project_name="TestProject",
            selections=selections,
            interviews=interviews,
            handle_frames=12,
        )

        assert "TITLE: Plotline Selects - TestProject" in edl
        assert "NON-DROP FRAME" in edl
        assert "int-001" in edl or "R001" in edl
        assert "FROM CLIP NAME: interview1.mp4" in edl

    def test_generate_edl_multiple_selections(self):
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "role": "hook",
            },
            {
                "segment_id": "seg-2",
                "interview_id": "int-001",
                "start": 30.0,
                "end": 45.0,
                "role": "body",
            },
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "interview1.mp4",
                "source_file": "/path/to/interview1.mp4",
                "frame_rate": 24,
                "duration_seconds": 120,
            }
        }

        edl = generate_edl(
            project_name="TestProject",
            selections=selections,
            interviews=interviews,
        )

        lines = [line for line in edl.split("\n") if line.strip() and not line.startswith("*")]
        event_lines = [line for line in lines if line[0:3].strip().isdigit()]
        assert len(event_lines) == 2

    def test_generate_edl_drop_frame(self):
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 0,
                "end": 10,
            }
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "interview1.mp4",
                "source_file": "/path/to/interview1.mp4",
                "frame_rate": 29.97,
                "duration_seconds": 120,
            }
        }

        edl = generate_edl(
            project_name="TestProject",
            selections=selections,
            interviews=interviews,
        )

        assert "DROP FRAME" in edl


class TestFCPXML:
    def test_seconds_to_fcpxml_time_24fps(self):
        time_str = seconds_to_fcpxml_time(1.0, 24)
        assert "s" in time_str

    def test_seconds_to_fcpxml_time_23976fps(self):
        time_str = seconds_to_fcpxml_time(1.0, 23.976)
        assert "s" in time_str

    def test_get_fcpxml_format_24fps(self):
        fmt = get_fcpxml_format(24)
        assert fmt["frameDuration"] == "100/2400s"
        assert "24" in fmt["name"]

    def test_get_fcpxml_format_2997fps(self):
        fmt = get_fcpxml_format(29.97)
        assert fmt["frameDuration"] == "1001/30000s"
        assert "2997" in fmt["name"]

    def test_path_to_file_url(self):
        from pathlib import Path

        url = path_to_file_url(Path("/Users/test/video.mp4"))
        assert url.startswith("file://")
        assert "video.mp4" in url

    def test_generate_fcpxml_basic(self):
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 25.0,
                "role": "hook",
                "text": "Test segment text",
                "themes": ["theme1", "theme2"],
                "delivery_label": "confident",
            }
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "interview1.mp4",
                "source_file": "/path/to/interview1.mp4",
                "frame_rate": 24,
                "duration_seconds": 120,
            }
        }

        fcpxml = generate_fcpxml(
            project_name="TestProject",
            selections=selections,
            interviews=interviews,
        )

        assert '<?xml version="1.0"' in fcpxml
        assert "fcpxml" in fcpxml
        assert "TestProject" in fcpxml
        assert "Plotline Selects" in fcpxml

    def test_generate_fcpxml_with_keywords(self):
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 0,
                "end": 10,
                "themes": ["journey", "transformation"],
            }
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "interview1.mp4",
                "source_file": "/path/to/interview1.mp4",
                "frame_rate": 24,
                "duration_seconds": 120,
            }
        }

        fcpxml = generate_fcpxml(
            project_name="TestProject",
            selections=selections,
            interviews=interviews,
        )

        assert "keyword" in fcpxml
        assert "journey" in fcpxml or "transformation" in fcpxml
