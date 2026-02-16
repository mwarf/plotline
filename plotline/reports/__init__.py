"""
plotline.reports - HTML report generation.

Generates self-contained HTML reports:
- Pipeline dashboard
- Transcript & delivery report
- Selection review report
- Project summary report
"""

from __future__ import annotations

from plotline.reports.dashboard import generate_dashboard
from plotline.reports.generator import ReportGenerator
from plotline.reports.review import generate_review
from plotline.reports.summary import generate_summary

__all__ = ["ReportGenerator", "generate_dashboard", "generate_review", "generate_summary"]
