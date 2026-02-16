"""
plotline.analyze.scoring - Composite delivery score calculation.

Normalizes raw metrics to 0-1 scales and computes weighted composite
scores per segment. Generates human-readable delivery labels.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def normalize_metrics(
    raw_metrics: list[dict[str, Any]],
) -> list[dict[str, float]]:
    """Normalize raw metrics to 0-1 scale per interview.

    Uses min-max normalization across all segments in the interview.

    Args:
        raw_metrics: List of raw metric dicts from delivery analysis

    Returns:
        List of normalized metric dicts
    """
    if not raw_metrics:
        return []

    all_energy = [m.get("rms_energy", 0) for m in raw_metrics]
    all_pitch_std = [m.get("pitch_std_hz", 0) for m in raw_metrics]
    all_speech_rate = [m.get("speech_rate_wpm", 0) for m in raw_metrics]
    all_pause = [m.get("pause_before_sec", 0) + m.get("pause_after_sec", 0) for m in raw_metrics]
    all_spectral = [m.get("spectral_centroid_mean", 0) for m in raw_metrics]
    all_zcr = [m.get("zero_crossing_rate", 0) for m in raw_metrics]

    def min_max_normalize(values: list[float]) -> list[float]:
        if not values:
            return []
        min_val = min(values)
        max_val = max(values)
        if max_val == min_val:
            return [0.5] * len(values)
        return [(v - min_val) / (max_val - min_val) for v in values]

    norm_energy = min_max_normalize(all_energy)
    norm_pitch = min_max_normalize(all_pitch_std)
    norm_rate = min_max_normalize(all_speech_rate)
    norm_pause = min_max_normalize(all_pause)
    norm_spectral = min_max_normalize(all_spectral)
    norm_zcr = min_max_normalize(all_zcr)

    normalized = []
    for i, raw in enumerate(raw_metrics):
        normalized.append(
            {
                "energy": round(norm_energy[i], 3),
                "pitch_variation": round(norm_pitch[i], 3),
                "speech_rate": round(norm_rate[i], 3),
                "pause_weight": round(norm_pause[i], 3),
                "spectral_brightness": round(norm_spectral[i], 3),
                "voice_texture": round(norm_zcr[i], 3),
            }
        )

    return normalized


def compute_composite_score(
    normalized: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Compute weighted composite delivery score.

    Args:
        normalized: Normalized metrics dict
        weights: Weight dict from config

    Returns:
        Composite score 0-1
    """
    score = 0.0
    total_weight = 0.0

    metric_keys = [
        ("energy", "energy"),
        ("pitch_variation", "pitch_variation"),
        ("speech_rate", "speech_rate"),
        ("pause_weight", "pause_weight"),
        ("spectral_brightness", "spectral_brightness"),
        ("voice_texture", "voice_texture"),
    ]

    for norm_key, weight_key in metric_keys:
        w = weights.get(weight_key, 0)
        v = normalized.get(norm_key, 0)
        score += v * w
        total_weight += w

    if total_weight > 0:
        score = score / total_weight

    return round(score, 3)


def generate_delivery_label(
    normalized: dict[str, float],
    raw: dict[str, Any],
) -> str:
    """Generate human-readable delivery label.

    Combines the most notable metrics into a descriptive phrase.

    Args:
        normalized: Normalized metrics dict
        raw: Raw metrics dict

    Returns:
        Human-readable delivery label string
    """
    parts = []

    energy = normalized.get("energy", 0.5)
    speech_rate = normalized.get("speech_rate", 0.5)
    pause = normalized.get("pause_weight", 0.5)
    pitch_var = normalized.get("pitch_variation", 0.5)

    if energy < 0.3:
        parts.append("quiet")
    elif energy > 0.7:
        parts.append("energetic")
    else:
        parts.append("moderate energy")

    if pitch_var < 0.3:
        parts.append("flat delivery")
    elif pitch_var > 0.7:
        parts.append("varied pitch")

    if speech_rate < 0.3:
        parts.append("slow pace")
    elif speech_rate > 0.7:
        parts.append("fast pace")
    else:
        parts.append("measured pace")

    pause_before = raw.get("pause_before_sec", 0)
    if pause_before > 2.0:
        parts.append(f"{pause_before:.1f}s pause before")

    label = ", ".join(parts[:3])

    if pause_before > 2.0 or pause > 0.7:
        label += " — reflective/weighted"
    elif energy > 0.7 and speech_rate > 0.7:
        label += " — animated"
    elif energy < 0.3 and speech_rate < 0.3:
        label += " — deliberate"

    return label


def add_scores_to_delivery(
    delivery: dict[str, Any],
    weights: dict[str, float],
) -> dict[str, Any]:
    """Add normalized scores and composite scores to delivery analysis.

    Args:
        delivery: Delivery analysis dict with raw metrics
        weights: Weight dict from config

    Returns:
        Updated delivery dict with normalized scores and labels
    """
    segments = delivery.get("segments", [])
    if not segments:
        return delivery

    raw_metrics = [s.get("raw", {}) for s in segments]
    normalized = normalize_metrics(raw_metrics)

    for i, seg in enumerate(segments):
        if i < len(normalized):
            seg["normalized"] = normalized[i]
            seg["composite_score"] = compute_composite_score(normalized[i], weights)
            seg["delivery_label"] = generate_delivery_label(normalized[i], seg.get("raw", {}))

    return delivery


def score_all_interviews(
    project_path: Path,
    manifest: dict[str, Any],
    weights: dict[str, float],
    force: bool = False,
    console=None,
) -> dict[str, Any]:
    """Add scores to delivery analysis for all interviews.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        weights: Delivery weights from config
        force: Re-score even if already done
        console: Optional rich console for output

    Returns:
        Dict with scoring summary
    """
    from rich.table import Table

    from plotline.project import read_json, write_json

    data_dir = project_path / "data"
    delivery_dir = data_dir / "delivery"

    results = {
        "scored": 0,
        "skipped": 0,
        "failed": 0,
    }

    table = Table(title="Delivery Scoring")
    table.add_column("Interview", style="cyan")
    table.add_column("Avg Score", style="green")
    table.add_column("Status", style="yellow")

    for interview in manifest.get("interviews", []):
        interview_id = interview["id"]
        delivery_path = delivery_dir / f"{interview_id}.json"

        if not interview["stages"].get("analyzed"):
            table.add_row(interview_id, "-", "[dim]Skipped (not analyzed)[/dim]")
            results["skipped"] += 1
            continue

        if not delivery_path.exists():
            table.add_row(interview_id, "-", "[red]Delivery file not found[/red]")
            results["failed"] += 1
            continue

        try:
            delivery = read_json(delivery_path)
            delivery = add_scores_to_delivery(delivery, weights)
            write_json(delivery_path, delivery)

            scores = [s.get("composite_score", 0) for s in delivery.get("segments", [])]
            avg_score = sum(scores) / len(scores) if scores else 0

            table.add_row(
                interview_id,
                f"{avg_score:.2f}",
                "[green]✓ Scored[/green]",
            )
            results["scored"] += 1

        except Exception as e:
            table.add_row(interview_id, "-", f"[red]Error: {e}[/red]")
            results["failed"] += 1

    if console:
        console.print(table)

    return results
