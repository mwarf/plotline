"""Tests for plotline.reports.coverage module and brief normalization."""

from __future__ import annotations

import json
from pathlib import Path

from plotline.brief import normalize_key_messages
from plotline.reports.coverage import (
    analyze_coverage,
    build_theme_alignment_map,
    build_theme_to_segments_map,
    generate_coverage,
)


class TestNormalizeKeyMessages:
    def test_strings_normalized(self) -> None:
        """Test that string messages are wrapped into objects."""
        messages = ["First message", "Second message", "Third message"]
        result = normalize_key_messages(messages)

        assert len(result) == 3
        assert result[0]["id"] == "msg_001"
        assert result[0]["text"] == "First message"
        assert result[1]["id"] == "msg_002"
        assert result[2]["id"] == "msg_003"

    def test_dicts_with_ids_preserved(self) -> None:
        """Test that dicts with IDs are preserved."""
        messages = [
            {"id": "custom_001", "text": "Custom message"},
            {"id": "custom_002", "text": "Another message"},
        ]
        result = normalize_key_messages(messages)

        assert result[0]["id"] == "custom_001"
        assert result[1]["id"] == "custom_002"

    def test_dicts_without_ids_get_generated(self) -> None:
        """Test that dicts without IDs get auto-generated IDs."""
        messages = [
            {"text": "Message one"},
            {"text": "Message two"},
        ]
        result = normalize_key_messages(messages)

        assert result[0]["id"] == "msg_001"
        assert result[0]["text"] == "Message one"
        assert result[1]["id"] == "msg_002"

    def test_mixed_formats(self) -> None:
        """Test mixed strings and dicts."""
        messages = [
            "String message",
            {"id": "custom_id", "text": "Dict message"},
            {"text": "Dict without ID"},
        ]
        result = normalize_key_messages(messages)

        assert len(result) == 3
        assert result[0]["id"] == "msg_001"
        assert result[1]["id"] == "custom_id"
        assert result[2]["id"] == "msg_003"

    def test_empty_list(self) -> None:
        """Test empty list returns empty."""
        result = normalize_key_messages([])
        assert result == []


class TestBuildThemeAlignmentMap:
    def test_empty_synthesis(self) -> None:
        """Test with no synthesis data."""
        result = build_theme_alignment_map(None)
        assert result == {}

    def test_no_alignments(self) -> None:
        """Test with themes but no brief alignments."""
        synthesis = {
            "unified_themes": [
                {"unified_theme_id": "utheme_001", "brief_alignment": None},
            ]
        }
        result = build_theme_alignment_map(synthesis)
        assert result == {}

    def test_single_alignment(self) -> None:
        """Test with single theme alignment."""
        synthesis = {
            "unified_themes": [
                {"unified_theme_id": "utheme_001", "brief_alignment": "msg_001"},
            ]
        }
        result = build_theme_alignment_map(synthesis)

        assert "msg_001" in result
        assert "utheme_001" in result["msg_001"]

    def test_multiple_themes_same_message(self) -> None:
        """Test multiple themes aligned to same message."""
        synthesis = {
            "unified_themes": [
                {"unified_theme_id": "utheme_001", "brief_alignment": "msg_001"},
                {"unified_theme_id": "utheme_002", "brief_alignment": "msg_001"},
            ]
        }
        result = build_theme_alignment_map(synthesis)

        assert len(result["msg_001"]) == 2


class TestBuildThemeToSegmentsMap:
    def test_empty_synthesis(self) -> None:
        """Test with no synthesis data."""
        result = build_theme_to_segments_map(None)
        assert result == {}

    def test_maps_segments(self) -> None:
        """Test mapping themes to segments."""
        synthesis = {
            "unified_themes": [
                {
                    "unified_theme_id": "utheme_001",
                    "all_segment_ids": ["seg_001", "seg_002"],
                },
            ]
        }
        result = build_theme_to_segments_map(synthesis)

        assert result["utheme_001"] == ["seg_001", "seg_002"]


