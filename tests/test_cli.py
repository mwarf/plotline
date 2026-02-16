"""Tests for plotline CLI commands."""

from __future__ import annotations

import os
from pathlib import Path

from typer.testing import CliRunner

from plotline.cli import app

runner = CliRunner()


class TestInitCommand:
    def test_init_creates_project_directory(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", "test-project", "-d", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "test-project").exists()
        assert (tmp_path / "test-project" / "plotline.yaml").exists()
        assert (tmp_path / "test-project" / "interviews.json").exists()

    def test_init_with_profile(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", "brand-project", "-p", "brand", "-d", str(tmp_path)])
        assert result.exit_code == 0
        config_file = tmp_path / "brand-project" / "plotline.yaml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "brand" in content

    def test_init_fails_if_directory_exists(self, tmp_path: Path) -> None:
        (tmp_path / "existing").mkdir()
        result = runner.invoke(app, ["init", "existing", "-d", str(tmp_path)])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_init_creates_subdirectories(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", "test", "-d", str(tmp_path)])
        assert result.exit_code == 0
        project = tmp_path / "test"
        assert (project / "source").is_dir()
        assert (project / "data").is_dir()
        assert (project / "data" / "transcripts").is_dir()
        assert (project / "data" / "delivery").is_dir()
        assert (project / "export").is_dir()
        assert (project / "reports").is_dir()
        assert (project / "prompts").is_dir()


class TestAddCommand:
    def test_add_fails_outside_project(self, tmp_path: Path) -> None:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["add", "video.mp4"])
            assert result.exit_code == 1
            assert "Not in a Plotline project" in result.output
        finally:
            os.chdir(original_cwd)

    def test_add_nonexistent_file(self, tmp_project: Path) -> None:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_project)
            result = runner.invoke(app, ["add", "nonexistent.mp4"])
            assert result.exit_code == 0
            assert "Not found" in result.output
        finally:
            os.chdir(original_cwd)

    def test_add_creates_interview_entry(self, tmp_project: Path) -> None:
        import json

        video_file = tmp_project / "test.mp4"
        video_file.write_bytes(b"fake video content")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_project)
            runner.invoke(app, ["add", str(video_file)])
        finally:
            os.chdir(original_cwd)

        manifest_path = tmp_project / "interviews.json"
        with open(manifest_path) as f:
            updated = json.load(f)

        if updated["interviews"]:
            assert updated["interviews"][0]["filename"] == "test.mp4"
            assert updated["interviews"][0]["stages"]["extracted"] is False
