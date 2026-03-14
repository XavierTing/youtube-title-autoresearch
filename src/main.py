"""Main entrypoint — the experiment loop orchestrator.

Designed to be called hourly by GitHub Actions. Each invocation:
1. Checks if the current experiment has matured (72h of analytics data)
2. If ready: evaluates CTR, keeps or discards the title
3. Proposes a new title via Claude and updates the video
4. Logs everything to results.tsv and commits back to the repo
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from src.analyzer import (
    append_result,
    evaluate_experiment,
    get_best_ctr,
    get_best_title,
    get_current_experiment,
    get_experiment_history_summary,
    hours_remaining,
    init_results_file,
    is_data_ready,
    load_results,
    update_last_result,
)
from src.generator import propose_new_title
from src.youtube_api import (
    get_authenticated_services,
    get_ctr_data,
    get_date_range_for_experiment,
    get_video_info,
    update_video_title,
)


def commit_and_push_results() -> None:
    """Commit results.tsv and push to remote (for state persistence in CI)."""
    try:
        subprocess.run(["git", "add", "results.tsv"], check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if result.returncode != 0:  # There are staged changes
            subprocess.run(
                ["git", "commit", "-m", "Update experiment results"],
                check=True,
            )
            subprocess.run(["git", "push"], check=True)
            print("Results committed and pushed.")
        else:
            print("No changes to commit.")
    except subprocess.CalledProcessError as e:
        print(f"Warning: git commit/push failed: {e}")


def main() -> None:
    load_dotenv()

    video_id = os.environ.get("VIDEO_ID")
    if not video_id:
        print("ERROR: VIDEO_ID environment variable is required.")
        sys.exit(1)

    # Authenticate
    youtube_data, youtube_analytics = get_authenticated_services()

    # Initialize results file
    init_results_file()
    results = load_results()

    # Check if there's a running experiment
    current = get_current_experiment(results)

    if current is not None:
        if not is_data_ready(current):
            remaining = hours_remaining(current)
            print(
                f"Experiment still running: \"{current['title']}\"\n"
                f"  {remaining:.1f}h remaining until data is ready. Exiting."
            )
            return

        # --- Evaluate the running experiment ---
        print(f"Evaluating experiment: \"{current['title']}\"")
        start_date, end_date = get_date_range_for_experiment(
            current["timestamp"]
        )
        ctr_data = get_ctr_data(
            youtube_analytics, video_id, start_date, end_date
        )

        baseline_ctr = get_best_ctr(results)
        status = evaluate_experiment(ctr_data["ctr"], baseline_ctr)

        # Update the running experiment with results
        update_last_result({
            "impressions": ctr_data["impressions"],
            "ctr": ctr_data["ctr"],
            "status": status,
        })

        ctr_pct = ctr_data["ctr"] * 100
        print(
            f"  CTR: {ctr_pct:.2f}% | Impressions: {ctr_data['impressions']} | "
            f"Status: {status.upper()}"
        )

        if status == "discard":
            # Revert to best-known title
            best_title = get_best_title(results)
            if best_title:
                print(f"  Reverting to best title: \"{best_title}\"")
                update_video_title(youtube_data, video_id, best_title)

        # Reload results after update
        results = load_results()

    # --- Handle first run: record baseline ---
    if not results:
        print("First run — recording baseline title and CTR.")
        video_info = get_video_info(youtube_data, video_id)
        append_result({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "video_id": video_id,
            "title": video_info["title"],
            "impressions": 0,
            "ctr": 0.0,
            "status": "running",
            "description": "baseline — original title",
        })
        print(f"  Baseline title: \"{video_info['title']}\"")
        print("  Waiting 72h for analytics data before first evaluation.")
        # Git commit/push is handled by the GitHub Actions workflow step
        return

    # --- Propose and set a new title ---
    print("Proposing new title via Claude...")
    video_info = get_video_info(youtube_data, video_id)
    history_summary = get_experiment_history_summary(results)
    best_title = get_best_title(results)
    best_ctr = get_best_ctr(results)

    new_title, strategy = propose_new_title(
        experiment_history=history_summary,
        current_best_title=best_title,
        current_best_ctr=best_ctr,
        video_metadata=video_info,
    )

    print(f"  New title: \"{new_title}\"")
    print(f"  Strategy: {strategy}")

    # Update YouTube
    update_video_title(youtube_data, video_id, new_title)
    print("  Title updated on YouTube.")

    # Log the new experiment
    append_result({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "video_id": video_id,
        "title": new_title,
        "impressions": 0,
        "ctr": 0.0,
        "status": "running",
        "description": strategy,
    })

    # Git commit/push is handled by the GitHub Actions workflow step
    print("Done. Next check in 1 hour.")


if __name__ == "__main__":
    main()
