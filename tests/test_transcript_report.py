"""Tests for plotline.reports.transcript module."""

from __future__ import annotations

import json
from pathlib import Path

from plotline.reports.transcript import (
    build_theme_map,
    generate_transcript,
    get_confidence_class,
    get_delivery_class,
    get_theme_color,
)


class TestGetDeliveryClass:
    def test_high_score(self) -> None:
        assert get_delivery_class(0.8) == "filled"
        assert get_delivery_class(0.7) == "filled"

    def test_medium_score(self) -> None:
        assert get_delivery_class(0.5) == "medium"
        assert get_delivery_class(0.4) == "medium"

    def test_low_score(self) -> None:
        assert get_delivery_class(0.3) == "low"
        assert get_delivery_class(0.1) == "low"


class TestGetConfidenceClass:
    def test_high_confidence(self) -> None:
        assert get_confidence_class(0.95) == "high"
        assert get_confidence_class(0.9) == "high"

    def test_medium_confidence(self) -> None:
        assert get_confidence_class(0.8) == "medium"
        assert get_confidence_class(0.7) == "medium"

    def test_low_confidence(self) -> None:
        assert get_confidence_class(0.6) == "low"
        assert get_confidence_class(0.5) == "low"


class TestGetThemeColor:
    def test_first_eight_colors(self) -> None:
        assert get_theme_color(0) == "#3b82f6"
        assert get_theme_color(1) == "#8b5cf6"
        assert get_theme_color(7) == "#14b8a6"

    def test_wraps_around(self) -> None:
        assert get_theme_color(8) == get_theme_color(0)
        assert get_theme_color(9) == get_theme_color(1)


class TestBuildThemeMap:
    def test_empty_themes(self) -> None:
        result = build_theme_map(None)
        assert result == {}

    def test_no_themes_key(self) -> None:
        result = build_theme_map({})
        assert result == {}

    def test_single_theme_single_segment(self) -> None:
        themes_data = {
            "themes": [
                {
                    "name": "Connection to water",
                    "segment_ids": ["interview_001_seg_001"],
                }
            ]
        }
        result = build_theme_map(themes_data)
        assert result == {"interview_001_seg_001": ["Connection to water"]}

    def test_multiple_themes_same_segment(self) -> None:
        themes_data = {
            "themes": [
                {
                    "name": "Water",
                    "segment_ids": ["seg_001", "seg_002"],
                },
                {
                    "name": "Loss",
                    "segment_ids": ["seg_001"],
                },
            ]
        }
        result = build_theme_map(themes_data)
        assert result == {
            "seg_001": ["Water", "Loss"],
            "seg_002": ["Water"],
        }

    def test_multiple_segments_different_themes(self) -> None:
        themes_data = {
            "themes": [
                {
                    "name": "Theme A",
                    "segment_ids": ["seg_001", "seg_003"],
                },
                {
                    "name": "Theme B",
                    "segment_ids": ["seg_002"],
                },
            ]
        }
        result = build_theme_map(themes_data)
        assert len(result) == 3
        assert "Theme A" in result["seg_001"]
        assert "Theme B" in result["seg_002"]
        assert "Theme A" in result["seg_003"]


