"""Tests for plotline.validation module."""

from pathlib import Path

import pytest

from plotline.exceptions import ValidationError
from plotline.validation import (
    estimate_audio_size,
    validate_interview_duration,
    validate_video_file,
)


class TestEstimateAudioSize:
    def test_short_audio(self):
        size = estimate_audio_size(60)
        assert size < 2

    def test_one_hour_audio(self):
        size = estimate_audio_size(3600)
        assert size > 100
        assert size < 150

    def test_custom_sample_rate(self):
        size_16k = estimate_audio_size(60, sample_rate=16000)
        size_44k = estimate_audio_size(60, sample_rate=44100)
        assert size_44k > size_16k


class TestValidateInterviewDuration:
    def test_normal_duration(self):
        result = validate_interview_duration(1800)
        assert result["valid"] is True
        assert len(result["warnings"]) == 0

    def test_very_short_interview(self):
        result = validate_interview_duration(60)
        assert result["valid"] is True
        assert len(result["warnings"]) == 1
        assert "short" in result["warnings"][0].lower()

    def test_very_long_interview(self):
        result = validate_interview_duration(10800)
        assert result["valid"] is True
        assert len(result["warnings"]) == 1
        assert "long" in result["warnings"][0].lower()

    def test_duration_formatting_minutes(self):
        result = validate_interview_duration(185)
        assert "3m" in result["duration_formatted"]

    def test_duration_formatting_hours(self):
        result = validate_interview_duration(3725)
        assert "1h" in result["duration_formatted"]


class TestValidateVideoFile:
    def test_nonexistent_file(self):
        with pytest.raises(ValidationError):
            validate_video_file(Path("/nonexistent/video.mp4"))

    def test_directory_not_file(self, tmp_path):
        with pytest.raises(ValidationError):
            validate_video_file(tmp_path)

    def test_valid_file(self, tmp_path):
        video_file = tmp_path / "test.mp4"
        video_file.write_text("fake video")
        result = validate_video_file(video_file)
        assert result["exists"] is True
        assert result["size_mb"] == 0
