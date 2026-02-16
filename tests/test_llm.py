"""Tests for plotline.llm modules."""

from __future__ import annotations

from plotline.llm.parsing import parse_llm_json, validate_themes_response
from plotline.llm.templates import format_timecode, format_transcript_for_prompt


class TestParseLLMJson:
    def test_parse_clean_json(self) -> None:
        """Test parsing clean JSON."""
        response = '{"themes": [{"name": "Test"}]}'
        result = parse_llm_json(response)
        assert result["themes"][0]["name"] == "Test"

    def test_parse_json_with_markdown(self) -> None:
        """Test parsing JSON wrapped in markdown."""
        response = '```json\n{"themes": []}\n```'
        result = parse_llm_json(response)
        assert result["themes"] == []

    def test_parse_json_with_trailing_commas(self) -> None:
        """Test parsing JSON with trailing commas."""
        response = '{"themes": [{"name": "A",}, {"name": "B",}],}'
        result = parse_llm_json(response)
        assert len(result["themes"]) == 2

    def test_parse_json_with_surrounding_text(self) -> None:
        """Test parsing JSON with text before/after."""
        response = 'Here is the result:\n{"themes": []}\nLet me know if you need more.'
        result = parse_llm_json(response)
        assert result["themes"] == []


class TestValidateThemesResponse:
    def test_validate_basic_response(self) -> None:
        """Test validating a basic themes response."""
        data = {"themes": [{"name": "Connection to water", "segment_ids": ["seg_001"]}]}
        result = validate_themes_response(data, "interview_001")
        assert len(result["themes"]) == 1
        assert result["themes"][0]["name"] == "Connection to water"

    def test_validate_adds_missing_fields(self) -> None:
        """Test that validation adds missing optional fields."""
        data = {"themes": [{"name": "Test"}]}
        result = validate_themes_response(data, "interview_001")
        assert result["themes"][0]["strength"] == 0.5
        assert result["themes"][0]["segment_ids"] == []


class TestFormatTimecode:
    def test_format_seconds(self) -> None:
        assert format_timecode(45) == "00:00:45"

    def test_format_minutes(self) -> None:
        assert format_timecode(125) == "00:02:05"

    def test_format_hours(self) -> None:
        assert format_timecode(3725) == "01:02:05"


class TestFormatTranscriptForPrompt:
    def test_format_empty_segments(self) -> None:
        result = format_transcript_for_prompt([])
        assert result == ""

    def test_format_single_segment(self) -> None:
        segments = [
            {
                "segment_id": "seg_001",
                "start": 0.0,
                "end": 5.0,
                "text": "Hello world",
                "delivery": {"delivery_label": "moderate energy"},
            }
        ]
        result = format_transcript_for_prompt(segments)
        assert "seg_001" in result
        assert "Hello world" in result
        assert "moderate energy" in result


class TestLLMClient:
    def test_privacy_mode_local_blocks_cloud(self) -> None:
        """Test that local privacy mode blocks cloud backends."""
        from plotline.exceptions import LLMPrivacyError
        from plotline.llm.client import LLMClient

        client = LLMClient(backend="claude", privacy_mode="local")

        try:
            client._check_privacy()
            assert False, "Should have raised LLMPrivacyError"
        except LLMPrivacyError:
            pass

    def test_privacy_mode_hybrid_allows_cloud(self) -> None:
        """Test that hybrid privacy mode allows cloud backends."""
        from plotline.llm.client import LLMClient

        client = LLMClient(backend="claude", privacy_mode="hybrid")
        client._check_privacy()

    def test_local_backend_always_allowed(self) -> None:
        """Test that local backends are always allowed."""
        from plotline.llm.client import LLMClient

        client = LLMClient(backend="ollama", privacy_mode="local")
        client._check_privacy()
