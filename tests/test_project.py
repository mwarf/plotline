"""Tests for plotline.project module."""

from __future__ import annotations

from pathlib import Path

from plotline.project import Project, generate_interview_id, write_json


class TestProject:
    def test_project_paths(self, tmp_path: Path) -> None:
        project = Project(tmp_path / "my-project")
        assert project.path.name == "my-project"
        assert project.source_dir.name == "source"
        assert project.data_dir.name == "data"

    def test_create_project(self, tmp_path: Path) -> None:
        project = Project(tmp_path / "new-project")
        project.create(profile="documentary")
        assert project.config_path.exists()
        assert project.manifest_path.exists()
        assert project.source_dir.exists()

    def test_load_manifest(self, tmp_project: Path) -> None:
        manifest_data = {"project_name": "test", "interviews": []}
        write_json(tmp_project / "interviews.json", manifest_data)
        project = Project(tmp_project)
        manifest = project.load_manifest()
        assert manifest["project_name"] == "test"

    def test_get_interview(self, tmp_project: Path) -> None:
        manifest_data = {
            "project_name": "test",
            "interviews": [
                {"id": "interview_001", "filename": "test.mov"},
            ],
        }
        write_json(tmp_project / "interviews.json", manifest_data)
        project = Project(tmp_project)
        interview = project.get_interview("interview_001")
        assert interview is not None
        assert interview["filename"] == "test.mov"


class TestGenerateInterviewId:
    def test_first_interview(self) -> None:
        manifest = {"interviews": []}
        interview_id = generate_interview_id(manifest)
        assert interview_id == "interview_001"

    def test_next_interview(self) -> None:
        manifest = {"interviews": [{"id": "interview_001"}]}
        interview_id = generate_interview_id(manifest)
        assert interview_id == "interview_002"

    def test_gap_in_ids(self) -> None:
        manifest = {"interviews": [{"id": "interview_001"}, {"id": "interview_003"}]}
        interview_id = generate_interview_id(manifest)
        assert interview_id == "interview_002"
