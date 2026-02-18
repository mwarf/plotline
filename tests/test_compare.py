"""Tests for plotline.compare module."""

from __future__ import annotations

from pathlib import Path

from plotline.compare import (
    build_comparison_groups,
    collect_all_segments,
    get_delivery_class,
    normalize_scores_cross_interview,
)


class TestCollectAllSegments:
    def test_collect_from_empty_project(self, tmp_project: Path) -> None:
        """Test collecting segments from project with no interviews."""
        manifest = {"interviews": []}
        segments, by_id = collect_all_segments(tmp_project, manifest)

        assert segments == []
        assert by_id == {}

    def test_collect_from_missing_segments_file(self, tmp_project: Path) -> None:
        """Test handling of missing segments file."""
        manifest = {
            "interviews": [
                {"id": "interview_001", "stages": {"enriched": True}},
            ]
        }
        segments, by_id = collect_all_segments(tmp_project, manifest)

        assert segments == []
        assert by_id == {}

    def test_collect_from_single_interview(self, tmp_project: Path, sample_segments: dict) -> None:
        """Test collecting segments from a single interview."""
        import json

        segments_dir = tmp_project / "data" / "segments"
        with open(segments_dir / "interview_001.json", "w") as f:
            json.dump(sample_segments, f)

        manifest = {
            "interviews": [
                {"id": "interview_001"},
            ]
        }

        segments, by_id = collect_all_segments(tmp_project, manifest)

        assert len(segments) == 1
        assert "interview_001_seg_001" in by_id
        assert by_id["interview_001_seg_001"]["_interview_id"] == "interview_001"

    def test_collect_from_multiple_interviews(self, tmp_project: Path) -> None:
        """Test collecting segments from multiple interviews."""
        import json

        segments_dir = tmp_project / "data" / "segments"

        for i in range(1, 3):
            segments_data = {
                "interview_id": f"interview_00{i}",
                "segments": [
                    {
                        "segment_id": f"interview_00{i}_seg_001",
                        "text": f"Segment {i}",
                        "delivery": {"composite_score": 0.5 + i * 0.1},
                    }
                ],
            }
            with open(segments_dir / f"interview_00{i}.json", "w") as f:
                json.dump(segments_data, f)

        manifest = {
            "interviews": [
                {"id": "interview_001"},
                {"id": "interview_002"},
            ]
        }

        segments, by_id = collect_all_segments(tmp_project, manifest)

        assert len(segments) == 2
        assert len(by_id) == 2


class TestNormalizeScoresCrossInterview:
    def test_normalize_empty_segments(self) -> None:
        """Test normalization with no segments."""
        weights = {
            "energy": 0.15,
            "pitch_variation": 0.15,
            "speech_rate": 0.25,
            "pause_weight": 0.30,
            "spectral_brightness": 0.10,
            "voice_texture": 0.05,
        }
        scores = normalize_scores_cross_interview([], weights)

        assert scores == {}

    def test_normalize_single_segment(self) -> None:
        """Test normalization with a single segment."""
        segments = [
            {
                "segment_id": "interview_001_seg_001",
                "delivery": {
                    "raw": {
                        "rms_energy": 0.5,
                        "pitch_std_hz": 30,
                        "speech_rate_wpm": 150,
                        "pause_before_sec": 0.5,
                        "pause_after_sec": 0.5,
                        "spectral_centroid_mean": 2000,
                        "zero_crossing_rate": 0.2,
                    }
                },
            }
        ]
        weights = {
            "energy": 0.15,
            "pitch_variation": 0.15,
            "speech_rate": 0.25,
            "pause_weight": 0.30,
            "spectral_brightness": 0.10,
            "voice_texture": 0.05,
        }

        scores = normalize_scores_cross_interview(segments, weights)

        assert "interview_001_seg_001" in scores
        assert 0.0 <= scores["interview_001_seg_001"] <= 1.0

    def test_normalize_multiple_segments(self) -> None:
        """Test cross-interview normalization produces comparable scores."""
        segments = [
            {
                "segment_id": "interview_001_seg_001",
                "delivery": {
                    "raw": {
                        "rms_energy": 0.2,
                        "pitch_std_hz": 20,
                        "speech_rate_wpm": 120,
                        "pause_before_sec": 0.5,
                        "pause_after_sec": 0.5,
                        "spectral_centroid_mean": 1500,
                        "zero_crossing_rate": 0.15,
                    }
                },
            },
            {
                "segment_id": "interview_002_seg_001",
                "delivery": {
                    "raw": {
                        "rms_energy": 0.4,
                        "pitch_std_hz": 40,
                        "speech_rate_wpm": 180,
                        "pause_before_sec": 1.0,
                        "pause_after_sec": 1.0,
                        "spectral_centroid_mean": 2500,
                        "zero_crossing_rate": 0.25,
                    }
                },
            },
        ]
        weights = {
            "energy": 0.15,
            "pitch_variation": 0.15,
            "speech_rate": 0.25,
            "pause_weight": 0.30,
            "spectral_brightness": 0.10,
            "voice_texture": 0.05,
        }

        scores = normalize_scores_cross_interview(segments, weights)

        assert len(scores) == 2
        assert scores["interview_001_seg_001"] < scores["interview_002_seg_001"]

    def test_normalize_without_raw_delivery(self) -> None:
        """Test normalization handles segments without raw delivery data."""
        segments = [
            {
                "segment_id": "interview_001_seg_001",
                "delivery": {},
            }
        ]
        weights = {
            "energy": 0.15,
            "pitch_variation": 0.15,
            "speech_rate": 0.25,
            "pause_weight": 0.30,
            "spectral_brightness": 0.10,
            "voice_texture": 0.05,
        }

        scores = normalize_scores_cross_interview(segments, weights)

        assert "interview_001_seg_001" in scores


