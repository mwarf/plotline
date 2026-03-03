"""
plotline.reports - HTML report generation.

Generates self-contained HTML reports:
- Pipeline dashboard
- Transcript & delivery report
- Selection review report
- Project summary report
- Theme explorer report
- Best-take comparison report
- Coverage matrix report
"""

from __future__ import annotations

from plotline.reports.compare import generate_compare_report
from plotline.reports.coverage import generate_coverage
from plotline.reports.dashboard import generate_dashboard
from plotline.reports.generator import ReportGenerator
from plotline.reports.review import generate_review
from plotline.reports.summary import generate_summary
from plotline.reports.themes import generate_themes_report
from plotline.reports.transcript import generate_transcript

__all__ = [
    "ReportGenerator",
    "generate_compare_report",
    "generate_coverage",
    "generate_dashboard",
    "generate_review",
    "generate_summary",
    "generate_themes_report",
    "generate_transcript",
]
