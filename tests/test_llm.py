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

    def test_parse_truncated_json_with_incomplete_object(self) -> None:
        """Test parsing truncated JSON with incomplete object."""
        response = '{"themes": [{"name": "A"}, {"name": "B", "description": "foo"'
        result = parse_llm_json(response)
        assert len(result["themes"]) >= 1
        assert result["themes"][0]["name"] == "A"

    def test_parse_truncated_json_with_incomplete_key(self) -> None:
        """Test parsing truncated JSON with incomplete key."""
        response = '{"themes": [{"name": "A"}, {"name": "B", "descri'
        result = parse_llm_json(response)
        assert len(result["themes"]) >= 1
        assert result["themes"][0]["name"] == "A"

    def test_parse_truncated_json_recovers_first_complete_items(self) -> None:
        """Test that truncated JSON recovery keeps complete items."""
        response = '{"themes": [{"name": "First"}, {"name": "Second"}, {"name": "Third", "incom'
        result = parse_llm_json(response)
        assert len(result["themes"]) >= 2
        assert result["themes"][0]["name"] == "First"
        assert result["themes"][1]["name"] == "Second"

    def test_parse_missing_closing_braces(self) -> None:
        """Test parsing JSON with missing closing braces."""
        response = '{"themes": [{"name": "A"}]'
        result = parse_llm_json(response)
        assert result["themes"][0]["name"] == "A"

    def test_parse_missing_closing_brackets(self) -> None:
        """Test parsing JSON with missing closing brackets."""
        response = '{"themes": [{"name": "A"}'
        result = parse_llm_json(response)
        assert len(result["themes"]) >= 1


