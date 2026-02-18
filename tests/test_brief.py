"""Tests for plotline.brief module - creative brief parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plotline.brief import (
    normalize_key_messages,
    parse_brief,
    parse_markdown_brief,
    parse_yaml_brief,
    save_brief,
)


class TestNormalizeKeyMessages:
    def test_strings_normalized(self) -> None:
        messages = ["First message", "Second message", "Third message"]
        result = normalize_key_messages(messages)

        assert len(result) == 3
        assert result[0]["id"] == "msg_001"
        assert result[0]["text"] == "First message"
        assert result[1]["id"] == "msg_002"
        assert result[2]["id"] == "msg_003"

    def test_dicts_with_ids_preserved(self) -> None:
        messages = [
            {"id": "custom_001", "text": "Custom message"},
            {"id": "custom_002", "text": "Another message"},
        ]
        result = normalize_key_messages(messages)

        assert result[0]["id"] == "custom_001"
        assert result[1]["id"] == "custom_002"

    def test_dicts_without_ids_get_generated(self) -> None:
        messages = [
            {"text": "Message one"},
            {"text": "Message two"},
        ]
        result = normalize_key_messages(messages)

        assert result[0]["id"] == "msg_001"
        assert result[0]["text"] == "Message one"
        assert result[1]["id"] == "msg_002"

    def test_mixed_formats(self) -> None:
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
        result = normalize_key_messages([])
        assert result == []


class TestParseMarkdownBrief:
    def test_empty_content(self) -> None:
        result = parse_markdown_brief("")
        assert result["key_messages"] == []
        assert result["audience"] is None

    def test_key_messages_list(self) -> None:
        content = """# Key Messages

- First key point
- Second key point
- Third key point
"""
        result = parse_markdown_brief(content)
        assert len(result["key_messages"]) == 3
        assert result["key_messages"][0] == "First key point"

    def test_all_sections(self) -> None:
        content = """# Key Messages

- Innovation is key
- Community matters

# Audience

Decision makers in tech

# Target Duration

3-5 minutes

# Tone

Professional but warm

# Must Include

- Customer stories
- Product demo

# Avoid

- Jargon
- Competitor names
"""
        result = parse_markdown_brief(content)

        assert len(result["key_messages"]) == 2
        assert result["audience"] == "Decision makers in tech"
        assert result["target_duration"] == "3-5 minutes"
        assert result["tone_direction"] == "Professional but warm"
        assert len(result["must_include_topics"]) == 2
        assert len(result["avoid_topics"]) == 2

    def test_single_paragraph_key_messages(self) -> None:
        content = """# Key Messages

This is a single paragraph describing the key message.
"""
        result = parse_markdown_brief(content)
        assert len(result["key_messages"]) == 1
        assert "single paragraph" in result["key_messages"][0]


class TestParseYamlBrief:
    def test_empty_content(self) -> None:
        result = parse_yaml_brief("")
        assert result["key_messages"] == []
        assert result["audience"] is None

    def test_none_content(self) -> None:
        result = parse_yaml_brief("null")
        assert result["key_messages"] == []

    def test_snake_case_keys(self) -> None:
        content = """
key_messages:
  - First message
  - Second message
audience: Tech professionals
target_duration: 3 minutes
tone_direction: Professional
must_include_topics:
  - Demo
avoid_topics:
  - Jargon
"""
        result = parse_yaml_brief(content)

        assert len(result["key_messages"]) == 2
        assert result["audience"] == "Tech professionals"
        assert result["target_duration"] == "3 minutes"

    def test_camel_case_keys(self) -> None:
        content = """
keyMessages:
  - First message
audience: Tech professionals
targetDuration: 3 minutes
toneDirection: Professional
mustIncludeTopics:
  - Demo
avoidTopics:
  - Jargon
"""
        result = parse_yaml_brief(content)

        assert len(result["key_messages"]) == 1
        assert result["audience"] == "Tech professionals"

    def test_extra_fields_preserved(self) -> None:
        content = """
name: My Brief
key_messages:
  - Message one
title: Project Title
summary: A summary
"""
        result = parse_yaml_brief(content)

        assert result["name"] == "My Brief"
        assert result["title"] == "Project Title"
        assert result["summary"] == "A summary"


class TestParseBrief:
    def test_markdown_file(self, tmp_path: Path) -> None:
        brief_file = tmp_path / "brief.md"
        brief_file.write_text(
            """# Key Messages

- First point
- Second point

# Audience

General public
"""
        )

        result = parse_brief(brief_file)

        assert len(result["key_messages"]) == 2
        assert result["audience"] == "General public"
        assert result["source_file"] == str(brief_file)
        assert result["name"] == "brief"

    def test_yaml_file(self, tmp_path: Path) -> None:
        brief_file = tmp_path / "brief.yaml"
        brief_file.write_text(
            """
key_messages:
  - First point
  - Second point
audience: General public
"""
        )

        result = parse_brief(brief_file)

        assert len(result["key_messages"]) == 2
        assert result["audience"] == "General public"

    def test_yml_extension(self, tmp_path: Path) -> None:
        brief_file = tmp_path / "brief.yml"
        brief_file.write_text(
            """
key_messages:
  - Message
"""
        )

        result = parse_brief(brief_file)
        assert len(result["key_messages"]) == 1

    def test_key_messages_normalized(self, tmp_path: Path) -> None:
        brief_file = tmp_path / "brief.md"
        brief_file.write_text(
            """# Key Messages

- First point
- Second point
"""
        )

        result = parse_brief(brief_file)

        assert result["key_messages"][0]["id"] == "msg_001"
        assert result["key_messages"][0]["text"] == "First point"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        brief_file = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError, match="Brief file not found"):
            parse_brief(brief_file)

    def test_no_key_messages_raises(self, tmp_path: Path) -> None:
        brief_file = tmp_path / "brief.md"
        brief_file.write_text("# Audience\n\nSome audience\n")

        with pytest.raises(ValueError, match="at least one key message"):
            parse_brief(brief_file)


class TestSaveBrief:
    def test_saves_json_file(self, tmp_path: Path) -> None:
        brief_data = {
            "key_messages": [{"id": "msg_001", "text": "Test message"}],
            "audience": "Test audience",
        }

        output_path = tmp_path / "brief.json"
        save_brief(brief_data, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            saved = json.load(f)

        assert saved["key_messages"][0]["text"] == "Test message"
        assert "parsed_at" in saved

    def test_parsed_at_is_iso8601(self, tmp_path: Path) -> None:
        brief_data = {"key_messages": [{"id": "msg_001", "text": "Test"}]}

        output_path = tmp_path / "brief.json"
        save_brief(brief_data, output_path)

        with open(output_path) as f:
            saved = json.load(f)

        assert "parsed_at" in saved
        assert "T" in saved["parsed_at"]
        assert "+" in saved["parsed_at"] or "Z" in saved["parsed_at"]
