"""Tests for plotline.extract.audio module."""

from __future__ import annotations

from pathlib import Path

import pytest

from plotline.extract.audio import format_size


class TestFormatSize:
    def test_bytes(self) -> None:
        assert format_size_path(500) == "500.0 B"

    def test_kilobytes(self) -> None:
        assert format_size_path(1500) == "1.5 KB"

    def test_megabytes(self) -> None:
        assert format_size_path(1572864) == "1.5 MB"

    def test_gigabytes(self) -> None:
        assert format_size_path(1610612736) == "1.5 GB"

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = format_size(tmp_path / "nonexistent.wav")
        assert result == "-"


def format_size_path(size: int) -> str:
    """Helper to test format_size with a temp file."""
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"x" * size)
        path = Path(f.name)
    try:
        return format_size(path)
    finally:
        path.unlink()


class TestExtractAudio:
    @pytest.mark.slow
    def test_extract_creates_wav_files(self, tmp_path: Path) -> None:
        """Test that extraction creates both WAV files."""
        pytest.skip("Requires FFmpeg and video file - run manually")

    def test_extract_missing_source_raises(self, tmp_path: Path) -> None:
        """Test that missing source file raises ExtractionError."""
        from plotline.exceptions import ExtractionError
        from plotline.extract.audio import extract_audio

        source = tmp_path / "missing.mp4"
        output_16k = tmp_path / "audio_16k.wav"
        output_full = tmp_path / "audio_full.wav"

        with pytest.raises(ExtractionError):
            extract_audio(source, output_16k, output_full)


class TestExtractAllInterviews:
    def test_empty_manifest(self, tmp_path: Path) -> None:
        """Test extraction with no interviews."""
        from plotline.extract.audio import extract_all_interviews

        manifest = {"interviews": []}
        results = extract_all_interviews(tmp_path, manifest)

        assert results["extracted"] == 0
        assert results["skipped"] == 0
        assert results["failed"] == 0

    def test_missing_source_file(self, tmp_path: Path) -> None:
        """Test handling of missing source file."""
        from plotline.extract.audio import extract_all_interviews

        manifest = {
            "interviews": [
                {
                    "id": "interview_001",
                    "source_file": "/nonexistent/video.mp4",
                    "stages": {"extracted": False},
                }
            ]
        }

        results = extract_all_interviews(tmp_path, manifest)

        assert results["extracted"] == 0
        assert results["failed"] == 1
        assert len(results["errors"]) == 1
        assert results["errors"][0]["interview_id"] == "interview_001"

    def test_already_extracted_skipped(self, tmp_path: Path) -> None:
        """Test that already extracted interviews are skipped."""
        from plotline.extract.audio import extract_all_interviews

        manifest = {
            "interviews": [
                {
                    "id": "interview_001",
                    "source_file": "/some/video.mp4",
                    "stages": {"extracted": True},
                }
            ]
        }

        results = extract_all_interviews(tmp_path, manifest, force=False)

        assert results["extracted"] == 0
        assert results["skipped"] == 1
        assert results["failed"] == 0