class TestValidateThemesResponse:
    def test_validate_basic_response(self) -> None:
        """Test validating a basic themes response."""
        data = {
            "themes": [{"name": "Connection to water", "segment_ids": ["interview_001_seg_001"]}]
        }
        result = validate_themes_response(data, "interview_001")
        assert len(result["themes"]) == 1
        assert result["themes"][0]["name"] == "Connection to water"

    def test_validate_adds_missing_fields(self) -> None:
        """Test that validation adds missing optional fields."""
        data = {"themes": [{"name": "Test"}]}
        result = validate_themes_response(data, "interview_001")
        assert result["themes"][0]["strength"] == 0.5
        assert result["themes"][0]["segment_ids"] == []

    def test_validate_filters_invalid_segment_ids(self) -> None:
        """Test that segment_ids not matching interview_id are filtered."""
        data = {
            "themes": [
                {
                    "name": "Test",
                    "segment_ids": [
                        "interview_001_seg_001",  # Valid
                        "interview_002_seg_005",  # Wrong interview
                        "seg_999",  # Wrong format
                    ],
                }
            ]
        }
        result = validate_themes_response(data, "interview_001")
        assert result["themes"][0]["segment_ids"] == ["interview_001_seg_001"]

    def test_validate_rejects_themes_as_non_list(self) -> None:
        """Test that themes must be a list."""
        from plotline.exceptions import LLMResponseError

        data = {"themes": "not a list"}
        try:
            validate_themes_response(data, "interview_001")
            assert False, "Should have raised LLMResponseError"
        except LLMResponseError as e:
            assert "must be a list" in str(e)

    def test_validate_rejects_theme_as_non_dict(self) -> None:
        """Test that each theme must be a dict."""
        from plotline.exceptions import LLMResponseError

        data = {"themes": ["not a dict"]}
        try:
            validate_themes_response(data, "interview_001")
            assert False, "Should have raised LLMResponseError"
        except LLMResponseError as e:
            assert "must be an object" in str(e)

    def test_validate_safe_strength_coercion(self) -> None:
        """Test that strength is safely coerced to float."""
        data = {"themes": [{"name": "Test", "strength": "very strong"}]}
        result = validate_themes_response(data, "interview_001")
        assert result["themes"][0]["strength"] == 0.5  # Falls back to default

    def test_validate_numeric_strength(self) -> None:
        """Test that numeric strength is preserved."""
        data = {"themes": [{"name": "Test", "strength": 0.85}]}
        result = validate_themes_response(data, "interview_001")
        assert result["themes"][0]["strength"] == 0.85

    def test_validate_string_numeric_strength(self) -> None:
        """Test that string numeric strength is converted."""
        data = {"themes": [{"name": "Test", "strength": "0.75"}]}
        result = validate_themes_response(data, "interview_001")
        assert result["themes"][0]["strength"] == 0.75

    def test_validate_intersections_filtered_by_interview_id(self) -> None:
        """Test that intersections are validated against interview_id."""
        data = {
            "themes": [{"name": "Test"}],
            "intersections": [
                {"segment_id": "interview_001_seg_010", "themes": ["t1", "t2"]},
                {"segment_id": "interview_002_seg_005", "themes": ["t3"]},  # Wrong interview
            ],
        }
        result = validate_themes_response(data, "interview_001")
        assert len(result["intersections"]) == 1
        assert result["intersections"][0]["segment_id"] == "interview_001_seg_010"

    def test_validate_intersections_handles_non_dict(self) -> None:
        """Test that non-dict intersections are skipped."""
        data = {
            "themes": [{"name": "Test"}],
            "intersections": ["not a dict", {"segment_id": "interview_001_seg_010", "themes": []}],
        }
        result = validate_themes_response(data, "interview_001")
        assert len(result["intersections"]) == 1

    def test_validate_intersections_handles_non_list(self) -> None:
        """Test that non-list intersections field is handled."""
        data = {"themes": [{"name": "Test"}], "intersections": "not a list"}
        result = validate_themes_response(data, "interview_001")
        assert result["intersections"] == []

    def test_validate_off_message_segments_filtered(self) -> None:
        """Test that off_message_segments are filtered by interview_id."""
        data = {
            "themes": [{"name": "Test"}],
            "off_message_segments": [
                {"segment_id": "interview_001_seg_020", "reason": "Off topic"},
                {"segment_id": "interview_002_seg_010", "reason": "Wrong interview"},
            ],
        }
        result = validate_themes_response(data, "interview_001")
        assert len(result["off_message_segments"]) == 1
        assert result["off_message_segments"][0]["segment_id"] == "interview_001_seg_020"

    def test_validate_off_message_segments_handles_non_list(self) -> None:
        """Test that non-list off_message_segments is handled."""
        data = {"themes": [{"name": "Test"}], "off_message_segments": "not a list"}
        result = validate_themes_response(data, "interview_001")
        assert "off_message_segments" not in result

    def test_validate_segment_ids_handles_non_list(self) -> None:
        """Test that non-list segment_ids is handled."""
        data = {"themes": [{"name": "Test", "segment_ids": "not a list"}]}
        result = validate_themes_response(data, "interview_001")
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

    def test_format_includes_speaker_when_present(self) -> None:
        """Test that speaker label is included when present."""
        segments = [
            {
                "segment_id": "seg_001",
                "start": 0.0,
                "end": 5.0,
                "text": "Hello world",
                "speaker": "SPEAKER_00",
            }
        ]
        result = format_transcript_for_prompt(segments)
        assert "Speaker: SPEAKER_00" in result

    def test_format_omits_speaker_when_none(self) -> None:
        """Test that speaker label is omitted when None."""
        segments = [
            {
                "segment_id": "seg_001",
                "start": 0.0,
                "end": 5.0,
                "text": "Hello world",
                "speaker": None,
            }
        ]
        result = format_transcript_for_prompt(segments)
        assert "Speaker:" not in result

    def test_format_omits_speaker_when_missing(self) -> None:
        """Test that speaker label is omitted when field is absent."""
        segments = [
            {
                "segment_id": "seg_001",
                "start": 0.0,
                "end": 5.0,
                "text": "Hello world",
            }
        ]
        result = format_transcript_for_prompt(segments)
        assert "Speaker:" not in result

    def test_format_includes_speaker_and_delivery(self) -> None:
        """Test that both speaker and delivery are included."""
        segments = [
            {
                "segment_id": "seg_001",
                "start": 0.0,
                "end": 5.0,
                "text": "Hello world",
                "speaker": "SPEAKER_01",
                "delivery": {"delivery_label": "confident"},
            }
        ]
        result = format_transcript_for_prompt(segments)
        assert "Speaker: SPEAKER_01" in result
        assert "Delivery: confident" in result


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
