"""Tests for plotline.io module - JSON and text I/O utilities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plotline.io import read_json, read_text, write_json, write_text


class TestReadJson:
    def test_read_valid_json(self, tmp_path: Path) -> None:
        data = {"key": "value", "number": 42}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        result = read_json(json_file)

        assert result == data

    def test_read_json_with_unicode(self, tmp_path: Path) -> None:
        data = {"message": "Hello 世界"}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = read_json(json_file)

        assert result["message"] == "Hello 世界"

    def test_read_missing_file_raises(self, tmp_path: Path) -> None:
        json_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            read_json(json_file)

    def test_read_invalid_json_raises(self, tmp_path: Path) -> None:
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{not valid json}")

        with pytest.raises(json.JSONDecodeError):
            read_json(json_file)


class TestWriteJson:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        data = {"key": "value", "nested": {"a": 1}}

        output_path = tmp_path / "output.json"
        write_json(output_path, data)

        assert output_path.exists()

        with open(output_path) as f:
            result = json.load(f)

        assert result == data

    def test_pretty_prints_by_default(self, tmp_path: Path) -> None:
        data = {"key": "value"}

        output_path = tmp_path / "output.json"
        write_json(output_path, data)

        content = output_path.read_text()
        assert "\n" in content
        assert "  " in content

    def test_custom_indent(self, tmp_path: Path) -> None:
        data = {"key": "value"}

        output_path = tmp_path / "output.json"
        write_json(output_path, data, indent=4)

        content = output_path.read_text()
        assert "    " in content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        data = {"key": "value"}

        output_path = tmp_path / "subdir" / "nested" / "output.json"
        write_json(output_path, data)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_preserves_unicode(self, tmp_path: Path) -> None:
        data = {"message": "Hello 世界"}

        output_path = tmp_path / "output.json"
        write_json(output_path, data)

        with open(output_path, encoding="utf-8") as f:
            result = json.load(f)

        assert result["message"] == "Hello 世界"

    def test_does_not_escape_non_ascii(self, tmp_path: Path) -> None:
        data = {"emoji": "🎉"}

        output_path = tmp_path / "output.json"
        write_json(output_path, data)

        content = output_path.read_text()
        assert "🎉" in content
        assert "\\u" not in content


class TestReadText:
    def test_reads_text_file(self, tmp_path: Path) -> None:
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello, World!")

        result = read_text(text_file)

        assert result == "Hello, World!"

    def test_reads_unicode(self, tmp_path: Path) -> None:
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello 世界", encoding="utf-8")

        result = read_text(text_file)

        assert result == "Hello 世界"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        text_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            read_text(text_file)


class TestWriteText:
    def test_writes_text_file(self, tmp_path: Path) -> None:
        content = "Hello, World!"

        output_path = tmp_path / "output.txt"
        write_text(output_path, content)

        assert output_path.exists()
        assert output_path.read_text() == content

    def test_writes_unicode(self, tmp_path: Path) -> None:
        content = "Hello 世界 🎉"

        output_path = tmp_path / "output.txt"
        write_text(output_path, content)

        assert output_path.read_text(encoding="utf-8") == content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        content = "Test content"

        output_path = tmp_path / "subdir" / "nested" / "output.txt"
        write_text(output_path, content)

        assert output_path.exists()
        assert output_path.parent.exists()


class TestAtomicWrites:
    def test_write_json_atomic(self, tmp_path: Path) -> None:
        data = {"key": "value"}

        output_path = tmp_path / "output.json"
        write_json(output_path, data)

        assert output_path.exists()
        assert not any(tmp_path.glob("*.tmp"))

    def test_write_text_atomic(self, tmp_path: Path) -> None:
        content = "Test content"

        output_path = tmp_path / "output.txt"
        write_text(output_path, content)

        assert output_path.exists()
        assert not any(tmp_path.glob("*.tmp"))

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        output_path = tmp_path / "output.json"
        output_path.write_text(json.dumps({"old": "data"}))

        new_data = {"new": "value"}
        write_json(output_path, new_data)

        with open(output_path) as f:
            result = json.load(f)

        assert result == new_data