class TestGetDeliveryClass:
    def test_high_score(self) -> None:
        """Test classification of high scores."""
        assert get_delivery_class(0.8) == "filled"
        assert get_delivery_class(0.7) == "filled"

    def test_medium_score(self) -> None:
        """Test classification of medium scores."""
        assert get_delivery_class(0.5) == "medium"
        assert get_delivery_class(0.4) == "medium"

    def test_low_score(self) -> None:
        """Test classification of low scores."""
        assert get_delivery_class(0.3) == "low"
        assert get_delivery_class(0.1) == "low"


class TestBuildComparisonGroups:
    def test_empty_synthesis(self) -> None:
        """Test building groups with empty synthesis."""
        synthesis = {"best_takes": [], "unified_themes": []}
        groups = build_comparison_groups(
            synthesis=synthesis,
            segments_by_id={},
            cross_scores={},
            interviews_map={},
        )

        assert groups == []

    def test_single_best_take(self) -> None:
        """Test building groups with a single best take."""
        synthesis = {
            "best_takes": [
                {
                    "topic": "Connection to water",
                    "candidates": [
                        {
                            "segment_id": "interview_001_seg_001",
                            "rank": 1,
                            "reasoning": "Best delivery",
                        }
                    ],
                }
            ],
            "unified_themes": [
                {
                    "name": "Connection to water",
                    "perspectives": "Complementary",
                    "source_themes": [{"interview_id": "interview_001", "theme_id": "theme_001"}],
                }
            ],
        }
        segments_by_id = {
            "interview_001_seg_001": {
                "segment_id": "interview_001_seg_001",
                "_interview_id": "interview_001",
                "text": "The water was sacred to us.",
                "start": 10.0,
                "end": 15.0,
                "delivery": {"delivery_label": "reflective"},
            }
        }
        cross_scores = {"interview_001_seg_001": 0.85}
        interviews_map = {"interview_001": {"id": "interview_001", "frame_rate": 24}}

        groups = build_comparison_groups(
            synthesis=synthesis,
            segments_by_id=segments_by_id,
            cross_scores=cross_scores,
            interviews_map=interviews_map,
        )

        assert len(groups) == 1
        assert groups[0]["topic"] == "Connection to water"
        assert len(groups[0]["candidates"]) == 1
        assert groups[0]["candidates"][0]["rank"] == 1

    def test_message_filter(self) -> None:
        """Test filtering by key message."""
        synthesis = {
            "best_takes": [
                {
                    "topic": "Connection to water",
                    "candidates": [{"segment_id": "seg_001", "rank": 1, "reasoning": "Good"}],
                },
                {
                    "topic": "Community traditions",
                    "candidates": [{"segment_id": "seg_002", "rank": 1, "reasoning": "Good"}],
                },
            ],
            "unified_themes": [
                {"name": "Connection to water", "perspectives": "", "source_themes": []},
                {"name": "Community traditions", "perspectives": "", "source_themes": []},
            ],
        }
        segments_by_id = {
            "seg_001": {
                "segment_id": "seg_001",
                "_interview_id": "interview_001",
                "text": "Water text",
                "start": 0,
                "end": 5,
                "delivery": {},
            },
            "seg_002": {
                "segment_id": "seg_002",
                "_interview_id": "interview_001",
                "text": "Community text",
                "start": 10,
                "end": 15,
                "delivery": {},
            },
        }
        cross_scores = {"seg_001": 0.8, "seg_002": 0.7}
        brief = {"key_messages": ["Water is central to our culture", "Traditions bind us"]}
        interviews_map = {"interview_001": {"id": "interview_001", "frame_rate": 24}}

        groups = build_comparison_groups(
            synthesis=synthesis,
            segments_by_id=segments_by_id,
            cross_scores=cross_scores,
            interviews_map=interviews_map,
            brief=brief,
            message_filter="water",
        )

        assert len(groups) == 1
        assert groups[0]["topic"] == "Connection to water"

    def test_missing_segment_skipped(self) -> None:
        """Test that candidates with missing segments are skipped."""
        synthesis = {
            "best_takes": [
                {
                    "topic": "Test topic",
                    "candidates": [
                        {"segment_id": "missing_seg", "rank": 1, "reasoning": "Good"},
                        {
                            "segment_id": "existing_seg",
                            "rank": 2,
                            "reasoning": "Also good",
                        },
                    ],
                }
            ],
            "unified_themes": [{"name": "Test topic", "perspectives": "", "source_themes": []}],
        }
        segments_by_id = {
            "existing_seg": {
                "segment_id": "existing_seg",
                "_interview_id": "interview_001",
                "text": "Existing text",
                "start": 0,
                "end": 5,
                "delivery": {},
            }
        }
        cross_scores = {"existing_seg": 0.8}
        interviews_map = {"interview_001": {"id": "interview_001", "frame_rate": 24}}

        groups = build_comparison_groups(
            synthesis=synthesis,
            segments_by_id=segments_by_id,
            cross_scores=cross_scores,
            interviews_map=interviews_map,
        )

        assert len(groups) == 1
        assert len(groups[0]["candidates"]) == 1
        assert groups[0]["candidates"][0]["segment_id"] == "existing_seg"

    def test_candidates_sorted_by_rank(self) -> None:
        """Test that candidates are sorted by rank."""
        synthesis = {
            "best_takes": [
                {
                    "topic": "Test topic",
                    "candidates": [
                        {"segment_id": "seg_003", "rank": 3, "reasoning": "Third"},
                        {"segment_id": "seg_001", "rank": 1, "reasoning": "First"},
                        {"segment_id": "seg_002", "rank": 2, "reasoning": "Second"},
                    ],
                }
            ],
            "unified_themes": [{"name": "Test topic", "perspectives": "", "source_themes": []}],
        }
        segments_by_id = {
            "seg_001": {
                "segment_id": "seg_001",
                "_interview_id": "interview_001",
                "text": "First",
                "start": 0,
                "end": 5,
                "delivery": {},
            },
            "seg_002": {
                "segment_id": "seg_002",
                "_interview_id": "interview_001",
                "text": "Second",
                "start": 10,
                "end": 15,
                "delivery": {},
            },
            "seg_003": {
                "segment_id": "seg_003",
                "_interview_id": "interview_001",
                "text": "Third",
                "start": 20,
                "end": 25,
                "delivery": {},
            },
        }
        cross_scores = {"seg_001": 0.9, "seg_002": 0.8, "seg_003": 0.7}
        interviews_map = {"interview_001": {"id": "interview_001", "frame_rate": 24}}

        groups = build_comparison_groups(
            synthesis=synthesis,
            segments_by_id=segments_by_id,
            cross_scores=cross_scores,
            interviews_map=interviews_map,
        )

        assert len(groups[0]["candidates"]) == 3
        assert groups[0]["candidates"][0]["rank"] == 1
        assert groups[0]["candidates"][1]["rank"] == 2
        assert groups[0]["candidates"][2]["rank"] == 3
