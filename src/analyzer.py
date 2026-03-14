"""Experiment results tracking and evaluation logic."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

RESULTS_FILE = "results.tsv"
EVALUATION_HOURS = 24  # Hours to wait before evaluating an experiment

FIELDNAMES = [
    "timestamp",
    "video_id",
    "title",
    "impressions",
    "ctr",
    "status",
    "description",
]


def init_results_file(filepath: str = RESULTS_FILE) -> None:
    """Create results.tsv with header if it doesn't exist."""
    if not os.path.exists(filepath):
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter="\t")
            writer.writeheader()


def load_results(filepath: str = RESULTS_FILE) -> list[dict]:
    """Parse results.tsv into a list of experiment records."""
    if not os.path.exists(filepath):
        return []

    with open(filepath, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        results = []
        for row in reader:
            row["impressions"] = int(row["impressions"])
            row["ctr"] = float(row["ctr"])
            results.append(row)
        return results


def get_current_experiment(results: list[dict]) -> dict | None:
    """Return the last experiment if it's still running, else None."""
    if not results:
        return None
    last = results[-1]
    if last["status"] == "running":
        return last
    return None


def is_data_ready(experiment: dict, min_hours: int = EVALUATION_HOURS) -> bool:
    """Check if enough time has passed for YouTube Analytics data."""
    start = datetime.fromisoformat(experiment["timestamp"])
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    elapsed_hours = (now - start).total_seconds() / 3600
    return elapsed_hours >= min_hours


def hours_remaining(experiment: dict, min_hours: int = EVALUATION_HOURS) -> float:
    """Hours until experiment data is ready."""
    start = datetime.fromisoformat(experiment["timestamp"])
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    elapsed = (now - start).total_seconds() / 3600
    return max(0.0, min_hours - elapsed)


def evaluate_experiment(current_ctr: float, baseline_ctr: float) -> str:
    """Return 'keep' if CTR improved, 'discard' otherwise."""
    if current_ctr > baseline_ctr:
        return "keep"
    return "discard"


def get_best_result(results: list[dict]) -> dict | None:
    """Find the experiment with the highest CTR among 'keep' and 'baseline' entries."""
    evaluated = [r for r in results if r["status"] in ("keep", "baseline")]
    if not evaluated:
        return None
    return max(evaluated, key=lambda r: r["ctr"])


def get_best_title(results: list[dict]) -> str | None:
    """Return the best-performing title."""
    best = get_best_result(results)
    return best["title"] if best else None


def get_best_ctr(results: list[dict]) -> float:
    """Return the best CTR achieved so far."""
    best = get_best_result(results)
    return best["ctr"] if best else 0.0


def get_experiment_history_summary(results: list[dict]) -> str:
    """Format experiment history as a text summary for the Claude prompt."""
    if not results:
        return "No experiments yet."

    lines = []
    for i, r in enumerate(results, 1):
        ctr_pct = f"{r['ctr'] * 100:.2f}%" if r["ctr"] > 0 else "pending"
        lines.append(
            f"#{i} | Title: \"{r['title']}\" | CTR: {ctr_pct} | "
            f"Impressions: {r['impressions']} | Status: {r['status']} | "
            f"Strategy: {r['description']}"
        )
    return "\n".join(lines)


def append_result(record: dict, filepath: str = RESULTS_FILE) -> None:
    """Append a new experiment record to results.tsv."""
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writerow(record)


def update_last_result(
    updates: dict, filepath: str = RESULTS_FILE
) -> None:
    """Update the last row in results.tsv with new values."""
    results = load_results(filepath)
    if not results:
        return

    results[-1].update(updates)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(results)
