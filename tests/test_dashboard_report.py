"""Tests for plotline.reports.dashboard module."""

from __future__ import annotations

import json
from pathlib import Path

from plotline.reports.dashboard import (
    count_completed_stages,
    generate_dashboard,
    get_segment_count,
    get_selected_duration,
    get_stage_status,
)


class TestGetStageStatus:
    def test_all_completed(self) -> None:
        stages = {
            "extracted": True,
            "transcribed": True,
            "diarized": True,
            "analyzed": True,
            "enriched": True,
            "themes": True,
            "reviewed": True,
        }
        result = get_stage_status(stages)
        assert len(result) == 7
        assert all(s["status"] == "completed" for s in result)

    def test_all_pending(self) -> None:
        result = get_stage_status({})
        assert len(result) == 7
        assert all(s["status"] == "pending" for s in result)

    def test_partial_stages(self) -> None:
        stages = {"extracted": True, "transcribed": True, "analyzed": False}
        result = get_stage_status(stages)
        completed = [s for s in result if s["status"] == "completed"]
        pending = [s for s in result if s["status"] == "pending"]
        assert len(completed) == 2
        assert len(pending) == 5

    def test_stage_order_preserved(self) -> None:
        result = get_stage_status({})
        keys = [s["key"] for s in result]
        assert keys == [
            "extracted",
            "transcribed",
            "diarized",
            "analyzed",
            "enriched",
            "themes",
            "reviewed",
        ]

    def test_stage_initials(self) -> None:
        result = get_stage_status({})
        initials = [s["initial"] for s in result]
        assert initials == ["Ext", "Trn", "Dia", "Ana", "Enr", "Thm", "Rev"]


class TestCountCompletedStages:
    def test_all_complete(self) -> None:
        interviews = [
            {
                "stages": {
                    "extracted": True,
                    "transcribed": True,
                    "analyzed": True,
                    "enriched": True,
                }
            }
        ]
        assert count_completed_stages(interviews) == 1

    def test_none_complete(self) -> None:
        interviews = [{"stages": {"extracted": True, "transcribed": False}}]
        assert count_completed_stages(interviews) == 0

    def test_empty_list(self) -> None:
        assert count_completed_stages([]) == 0

    def test_mixed(self) -> None:
        interviews = [
            {
                "stages": {
                    "extracted": True,
                    "transcribed": True,
                    "analyzed": True,
                    "enriched": True,
                }
            },
            {"stages": {"extracted": True, "transcribed": True}},
        ]
        assert count_completed_stages(interviews) == 1


class TestGetSelectedDuration:
    def test_no_selections_file(self, tmp_project: Path) -> None:
        assert get_selected_duration(tmp_project) == 0.0

    def test_empty_segments(self, tmp_project: Path) -> None:
        selections_path = tmp_project / "data" / "selections.json"
        selections_path.write_text(json.dumps({"segments": []}))
        assert get_selected_duration(tmp_project) == 0.0

    def test_sums_durations(self, tmp_project: Path) -> None:
        selections_path = tmp_project / "data" / "selections.json"
        selections_path.write_text(
            json.dumps(
                {
                    "segments": [
                        {"start": 0, "end": 10},
                        {"start": 20, "end": 35},
                    ]
                }
            )
        )
        assert get_selected_duration(tmp_project) == 25.0


class TestGetSegmentCount:
    def test_no_file(self, tmp_project: Path) -> None:
        assert get_segment_count(tmp_project, "nonexistent") == 0

    def test_uses_segment_count_field(self, tmp_project: Path) -> None:
        segments_path = tmp_project / "data" / "segments" / "int_001.json"
        segments_path.write_text(json.dumps({"segment_count": 42, "segments": []}))
        assert get_segment_count(tmp_project, "int_001") == 42

    def test_falls_back_to_len(self, tmp_project: Path) -> None:
        segments_path = tmp_project / "data" / "segments" / "int_002.json"
        segments_path.write_text(json.dumps({"segments": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}))
        assert get_segment_count(tmp_project, "int_002") == 3


class TestGenerateDashboard:
    def test_generates_report(self, tmp_project: Path) -> None:
        manifest = {
            "project_name": "dash-test",
            "created": "2026-02-15",
            "profile": "documentary",
            "interviews": [
                {
                    "id": "int_001",
                    "filename": "alice.mov",
                    "duration_seconds": 120.0,
                    "stages": {"extracted": True, "transcribed": True},
                }
            ],
        }
        output = generate_dashboard(tmp_project, manifest, open_browser=False)

        assert output.exists()
        assert output.name == "dashboard.html"
        content = output.read_text()
        assert "dash-test" in content
        assert "alice.mov" in content

    def test_uses_friendly_duration(self, tmp_project: Path) -> None:
        """Dashboard should use friendly format (e.g. '2m') not timecode ('2:00')."""
        manifest = {
            "project_name": "dur-test",
            "interviews": [
                {
                    "id": "int_001",
                    "filename": "test.mov",
                    "duration_seconds": 120.0,
                    "stages": {},
                }
            ],
        }
        output = generate_dashboard(tmp_project, manifest, open_browser=False)
        content = output.read_text()
        assert "2m" in content

    def test_custom_output_path(self, tmp_project: Path) -> None:
        manifest = {"project_name": "custom", "interviews": []}
        custom = tmp_project / "my_dashboard.html"
        output = generate_dashboard(tmp_project, manifest, output_path=custom, open_browser=False)
        assert output == custom
        assert custom.exists()

    def test_nav_bar_present(self, tmp_project: Path) -> None:
        """Dashboard report includes the shared navigation bar."""
        manifest = {
            "project_name": "nav-test",
            "interviews": [
                {"id": "int_001", "filename": "test.mov", "duration_seconds": 60.0, "stages": {}}
            ],
        }
        output = generate_dashboard(tmp_project, manifest, open_browser=False)
        content = output.read_text()
        assert "plotline-nav" in content
        assert 'href="dashboard.html"' in content
        assert 'href="review.html"' in content
        assert "transcript_int_001.html" in content

    def test_no_interviews(self, tmp_project: Path) -> None:
        manifest = {"project_name": "empty", "interviews": []}
        output = generate_dashboard(tmp_project, manifest, open_browser=False)
        assert output.exists()
        content = output.read_text()
        assert "empty" in content

    def test_brief_detected(self, tmp_project: Path) -> None:
        brief_path = tmp_project / "brief.json"
        brief_path.write_text(
            json.dumps(
                {
                    "name": "My Brief",
                    "summary": "A test brief.",
                    "audience": "Documentary lovers",
                    "tone_direction": "Serious and moody",
                    "avoid_topics": ["politics", "religion"],
                    "target_duration": "90 seconds",
                }
            )
        )

        manifest = {"project_name": "brief-test", "interviews": []}
        output = generate_dashboard(tmp_project, manifest, open_browser=False)
        content = output.read_text()

        assert "My Brief" in content
        assert "Documentary lovers" in content
        assert "Serious and moody" in content
        assert "politics" in content
        assert "religion" in content
        assert "90 seconds" in content