class TestGenerateTranscript:
    def test_missing_segments_raises(self, tmp_project: Path) -> None:
        """Test that missing segments file raises FileNotFoundError."""
        manifest = {
            "project_name": "test",
            "interviews": [{"id": "interview_001"}],
        }

        try:
            generate_transcript(
                project_path=tmp_project,
                manifest=manifest,
                interview_id="interview_001",
            )
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "segments" in str(e).lower()

    def test_generates_report_with_segments(self, tmp_project: Path, sample_segments: dict) -> None:
        """Test report generation with valid segments."""
        segments_dir = tmp_project / "data" / "segments"
        with open(segments_dir / "interview_001.json", "w") as f:
            json.dump(sample_segments, f)

        manifest = {
            "project_name": "test-project",
            "interviews": [
                {
                    "id": "interview_001",
                    "filename": "test_video.mov",
                    "frame_rate": 24,
                }
            ],
        }

        output_path = generate_transcript(
            project_path=tmp_project,
            manifest=manifest,
            interview_id="interview_001",
            open_browser=False,
        )

        assert output_path.exists()
        assert output_path.name == "transcript_interview_001.html"

        content = output_path.read_text()
        assert "interview_001" in content
        assert "test_video.mov" in content

    def test_generates_report_with_themes(self, tmp_project: Path, sample_segments: dict) -> None:
        """Test report generation includes theme pills."""
        segments_dir = tmp_project / "data" / "segments"
        with open(segments_dir / "interview_001.json", "w") as f:
            json.dump(sample_segments, f)

        themes_dir = tmp_project / "data" / "themes"
        themes_data = {
            "interview_id": "interview_001",
            "themes": [
                {
                    "name": "Connection to water",
                    "segment_ids": ["interview_001_seg_001"],
                }
            ],
        }
        with open(themes_dir / "interview_001.json", "w") as f:
            json.dump(themes_data, f)

        manifest = {
            "project_name": "test-project",
            "interviews": [
                {
                    "id": "interview_001",
                    "filename": "test_video.mov",
                    "frame_rate": 24,
                }
            ],
        }

        output_path = generate_transcript(
            project_path=tmp_project,
            manifest=manifest,
            interview_id="interview_001",
            open_browser=False,
        )

        content = output_path.read_text()
        assert "Connection to water" in content

    def test_custom_output_path(self, tmp_project: Path, sample_segments: dict) -> None:
        """Test custom output path is respected."""
        segments_dir = tmp_project / "data" / "segments"
        with open(segments_dir / "interview_001.json", "w") as f:
            json.dump(sample_segments, f)

        manifest = {
            "project_name": "test",
            "interviews": [{"id": "interview_001"}],
        }

        custom_path = tmp_project / "custom_transcript.html"
        output_path = generate_transcript(
            project_path=tmp_project,
            manifest=manifest,
            interview_id="interview_001",
            output_path=custom_path,
            open_browser=False,
        )

        assert output_path == custom_path
        assert custom_path.exists()

    def test_timeline_data_generated(self, tmp_project: Path, sample_segments: dict) -> None:
        """Test that timeline data is included for waveform."""
        segments_dir = tmp_project / "data" / "segments"
        with open(segments_dir / "interview_001.json", "w") as f:
            json.dump(sample_segments, f)

        manifest = {
            "project_name": "test",
            "interviews": [{"id": "interview_001"}],
        }

        output_path = generate_transcript(
            project_path=tmp_project,
            manifest=manifest,
            interview_id="interview_001",
            open_browser=False,
        )

        content = output_path.read_text()
        assert "timeline_data" in content
        assert "delivery-timeline" in content

    def test_low_confidence_segment_flagged(self, tmp_project: Path) -> None:
        """Test that low confidence segments get special styling."""
        segments_dir = tmp_project / "data" / "segments"
        low_confidence_segments = {
            "interview_id": "interview_001",
            "segments": [
                {
                    "segment_id": "interview_001_seg_001",
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Unclear transcription",
                    "confidence": 0.5,
                    "delivery": {"composite_score": 0.6},
                }
            ],
        }
        with open(segments_dir / "interview_001.json", "w") as f:
            json.dump(low_confidence_segments, f)

        manifest = {
            "project_name": "test",
            "interviews": [{"id": "interview_001"}],
        }

        output_path = generate_transcript(
            project_path=tmp_project,
            manifest=manifest,
            interview_id="interview_001",
            open_browser=False,
        )

        content = output_path.read_text()
        assert "low-confidence" in content

    def test_audio_path_constructed(self, tmp_project: Path, sample_segments: dict) -> None:
        """Test audio path is correctly constructed."""
        segments_dir = tmp_project / "data" / "segments"
        with open(segments_dir / "interview_001.json", "w") as f:
            json.dump(sample_segments, f)

        manifest = {
            "project_name": "test",
            "interviews": [
                {
                    "id": "interview_001",
                    "audio_full_path": "source/interview_001/audio_full.wav",
                }
            ],
        }

        output_path = generate_transcript(
            project_path=tmp_project,
            manifest=manifest,
            interview_id="interview_001",
            open_browser=False,
        )

        content = output_path.read_text()
        assert "audio_full.wav" in content
        assert "#t=" in content

    def test_no_delivery_shows_notice(self, tmp_project: Path) -> None:
        """Test that missing delivery shows appropriate notice."""
        segments_dir = tmp_project / "data" / "segments"
        no_delivery_segments = {
            "interview_id": "interview_001",
            "segments": [
                {
                    "segment_id": "interview_001_seg_001",
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Just text",
                    "confidence": 0.9,
                    "delivery": {},
                }
            ],
        }
        with open(segments_dir / "interview_001.json", "w") as f:
            json.dump(no_delivery_segments, f)

        manifest = {
            "project_name": "test",
            "interviews": [{"id": "interview_001"}],
        }

        output_path = generate_transcript(
            project_path=tmp_project,
            manifest=manifest,
            interview_id="interview_001",
            open_browser=False,
        )

        content = output_path.read_text()
        assert "No delivery analysis" in content or "plotline analyze" in content
