"""Tests for plotline.enrich.merge module."""

from __future__ import annotations

from pathlib import Path

from plotline.enrich.merge import merge_transcript_and_delivery


class TestMergeTranscriptAndDelivery:
    def test_merge_basic(self) -> None:
        """Test basic merge of transcript and delivery."""
        transcript = {
            "interview_id": "interview_001",
            "duration_seconds": 60.0,
            "segments": [
                {
                    "segment_id": "interview_001_seg_001",
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Hello world",
                    "words": [{"word": "Hello", "start": 0.0, "end": 0.5}],
                    "confidence": 0.95,
                    "corrected": False,
                }
            ],
        }

        delivery = {
            "interview_id": "interview_001",
            "segments": [
                {
                    "segment_id": "interview_001_seg_001",
                    "normalized": {
                        "energy": 0.5,
                        "pitch_variation": 0.3,
                    },
                    "composite_score": 0.65,
                    "delivery_label": "moderate energy",
                }
            ],
        }

        result = merge_transcript_and_delivery(transcript, delivery)

        assert result["interview_id"] == "interview_001"
        assert result["segment_count"] == 1
        assert len(result["segments"]) == 1

        seg = result["segments"][0]
        assert seg["segment_id"] == "interview_001_seg_001"
        assert seg["text"] == "Hello world"
        assert seg["delivery"]["energy"] == 0.5
        assert seg["delivery"]["composite_score"] == 0.65
        assert seg["delivery"]["delivery_label"] == "moderate energy"

    def test_merge_multiple_segments(self) -> None:
        """Test merge with multiple segments."""
        transcript = {
            "interview_id": "interview_001",
            "segments": [
                {
                    "segment_id": "seg_001",
                    "start": 0.0,
                    "end": 2.0,
                    "text": "First",
                    "confidence": 0.9,
                    "corrected": False,
                    "words": [],
                },
                {
                    "segment_id": "seg_002",
                    "start": 2.5,
                    "end": 5.0,
                    "text": "Second",
                    "confidence": 0.85,
                    "corrected": False,
                    "words": [],
                },
                {
                    "segment_id": "seg_003",
                    "start": 5.5,
                    "end": 8.0,
                    "text": "Third",
                    "confidence": 0.88,
                    "corrected": False,
                    "words": [],
                },
            ],
        }

        delivery = {
            "segments": [
                {
                    "segment_id": "seg_001",
                    "normalized": {},
                    "composite_score": 0.5,
                    "delivery_label": "a",
                },
                {
                    "segment_id": "seg_002",
                    "normalized": {},
                    "composite_score": 0.6,
                    "delivery_label": "b",
                },
                {
                    "segment_id": "seg_003",
                    "normalized": {},
                    "composite_score": 0.7,
                    "delivery_label": "c",
                },
            ],
        }

        result = merge_transcript_and_delivery(transcript, delivery)

        assert result["segment_count"] == 3
        assert result["segments"][0]["text"] == "First"
        assert result["segments"][1]["text"] == "Second"
        assert result["segments"][2]["text"] == "Third"

    def test_merge_missing_delivery(self) -> None:
        """Test merge when delivery is missing for a segment."""
        transcript = {
            "interview_id": "interview_001",
            "segments": [
                {
                    "segment_id": "seg_001",
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Test",
                    "confidence": 0.9,
                    "corrected": False,
                    "words": [],
                },
            ],
        }

        delivery = {"segments": []}

        result = merge_transcript_and_delivery(transcript, delivery)

        assert result["segment_count"] == 1
        assert result["segments"][0]["delivery"]["composite_score"] == 0
        assert result["segments"][0]["delivery"]["delivery_label"] == ""

    def test_merge_with_metadata(self) -> None:
        """Test merge includes interview metadata."""
        transcript = {
            "interview_id": "interview_001",
            "segments": [],
        }

        delivery = {"segments": []}

        metadata = {"filename": "test_video.mp4", "duration_seconds": 120}

        result = merge_transcript_and_delivery(transcript, delivery, metadata)

        assert result["source_file"] == "test_video.mp4"


class TestEnrichAllInterviews:
    def test_empty_manifest(self, tmp_path: Path) -> None:
        """Test enrichment with no interviews."""
        from plotline.enrich.merge import enrich_all_interviews

        manifest = {"interviews": []}
        results = enrich_all_interviews(tmp_path, manifest)

        assert results["enriched"] == 0
        assert results["skipped"] == 0
        assert results["failed"] == 0

    def test_not_analyzed_skipped(self, tmp_path: Path) -> None:
        """Test that non-analyzed interviews are skipped."""
        from plotline.enrich.merge import enrich_all_interviews

        manifest = {
            "interviews": [
                {
                    "id": "interview_001",
                    "stages": {"analyzed": False, "enriched": False},
                }
            ]
        }

        results = enrich_all_interviews(tmp_path, manifest)

        assert results["enriched"] == 0
        assert results["skipped"] == 1

    def test_already_enriched_skipped(self, tmp_path: Path) -> None:
        """Test that already enriched interviews are skipped."""
        from plotline.enrich.merge import enrich_all_interviews

        manifest = {
            "interviews": [
                {
                    "id": "interview_001",
                    "stages": {"analyzed": True, "enriched": True},
                }
            ]
        }

        results = enrich_all_interviews(tmp_path, manifest, force=False)

        assert results["enriched"] == 0
        assert results["skipped"] == 1