class TestAnalyzeCoverage:
    def test_strong_coverage(self) -> None:
        """Test message with direct segment match."""
        brief_data = {
            "key_messages": [
                {"id": "msg_001", "text": "Test message"},
            ]
        }
        selections_data = {
            "segments": [
                {
                    "segment_id": "seg_001",
                    "brief_message": "msg_001",
                    "composite_score": 0.85,
                    "text": "Test segment text",
                    "start": 0,
                    "end": 10,
                    "position": 1,
                }
            ]
        }

        result = analyze_coverage(brief_data, selections_data, None, None, {})

        assert len(result["messages"]) == 1
        assert result["messages"][0]["coverage_level"] == "strong"
        assert result["strong_count"] == 1
        assert result["weak_count"] == 0
        assert result["gap_count"] == 0

    def test_weak_coverage(self) -> None:
        """Test message with only theme-level alignment."""
        brief_data = {
            "key_messages": [
                {"id": "msg_001", "text": "Test message"},
            ]
        }
        selections_data = {
            "segments": [
                {
                    "segment_id": "seg_001",
                    "brief_message": None,
                    "composite_score": 0.75,
                    "text": "Related segment",
                    "start": 0,
                    "end": 10,
                    "position": 1,
                    "themes": ["utheme_001"],
                }
            ]
        }
        synthesis_data = {
            "unified_themes": [
                {
                    "unified_theme_id": "utheme_001",
                    "brief_alignment": "msg_001",
                    "all_segment_ids": ["seg_001"],
                }
            ]
        }

        result = analyze_coverage(brief_data, selections_data, synthesis_data, None, {})

        assert result["messages"][0]["coverage_level"] == "weak"
        assert result["weak_count"] == 1

    def test_gap_coverage(self) -> None:
        """Test message with no coverage."""
        brief_data = {
            "key_messages": [
                {"id": "msg_001", "text": "Uncovered message"},
            ]
        }
        selections_data = {"segments": []}

        result = analyze_coverage(brief_data, selections_data, None, None, {})

        assert result["messages"][0]["coverage_level"] == "gap"
        assert result["gap_count"] == 1
        assert result["coverage_percent"] == 0

    def test_full_coverage(self) -> None:
        """Test all messages covered."""
        brief_data = {
            "key_messages": [
                {"id": "msg_001", "text": "First message"},
                {"id": "msg_002", "text": "Second message"},
            ]
        }
        selections_data = {
            "segments": [
                {
                    "segment_id": "seg_001",
                    "brief_message": "msg_001",
                    "composite_score": 0.8,
                    "text": "Covers first",
                    "start": 0,
                    "end": 10,
                    "position": 1,
                },
                {
                    "segment_id": "seg_002",
                    "brief_message": "msg_002",
                    "composite_score": 0.9,
                    "text": "Covers second",
                    "start": 10,
                    "end": 20,
                    "position": 2,
                },
            ]
        }

        result = analyze_coverage(brief_data, selections_data, None, None, {})

        assert result["coverage_percent"] == 100
        assert result["strong_count"] == 2

    def test_mixed_coverage(self) -> None:
        """Test mix of strong, weak, and gap."""
        brief_data = {
            "key_messages": [
                {"id": "msg_001", "text": "Strong message"},
                {"id": "msg_002", "text": "Weak message"},
                {"id": "msg_003", "text": "Gap message"},
            ]
        }
        selections_data = {
            "segments": [
                {
                    "segment_id": "seg_001",
                    "brief_message": "msg_001",
                    "composite_score": 0.8,
                    "text": "Strong",
                    "start": 0,
                    "end": 10,
                    "position": 1,
                    "themes": [],
                },
                {
                    "segment_id": "seg_002",
                    "brief_message": None,
                    "composite_score": 0.7,
                    "text": "Weak",
                    "start": 10,
                    "end": 20,
                    "position": 2,
                    "themes": ["utheme_001"],
                },
            ]
        }
        synthesis_data = {
            "unified_themes": [
                {
                    "unified_theme_id": "utheme_001",
                    "brief_alignment": "msg_002",
                    "all_segment_ids": ["seg_002"],
                }
            ]
        }

        result = analyze_coverage(brief_data, selections_data, synthesis_data, None, {})

        assert result["strong_count"] == 1
        assert result["weak_count"] == 1
        assert result["gap_count"] == 1

    def test_coverage_gaps_from_arc(self) -> None:
        """Test that coverage_gaps from arc are included."""
        brief_data = {"key_messages": [{"id": "msg_001", "text": "Test"}]}
        selections_data = {"segments": []}
        arc_data = {"coverage_gaps": ["Missing coverage for msg_001"]}

        result = analyze_coverage(brief_data, selections_data, None, arc_data, {})

        assert len(result["coverage_gaps"]) == 1
        assert "msg_001" in result["coverage_gaps"][0]

    def test_must_include_status(self) -> None:
        """Test must-include topic tracking."""
        brief_data = {
            "key_messages": [{"id": "msg_001", "text": "Test"}],
            "must_include_topics": ["sustainability", "innovation"],
        }
        selections_data = {"segments": []}
        synthesis_data = {
            "unified_themes": [
                {"name": "Sustainability in Practice"},
            ]
        }

        result = analyze_coverage(brief_data, selections_data, synthesis_data, None, {})

        assert len(result["must_include_status"]) == 2
        sustainability = next(
            (m for m in result["must_include_status"] if m["topic"] == "sustainability"),
            None,
        )
        assert sustainability is not None
        assert sustainability["covered"] is True


