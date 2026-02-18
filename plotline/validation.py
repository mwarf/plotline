"""
plotline.validation - Dependency checks and validation utilities.

Validates environment, dependencies, and input files before processing.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from plotline.exceptions import DependencyError, ValidationError


def check_ffmpeg() -> dict[str, str]:
    """Check if FFmpeg and FFprobe are installed and get versions.

    Returns:
        Dict with 'ffmpeg_version' and 'ffprobe_version'

    Raises:
        DependencyError: If FFmpeg or FFprobe not found
    """
    result = {}

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise DependencyError(
            "ffmpeg",
            "FFmpeg not found in PATH",
            "Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)",
        )

    try:
        proc = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version_line = proc.stdout.split("\n")[0]
        result["ffmpeg_version"] = version_line.split()[2] if version_line else "unknown"
    except (subprocess.TimeoutExpired, IndexError):
        result["ffmpeg_version"] = "unknown"

    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        raise DependencyError(
            "ffprobe",
            "FFprobe not found in PATH",
            "Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)",
        )

    try:
        proc = subprocess.run(
            [ffprobe_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version_line = proc.stdout.split("\n")[0]
        result["ffprobe_version"] = version_line.split()[2] if version_line else "unknown"
    except (subprocess.TimeoutExpired, IndexError):
        result["ffprobe_version"] = "unknown"

    return result


def check_disk_space(path: Path, required_mb: int) -> dict[str, Any]:
    """Check if there's enough disk space at the given path.

    Args:
        path: Path to check (will use parent directory if file)
        required_mb: Required space in megabytes

    Returns:
        Dict with 'available_mb', 'required_mb', 'sufficient'

    Raises:
        ValidationError: If path doesn't exist
    """
    check_path = path.parent if path.is_file() else path

    if not check_path.exists():
        check_path = check_path.parent

    try:
        stat = shutil.disk_usage(check_path)
        available_mb = stat.free // (1024 * 1024)

        return {
            "available_mb": available_mb,
            "required_mb": required_mb,
            "sufficient": available_mb >= required_mb,
        }
    except OSError as e:
        raise ValidationError(f"Cannot check disk space: {e}") from e


def estimate_audio_size(duration_seconds: float, sample_rate: int = 16000) -> int:
    """Estimate WAV file size in MB for given duration.

    Args:
        duration_seconds: Audio duration in seconds
        sample_rate: Sample rate (default 16000 for 16kHz mono)

    Returns:
        Estimated size in megabytes
    """
    bytes_per_sample = 2
    channels = 1
    bytes_per_second = sample_rate * channels * bytes_per_sample
    total_bytes = int(duration_seconds * bytes_per_second)
    return total_bytes // (1024 * 1024)


def validate_video_file(path: Path) -> dict[str, Any]:
    """Validate a video file exists and has required properties.

    Args:
        path: Path to video file

    Returns:
        Dict with validation results

    Raises:
        ValidationError: If file doesn't exist or is invalid
    """
    if not path.exists():
        raise ValidationError(f"File not found: {path}")

    if not path.is_file():
        raise ValidationError(f"Not a file: {path}")

    return {
        "path": str(path),
        "exists": True,
        "size_mb": path.stat().st_size // (1024 * 1024),
    }


def check_audio_track(video_path: Path) -> dict[str, Any]:
    """Check if video file has an audio track.

    Args:
        video_path: Path to video file

    Returns:
        Dict with 'has_audio', 'audio_codec', 'sample_rate', 'channels'

    Raises:
        DependencyError: If ffprobe not available
        ValidationError: If file doesn't exist
    """
    from plotline.project import probe_video

    try:
        metadata = probe_video(video_path)
        has_audio = metadata.get("sample_rate") is not None

        return {
            "has_audio": has_audio,
            "audio_codec": metadata.get("audio_codec"),
            "sample_rate": metadata.get("sample_rate"),
            "channels": metadata.get("audio_channels"),
        }
    except Exception as e:
        return {
            "has_audio": False,
            "error": str(e),
        }


def validate_interview_duration(duration_seconds: float) -> dict[str, Any]:
    """Validate interview duration and return warnings.

    Args:
        duration_seconds: Interview duration in seconds

    Returns:
        Dict with 'valid', 'warnings', 'duration_formatted'
    """
    warnings = []
    valid = True

    if duration_seconds < 120:
        warnings.append(
            "Interview is very short (<2 minutes). May not have enough content for analysis."
        )
        valid = True
    elif duration_seconds > 7200:
        warnings.append("Interview is very long (>2 hours). Processing may take significant time.")
        valid = True

    hours = int(duration_seconds // 3600)
    minutes = int((duration_seconds % 3600) // 60)
    seconds = int(duration_seconds % 60)

    if hours > 0:
        duration_formatted = f"{hours}h {minutes}m {seconds}s"
    else:
        duration_formatted = f"{minutes}m {seconds}s"

    return {
        "valid": valid,
        "warnings": warnings,
        "duration_formatted": duration_formatted,
        "duration_seconds": duration_seconds,
    }


def check_ollama_running(model: str | None = None) -> dict[str, Any]:
    """Check if Ollama server is running and optionally if a model is available.

    Args:
        model: Optional model name to check

    Returns:
        Dict with 'running', 'model_available', 'error'
    """
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                import json

                data = json.loads(response.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]

                model_available = True
                if model:
                    model_available = any(model in m for m in models)

                return {
                    "running": True,
                    "model_available": model_available,
                    "models": models,
                }
    except urllib.error.URLError:
        return {
            "running": False,
            "model_available": False,
            "error": "Ollama server not running. Start with: ollama serve",
        }
    except Exception as e:
        return {
            "running": False,
            "model_available": False,
            "error": str(e),
        }

    return {"running": False, "model_available": False, "error": "Unknown error"}


def validate_llm_config(config: Any) -> dict[str, Any]:
    """Validate LLM configuration.

    Args:
        config: Config object with llm settings

    Returns:
        Dict with validation results
    """
    result = {"valid": True, "warnings": [], "errors": []}

    backend = config.llm_backend

    if backend == "ollama":
        ollama_status = check_ollama_running(config.llm_model)
        if not ollama_status["running"]:
            result["errors"].append(ollama_status.get("error", "Ollama not running"))
            result["valid"] = False
        elif not ollama_status["model_available"]:
            result["warnings"].append(
                f"Model '{config.llm_model}' may not be pulled. Run: ollama pull {config.llm_model}"
            )

    return result


def run_preflight_checks(
    project_path: Path,
    config: Any,
    video_files: list[Path] | None = None,
) -> dict[str, Any]:
    """Run all preflight checks before starting pipeline.

    Args:
        project_path: Project directory path
        config: Config object
        video_files: Optional list of video files to validate

    Returns:
        Dict with all check results
    """
    results = {
        "passed": True,
        "checks": {},
    }

    try:
        results["checks"]["ffmpeg"] = check_ffmpeg()
    except DependencyError as e:
        results["checks"]["ffmpeg"] = {"error": str(e), "install_hint": e.install_hint}
        results["passed"] = False

    try:
        disk = check_disk_space(project_path, 1000)
        results["checks"]["disk_space"] = disk
        if not disk["sufficient"]:
            results["passed"] = False
    except ValidationError as e:
        results["checks"]["disk_space"] = {"error": str(e)}
        results["passed"] = False

    results["checks"]["llm"] = validate_llm_config(config)
    if results["checks"]["llm"].get("errors"):
        results["passed"] = False

    if video_files:
        results["checks"]["video_files"] = []
        for vf in video_files:
            try:
                validate_video_file(vf)
                audio = check_audio_track(vf)
                file_result = {"path": str(vf), "valid": True, **audio}
                if not audio.get("has_audio"):
                    file_result["warning"] = "No audio track detected"
                results["checks"]["video_files"].append(file_result)
            except ValidationError as e:
                results["checks"]["video_files"].append(
                    {"path": str(vf), "valid": False, "error": str(e)}
                )
                results["passed"] = False

    return results
