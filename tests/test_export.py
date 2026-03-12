"""Tests for plotline.export module."""

import pytest

from plotline.export.edl import _make_reel_name, generate_edl
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

    def test_df_timecode_round_trip_1_hour(self):
        """Verify drop-frame round-trip at 1 hour boundary is frame-accurate."""
        # 01:00:00;00 should convert to ~3600 seconds
        secs = timecode_to_seconds("01:00:00;00", 29.97)
        assert secs == pytest.approx(3600, abs=0.04)  # Within ~1 frame

        # And converting 3600s to timecode should give 01:00:00;00
        tc = seconds_to_timecode(3600, 29.97, drop_frame=True)
        assert tc == "01:00:00;00"

    def test_df_timecode_round_trip_2_hours(self):
        """Verify drop-frame round-trip at 2 hour boundary."""
        secs = timecode_to_seconds("02:00:00;00", 29.97)
        assert secs == pytest.approx(7200, abs=0.04)

        tc = seconds_to_timecode(7200, 29.97, drop_frame=True)
        assert tc == "02:00:00;00"

    def test_df_timecode_10_minutes(self):
        """Verify 10-minute boundary (no frame drop at 10th minute)."""
        secs = timecode_to_seconds("00:10:00;00", 29.97)
        assert secs == pytest.approx(600, abs=0.04)

        tc = seconds_to_timecode(600, 29.97, drop_frame=True)
        assert tc == "00:10:00;00"

    def test_df_source_timecode_offset_accuracy(self):
        """Simulate EDL export with DF start_timecode — the critical real-world scenario."""
        # Camera starts recording at 01:00:00;00
        # Segment is 10 seconds into the video
        offset = timecode_to_seconds("01:00:00;00", 29.97)
        absolute = offset + 10.0
        src_tc = seconds_to_timecode(absolute, 29.97, True)
        # Must produce 01:00:10;00, not 01:00:13;18 (the old buggy result)
        assert src_tc == "01:00:10;00"

    def test_ndf_23976_frame_accurate(self):
        """Verify 23.976 NDF timecodes are frame-accurate at key boundaries."""
        # Frame 24 at 23.976fps occurs at exactly 1001/24000 * 24 = 1.001 seconds
        tc = seconds_to_timecode(24 * 1001 / 24000, 23.976, drop_frame=False)
        assert tc == "00:00:01:00"

        # Frame 86400 = 1 hour of 24fps display = 3603.6 seconds at 23.976fps
        tc = seconds_to_timecode(86400 * 1001 / 24000, 23.976, drop_frame=False)
        assert tc == "01:00:00:00"


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
        # Reel name derived from filename stem "interview1" → "intervie"
        assert "intervie" in edl
        assert "FROM CLIP NAME: interview1.mp4" in edl
        assert "SOURCE FILE: interview1.mp4" in edl

    def test_generate_edl_includes_speaker_comment(self):
        """Test that EDL includes speaker comment when present."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 25.0,
                "role": "hook",
                "text": "Test segment",
                "speaker": "SPEAKER_00",
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
        )

        assert "* SPEAKER: SPEAKER_00" in edl

    def test_generate_edl_no_speaker_when_none(self):
        """Test that EDL omits speaker comment when not present."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 25.0,
                "role": "hook",
                "text": "Test segment",
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
        )

        assert "* SPEAKER:" not in edl

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
        # Each event produces 3 lines: V, A1, A2 (standard CMX 3600)
        event_lines = [line for line in lines if line[0:3].strip().isdigit()]
        assert len(event_lines) == 6  # 2 events * 3 tracks (V, A1, A2)
        # Verify 2 distinct event numbers
        video_lines = [line for line in event_lines if " V " in line]
        assert len(video_lines) == 2

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

    def test_generate_edl_unique_reel_names_per_source(self):
        """Different source files get distinct reel names, not all 'intervie'."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 5.0, "end": 15.0},
            {"segment_id": "seg-2", "interview_id": "int-002", "start": 10.0, "end": 20.0},
            {"segment_id": "seg-3", "interview_id": "int-003", "start": 8.0, "end": 18.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "A_0005C909H260226_131506PT_CANON.MP4",
                "frame_rate": 24,
                "duration_seconds": 600,
            },
            "int-002": {
                "id": "int-002",
                "filename": "A_0005D016H260227_094701PX_CANON.MP4",
                "frame_rate": 24,
                "duration_seconds": 600,
            },
            "int-003": {
                "id": "int-003",
                "filename": "A_0004C596H260225_0835138I_CANON.MP4",
                "frame_rate": 24,
                "duration_seconds": 600,
            },
        }

        edl = generate_edl("TestProject", selections, interviews, handle_frames=12)

        # Extract reel names from video event lines (positions 5-13 in CMX 3600)
        event_lines = [
            line
            for line in edl.split("\n")
            if line.strip() and line[:3].strip().isdigit() and " V " in line
        ]
        reel_names = [line[5:13].strip() for line in event_lines]
        assert len(reel_names) == 3
        # All three must be unique
        assert len(set(reel_names)) == 3, f"Reel names should be unique but got: {reel_names}"

    def test_generate_edl_collision_resolution(self):
        """Files with similar names get distinct reels via collision counter."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 0, "end": 10.0},
            {"segment_id": "seg-2", "interview_id": "int-002", "start": 0, "end": 10.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "A_0005C909_CANON.MP4",
                "frame_rate": 24,
                "duration_seconds": 60,
            },
            "int-002": {
                "id": "int-002",
                "filename": "A_0005C905_CANON.MP4",
                "frame_rate": 24,
                "duration_seconds": 60,
            },
        }

        edl = generate_edl("TestProject", selections, interviews, handle_frames=0)

        event_lines = [
            line
            for line in edl.split("\n")
            if line.strip() and line[:3].strip().isdigit() and " V " in line
        ]
        reel_names = [line[5:13].strip() for line in event_lines]
        assert len(reel_names) == 2
        assert len(set(reel_names)) == 2, f"Collision not resolved: {reel_names}"
        # Both SOURCE FILE comments present
        assert "SOURCE FILE: A_0005C909_CANON.MP4" in edl
        assert "SOURCE FILE: A_0005C905_CANON.MP4" in edl

    def test_generate_edl_source_file_comment(self):
        """Every event includes both FROM CLIP NAME and SOURCE FILE."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 0, "end": 10.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "my_video.mov",
                "frame_rate": 24,
                "duration_seconds": 60,
            },
        }

        edl = generate_edl("TestProject", selections, interviews)

        assert "* FROM CLIP NAME: my_video.mov" in edl
        assert "* SOURCE FILE: my_video.mov" in edl


class TestMakeReelName:
    def test_basic_filename(self):
        assert _make_reel_name("interview1.mp4", set(), 1) == "intervie"

    def test_short_filename(self):
        assert _make_reel_name("clip.mp4", set(), 1) == "clip"

    def test_exactly_8_chars(self):
        assert _make_reel_name("12345678.mp4", set(), 1) == "12345678"

    def test_collision_resolved(self):
        used = {"A_0005C9"}
        result = _make_reel_name("A_0005C905_CANON.MP4", used, 2)
        assert result != "A_0005C9"
        assert len(result) <= 8
        assert result not in used

    def test_multiple_collisions(self):
        used = {"A_0005C9", "A_0005C1", "A_0005C2"}
        result = _make_reel_name("A_0005C999_CANON.MP4", used, 4)
        assert result not in used
        assert len(result) <= 8

    def test_empty_stem_fallback(self):
        result = _make_reel_name(".mp4", set(), 3)
        assert len(result) <= 8
        assert len(result) > 0

    def test_special_characters_stripped(self):
        result = _make_reel_name("my-clip (final).mp4", set(), 1)
        # Hyphens, parens, spaces stripped; only alnum + underscore kept
        assert result == "myclipfi"

    def test_real_canon_filenames_unique(self):
        """Real-world Canon filenames from the Homes4Hope project get unique reels."""
        filenames = [
            "A_0005C909H260226_131506PT_CANON.MP4",
            "A_0005D016H260227_094701PX_CANON.MP4",
            "A_0004C596H260225_0835138I_CANON.MP4",
            "A_0005D037H260227_103120KF_CANON.MP4",
            "A_0005C905H260226_121205ZK_CANON.MP4",
            "A_0005D058H260227_120126C2_CANON.MP4",
        ]
        used: set[str] = set()
        reels = []
        for i, fn in enumerate(filenames, 1):
            reel = _make_reel_name(fn, used, i)
            reels.append(reel)
            used.add(reel)

        assert len(set(reels)) == 6, f"Expected 6 unique reels, got {reels}"
        for reel in reels:
            assert len(reel) <= 8, f"Reel '{reel}' exceeds 8 chars"


class TestEDLCompliance:
    """Tests for CMX 3600 spec compliance and parity with client-side JS."""

    def test_cmx3600_field_widths(self):
        """Verify event lines have correct CMX 3600 field layout."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 10.0, "end": 25.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "clip.mp4",
                "frame_rate": 24,
                "duration_seconds": 120,
            },
        }

        edl = generate_edl("Test", selections, interviews, handle_frames=12)
        event_lines = [
            line for line in edl.split("\n") if line.strip() and line[:3].strip().isdigit()
        ]
        assert len(event_lines) == 3  # V, A1, A2

        for line in event_lines:
            # Event number: 3 chars, positions 0-2
            event_num = line[0:3]
            assert event_num.strip().isdigit(), f"Event number not numeric: '{event_num}'"
            # Two spaces after event number
            assert line[3:5] == "  ", f"Missing double-space after event num: '{line[3:5]}'"
            # Reel name: 8 chars, positions 5-12
            reel = line[5:13]
            assert len(reel) == 8, f"Reel field not 8 chars: '{reel}'"
            # Space then track type
            assert line[13] == " ", f"Missing space after reel: '{line[13]}'"
            # Track type field ends before "C" (cut transition)
            assert "C    " in line, "Missing cut transition marker"
            # Timecodes are present (4 of them, 11 chars each: HH:MM:SS:FF)
            import re

            timecodes = re.findall(r"\d{2}:\d{2}:\d{2}[:;]\d{2}", line)
            assert len(timecodes) == 4, f"Expected 4 timecodes, found {len(timecodes)} in: {line}"

    def test_mixed_fps_warning(self):
        """Mixed frame rate projects include a warning comment."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 0, "end": 10.0},
            {"segment_id": "seg-2", "interview_id": "int-002", "start": 0, "end": 10.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "clip24.mp4",
                "frame_rate": 24,
                "duration_seconds": 60,
            },
            "int-002": {
                "id": "int-002",
                "filename": "clip30.mp4",
                "frame_rate": 29.97,
                "duration_seconds": 60,
            },
        }

        edl = generate_edl("Test", selections, interviews, handle_frames=0)

        assert "WARNING: Mixed frame rates" in edl
        assert "24" in edl
        assert "29.97" in edl

    def test_no_mixed_fps_warning_when_uniform(self):
        """Uniform frame rate projects have no warning."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 0, "end": 10.0},
            {"segment_id": "seg-2", "interview_id": "int-002", "start": 0, "end": 10.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "clip1.mp4",
                "frame_rate": 24,
                "duration_seconds": 60,
            },
            "int-002": {
                "id": "int-002",
                "filename": "clip2.mp4",
                "frame_rate": 24,
                "duration_seconds": 60,
            },
        }

        edl = generate_edl("Test", selections, interviews, handle_frames=0)

        assert "WARNING" not in edl

    def test_duration_clamp_with_duration_seconds(self):
        """When duration_seconds is present, padded_end is clamped."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 55.0, "end": 60.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "clip.mp4",
                "frame_rate": 24,
                "duration_seconds": 60.0,  # Clip is exactly 60s
            },
        }

        edl = generate_edl("Test", selections, interviews, handle_frames=12)

        # Handle would push end to 60.5s, but duration_seconds clamps it to 60.0
        # Source out timecode should be based on 60s, not 60.5s
        # With start_timecode=None, offset=0, so src_out = seconds_to_timecode(60.0, 24, False)
        assert "00:01:00:00" in edl  # 60 seconds = 1 minute exactly

    def test_duration_no_clamp_without_duration_seconds(self):
        """When duration_seconds is absent, handle extends freely with default handles."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 55.0, "end": 60.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "clip.mp4",
                "frame_rate": 24,
                # No duration_seconds — handle padding extends freely
            },
        }

        edl = generate_edl("Test", selections, interviews, handle_frames=12)

        # Missing pause data → use default handles: src_in = 55 - 0.5 = 54.5s
        # src_out = 60 + 0.5 = 60.5s (no duration clamp)
        src_in = seconds_to_timecode(54.5, 24, False)
        src_out = seconds_to_timecode(60.5, 24, False)
        assert src_in in edl
        assert src_out in edl

    def test_df_timecode_offset_in_edl(self):
        """EDL with DF source timecode offset produces correct source IN/OUT.

        The offset 01:00:00;00 converts to ~3599.9964s (not exactly 3600s due to
        NTSC rate). Adding 10.0s gives ~3609.9964s which maps to 01:00:10;00.
        We verify by round-tripping through the timecode functions.
        """
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 10.0, "end": 20.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "clip.mp4",
                "frame_rate": 29.97,
                "duration_seconds": 3600,
                "start_timecode": "01:00:00;00",
            },
        }

        edl = generate_edl("Test", selections, interviews, handle_frames=0)

        # Compute expected timecodes the same way the generator does
        offset = timecode_to_seconds("01:00:00;00", 29.97)
        expected_in = seconds_to_timecode(offset + 10.0, 29.97, True)
        expected_out = seconds_to_timecode(offset + 20.0, 29.97, True)
        assert expected_in in edl, f"Expected src IN {expected_in} in EDL"
        assert expected_out in edl, f"Expected src OUT {expected_out} in EDL"
        # Also verify the source IN is near 01:00:10 (not off by 3.6s like the old bug)
        assert expected_in.startswith("01:00:10"), f"Source IN {expected_in} not near 01:00:10"

    def test_record_timecodes_contiguous(self):
        """Record OUT of event N equals Record IN of event N+1."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 0, "end": 10.0},
            {"segment_id": "seg-2", "interview_id": "int-001", "start": 30.0, "end": 45.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "clip.mp4",
                "frame_rate": 24,
                "duration_seconds": 120,
            },
        }

        edl = generate_edl("Test", selections, interviews, handle_frames=0)

        import re

        video_lines = [
            line
            for line in edl.split("\n")
            if line.strip() and line[:3].strip().isdigit() and " V " in line
        ]
        assert len(video_lines) == 2

        # Extract timecodes from each video line
        tc_pattern = r"(\d{2}:\d{2}:\d{2}[:;]\d{2})"
        tcs_1 = re.findall(tc_pattern, video_lines[0])
        tcs_2 = re.findall(tc_pattern, video_lines[1])
        # tcs = [srcIn, srcOut, recIn, recOut]
        rec_out_1 = tcs_1[3]
        rec_in_2 = tcs_2[2]
        assert rec_out_1 == rec_in_2, f"Rec OUT '{rec_out_1}' != Rec IN '{rec_in_2}'"

    def test_most_common_fps_used_for_record_track(self):
        """Record track uses the most common FPS, not last-wins."""
        selections = [
            {"segment_id": "seg-1", "interview_id": "int-001", "start": 0, "end": 10.0},
            {"segment_id": "seg-2", "interview_id": "int-002", "start": 0, "end": 10.0},
            {"segment_id": "seg-3", "interview_id": "int-003", "start": 0, "end": 10.0},
        ]
        interviews = {
            "int-001": {
                "id": "int-001",
                "filename": "a.mp4",
                "frame_rate": 24,
                "duration_seconds": 60,
            },
            "int-002": {
                "id": "int-002",
                "filename": "b.mp4",
                "frame_rate": 24,
                "duration_seconds": 60,
            },
            "int-003": {
                "id": "int-003",
                "filename": "c.mp4",
                "frame_rate": 29.97,
                "duration_seconds": 60,
            },
        }

        edl = generate_edl("Test", selections, interviews, handle_frames=0)

        # Record track should start at 1 hour = 3600 * 24 frames / 24 fps = 3600s
        # => 01:00:00:00 (NDF at 24fps)
        # If fps were 29.97, record track would start at 01:00:00;00 (DF with semicolon)
        video_lines = [
            line
            for line in edl.split("\n")
            if line.strip() and line[:3].strip().isdigit() and " V " in line
        ]
        import re

        tcs = re.findall(r"(\d{2}:\d{2}:\d{2}[:;]\d{2})", video_lines[0])
        rec_in = tcs[2]  # Third timecode is record IN
        # 24fps is most common (2 vs 1), so record timecode should be at 1h mark in NDF
        assert rec_in == "01:00:00:00", f"Expected NDF 01:00:00:00 but got {rec_in}"


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

    def test_generate_fcpxml_includes_speaker_keyword(self):
        """Test that FCPXML includes speaker keyword when present."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 0,
                "end": 10,
                "speaker": "SPEAKER_00",
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

        assert 'value="Speaker: SPEAKER_00"' in fcpxml

    def test_generate_fcpxml_speaker_in_clip_name(self):
        """Test that speaker is included in clip name."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 0,
                "end": 10,
                "speaker": "SPEAKER_01",
                "role": "hook",
                "text": "Test segment text here",
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

        assert "SPEAKER_01" in fcpxml
        assert "Hook" in fcpxml

    def test_generate_fcpxml_no_speaker_keyword_when_none(self):
        """Test that FCPXML omits speaker keyword when not present."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 0,
                "end": 10,
                "text": "Test segment",
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

        assert "Speaker:" not in fcpxml

    def test_generate_fcpxml_all_themes_exported(self):
        """Test that all themes are exported, not truncated to 3."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 0,
                "end": 10,
                "themes": ["journey", "transformation", "hope", "resilience", "community"],
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

        assert "journey" in fcpxml
        assert "transformation" in fcpxml
        assert "hope" in fcpxml
        assert "resilience" in fcpxml
        assert "community" in fcpxml

    def test_generate_fcpxml_chapter_markers_at_role_transitions(self):
        """Test that chapter markers are added at role transitions."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 0,
                "end": 10,
                "role": "hook",
            },
            {
                "segment_id": "seg-2",
                "interview_id": "int-001",
                "start": 10,
                "end": 20,
                "role": "body",
            },
            {
                "segment_id": "seg-3",
                "interview_id": "int-001",
                "start": 20,
                "end": 30,
                "role": "body",
            },
            {
                "segment_id": "seg-4",
                "interview_id": "int-001",
                "start": 30,
                "end": 40,
                "role": "climax",
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

        fcpxml = generate_fcpxml(
            project_name="TestProject",
            selections=selections,
            interviews=interviews,
        )

        assert "chapter-marker" in fcpxml
        assert "Hook" in fcpxml
        assert "Body" in fcpxml
        assert "Climax" in fcpxml

    def test_generate_fcpxml_user_notes_included(self):
        """Test that user_notes are included in FCPXML marker notes."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 0,
                "end": 10,
                "role": "hook",
                "editorial_notes": "Strong opening",
                "user_notes": "My personal note",
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

        assert "Strong opening" in fcpxml
        assert "My personal note" in fcpxml

    def test_generate_fcpxml_tcformat_df_for_2997fps(self):
        """FCPXML tcFormat should be DF for 29.97fps projects."""
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

        fcpxml = generate_fcpxml(
            project_name="TestProject",
            selections=selections,
            interviews=interviews,
        )

        assert 'tcFormat="DF"' in fcpxml

    def test_generate_fcpxml_tcformat_ndf_for_24fps(self):
        """FCPXML tcFormat should be NDF for 24fps projects."""
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
                "frame_rate": 24,
                "duration_seconds": 120,
            }
        }

        fcpxml = generate_fcpxml(
            project_name="TestProject",
            selections=selections,
            interviews=interviews,
        )

        assert 'tcFormat="NDF"' in fcpxml


class TestSmartHandles:
    """Tests for smart handle calculation using pause data."""

    def test_edl_uses_pause_data_for_smaller_handles(self):
        """When pause data is available, handles are reduced proportionally."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "pause_before_sec": 0.2,  # Only 0.2s pause before
                "pause_after_sec": 0.3,  # Only 0.3s pause after
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
            handle_frames=12,  # Default = 0.5s at 24fps
        )

        # With smart handles: handle_in = min(0.5, 0.2*0.8) = 0.16s
        # handle_out = min(0.5, 0.3*0.8) = 0.24s
        # So src_in = 10 - 0.16 = 9.84s, src_out = 20 + 0.24 = 20.24s
        # This is different from the default 0.5s handles
        assert "00:00:09" in edl  # Start around 9.8s
        assert "00:00:20" in edl  # End around 20.24s

    def test_edl_uses_default_handles_when_pause_data_missing(self):
        """When pause data is missing (key not present), default handles are used.

        Missing pause data indicates analysis wasn't run, so we use full handles.
        This is different from pause==0 (explicit), which means contiguous speech.
        """
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                # No pause_before_sec or pause_after_sec keys at all
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
            handle_frames=12,  # 0.5s at 24fps
        )

        # Missing pause data → use default handles
        assert "00:00:09:12" in edl  # 9.5s (10 - 0.5)
        assert "00:00:20:12" in edl  # 20.5s (20 + 0.5)

    def test_edl_uses_zero_handles_when_pause_explicitly_zero(self):
        """When pause is explicitly 0, zero handles are used (contiguous speech)."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "pause_before_sec": 0,  # Explicitly 0
                "pause_after_sec": 0,  # Explicitly 0
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
            handle_frames=12,  # 0.5s at 24fps, but not applied when pause==0
        )

        # Zero handles: src_in = 10.0s, src_out = 20.0s (no padding)
        assert "00:00:10:00" in edl
        assert "00:00:20:00" in edl

    def test_edl_uses_default_handles_when_pause_is_generous(self):
        """When pause is generous (> default), full handles are used."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "pause_before_sec": 2.0,  # Plenty of room
                "pause_after_sec": 3.0,  # Plenty of room
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
            handle_frames=12,  # 0.5s at 24fps
        )

        # Full handles used since pause * 0.8 > 0.5
        assert "00:00:09:12" in edl  # 9.5s
        assert "00:00:20:12" in edl  # 20.5s

    def test_fcpxml_uses_default_handles_when_pause_data_missing(self):
        """FCPXML uses default handles when pause data is missing."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
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
            handle_frames=12,
        )

        # Missing pause data → use default handles: start=9.5s, duration=11s
        # 9.5s at 24fps = 9.5 * 2400 = 22800/2400s
        # 11s at 24fps = 11 * 2400 = 26400/2400s
        assert 'start="22800/2400s"' in fcpxml
        assert 'duration="26400/2400s"' in fcpxml

    def test_fcpxml_uses_zero_handles_when_pause_explicitly_zero(self):
        """FCPXML uses zero handles when pause is explicitly 0."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "pause_before_sec": 0,
                "pause_after_sec": 0,
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
            handle_frames=12,
        )

        # Explicit zero → zero handles: start=10s, duration=10s
        # 10s at 24fps = 10 * 2400 = 24000/2400s
        assert 'start="24000/2400s"' in fcpxml
        assert 'duration="24000/2400s"' in fcpxml