class TestGenerateCoverage:
    def test_missing_brief_raises(self, tmp_project: Path) -> None:
        """Test error when brief is missing."""
        manifest = {"project_name": "test"}

        try:
            generate_coverage(tmp_project, manifest)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "brief" in str(e).lower()

    def test_missing_selections_raises(self, tmp_project: Path) -> None:
        """Test error when selections are missing."""
        brief_path = tmp_project / "brief.json"
        brief_path.write_text(json.dumps({"key_messages": [{"id": "msg_001", "text": "Test"}]}))

        manifest = {"project_name": "test"}

        try:
            generate_coverage(tmp_project, manifest)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "selections" in str(e).lower()

    def test_generates_report(self, tmp_project: Path) -> None:
        """Test successful report generation."""
        brief_path = tmp_project / "brief.json"
        brief_path.write_text(
            json.dumps({"key_messages": [{"id": "msg_001", "text": "Test message"}]})
        )

        selections_path = tmp_project / "data" / "selections.json"
        selections_path.parent.mkdir(parents=True, exist_ok=True)
        selections_path.write_text(
            json.dumps(
                {
                    "segments": [
                        {
                            "segment_id": "seg_001",
                            "brief_message": "msg_001",
                            "composite_score": 0.85,
                            "text": "Test segment",
                            "start": 0,
                            "end": 10,
                            "position": 1,
                        }
                    ]
                }
            )
        )

        manifest = {
            "project_name": "test-project",
            "interviews": [],
        }

        output_path = generate_coverage(tmp_project, manifest, open_browser=False)

        assert output_path.exists()
        assert output_path.name == "coverage.html"

        content = output_path.read_text()
        assert "Coverage Matrix" in content
        assert "msg_001" in content
        assert "Test message" in content

    def test_custom_output_path(self, tmp_project: Path) -> None:
        """Test custom output path."""
        brief_path = tmp_project / "brief.json"
        brief_path.write_text(json.dumps({"key_messages": [{"id": "msg_001", "text": "Test"}]}))

        selections_path = tmp_project / "data" / "selections.json"
        selections_path.parent.mkdir(parents=True, exist_ok=True)
        selections_path.write_text(json.dumps({"segments": []}))

        manifest = {"project_name": "test", "interviews": []}

        custom_path = tmp_project / "custom_coverage.html"
        output_path = generate_coverage(
            tmp_project, manifest, output_path=custom_path, open_browser=False
        )

        assert output_path == custom_path
        assert custom_path.exists()
