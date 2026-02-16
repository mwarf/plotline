"""
plotline.reports.generator - Jinja2-based report generator.

Produces self-contained HTML reports with embedded CSS and JavaScript.
"""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class ReportGenerator:
    """Jinja2-based HTML report generator."""

    def __init__(self, template_dir: Path | None = None):
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(
        self,
        template_name: str,
        data: dict[str, Any],
        output_path: Path,
    ) -> Path:
        """Render a report template to an HTML file.

        Args:
            template_name: Name of the template file
            data: Data dictionary to inject into template
            output_path: Path to write the HTML file

        Returns:
            Path to the generated file
        """
        template = self.env.get_template(template_name)

        data_json = json.dumps(data, indent=2, ensure_ascii=False)

        html = template.render(data=data, data_json=data_json, **data)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

        return output_path

    def open_in_browser(self, path: Path) -> None:
        """Open a file in the default browser.

        Args:
            path: Path to HTML file
        """
        webbrowser.open(f"file://{path.resolve()}")