class TestUserNotesExport:
    """Tests for user_notes export in EDL."""

    def test_edl_includes_user_notes_in_comment(self):
        """User notes are included in the EDL COMMENT line."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "role": "hook",
                "editorial_notes": "Strong delivery",
                "user_notes": "Double-check this fact",
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
        )

        assert "Strong delivery" in edl
        assert "Double-check this fact" in edl

    def test_edl_comment_without_user_notes(self):
        """EDL COMMENT works when only editorial_notes present."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "role": "hook",
                "editorial_notes": "Strong delivery",
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
        )

        assert "Strong delivery" in edl
        assert "Note:" not in edl  # No user notes prefix

    def test_edl_comment_truncation_with_ellipsis(self):
        """Long EDL comments are truncated at 200 chars with ellipsis."""
        long_notes = "x" * 250  # Very long notes
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "role": "hook",
                "editorial_notes": long_notes,
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
        )

        # Comment should be truncated with ellipsis
        assert "..." in edl
        # The truncated comment should be about 200 chars + "[hook] " prefix
        for line in edl.split("\n"):
            if line.startswith("* COMMENT:"):
                comment_content = line[10:]  # After "* COMMENT: "
                assert len(comment_content) <= 203  # 200 + "..."
                assert comment_content.endswith("...")
                break

    def test_edl_comment_not_truncated_when_short(self):
        """Short EDL comments are not truncated."""
        selections = [
            {
                "segment_id": "seg-1",
                "interview_id": "int-001",
                "start": 10.0,
                "end": 20.0,
                "role": "hook",
                "editorial_notes": "Short note",
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
        )

        # No ellipsis for short comments
        assert "* COMMENT: [hook] Short note" in edl
        assert "..." not in edl


class TestExportFromProject:
    """Tests for generate_*_from_project functions with path resolution."""

    def test_fcpxml_relative_source_file_resolved(self, tmp_path):
        """Relative source_file paths are resolved against project directory."""
        from plotline.export.fcpxml import generate_fcpxml_from_project

        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        data_dir = project_dir / "data"
        data_dir.mkdir()

        selections_data = {
            "segments": [
                {
                    "segment_id": "seg-1",
                    "interview_id": "int-001",
                    "start": 0,
                    "end": 10,
                    "position": 0,
                }
            ]
        }
        import json

        (data_dir / "selections.json").write_text(json.dumps(selections_data))

        manifest = {
            "project_name": "TestProject",
            "interviews": [
                {
                    "id": "int-001",
                    "filename": "interview1.mp4",
                    "source_file": "videos/interview1.mp4",  # Relative path
                    "frame_rate": 24,
                    "duration_seconds": 120,
                }
            ],
        }

        fcpxml = generate_fcpxml_from_project(
            project_path=project_dir,
            manifest=manifest,
            handle_frames=12,
            use_approvals=False,
        )

        # The source_file should be resolved to absolute path
        expected_path = project_dir / "videos" / "interview1.mp4"
        assert expected_path.as_uri() in fcpxml

    def test_edl_relative_source_file_resolved(self, tmp_path):
        """Relative source_file paths are resolved against project directory."""
        from plotline.export.edl import generate_edl_from_project

        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        data_dir = project_dir / "data"
        data_dir.mkdir()

        selections_data = {
            "segments": [
                {
                    "segment_id": "seg-1",
                    "interview_id": "int-001",
                    "start": 0,
                    "end": 10,
                    "position": 0,
                }
            ]
        }
        import json

        (data_dir / "selections.json").write_text(json.dumps(selections_data))

        manifest = {
            "project_name": "TestProject",
            "interviews": [
                {
                    "id": "int-001",
                    "filename": "interview1.mp4",
                    "source_file": "videos/interview1.mp4",  # Relative path
                    "frame_rate": 24,
                    "duration_seconds": 120,
                }
            ],
        }

        edl = generate_edl_from_project(
            project_path=project_dir,
            manifest=manifest,
            handle_frames=12,
            use_approvals=False,
        )

        # EDL uses filename for comments, not source_file path
        assert "interview1.mp4" in edl
