"""
plotline.exceptions - Custom exception classes.

All Plotline-specific exceptions inherit from PlotlineError.
"""


class PlotlineError(Exception):
    """Base exception for all Plotline errors."""

    pass


class ConfigError(PlotlineError):
    """Configuration loading or validation error."""

    pass


class ProjectError(PlotlineError):
    """Project directory or manifest error."""

    pass


class ExtractionError(PlotlineError):
    """Audio extraction error."""

    pass


class TranscriptionError(PlotlineError):
    """Transcription error."""

    pass


class AnalysisError(PlotlineError):
    """Delivery analysis error."""

    pass


class LLMError(PlotlineError):
    """LLM backend or prompt error."""

    pass


class LLMPrivacyError(LLMError):
    """Attempted to use cloud LLM in local privacy mode."""

    pass


class LLMResponseError(LLMError):
    """LLM returned malformed or unexpected response."""

    pass


class ExportError(PlotlineError):
    """Timeline export error."""

    pass


class ValidationError(PlotlineError):
    """Data validation error."""

    pass


class DependencyError(PlotlineError):
    """Required dependency missing or misconfigured."""

    def __init__(self, dependency: str, message: str, install_hint: str | None = None):
        self.dependency = dependency
        self.message = message
        self.install_hint = install_hint
        super().__init__(f"{dependency}: {message}")
